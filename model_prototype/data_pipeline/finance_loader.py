import yfinance as yf
import pandas as pd
from tqdm import tqdm
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "sp500_sbert_input.jsonl")
OUTPUT_FILE = os.path.join(BASE_DIR, "sp500_financials.jsonl")

def get_financial_narrative(ticker, name):
    try:
        stock = yf.Ticker(ticker)

        info = stock.info
        sector = info.get('sector', 'Unknown Sector')
        industry = info.get('industry', 'Unknwon Industry')

        financials = stock.financials
        if financials.empty: return "Empty"
        
        years = financials.columns[:4]
        narrative_parts = []
        
        narrative_parts.append(f"Financial Report for {name} ({ticker}). Sector: {sector}. Industry: {industry}")
        
        for date in years:
            year = date.year
            try:
                revenue = financials.loc['Total Revenue', date]
                net_income = financials.loc['Net Income', date]
                
                rev_str = f"{revenue/1e9:.2f} billion" if revenue > 1e9 else f"{revenue/1e6:.2f} million"
                inc_str = f"{net_income/1e9:.2f} billion" if abs(net_income) > 1e9 else f"{net_income/1e6:.2f} million"
                
                line = f"In {year}, Total Revenue was {rev_str}. Net Income was {inc_str}."
                
                if net_income > 0:
                    line += " The company was profitable and generated positive earnings."
                else:
                    line += " The company reported a net loss and negative earnings."

                narrative_parts.append(line)
                
            except KeyError:
                continue

        return " ".join(narrative_parts)
    
    except Exception as e:
        return ""
    
if __name__ == "__main__":
    print("Starting Financial Data Extraction")
    
    df = pd.read_json(INPUT_FILE, lines = True)
    financial_data = []
    
    for idx, row in tqdm(df.iterrows(), total = len(df)):
        ticker = row['Ticker']
        name = row['Name']
        
        fin_text = get_financial_narrative(ticker, name)
        
        if fin_text:
            financial_data.append({
                "Ticker": ticker,
                "Name": name,
                "Financial_Text": fin_text
            })
            
        time.sleep(0.1)
        
    pd.DataFrame(financial_data).to_json(OUTPUT_FILE, orient = 'records', lines = True)
    print(f"Saved financial data to {OUTPUT_FILE}")