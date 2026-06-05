import os
import json
import numpy as np
import pandas as pd
import yfinance as yf
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler
from ml_model import StockPredictorLSTM

# Hyperparameters
SEQ_LENGTH = 30 # Use 30 days of history to predict next day
BATCH_SIZE = 64
EPOCHS = 10
LEARNING_RATE = 0.001
HIDDEN_DIM = 64
NUM_LAYERS = 2
OUTPUT_DIM = 1 # Predict next day return or scaled price

def load_sentiment():
    if os.path.exists("sentiment_data.json"):
        with open("sentiment_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def prepare_data():
    with open("halal_universe.json", "r", encoding="utf-8") as f:
        universe = json.load(f)
        
    sentiment_data = load_sentiment()
    
    all_x = []
    all_y = []
    
    print("Fetching historical data for training...")
    count = 0
    symbols = list(universe.keys())
    
    # Just train on a subset to keep it fast for now
    for symbol in symbols[:50]:
        try:
            df = yf.download(symbol, period="2y", progress=False)
            if df.empty or len(df) < SEQ_LENGTH + 1:
                continue
                
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            df.ffill(inplace=True)
            df.bfill(inplace=True)
            
            # Sentiment Score
            sym_sent = sentiment_data.get(symbol, {}).get("score", 0.0)
            df['Sentiment'] = sym_sent
            
            scaler = MinMaxScaler()
            scaled_data = scaler.fit_transform(df.values)
            
            for i in range(len(scaled_data) - SEQ_LENGTH):
                x = scaled_data[i:i+SEQ_LENGTH]
                # Predict the next day's close price (column index 3)
                y = scaled_data[i+SEQ_LENGTH, 3] 
                
                all_x.append(x)
                all_y.append(y)
                
            count += 1
            if count % 10 == 0:
                print(f"Processed {count} symbols...")
                
        except Exception as e:
            pass
            
    print(f"Total sequences generated: {len(all_x)}")
    if len(all_x) == 0:
        return None, None
        
    X = np.array(all_x)
    y = np.array(all_y)
    
    # Train test split (80/20) - Sequential split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.float32).unsqueeze(1))
    test_dataset = TensorDataset(torch.tensor(X_test, dtype=torch.float32), torch.tensor(y_test, dtype=torch.float32).unsqueeze(1))
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    return train_loader, test_loader

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    train_loader, test_loader = prepare_data()
    if not train_loader:
        print("Not enough data to train.")
        return
        
    # Input dim: Open, High, Low, Close, Volume, Sentiment = 6 features
    model = StockPredictorLSTM(input_dim=6, hidden_dim=HIDDEN_DIM, num_layers=NUM_LAYERS, output_dim=OUTPUT_DIM).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    print("Starting training...")
    best_loss = float('inf')
    
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * batch_x.size(0)
            
        train_loss /= len(train_loader.dataset)
        
        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item() * batch_x.size(0)
                
        val_loss /= len(test_loader.dataset)
        
        print(f"Epoch {epoch+1}/{EPOCHS} - Train Loss: {train_loss:.4f} - Val Loss: {val_loss:.4f}")
        
        if val_loss < best_loss:
            best_loss = val_loss
            torch.save(model.state_dict(), "best_model.pth")
            print("  --> Saved new best model")
            
    print("Training complete!")

if __name__ == "__main__":
    main()
