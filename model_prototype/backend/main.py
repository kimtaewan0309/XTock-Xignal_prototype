import os
import datetime as dt
from typing import Optional, List
from contextlib import asynccontextmanager
import json
import httpx
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from pymongo import MongoClient
import random

from search_service import search_engine

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMPACT_TWEETS_PATH = os.path.join(BASE_DIR, "impact_tweets.json")
SP500_HANDLES_PATH = os.path.join(BASE_DIR, "sp500_handles.json")


IMPACT_TWEETS = []
SP500_HANDLE = {}

if os.path.exists(IMPACT_TWEETS_PATH):
    with open(IMPACT_TWEETS_PATH, 'r', encoding='utf-8') as f:
        IMPACT_TWEETS = json.load(f)
    print(f"[Education Mode] Loaded {len(IMPACT_TWEETS)} historical impact tweets.")
else:
    print("Warning: impact_tweets.json not found!")


if os.path.exists(SP500_HANDLES_PATH):
    with open(SP500_HANDLES_PATH, 'r', encoding = 'utf-8') as f:
        SP500_HANDLES = json.load(f)
    print(f"Loaded {len(SP500_HANDLES_PATH)} S&P 500 X Handles.")
else:
    print("Warning: sp500_handles.json not found")
BEARER_TOKEN = os.getenv("BEARER_TOKEN") or os.getenv("TWEETER_BEARER_TOKEN")
if not BEARER_TOKEN:
    print("Warning: BEARER_TOKEN is not set in .env")
    
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_NAME = os.getenv("MONGODB_NAME", "xtock")
MONGODB_COLLECTION_LOGS = "search_history"

mongo_client = None
search_log_col = None

