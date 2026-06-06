import os
import json
import time
from datetime import datetime, timedelta
import finnhub
from transformers import pipeline

def load_universe():
    try:
        with open("halal_universe.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading universe: {e}")
        return {}

def main():
    print("Starting Finnhub Sentiment Ingestion...")
    
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        print("WARNING: FINNHUB_API_KEY environment variable not set. Please set it to run sentiment ingestion.")
        # We can still proceed if the finnhub client works without it for some reason, but usually it requires one.
    
    try:
        finnhub_client = finnhub.Client(api_key=api_key or "YOUR_API_KEY")
    except Exception as e:
        print(f"Failed to initialize Finnhub client: {e}")
        return
        
    print("Loading FinBERT sentiment analysis pipeline...")
    # Using FinBERT for financial sentiment analysis
    try:
        sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")
    except Exception as e:
        print(f"Failed to load FinBERT model: {e}")
        return

    universe = load_universe()
    if not universe:
        return
        
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    sentiment_data = {}
    
    # Load existing to avoid rewriting everything if we just want to update
    if os.path.exists("sentiment_data.json"):
        with open("sentiment_data.json", "r", encoding="utf-8") as f:
            try:
                sentiment_data = json.load(f)
            except json.JSONDecodeError:
                pass

    print(f"Fetching news from {start_str} to {end_str}")
    count = 0
    
    for symbol in universe.keys():
        # Finnhub may use different ticker formats, especially for Indian stocks. 
        # Typically Finnhub requires '.NS' or '.BO' removed, or sometimes it doesn't support them on free tier.
        # Actually, Finnhub free tier supports US stocks mostly, but some global. Let's try as is, or strip '.NS'.
        query_symbol = symbol.replace(".NS", "").replace(".BO", "")
        
        print(f"Fetching news for {query_symbol}...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                news = finnhub_client.company_news(query_symbol, _from=start_str, to=end_str)
                
                if not news:
                    sentiment_data[symbol] = {"score": 0.0, "news_count": 0, "last_updated": end_date.isoformat()}
                    break
                    
                total_score = 0.0
                valid_news = 0
                
                for article in news:
                    text = article.get('headline', '') + ". " + article.get('summary', '')
                    if not text.strip() or len(text.strip()) < 10:
                        continue
                        
                    # Truncate text to avoid model length errors
                    text = text[:512]
                    
                    result = sentiment_pipeline(text)[0]
                    label = result['label']
                    
                    if label == 'positive':
                        score = 1.0
                    elif label == 'negative':
                        score = -1.0
                    else:
                        score = 0.0
                        
                    total_score += score
                    valid_news += 1
                    
                avg_score = total_score / valid_news if valid_news > 0 else 0.0
                
                sentiment_data[symbol] = {
                    "score": avg_score,
                    "news_count": valid_news,
                    "last_updated": end_date.isoformat()
                }
                break # Success, break out of retry loop
                
            except Exception as e:
                print(f"Error fetching news for {symbol}: {e}")
                if "429" in str(e) or "limit" in str(e).lower():
                    if attempt < max_retries - 1:
                        print("Rate limit reached. Sleeping for 60 seconds before retrying...")
                        time.sleep(60)
                    else:
                        print("Max retries reached for this symbol.")
                else:
                    break # Break on other errors
            
        count += 1
        if count % 10 == 0:
            print(f"Processed {count}/{len(universe)} stocks.")
            
        # Finnhub free tier limit is usually 30 calls per minute
        time.sleep(2.1)

    with open("sentiment_data.json", "w", encoding="utf-8") as f:
        json.dump(sentiment_data, f, indent=4)
        
    print("Sentiment ingestion complete. Saved to sentiment_data.json")

if __name__ == "__main__":
    main()
