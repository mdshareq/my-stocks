import json
import time
import concurrent.futures
import yfinance as yf
import os

def fetch_data(symbol, name):
    try:
        t = yf.Ticker(symbol)
        info = t.info
        fast = t.fast_info
        
        # Get basic info safely
        price = fast.last_price if hasattr(fast, 'last_price') else info.get('currentPrice', 0.0)
        mcap = fast.market_cap if hasattr(fast, 'market_cap') else info.get('marketCap', 0.0)
        
        if price is None or price <= 0:
            return {"symbol": symbol, "error": "No price data"}
            
        return {
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
        return {"symbol": symbol, "error": str(e)}

def main():
    print("Starting Halal Metrics Ingestion...")
    start_time = time.time()
    
    universe_path = "halal_universe.json"
    if not os.path.exists(universe_path):
        print(f"Error: {universe_path} not found.")
        return
        
    with open(universe_path, "r", encoding="utf-8") as f:
        universe = json.load(f)
        
    print(f"Loaded {len(universe)} symbols from universe.")
    
    results = {}
    
    # We use a ThreadPoolExecutor to speed up fetching
    # Max workers set to 20 to avoid overwhelming Yahoo Finance too fast
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_data, sym, name): sym for sym, name in universe.items()}
        
        count = 0
        for future in concurrent.futures.as_completed(futures):
            count += 1
            if count % 100 == 0:
                print(f"Processed {count}/{len(universe)}...")
                
            res = future.result()
            if "error" not in res:
                results[res["symbol"]] = res

    end_time = time.time()
    print(f"Finished processing in {end_time - start_time:.2f} seconds.")
    print(f"Successfully fetched data for {len(results)} / {len(universe)} symbols.")
    
    with open("halal_metrics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print("Saved to halal_metrics.json")

if __name__ == "__main__":
    main()
