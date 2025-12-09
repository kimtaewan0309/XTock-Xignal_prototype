import nltk
from nltk.corpus import stopwords


# 1. NLTK 불용어 설정
try:
    nltk.data.find('corpus/stopwords')
except LookupError:
    nltk.download('stopwords')
    
# 기본 불용어 집합
STOPWORDS = set(stopwords.words('english'))

# 불용어에서 제외할 티커 목록
TICKER_STOPWORDS_EXCEPTION = {'it', 'on', 'be', 'do', 'no', 'up', 'all', 'a', 'can', 'or', 'so', 'key'}
STOPWORDS = STOPWORDS - TICKER_STOPWORDS_EXCEPTION

# 커스텀 비즈니스 불용어
BUSINESS_STOPWORDS ={
    'inc', 'corp', 'company', 'ltd', 'incorporated', 'group', 'class', 'plc', 'holding', 'holdings',
    'firm', 'shares', 'stock', 'business', 'corporate', 'operations', 'segment', 'global', 'international',
    'services', 'solutions', 'systems', 'products', 'industries', 'technologies'
}
STOPWORDS.update(BUSINESS_STOPWORDS)

# 2. 기업 별칭
# iphone을 검색 시에 AAPL이 나오도록 만들어줌
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
    
    # Ambiguous Tickers 보완 (티커가 흔한 단어일 때 별칭이 있으면 확실함)
    "ALL": ["allstate", "allstate insurance"],
    "O":   ["realty income", "monthly dividend company"],
    "IT":  ["gartner"],
    "SO":  ["southern company"],
    "A":   ["agilent", "agilent technologies"],
    
    # Finance / Others (필요한 만큼 추가 가능)
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

# 3. Ambiguous Tickers
# 일반 문장에서 자주 사용되는 단어가 티커인 경우
# $ 표시, 별칭, AI가 확실하게 인식할 때만 검색 대상으로 설정
AMBIGUOUS_TICKERS = {
    "ALL", "O", "A", "IT", "ON", "SO", "NOW", "ARE", "CAN", "WELL", "OR", "BE", "KEY", "PH"
}

# 4. Wikipedia 검색용 수동 매핑
MANUAL_MAPPING = {
    # [한 글자 티커]
    "O": "Realty Income",
    "T": "AT&T",
    "C": "Citigroup",
    "F": "Ford Motor Company",
    "V": "Visa Inc.",
    "M": "Macy's",
    "A": "Agilent Technologies",
    "D": "Dominion Energy",
    "E": "Eni",
    "K": "Kellogg Company",
    
    # [일반 명사 티커]
    "ALL": "Allstate",
    "KEY": "KeyCorp",
    "PH":  "Parker Hannifin",
    "SO":  "Southern Company",
    "ED":  "Consolidated Edison",
    "BA":  "Boeing",
    "CAT": "Caterpillar Inc.",
    "DD":  "DuPont",
    "DG":  "Dollar General",
    "MA":  "Mastercard",
    "MO":  "Altria",
    "MU":  "Micron Technology",
    "PM":  "Philip Morris International",
    "RF":  "Regions Financial Corporation",
    "ST":  "Sensata Technologies",
    "TJX": "TJX Companies",
    "UPS": "United Parcel Service",
    "WM":  "Waste Management (corporation)",
    
    # [동음이의어 / 모호한 이름]
    "GOOG": "Alphabet Inc.",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon (company)",
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft",
    "META": "Meta Platforms",
    "TSLA": "Tesla, Inc.",
    "NVDA": "Nvidia",
    
    # [최근 변경 / 특수 케이스]
    "PODD": "Insulet", 
    "BF-B": "Brown-Forman", 
    "BRK-B": "Berkshire Hathaway", 
    "SOLV": "Solventum", 
    "KVUE": "Kenvue",
    "GEHC": "GE HealthCare"
}

# 5. 일반적인 푀사 키워드
# KeyBERT가 추출한 키워드 중 너무 뻔한 단어는 점수 계산에서 제외
GENERIC_KEYWORDS = {
    # [1] 비즈니스 일반 명사
    "tech", "technology", "technologies", "software", "hardware", "system", "systems", 
    "group", "global", "international", "service", "services", "solution", "solutions", 
    "company", "companies", "corp", "corporation", "holding", "holdings", 
    "inc", "ltd", "plc", "investment", "capital", "financial", "finance", "business",
    "sector", "industry", "provider", "offers", "provides", "operates", "headquartered",
    "subsidiaries", "subsidiary", "listed", "public", "private", "conglomerate",
    "component", "components", "index", "indices", "stock", "market", "nasdaq", "nyse",
    "role", "filled", "became", "become", "based", "located", "place",
    
    # [2] 부정적 / 법적 / 뉴스성 키워드 (노이즈)
    "history", "founded", "founder", "established", "incorporated", # 역사
    "lawsuit", "sued", "legal", "settlement", "alleged", "accused", "violation", "investigation", # 소송
    "controversy", "controversies", "ethical", "criticized", "criticism", "faced", "facing", # 논란
    "bankruptcy", "bankrupt", "debt", "stolen", "seized", "account", # 파산/범죄
    "termination", "terminated", "layoff", "layoffs", "mass", "fired", "resignation", # 해고
    "antitrust", "monopoly", "fine", "fined", "penalty", "judge", "court", # 독과점
    "uber", "russia", "china", "eu", "european", "commission", # 특정 국가/경쟁사 이슈
    
    # [3] 무의미한 수식어
    "largest", "biggest", "world", "major", "widely", "described", "numerous", "various",
    "united", "states", "american", "california", "york", "mountain", "view", 
    "million", "billion", "trillion", "revenue", "profit", "income", "year", "years",
    "ceo", "announced", "appointed", "member", "board", "executive", "officer",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    
    "law", "actions", "action", "discovered", "access", "self", "greater", 
    "multiple", "large", "cap", "products", "services", "solutions", "platforms",
    "customer", "customers", "operations", "operate", "operating", "segment",
    "also", "include", "includes", "including", "related", "various", "involved",
    "based", "tools", "internet", "digital", "content", "devices", "apps"

}