if MONGODB_URI:
    try:
        mongo_client = MongoClient(MONGODB_URI)
        db = mongo_client[MONGODB_NAME]
        search_log_col = db[MONGODB_COLLECTION_LOGS]
        print("[DB] MongoDB Connected for Logging.")
    except Exception as e:
        print(f"[DB] Connection Failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("XTock-Xignal Backend Starting")
    yield
    print("XTock-Xignal Backend Shutting Down")
    if mongo_client:
        mongo_client.close()
    
app = FastAPI(
    title = "Xtock-Xignal Backend",
    description = "Backend API for Xtock-Xignal Service",
    version = "1.0.0",
    lifesapan = lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins =["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TweetImpactRequest(BaseModel):
    symbol: str
    tweet_created_at: str
    tweet_id: str
    tweet_text: str
    
class SearchRequest(BaseModel):
    text: str

# ===========================================
# X API 호출 함수
# 과거 7일간의 트윗만 가져올 수 있기 때문에 모델 성능 및 웹 페이지 구성때는 잠시 주석 처리
async def call_x_recent_search(query: str, max_results: int = 10, next_token: Optional[str] = None):
    if not BEARER_TOKEN:
        raise HTTPException(status_code = 500, detail = "X API Token missing")
    
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

    final_query = f"({query}) -is:retweet"

    params = {
        "query": final_query,
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,public_metrics,lang",
        "expansions": "author_id",
        "user.fields": "name,username"
    }
    if next_token:
        params["next_token"] = next_token

    # X API 호출 (기본 주소 or 대체 주소)
    base_url = "https://api.x.com/2/tweets/search/recent"
    # base_url = "https://api.twitter.com/2/tweets/search/recent" # 필요시 변경

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(base_url, headers=headers, params=params)

    if resp.status_code == 200:
        data = resp.json()
        tweets = data.get("data", [])
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

        result = []
        for t in tweets:
            author_info = users.get(t["author_id"], {})
            result.append({
                "text": t["text"],
                "author": author_info.get("name", "Unknown"),
                "username": author_info.get("username", ""),
                "date": t["created_at"].split("T")[0],
                "created_at": t["created_at"]
            })
        return result
    else:
        print(f" XAPI Error {resp.status_code} - {resp.text}")
        return []
    
def get_stock_price_history(symbol: str, start_date, end_date):
    print(f"[YFinance] Fetching {symbol}: {start_date} - {end_date}")
    try:
        df = yf.download(
            symbol,
            start = start_date.strftime("%Y-%m-%d"),
            end = end_date.strftime("%Y-%m-%d"),
            interval = "1d",
            progress = False,
            auto_adjust = False,
            multi_level_index = False
        )

        if df.empty: return []

        df = df.reset_index()
        if 'Date' in df.columns: date_col = 'Date'
        elif 'date' in df.columns: date_col = 'date'
        else: date_col = df.columns[0]

        records = []
        for _, row in df.iterrows():
            records.append({
                "date": pd.to_datetime(row[date_col]).strftime("%Y-%m-%d"),
                "price": float(row['Close'])
            })
            return records
    except Exception as e:
        print(f"[YFinance] Error: {e}")
        return []

# def infer_base_date_from_tweet_created_at(created_at: str) -> dt.date:
#     """트윗 작성 시간(ISO8601) -> 날짜(Date) 변환"""
#     s = created_at.strip()
#     if s.endswith("Z"):
#         s = s[:-1] + "+00:00"
#     if len(s) == 19:
#         s += "+00:00"
    
#     return dt.datetime.fromisoformat(s).date()

# def fetch_price_history(symbol: str, start: str, end: str, interval: str = "1d"):
#     """yfinance 주가 조회"""
#     try:
#         df = yf.download(
#             symbol, start=start, end=end, interval=interval,
#             group_by="column", auto_adjust=False, progress=False
#         )
#         if df.empty:
#             return []

#         df = df.reset_index()
#         date_col = df.columns[0]
#         records = []
#         for _, row in df.iterrows():
#             records.append({
#                 "date": str(row[date_col])[:10],
#                 "open": float(row["Open"]),
#                 "high": float(row["High"]),
#                 "low": float(row["Low"]),
#                 "close": float(row["Close"]),
#                 "volume": int(row["Volume"]),
#             })
#         return records
#     except Exception as e:
#         print(f"Error fetching price for {symbol}: {e}")
#         return []

# def calculate_next_day_return(symbol: str, date_str: str):
#     """특정 날짜 기준 익일 수익률 계산"""
#     try:
#         base_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
        
#         # 앞뒤 7일치 데이터 가져오기 (주말/휴일 고려)
#         start = base_date - dt.timedelta(days=7)
#         end = base_date + dt.timedelta(days=7)
        
#         df = yf.download(
#             symbol, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
#             interval="1d", group_by="column", auto_adjust=False, progress=False
#         )

#         if df.empty or len(df) < 2:
#             return None

#         df = df.reset_index()
#         date_col = df.columns[0]
#         # 날짜 타입 통일
#         df[date_col] = pd.to_datetime(df[date_col]).dt.date
#         df = df.sort_values(date_col).reset_index(drop=True)

#         # 기준일(base_date) 이하인 날짜 중 가장 최신 날짜 찾기
#         candidates = df[df[date_col] <= base_date]
#         if candidates.empty:
#             return None
            
#         base_idx = candidates.index[-1]
#         next_idx = base_idx + 1
        
#         if next_idx >= len(df):
#             return None

#         base_row = df.loc[base_idx]
#         next_row = df.loc[next_idx]

#         base_close = float(base_row["Close"])
#         next_close = float(next_row["Close"])
        
#         # 수익률 계산 ((다음날 - 오늘) / 오늘 * 100)
#         next_return = (next_close - base_close) / base_close * 100.0

#         return {
#             "symbol": symbol,
#             "base_date": str(base_row[date_col]),
#             "base_close": base_close,
#             "next_date": str(next_row[date_col]),
#             "next_close": next_close,
#             "next_day_return": next_return,
#         }
#     except Exception as e:
#         print(f"Error calculating return for {symbol}: {e}")
#         return None
# # ===========================================

# def find_impact_candidates(query: str):
#     """
#     사용자 검색어와 연관된 과거 사건(Case Study) 후보군을 모두 찾습니다.
#     """
#     query = query.lower().strip()
#     candidates = []
    
#     for tweet in IMPACT_TWEETS:
#         # 심볼, 내용, 설명, 작성자 어디든 키워드가 있으면 매칭
#         if (query in tweet['symbol'].lower() or 
#             query in tweet['text'].lower() or 
#             query in tweet['note'].lower() or 
#             query in tweet['author_id'].lower()):
#             candidates.append(tweet)
            
#     return candidates

# def fetch_historical_chart_data(symbol: str, tweet_date_str: str):
#     """
#     트윗 발생일 기준 전후 15일치 주가 데이터를 가져오고, 수익률을 계산합니다.
#     """
#     # UTC 'Z' 제거 및 날짜 변환
#     tweet_date_str = tweet_date_str.replace("Z", "")
#     try:
#         tweet_date = dt.datetime.fromisoformat(tweet_date_str).date()
#     except ValueError:
#         tweet_date = dt.datetime.strptime(tweet_date_str, "%Y-%m-%dT%H:%M:%S").date()
    
#     # 앞뒤 15일 (약 1달) 데이터 조회
#     start_date = tweet_date - dt.timedelta(days=15)
#     end_date = tweet_date + dt.timedelta(days=15)
    
#     print(f"Fetching History for {symbol}: {start_date} ~ {end_date}")

#     try:
#         df = yf.download(
#             symbol, 
#             start=start_date.strftime("%Y-%m-%d"), 
#             end=end_date.strftime("%Y-%m-%d"),
#             interval="1d", 
#             progress=False,
#             auto_adjust=False,
#             multi_level_index=False
#         )
#     except Exception as e:
#         print(f"yfinance error: {e}")
#         return [], 0, 0.0

#     if df.empty:
#         return [], 0, 0.0

#     df = df.reset_index()
#     # 컬럼명 통일 (Date, Close)
#     df.columns = [c.capitalize() for c in df.columns] 
    
#     records = []
    
#     # 1. 데이터 리스트 변환
#     for _, row in df.iterrows():
#         if 'Date' not in row: continue
#         d_val = pd.to_datetime(row['Date']).strftime("%Y-%m-%d")
#         close_val = float(row["Close"])
#         records.append({"date": d_val, "price": close_val})

#     # 2. 트윗 시점 인덱스 찾기
#     post_index = -1
#     target_date_str = tweet_date.strftime("%Y-%m-%d")
    
#     for i, rec in enumerate(records):
#         if rec["date"] >= target_date_str:
#             post_index = i
#             break
            
#     if post_index == -1: post_index = len(records) // 2

#     # 3. 수익률 계산 (Impact Return)
#     # 트윗 발생 전날(T-1) vs 발생 다음날(T+1) 비교
#     impact_return = 0.0
#     if post_index > 0 and post_index < len(records) - 1:
#         prev_price = records[post_index - 1]['price'] # 하루 전
#         next_price = records[post_index + 1]['price'] # 하루 후
#         if prev_price > 0:
#             impact_return = ((next_price - prev_price) / prev_price) * 100.0

#     return records, post_index, impact_return

# ==========================================
# [API 엔드포인트]
# ==========================================

# ==========================================
# [API 1] 최근 기업 근황 (Recent Status) - 실시간 X API 사용
# ==========================================

@app.post("/api/recent-status")
async def get_recent_status(payload: SearchRequest):
    query = payload.text.upper().strip()

    if query in SP500_HANDLES:
        twitter_query = SP500_HANDLES[query]
        print(f"[Recent] Found Official Hanlde: {twitter_query}")
    else:
        twitter_query = f"${query} or {query}"
        print(f"[Recent] No Handle for {query}. Using keyword: {twitter_query}")

    tweets = await call_x_recent_search(twitter_query, max_results = 10)

    end_date = dt.datetime.now()
    start_date = end_date - dt.timedelta(days = 30)

    stock_data_full = get_stock_price_history(query, start_date, end_date)
    stock_data = stock_data_full[-20:]

    return {
        "found": True,
        "symbol": query,
        "tweets": tweets,
        "stock_data": stock_data
    }

@app.post("/api/historical-impact")
def get_historical_impact(payload: SearchRequest):
    query = payload.text.lower().strip()
    print(f"[History] Analyzing: {query}")

    candidates = []
    for tweet in IMPACT_TWEETS:
        if (query in tweet['symbol'].lower() or
            query in tweet['text'].lower() or
            query in tweet['note'].lower() or
            query in tweet['author_id'].lower()):
            candidates.append(tweet)

    if not candidates:
        return {"found": False, "msg": "관련된 과거 분석 사례가 없습니다."}
    
    event = random.choice(candidates)

    event_date = dt.datetime.fromisoformat(event['created_at'].replace("Z", ""))
    start_date = event_date - dt.timedelta(days = 15)
    end_date = event_date + dt.timedelta(days = 15)

    stock_data = get_stock_price_history(event["symbol"], start_date, end_date)

    target_date_str = event_date.strftime("%Y-%m-%d")
    post_index = -1
    for i, r in enumerate(stock_data):
        if r["date"] >= target_date_str:
            post_indez = i
            break
    if post_index == -1: post_index = len(stock_data) // 2

    impact_return = 0.0
    if 0 < post_index < len(stock_data) - 1:
        prev = stock_data[post_index-1]['price']
        next = stock_data[post_index+1]['price']
        if prev > 0:
            impoact_return  = ((next - prev) / prev) * 100.0

    if search_log_col is not None:
        try:
            search_log_col.inset_one({
                "type": "history",
                "query": query,
                "matched_event": event["id"],
                "impoact_return": impoact_return,
                "timestamp": dt.datetime.utcnoww()
            })
        except Exception as e:
            print(f"Log Save Error: {e}")

    return {
        "found": True,
        "event": event,
        "stock_data": stock_data,
        "post_index": post_index,
        "impact_return": impact_return
    }
# @app.get("/api/tweets")
# async def get_tweets(
#     q: str = Query(..., description="검색 쿼리 ($TSLA, Elon Musk 등)"),
#     max_results: int = Query(10, ge=10, le=100),
#     next_token: Optional[str] = Query(None),
# ):
#     """X(Twitter) 트윗 검색"""
#     data = await call_x_recent_search(q, max_results=max_results, next_token=next_token)
#     return {"query": q, "max_results": max_results, "raw": data}


# @app.get("/api/price")
# def get_price_history_endpoint(symbol: str, start: str, end: str):
#     """주가 히스토리 조회"""
#     data = fetch_price_history(symbol, start, end)
#     return {"symbol": symbol, "start": start, "end": end, "prices": data}


# @app.get("/api/next-return")
# def get_next_day_return(symbol: str, date: str):
#     """특정 날짜 기준 수익률 계산 조회"""
#     result = calculate_next_day_return(symbol, date)
#     if result is None:
#         raise HTTPException(status_code=404, detail="Not enough data to compute return")
#     return result


# @app.post("/api/tweet-impact")
# def tweet_impact(payload: TweetImpactRequest):
#     """
#     [ETL Pipeline] 트윗 정보 수신 -> 날짜 추출 -> 수익률 계산 -> DB 저장
#     """
#     # 1. 날짜 추출
#     try:
#         base_date = infer_base_date_from_tweet_created_at(payload.tweet_created_at)
#         base_date_str = base_date.strftime("%Y-%m-%d")
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

#     # 2. 수익률 계산
#     result = calculate_next_day_return(payload.symbol, base_date_str)
#     if result is None:
#         raise HTTPException(status_code=404, detail="Market data not found for calculation")

#     # 3. 데이터 조립 (MongoDB Schema)
#     doc = {
#         "tweet_id": payload.tweet_id,  # Unique Key
#         "symbol": payload.symbol,
#         "tweet_text": payload.tweet_text,
#         "tweet_created_at": payload.tweet_created_at,
        
#         # 계산된 주가 정보
#         "base_date": result["base_date"],
#         "base_close": result["base_close"],
#         "next_date": result["next_date"],
#         "next_close": result["next_close"],
#         "next_day_return": result["next_day_return"],
        
#         # 시스템 메타데이터
#         "created_at_system": dt.datetime.utcnow(),
        
#     }

#     # 4. MongoDB 저장 (Upsert)
#     if tweet_impact_col is not None:
#         try:
#             tweet_impact_col.update_one(
#                 {"tweet_id": payload.tweet_id}, 
#                 {"$set": doc}, 
#                 upsert=True
#             )
#             print(f"Saved impact data for {payload.symbol} (Tweet ID: {payload.tweet_id})")
#         except Exception as e:
#             print(f"MongoDB Save Error: {e}")
#     else:
#         print("MongoDB not connected! Data NOT saved.")

#     return doc


# @app.post("/api/match-company")
# def match_company(payload: SearchRequest):
#     """
#     [Main Scenario]
#     1. 사용자 검색어 수신
#     2. 연관된 과거 사건 후보군 탐색 -> 랜덤 1개 선택 (Dynamic Simulation)
#     3. 해당 시점의 주가 데이터 및 수익률 계산
#     4. 검색 로그 MongoDB 저장 (Data Accumulation)
#     5. 최종 결과 반환
#     """
#     query = payload.text.strip()
#     print(f"Analyzing Request: {query}")
    
#     # 1. 후보군 탐색
#     candidates = find_impact_candidates(query)
    
#     # 검색 결과가 없으면 랜덤으로 예시(Demo) 보여주기
#     if not candidates:
#         print("No match. Picking random sample.")
#         tweet = random.choice(IMPACT_TWEETS)
#         note_prefix = "[Demo: 검색어와 무관한 예시] "
#         is_exact_match = False
#     else:
#         tweet = random.choice(candidates) # 매번 다른 사례를 보여줌
#         note_prefix = ""
#         is_exact_match = True
    
#     print(f"Selected Case: {tweet['id']} ({tweet['symbol']})")
    
#     # 2. 주가 데이터 및 수익률 조회
#     stock_data, post_index, impact_return = fetch_historical_chart_data(tweet['symbol'], tweet['created_at'])
    
#     if not stock_data:
#         return {"matches": [], "note": "Failed to fetch price data."}

#     # 3. MongoDB 로그 저장 (Log History)
#     if search_log_col is not None:
#         try:
#             log_entry = {
#                 "query": query,
#                 "matched_symbol": tweet['symbol'],
#                 "matched_event_id": tweet['id'],
#                 "impact_return": impact_return,
#                 "is_exact_match": is_exact_match,
#                 "timestamp": dt.datetime.utcnow()
#             }
#             search_log_col.insert_one(log_entry)
#             print(f"Log saved to MongoDB.")
#         except Exception as e:
#             print(f"Log Save Error: {e}")

#     # 4. 결과 조립 (Frontend Compatible)
#     result = {
#         "symbol": tweet['symbol'],
#         "name": tweet['symbol'], # 필요 시 이름 매핑 가능
#         "score": 0.99, # 매칭 신뢰도
#         # note를 financial_summary에 넣어서 프론트엔드가 보여주게 함
#         "financial_summary": f"{note_prefix} 학습 포인트: {tweet['note']}",
        
#         # 트윗 정보
#         "tweet": {
#             "author_id": tweet['author_id'],
#             "text": tweet['text'],
#             "created_at": tweet['created_at'],
#             "impact_return": impact_return # 프론트엔드에서 색깔 표시용 등으로 사용 가능
#         },
        
#         # 차트 데이터
#         "stockData": stock_data,
#         "postIndex": post_index
#     }
    
#     return {
#         "input_text": query,
#         "matches": [result], 
#         "note": "Historical Impact Analysis Mode"
#     }

# 헬스체크
@app.get("/health")
def health_check():
    return {"status": "ok", "mongodb": mongo_client is not None}