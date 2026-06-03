import json
import time
import yfinance as yf
import os
import random

def main():
    print("Starting Halal Metrics Ingestion (Incremental Safe Mode)...")
    
    universe_path = "halal_universe.json"
    metrics_path = "halal_metrics.json"
    
    if not os.path.exists(universe_path):
        print(f"Error: {universe_path} not found.")
        return
        
    with open(universe_path, "r", encoding="utf-8") as f:
        universe = json.load(f)
        
    print(f"Loaded {len(universe)} symbols from universe.")
    
    metrics = {}
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            try:
                metrics = json.load(f)
            except json.JSONDecodeError:
                metrics = {}
                
    print(f"Found {len(metrics)} symbols already in metrics database.")
    
    # Find symbols that haven't been successfully processed or explicitly marked invalid
    pending_symbols = []
    for sym in universe.keys():
        if sym not in metrics:
            pending_symbols.append(sym)
        elif "error" in metrics[sym] and metrics[sym]["error"] != "invalid":
            # Retry if it was a transient error (like a firewall block)
            pending_symbols.append(sym)
            
    print(f"Remaining symbols to fetch: {len(pending_symbols)}")
    
    # Limit to 350 to absolutely guarantee we don't hit the 500-request Yahoo Firewall
    # Since this runs daily, it will chunk through the database perfectly!
    batch_size = min(350, len(pending_symbols))
    batch_symbols = pending_symbols[:batch_size]
    
    print(f"Processing batch of {batch_size} symbols...")
    
    count = 0
    success_count = 0
    
    for symbol in batch_symbols:
        name = universe[symbol]
        count += 1
        if count % 25 == 0:
            print(f"Processed {count}/{batch_size} in this batch... (Success: {success_count})")
            
        try:
            t = yf.Ticker(symbol)
            info = t.info
            fast = t.fast_info
            
            price = fast.last_price if hasattr(fast, 'last_price') else info.get('currentPrice', 0.0)
            mcap = fast.market_cap if hasattr(fast, 'market_cap') else info.get('marketCap', 0.0)
            
            if price is not None and price > 0:
                metrics[symbol] = {
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
                success_count += 1
            else:
                # Genuinely delisted or no data available
                metrics[symbol] = {"symbol": symbol, "error": "invalid"}
        except Exception as e:
            err_msg = str(e).lower()
            if "delisted" in err_msg or "not found" in err_msg or "404" in err_msg:
                metrics[symbol] = {"symbol": symbol, "error": "invalid"}
            else:
                # Transient error (rate limit, timeout, 401)
                metrics[symbol] = {"symbol": symbol, "error": "transient_failed"}
                
        # Random sleep between 0.2 and 0.6 seconds to mimic human behavior
        time.sleep(random.uniform(0.2, 0.6))

    # Save the updated database
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)
        
    print(f"Batch complete. Total metrics database size: {len(metrics)}")
    print("Saved to halal_metrics.json")

if __name__ == "__main__":
    main()
