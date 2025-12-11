import nltk
from nltk.corpus import stopwords
import os

# 1. NLTK 불용어 설정
try:
    nltk.data.find('corpora/stipwords')
except LookupError:
    nltk.download('stopwords')

# 기본 불용어 + 커스텀 불용어
STOPWORDS = set(stopwords.words('english'))
# 티커로 사용되지만 불용어에서 제외해야할 단어들 (IT, ON, A 등)
TICKER_STOPWORDS_EXCEPTION = {'it', 'on', 'be', 'do', 'no', 'up', 'all', 'a', 'can', 'or'}
STOPWORDS = STOPWORDS - TICKER_STOPWORDS_EXCEPTION

# 2. 기업 별칭 - 검색 보정용
# 사용자가 "iphone"을 검색해도 AAPL을 찾게 해주는 사전 역할
ALIASES = {
    # Big Tech
    "AAPL": ["apple", "iphone", "ipad", "macbook", "ios", "vision pro", "tim cook"],
    "GOOGL": ["google", "android", "youtube", "gmail", "pixel", "deepmind", "gemini", "sundar pichai"],
    "GOOG":  ["google", "android", "youtube", "gmail", "pixel", "deepmind", "gemini"],
    "MSFT":  ["microsoft", "xbox", "windows", "office 365", "copilot", "azure", "satya nadella"],
    "AMZN":  ["amazon", "aws", "prime day", "alexa", "jeff bezos", "andy jassy"],
    "META":  ["facebook", "instagram", "whatsapp", "oculus", "zuck", "mark zuckerberg"],
    "TSLA":  ["tesla", "cybertruck", "optimus", "model 3", "model y", "elon musk", "spacex"],
    "NVDA":  ["nvidia", "geforce", "rtx", "h100", "blackwell", "jensen huang", "cuda"],
    
    # Ambiguous Tickers 보완 (티커가 흔한 단어일 때)
    "ALL": ["allstate", "allstate insurance"],
    "O":   ["realty income", "monthly dividend company"],
    "IT":  ["gartner"],
    "SO":  ["southern company"],
    "A":   ["agilent", "agilent technologies"],
    
    # Finance / Others
    "JPM": ["jpmorgan", "jamie dimon", "chase bank"],
    "BRK.B": ["berkshire hathaway", "warren buffett", "charlie munger"],
    "LLY": ["eli lilly", "mounjaro", "zepbound"],
    "NVO": ["novo nordisk", "ozempic", "wegovy"],
    "AMD": ["lisa su", "ryzen", "epyc", "radeon"],
    "INTC": ["intel", "pat gelsinger"],
    "NFLX": ["netflix", "squid game"],
    "DIS": ["disney", "pixar", "marvel", "bob iger", "espn"],
    "COIN": ["coinbase", "brian armstrong"],
    "BA": ["boeing", "737 max"],
}

# 3. 위험한 티커
# 해당 단어들은 $ 표시가 없거나, 별칭이 없으면 검색에서 제외
AMBIGUOUS_TICKERS = {
    "ALL", "O", "A", "IT", "ON", "SO", "NOW", "ARE", "CAN", "WELL", "OR", "BE"
}

# 4. 위키피디아 검색용 수동 매핑
MANUAL_MAPPING = {
    "GOOG": "Alphabet Inc.",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon (company)", 
    "V": "Visa Inc.",
    "O": "Realty Income",
    "T": "AT&T",
    "MA": "Mastercard",
    "BA": "Boeing",
    "CAT": "Caterpillar Inc.",
    "ALL": "Allstate",
    "DD": "DuPont",
    "M": "Macy's",
    "F": "Ford Motor Company",
    "PODD": "Insulet", 
    "BF-B": "Brown-Forman", 
    "BRK-B": "Berkshire Hathaway", 
    "SOLV": "Solventum", 
    "KVUE": "Kenvue"
}

# 5. 일반적인 회사 키워드
# Ket BERT가 추출한 키워드 중 뻔한 단어 제거용 
GENERIC_KEYWORDS = {
    "tech", "technology", "technologies", "software", "hardware", "system", "systems", 
    "group", "global", "international", "service", "services", "solution", "solutions", 
    "company", "companies", "corp", "corporation", "holding", "holdings", 
    "inc", "ltd", "plc", "investment", "capital", "financial", "finance", "business"
}