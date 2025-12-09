from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import os
import torch
import sys

# 상수 파일 로드용
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from constants import ALIASES

app = FastAPI(title="XTock Search Engine", version="1.0")

# 1. 경로 및 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH_STATIC = os.path.join(BASE_DIR, "chromaDB/static")
DB_PATH_DYNAMIC = os.path.join(BASE_DIR, "chromaDB/dynamic")
BEST_PARAMS_PATH = os.path.join(BASE_DIR, "best_params.json")

# 2. 파라미터 로드
if os.path.exists(BEST_PARAMS_PATH):
    with open(BEST_PARAMS_PATH, 'r') as f:
        params = json.load(f)
    ALPHA = params.get('alpha', 0.7)
    BETA = params.get('beta', 0.3)
    LAMBDA_MENTION = params.get('lambda_mention', 1.0)
    print(f"Loaded Best Params: α={ALPHA:.2f}, β={BETA:.2f}, λ={LAMBDA_MENTION:.2f}")
else:
    print("Best params not found. Using defaults.")
    ALPHA, BETA, LAMBDA_MENTION = 0.7, 0.3, 1.0

# 3. 모델 및 DB 로드
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading Model on {device.upper()}...")
model = SentenceTransformer('BAAI/bge-m3', device=device)

try:
    client_static = chromadb.PersistentClient(path=DB_PATH_STATIC)
    client_dynamic = chromadb.PersistentClient(path=DB_PATH_DYNAMIC)
    col_static = client_static.get_collection("sbert")
    col_dynamic = client_dynamic.get_collection("sbert")
except Exception as e:
    print(f"DB Connection Error: {e}")
    sys.exit(1)

# 4. 유틸리티 함수
def calculate_score(query_vec, vec_static, vec_dyn, mention_bonus):
    score_static = np.dot(query_vec, vec_static)
    score_dynamic = np.dot(query_vec, vec_dyn)
    return (ALPHA * score_static) + (BETA * score_dynamic) + mention_bonus

def detect_mention_score(text, ticker):
    text_lower = text.lower()
    if f"${ticker.lower()}" in text_lower: return 1.0
    if ticker in ALIASES:
        for alias in ALIASES[ticker]:
            if alias in text_lower: return 1.0
    return 0.0

# 5. API 정의
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

@app.post("/search")
async def search(request: SearchRequest):
    query_text = request.query
    top_k = request.top_k
    
    # 1. 쿼리 임베딩
    query_vec = model.encode(query_text, convert_to_numpy=True)
    
    # 2. 1차 검색 (Static DB)
    res = col_static.query(
        query_embeddings=[query_vec.tolist()], 
        n_results=top_k * 3, 
        include=['embeddings', 'metadatas']
    )
    
    if not res['ids'] or not res['ids'][0]:
        return {"results": []}

    ids = res['ids'][0]
    embeddings = res['embeddings'][0]
    metadatas = res['metadatas'][0]
    
    candidates = []
    
    # 3. Dynamic DB 조회 및 점수 재계산
    for i, ticker in enumerate(ids):
        vec_static = np.array(embeddings[i])
        
        # 변수 무조건 초기화 (UnboundLocalError 방지)
        vec_dyn = np.zeros_like(vec_static)
        dyn_meta = {}
        
        try:
            # Dynamic DB 조회
            res_dyn = col_dynamic.get(ids=[ticker], include=['embeddings', 'metadatas'])
            
            # 메타데이터 체크
            if res_dyn['metadatas'] is not None and len(res_dyn['metadatas']) > 0:
                dyn_meta = res_dyn['metadatas'][0]

            # 임베딩 체크 (NumPy Ambiguous Error 방지)
            if res_dyn['embeddings'] is not None and len(res_dyn['embeddings']) > 0:
                vec_dyn = np.array(res_dyn['embeddings'][0])
                
        except Exception as e:
            # 에러 로그는 찍되, 멈추지 않음 (vec_dyn은 위에서 0으로 초기화됨)
            print(f"Error fetching dynamic for {ticker}: {e}")
            
        # 점수 계산
        mention_score = detect_mention_score(query_text, ticker) * LAMBDA_MENTION
        final_score = calculate_score(query_vec, vec_static, vec_dyn, mention_score)
        
        # 키워드 필드 처리
        keywords = metadatas[i].get('keywords', '')
        
        # Financial Text 처리
        fin_text = dyn_meta.get('Financial_Text', 'N/A')
        
        candidates.append({
            "ticker": ticker,
            "name": metadatas[i].get('name', ''),
            "score": float(final_score),
            "keywords": keywords,
            "financial_summary": fin_text
        })
        
    # 4. 최종 정렬
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return {"results": candidates[:top_k]}

@app.get("/health")
def health_check():
    return {"status": "ok", "device": device}