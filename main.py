from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import pandas as pd
import yfinance as yf
import numpy as np

app = FastAPI(title="JarNox Stock Intelligence")

# SQLite setup
conn = sqlite3.connect("stock_data.db", check_same_thread=False)
conn.row_factory = sqlite3.Row

@app.on_event("startup")
def startup_event():
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.commit()

# Use proper uppercase .NS symbols
COMPANIES = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Ltd"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services"},
    {"symbol": "INFY.NS", "name": "Infosys Limited"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Ltd"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Ltd"},
    {"symbol": "SBIN.NS", "name": "State Bank of India"},
]

def normalize_symbol(symbol: str) -> str:
    """Ensure symbol is uppercase and ends with .NS"""
    symbol = symbol.upper().strip()
    if not symbol.endswith(".NS"):
        symbol += ".NS"
    return symbol

def get_or_fetch_data(symbol: str):
    symbol = normalize_symbol(symbol)
    
    cursor = conn.cursor()
    
    # Check if we already have data
    cursor.execute("SELECT COUNT(*) as cnt FROM stock_data WHERE symbol=?", (symbol,))
    count = cursor.fetchone()["cnt"]
    
    if count == 0:
        print(f"📥 Fetching data for {symbol} using yfinance...")
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="2y", interval="1d")
            
            if df.empty:
                raise Exception(f"No data returned for {symbol}")
            
            # Clean data
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            df = df.fillna(0)
            
            records = []
            for date, row in df.iterrows():
                records.append((
                    symbol,
                    date.strftime("%Y-%m-%d"),
                    float(row.get("Open", 0)),
                    float(row.get("High", 0)),
                    float(row.get("Low", 0)),
                    float(row.get("Close", 0)),
                    int(row.get("Volume", 0))
                ))
            
            if records:
                cursor.executemany("""
                    INSERT OR IGNORE INTO stock_data 
                    (symbol, date, open, high, low, close, volume) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, records)
                conn.commit()
                print(f"✅ Saved {len(records)} records for {symbol}")
            else:
                print(f"⚠️ No valid records for {symbol}")
                
        except Exception as e:
            print(f"❌ Failed to fetch {symbol}: {e}")
            raise HTTPException(status_code=404, detail=f"Could not fetch data for {symbol}. Try again later.")
    
    # Fetch from database
    cursor.execute("""
        SELECT date, open, high, low, close, volume 
        FROM stock_data 
        WHERE symbol=? 
        ORDER BY date ASC
    """, (symbol,))
    rows = cursor.fetchall()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"No cached data for {symbol}")
    
    df = pd.DataFrame([dict(row) for row in rows])
    df["date"] = pd.to_datetime(df["date"])
    return df

# Endpoints remain mostly same (just using normalize_symbol)
@app.get("/companies")
def get_companies():
    return COMPANIES

@app.get("/data/{symbol}")
def get_stock_data(symbol: str):
    df = get_or_fetch_data(symbol)
    
    data_df = df.tail(730).copy()   # up to 2 years
    
    data_df["daily_return"] = ((data_df["close"] - data_df["open"]) / data_df["open"].replace(0, np.nan)) * 100
    data_df["ma7"] = data_df["close"].rolling(window=7, min_periods=1).mean()
    
    data_df = data_df.replace({np.nan: None})
    
    data_list = data_df.to_dict(orient="records")
    for item in data_list:
        item["date"] = item["date"].strftime("%Y-%m-%d")
    
    return {"symbol": symbol, "data": data_list}

@app.get("/summary/{symbol}")
def get_summary(symbol: str):
    df = get_or_fetch_data(symbol)
    recent = df.tail(365) if len(df) > 365 else df
    
    return {
        "symbol": symbol,
        "52_week_high": round(float(recent["high"].max() or 0), 2),
        "52_week_low": round(float(recent["low"].min() or 0), 2),
        "average_close": round(float(recent["close"].mean() or 0), 2),
        "last_updated": df["date"].max().strftime("%Y-%m-%d") if not df.empty else ""
    }

@app.get("/compare")
def compare_stocks(symbol1: str, symbol2: str):
    df1 = get_or_fetch_data(symbol1).tail(30)["close"].dropna()
    df2 = get_or_fetch_data(symbol2).tail(30)["close"].dropna()
    correlation = float(df1.corr(df2)) if len(df1) == len(df2) and len(df1) > 1 else 0.0
    return {"symbol1": symbol1, "symbol2": symbol2, "correlation": round(correlation, 4)}

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: static/index.html not found</h1>"

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)