import json
import time
import yfinance as yf
import os

def main():
    print("Starting Halal Metrics Ingestion (Safe Mode)...")
    start_time = time.time()
    
    universe_path = "halal_universe.json"
    if not os.path.exists(universe_path):
        print(f"Error: {universe_path} not found.")
        return
        
    with open(universe_path, "r", encoding="utf-8") as f:
        universe = json.load(f)
        
    print(f"Loaded {len(universe)} symbols from universe.")
    
    results = {}
    count = 0
    
    # Process sequentially to avoid Yahoo Finance 401 Unauthorized / Crumb errors
    for symbol, name in universe.items():
        count += 1
        if count % 50 == 0:
            print(f"Processed {count}/{len(universe)}... (Success: {len(results)})")
            
        try:
            t = yf.Ticker(symbol)
            info = t.info
            fast = t.fast_info
            
            price = fast.last_price if hasattr(fast, 'last_price') else info.get('currentPrice', 0.0)
            mcap = fast.market_cap if hasattr(fast, 'market_cap') else info.get('marketCap', 0.0)
            
            if price is not None and price > 0:
                results[symbol] = {
                    "symbol": symbol,
                    "name": name,
                    "price": price,
                    "market_cap": mcap,
                    "beta": info.get("beta", 1.0) if info.get("beta") is not None else 1.0,
                    "pe": info.get("trailingPE", 0.0) if info.get("trailingPE") is not None else 0.0,
                    "sector": info.get("sector", "Unknown"),
                    "industry": info.get("industry", "Unknown"),
                    "dividend_yield": info.get("dividendYield", 0.0) if info.get("dividendYield") is not None else 0.0
                }
        except Exception as e:
            # Ignore delisted/missing symbols silently to avoid console spam
            pass
            
        # Add a small delay to respect rate limits
        time.sleep(0.1)

    end_time = time.time()
    print(f"Finished processing in {end_time - start_time:.2f} seconds.")
    print(f"Successfully fetched data for {len(results)} / {len(universe)} symbols.")
    
    with open("halal_metrics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print("Saved to halal_metrics.json")

if __name__ == "__main__":
    main()
