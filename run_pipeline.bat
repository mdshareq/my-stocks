@echo off
echo ==========================================
echo Shareq Equities - Daily ML Pipeline Update
echo ==========================================

REM Set your Finnhub API Key here before running
set FINNHUB_API_KEY=your_api_key_here

echo [1/3] Ingesting Daily Halal Metrics...
python ingest_metrics.py

echo [2/3] Fetching Latest Sentiment & News...
python ingest_sentiment.py

echo [3/3] Re-training PyTorch LSTM Model...
python train_model.py

echo ==========================================
echo Pipeline Complete! Best model saved.
echo ==========================================
