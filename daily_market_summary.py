import os
import requests
from openai import OpenAI
import yfinance as yf
from datetime import datetime

os.environ["PYTHONIOENCODING"] = "utf-8"

# ================== CONFIG ==================
NEWSAPI_KEY     = "31aaa9dd35504227b39dda10b6fadf9c"
GROQ_API_KEY    = "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"
TELEGRAM_TOKEN  = "8247425308:AAGPmUdyusQa9bflSddcqA18FjRjpBRhCps"
TELEGRAM_CHAT_ID = "5846299405"

GROQ_MODEL = "llama-3.3-70b-versatile"

TICKERS = ["BTC-USD", "ETH-USD", "GC=F", "^GSPC", "^DJI", "^IXIC", "AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]

# ================== FONCTIONS ==================

def get_news():
    articles = []
    url = "https://newsapi.org/v2/top-headlines"

    # Business en anglais
    r = requests.get(url, params={"apiKey": NEWSAPI_KEY, "pageSize": 10, "category": "business", "language": "en"})
    if r.status_code == 200:
        articles.extend(r.json().get("articles", []))

    # Actualités générales en français
    r = requests.get(url, params={"apiKey": NEWSAPI_KEY, "pageSize": 10, "category": "general", "language": "fr", "country": "fr"})
    if r.status_code == 200:
        articles.extend(r.json().get("articles", []))

    return [
        f"- {a['title']} : {a.get('description', '')[:150]}..."
        for a in articles[:12] if a.get("title") and a.get("description")
    ]

def get_market_data():
    data = yf.download(TICKERS, period="2d", interval="1d")["Close"]
    latest = data.iloc[-1]
    change_pct = data.pct_change().iloc[-1] * 100

    mapping = {
        "BTC-USD": "Bitcoin (BTC)", "ETH-USD": "Ethereum (ETH)", "GC=F": "Or (GOLD)",
        "^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "Nasdaq",
        "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
        "TSLA": "Tesla", "AMZN": "Amazon"
    }
    lines = []
    for t in TICKERS:
        name = mapping.get(t, t)
        price = latest[t]
        chg = change_pct[t]
        lines.append(f"{name}: {price:,.2f} ({chg:+.2f}%)")
    return "\n".join(lines)

def generate_summary(news_list, market_str):
    news_text = "\n".join(news_list)
    today = datetime.now().strftime('%d/%m/%Y')

    prompt = f"""Tu es un analyste financier senior ultra-objectif.
Aujourd'hui le {today}

ACTUALITES :
{news_text}

MARCHES AUJOURD'HUI :
{market_str}

Reponds en francais, format clair pour telephone :

**RESUME GLOBAL DES ACTUS** (6-8 points cles)
**DIRECTION DES MARCHES** (BTC, ETH, GOLD, S&P 500, Nasdaq, Apple, Nvidia, Tesla)
-> Direction + probabilite % + explication courte
**CONCLUSION** : Tendance generale + probabilite globale

Maximum 3800 caracteres."""

    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=1100
    )
    return response.choices[0].message.content

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, json=payload, timeout=10)
    if r.status_code != 200:
        print(f"Erreur Telegram : {r.text}")

# ================== LANCEMENT ==================
if __name__ == "__main__":
    print("Recuperation des actus...")
    news = get_news()
    market = get_market_data()

    print("Analyse avec Groq (Llama 3.3)...")
    summary = generate_summary(news, market)

    message = f"Resume Marche Quotidien - {datetime.now().strftime('%d/%m/%Y')}\n\n{summary}"

    print(message)
    send_to_telegram(message)
    print("Envoye sur Telegram !")