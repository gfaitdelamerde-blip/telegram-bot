import os
import requests
import yfinance as yf
from openai import OpenAI
from datetime import datetime, timedelta, timezone
import time
import pandas as pd
import json
import random
import pytz

os.environ["PYTHONIOENCODING"] = "utf-8"

PARIS_TZ = pytz.timezone("Europe/Paris")

def now_paris():
    return datetime.now(pytz.utc).astimezone(PARIS_TZ).replace(tzinfo=None)


# ================== CONFIG ==================
NEWSAPI_KEY      = os.getenv("NEWSAPI_KEY")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

GROQ_MODEL   = "llama-3.3-70b-versatile"
PAYMENT_LINK = "https://paypal.me/tonnom/9.99EUR"
PRIX_MENSUEL = "9.99€"
PRIX_ANNUEL  = "79.99€"
USERS_FILE   = "users.json"

TICKERS = ["BTC-USD","ETH-USD","GC=F","^GSPC","^DJI","^IXIC","AAPL","MSFT","NVDA","TSLA","AMZN"]

SIGNAL_ASSETS = {
    "btc":   ("BTC-USD",  "₿ Bitcoin (BTC)"),
    "eth":   ("ETH-USD",  "🔷 Ethereum (ETH)"),
    "bnb":   ("BNB-USD",  "🟡 BNB"),
    "sol":   ("SOL-USD",  "🔵 Solana (SOL)"),
    "xrp":   ("XRP-USD",  "🟣 XRP"),
    "gold":  ("GC=F",     "🥇 Or (GOLD)"),
    "aapl":  ("AAPL",     "🍎 Apple"),
    "nvda":  ("NVDA",     "🟢 Nvidia"),
    "msft":  ("MSFT",     "🔵 Microsoft"),
    "tsla":  ("TSLA",     "🚗 Tesla"),
    "amzn":  ("AMZN",     "📦 Amazon"),
    "googl": ("GOOGL",    "🔍 Google"),
    "meta":  ("META",     "📘 Meta"),
    "amd":   ("AMD",      "🔴 AMD"),
}

RSI_ASSETS = {
    "btc":   ("BTC-USD", "₿ Bitcoin"),
    "eth":   ("ETH-USD", "🔷 Ethereum"),
    "bnb":   ("BNB-USD", "🟡 BNB"),
    "sol":   ("SOL-USD", "🔵 Solana"),
    "gold":  ("GC=F",    "🥇 Or"),
    "sp500": ("^GSPC",   "📈 S&P 500"),
    "aapl":  ("AAPL",    "🍎 Apple"),
    "nvda":  ("NVDA",    "🟢 Nvidia"),
    "tsla":  ("TSLA",    "🚗 Tesla"),
}

# ================== TRADUCTIONS ==================
LANGS = {
    "fr": {
        "welcome_title": "💎 ESPACE MEMBRE PREMIUM",
        "morning": ["🌅 Bonjour", "☀️ Bon après-midi", "🌙 Bonsoir"],
        "tools": "Voici tes outils exclusifs :",
        "menu_main": "🔄 Menu principal :",
        "processing": "⏳ Analyse en cours...",
        "signal_title": "📈 SIGNAL",
        "rsi_title": "📊 RSI (14)",
        "thanks_review": "Merci pour ton avis ! 🙏",
        "premium_required": "🔒 Fonctionnalité Premium",
        "sent": "✅ Message envoyé !",
    },
    "en": {
        "welcome_title": "💎 PREMIUM MEMBER AREA",
        "morning": ["🌅 Good morning", "☀️ Good afternoon", "🌙 Good evening"],
        "tools": "Here are your exclusive tools:",
        "menu_main": "🔄 Main menu:",
        "processing": "⏳ Analysis in progress...",
        "signal_title": "📈 SIGNAL",
        "rsi_title": "📊 RSI (14)",
        "thanks_review": "Thanks for your review! 🙏",
        "premium_required": "🔒 Premium Feature",
        "sent": "✅ Message sent!",
    },
    "es": {
        "welcome_title": "💎 ÁREA MIEMBRO PREMIUM",
        "morning": ["🌅 Buenos días", "☀️ Buenas tardes", "🌙 Buenas noches"],
        "tools": "Aquí están tus herramientas exclusivas:",
        "menu_main": "🔄 Menú principal:",
        "processing": "⏳ Análisis en curso...",
        "signal_title": "📈 SEÑAL",
        "rsi_title": "📊 RSI (14)",
        "thanks_review": "¡Gracias por tu reseña! 🙏",
        "premium_required": "🔒 Función Premium",
        "sent": "✅ ¡Mensaje enviado!",
    },
}

def t(chat_id, key):
    user = get_user(chat_id)
    lang = user.get("lang", "fr")
    return LANGS.get(lang, LANGS["fr"]).get(key, LANGS["fr"].get(key, ""))

def get_lang(chat_id):
    return get_user(chat_id).get("lang", "fr")

# ================== CITATIONS ==================
CITATIONS = [
    ("L'investissement, c'est mettre de l'argent aujourd'hui pour en avoir plus demain.", "Warren Buffett"),
    ("Le marché est un dispositif qui transfère de l'argent des impatients aux patients.", "Warren Buffett"),
    ("Le risque vient de ne pas savoir ce que vous faites.", "Warren Buffett"),
    ("Ne jamais investir dans ce que vous ne comprenez pas.", "Peter Lynch"),
    ("Le temps sur le marché bat le timing du marché.", "Ken Fisher"),
    ("Les marchés peuvent rester irrationnels plus longtemps que vous ne pouvez rester solvable.", "John Maynard Keynes"),
    ("Achetez quand tout le monde vend, vendez quand tout le monde achète.", "J. Paul Getty"),
    ("La bourse est le seul endroit où on vend moins quand les soldes commencent.", "Warren Buffett"),
    ("Il faut être craintif quand les autres sont avides, et avide quand les autres sont craintifs.", "Warren Buffett"),
    ("La première règle : ne jamais perdre d'argent. La deuxième : ne jamais oublier la première.", "Warren Buffett"),
    ("Un investisseur qui achète et vend frénétiquement paie des frais inutiles.", "Peter Lynch"),
    ("Les corrections de marché sont les meilleures opportunités pour les investisseurs.", "Peter Lynch"),
    ("La patience est la vertu la plus précieuse pour un investisseur.", "Charlie Munger"),
    ("Invert, always invert — comprendre l'échec pour l'éviter.", "Charlie Munger"),
    ("Le prix est ce que vous payez. La valeur est ce que vous obtenez.", "Warren Buffett"),
    ("Les quatre mots les plus dangereux : cette fois c'est différent.", "John Templeton"),
    ("La volatilité est le prix à payer pour la performance.", "Howard Marks"),
    ("Un portefeuille bien construit résiste à la peur autant qu'à la cupidité.", "Ray Dalio"),
    ("Cash is king quand tout le monde panique.", "Anonyme, Wall Street"),
    ("Les marchés montent par escalier et descendent par ascenseur.", "Proverbe boursier"),
    ("Dans les marchés comme dans la vie, la discipline sépare les gagnants des perdants.", "Paul Tudor Jones"),
    ("Je perds certains jours. Ce qui compte, c'est combien je perds quand j'ai tort.", "George Soros"),
    ("Achetez de belles entreprises à des prix raisonnables.", "Warren Buffett"),
    ("Savoir ce qu'on ne sait pas est plus utile que croire savoir ce qu'on ne sait pas.", "Howard Marks"),
    ("L'or est la mémoire du temps.", "Marc Faber"),
    ("Ne jamais vendre par panique, jamais acheter par euphorie.", "Bernard Baruch"),
    ("Le marché récompense ceux qui pensent à long terme.", "Benjamin Graham"),
    ("Diversifier, c'est admettre qu'on ne sait pas tout.", "Charlie Munger"),
    ("Un bon trader sait perdre. Un mauvais trader ne sait pas s'arrêter.", "Ed Seykota"),
    ("Tout le monde a un plan jusqu'à ce qu'il prenne un coup.", "Mike Tyson"),
    ("Le succès en bourse, c'est 90% de psychologie et 10% d'analyse.", "Peter Lynch"),
]

def get_daily_quote():
    idx = now_paris().timetuple().tm_yday % len(CITATIONS)
    text, author = CITATIONS[idx]
    return f'"{text}"\n— *{author}*'

# ================== GESTION USERS ==================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def is_admin(chat_id):
    return str(chat_id) == str(TELEGRAM_CHAT_ID)

def get_user(chat_id):
    return load_users().get(str(chat_id), {"plan": "free", "expiry": None, "name": "?", "lang": "fr"})

def is_premium(chat_id):
    if is_admin(chat_id):
        return True
    user = get_user(chat_id)
    if user.get("plan") == "premium":
        exp = user.get("expiry")
        if not exp:
            return True
        return now_paris() < datetime.strptime(exp, "%Y-%m-%d")
    return False

def add_premium(chat_id, name, days):
    users = load_users()
    expiry = (now_paris() + timedelta(days=days)).strftime("%Y-%m-%d")
    if str(chat_id) not in users:
        users[str(chat_id)] = {}
    users[str(chat_id)].update({"plan": "premium", "expiry": expiry, "name": name})
    save_users(users)
    return expiry

def remove_premium(chat_id):
    users = load_users()
    if str(chat_id) in users:
        users[str(chat_id)]["plan"] = "free"
        save_users(users)

def register_user(chat_id, name):
    users = load_users()
    if str(chat_id) not in users:
        users[str(chat_id)] = {"plan": "free", "expiry": None, "name": name, "lang": "fr"}
        save_users(users)

def set_user_field(chat_id, key, value):
    users = load_users()
    if str(chat_id) not in users:
        users[str(chat_id)] = {"plan": "free", "expiry": None, "name": "?", "lang": "fr"}
    users[str(chat_id)][key] = value
    save_users(users)

# ================== TELEGRAM ==================
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erreur envoi : {e}")

def answer_callback(callback_query_id, text=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_query_id, "text": text}, timeout=5)

# ================== MENUS ==================
def main_menu(chat_id):
    if is_premium(chat_id):
        return {"inline_keyboard": [
            [{"text": "📰 Actu",          "callback_data": "/actu"},
             {"text": "🎰 Pépite",        "callback_data": "/chance"}],
            [{"text": "📈 Signaux",       "callback_data": "/menu_signaux"},
             {"text": "📊 RSI",           "callback_data": "/menu_rsi"}],
            [{"text": "🏆 Top 5",         "callback_data": "/top"},
             {"text": "💬 Citation",      "callback_data": "/quote"}],
            [{"text": "🤖 Wallet IA",     "callback_data": "/aiwallet"}],
            [{"text": "🧰 Mes Outils",    "callback_data": "/menu_outils"}],
            [{"text": "🏠 Accueil",       "callback_data": "/accueil"},
             {"text": "⚙️ Compte",        "callback_data": "/menu_compte"}],
        ]}
    else:
        return {"inline_keyboard": [
            [{"text": "📰 Actu Marché — Gratuit",               "callback_data": "/actu"}],
            [{"text": "🔒 Signaux BUY/SHORT",                   "callback_data": "/premium"},
             {"text": "🔒 RSI",                                 "callback_data": "/premium"}],
            [{"text": "🔒 Pépite du jour",                      "callback_data": "/premium"},
             {"text": "🔒 Top 5 Actions",                       "callback_data": "/premium"}],
            [{"text": "🔒 Paper Trading",                       "callback_data": "/premium"},
             {"text": "🔒 Alertes de prix",                     "callback_data": "/premium"}],
            [{"text": "🔒 Score Marché",                        "callback_data": "/premium"},
             {"text": "🔒 Bilan hebdo",                         "callback_data": "/premium"}],
            [{"text": "🔒 Citation du jour",                    "callback_data": "/premium"}],
            [{"text": "🤖 Wallet IA — PUBLIC 👀",               "callback_data": "/aiwallet"}],
            [{"text": "━━━━━━━━━━━━━━━━━━━━━━━━━━",             "callback_data": "/noop"}],
            [{"text": "👑 PASSER PREMIUM — " + PRIX_MENSUEL + "/mois ⚡", "url": PAYMENT_LINK}],
            [{"text": "🏠 Accueil",  "callback_data": "/accueil"},
             {"text": "⚙️ Compte",  "callback_data": "/menu_compte"},
             {"text": "🛎️ SAV",    "callback_data": "/sav"}],
        ]}

def menu_signaux():
    return {"inline_keyboard": [
        [{"text": "─── 🪙 CRYPTO ───────────", "callback_data": "/noop"}],
        [{"text": "₿ Bitcoin",   "callback_data": "/signal btc"},
         {"text": "🔷 Ethereum", "callback_data": "/signal eth"}],
        [{"text": "🟡 BNB",      "callback_data": "/signal bnb"},
         {"text": "🔵 Solana",   "callback_data": "/signal sol"}],
        [{"text": "🟣 XRP",      "callback_data": "/signal xrp"},
         {"text": "🥇 Gold",     "callback_data": "/signal gold"}],
        [{"text": "─── 📈 ACTIONS ──────────", "callback_data": "/noop"}],
        [{"text": "🍎 Apple",    "callback_data": "/signal aapl"},
         {"text": "🟢 Nvidia",   "callback_data": "/signal nvda"}],
        [{"text": "🔵 Microsoft","callback_data": "/signal msft"},
         {"text": "🚗 Tesla",    "callback_data": "/signal tsla"}],
        [{"text": "📦 Amazon",   "callback_data": "/signal amzn"},
         {"text": "🔍 Google",   "callback_data": "/signal googl"}],
        [{"text": "📘 Meta",     "callback_data": "/signal meta"},
         {"text": "🔴 AMD",      "callback_data": "/signal amd"}],
        [{"text": "🔙 Retour",   "callback_data": "/menu_retour"}],
    ]}

def menu_rsi():
    return {"inline_keyboard": [
        [{"text": "₿ BTC",        "callback_data": "/rsi btc"},
         {"text": "🔷 ETH",       "callback_data": "/rsi eth"}],
        [{"text": "🟡 BNB",       "callback_data": "/rsi bnb"},
         {"text": "🔵 Solana",    "callback_data": "/rsi sol"}],
        [{"text": "🥇 Gold",      "callback_data": "/rsi gold"},
         {"text": "📈 S&P500",    "callback_data": "/rsi sp500"}],
        [{"text": "🍎 Apple",     "callback_data": "/rsi aapl"},
         {"text": "🟢 Nvidia",    "callback_data": "/rsi nvda"}],
        [{"text": "🚗 Tesla",     "callback_data": "/rsi tsla"}],
        [{"text": "🔙 Retour",    "callback_data": "/menu_retour"}],
    ]}

def menu_outils():
    return {"inline_keyboard": [
        [{"text": "🔔 Mes Alertes",        "callback_data": "/menu_alertes"}],
        [{"text": "📊 Paper Trading",      "callback_data": "/menu_paper"}],
        [{"text": "📅 Score Marché",       "callback_data": "/score"}],
        [{"text": "📈 Ma Performance",     "callback_data": "/performance"}],
        [{"text": "⭐ Donner un avis",     "callback_data": "/avis"}],
        [{"text": "🔙 Retour",            "callback_data": "/menu_retour"}],
    ]}

def menu_compte():
    return {"inline_keyboard": [
        [{"text": "👤 Mon Compte",         "callback_data": "/moncompte"}],
        [{"text": "🌐 Langue",             "callback_data": "/menu_langue"}],
        [{"text": "🛎️ SAV",              "callback_data": "/sav"}],
        [{"text": "🔙 Retour",            "callback_data": "/menu_retour"}],
    ]}

def menu_langue():
    return {"inline_keyboard": [
        [{"text": "🇫🇷 Français",         "callback_data": "/lang fr"},
         {"text": "🇬🇧 English",          "callback_data": "/lang en"},
         {"text": "🇪🇸 Español",          "callback_data": "/lang es"}],
        [{"text": "🔙 Retour",            "callback_data": "/menu_compte"}],
    ]}

def menu_alertes(chat_id):
    user = get_user(chat_id)
    alertes = user.get("alertes", [])
    rows = []
    for i, a in enumerate(alertes):
        rows.append([{"text": f"❌ Suppr. {a['asset']} @ {a['price']}", "callback_data": f"/alerte_del {i}"}])
    rows.append([{"text": "➕ Nouvelle alerte",  "callback_data": "/alerte_new"}])
    rows.append([{"text": "🔙 Retour",           "callback_data": "/menu_outils"}])
    return {"inline_keyboard": rows}

def menu_paper(chat_id):
    user = get_user(chat_id)
    balance = user.get("paper_balance", 10000)
    return {"inline_keyboard": [
        [{"text": f"💰 Solde : {balance:,.2f}$",  "callback_data": "/noop"}],
        [{"text": "📥 Acheter (BUY)",              "callback_data": "/paper_buy"},
         {"text": "📤 Vendre (SELL)",              "callback_data": "/paper_sell"}],
        [{"text": "📋 Mon Portefeuille",           "callback_data": "/paper_portfolio"}],
        [{"text": "📊 Mes Performances",           "callback_data": "/paper_perf"}],
        [{"text": "🔄 Réinitialiser (10 000$)",    "callback_data": "/paper_reset"}],
        [{"text": "🔙 Retour",                     "callback_data": "/menu_outils"}],
    ]}

# ================== DONNÉES MARCHÉ ==================
def get_news():
    articles = []
    url = "https://newsapi.org/v2/top-headlines"
    for params in [
        {"apiKey": NEWSAPI_KEY, "pageSize": 10, "category": "business", "language": "en"},
        {"apiKey": NEWSAPI_KEY, "pageSize": 10, "category": "general", "language": "fr", "country": "fr"},
    ]:
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                articles.extend(r.json().get("articles", []))
        except:
            pass
    return [f"- {a['title']} : {a.get('description','')[:150]}..."
            for a in articles[:12] if a.get("title") and a.get("description")]

def get_market_data():
    data = yf.download(TICKERS, period="2d", interval="1d", progress=False)["Close"]
    latest = data.iloc[-1]
    chg = data.pct_change().iloc[-1] * 100
    mapping = {
        "BTC-USD":"₿ Bitcoin","ETH-USD":"🔷 Ethereum","GC=F":"🥇 Or",
        "^GSPC":"📈 S&P 500","^DJI":"📊 Dow Jones","^IXIC":"💻 Nasdaq",
        "AAPL":"🍎 Apple","MSFT":"🔵 Microsoft","NVDA":"🟢 Nvidia",
        "TSLA":"🚗 Tesla","AMZN":"📦 Amazon",
    }
    lines = []
    for tk in TICKERS:
        name = mapping.get(tk, tk)
        c = float(chg[tk])
        e = "🟢" if c >= 0 else "🔴"
        lines.append(f"{e} *{name}*: {float(latest[tk]):,.2f} ({c:+.2f}%)")
    return "\n".join(lines)

def get_asset_price(ticker):
    try:
        data = yf.download(ticker, period="2d", interval="1d", progress=False)["Close"]
        vals = [float(v) for v in data.values.flatten() if str(v) != 'nan']
        return vals[-1] if vals else None
    except:
        return None

def get_asset_data(ticker, period="5d"):
    data = yf.download(ticker, period=period, interval="1d", progress=False)["Close"]
    return [float(v) for v in data.dropna().values.flatten() if str(v) != 'nan']

def compute_rsi(ticker, period=14):
    data = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
    if data.empty:
        return None
    close = data["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    close = pd.Series([float(v) for v in close.values.flatten()], index=close.index).dropna()
    if len(close) < period:
        return None
    delta = close.diff()
    avg_gain = delta.clip(lower=0).rolling(window=period).mean()
    avg_loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = float(rsi.iloc[-1])
    return None if pd.isna(val) else val

def get_top5():
    tickers = ["AAPL","MSFT","NVDA","TSLA","AMZN","GOOGL","META","AMD","NFLX","ORCL"]
    data = yf.download(tickers, period="2d", interval="1d", progress=False)["Close"]
    chg = data.pct_change().iloc[-1] * 100
    latest = data.iloc[-1]
    sorted_t = chg.dropna().sort_values(ascending=False)
    lines = ["🏆 *TOP 5 ACTIONS DU JOUR*\n"]
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣"]
    for i, (tk, c) in enumerate(sorted_t.head(5).items()):
        lines.append(f"{medals[i]} *{tk}*: {float(latest[tk]):,.2f} ({float(c):+.2f}%)")
    lines.append("\n📉 *FLOP 3 DU JOUR*")
    for tk, c in sorted_t.tail(3).iloc[::-1].items():
        lines.append(f"🔴 *{tk}*: {float(latest[tk]):,.2f} ({float(c):+.2f}%)")
    return "\n".join(lines)

# ================== IA ==================
def call_groq(prompt, max_tokens=1100, temperature=0.4):
    client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    r = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature, max_tokens=max_tokens
    )
    return r.choices[0].message.content

def generate_summary(news_list, market_str, lang="fr"):
    today = now_paris().strftime('%d/%m/%Y')
    if lang == "en":
        instr = "Answer in English with emojis, phone format:"
    elif lang == "es":
        instr = "Responde en español con emojis, formato teléfono:"
    else:
        instr = "Réponds en français avec emojis, format téléphone :"
    prompt = f"""You are a senior financial analyst. Today: {today}
NEWS: {chr(10).join(news_list)}
MARKETS: {market_str}
{instr}
*SUMMARY* (6-8 key points)
*MARKET DIRECTION* -> Each asset: direction + probability % + short explanation
*CONCLUSION*: General trend + probability
Max 3500 characters."""
    return call_groq(prompt, max_tokens=1100)

def generate_trade_signal(asset_name, ticker, news_list, lang="fr"):
    prices = get_asset_data(ticker)
    if len(prices) < 2:
        return "Insufficient data."
    pc = prices[-1]
    chg = ((pc - prices[-2]) / prices[-2]) * 100
    sma = sum(prices) / len(prices)
    today = now_paris().strftime('%d/%m/%Y %H:%M')
    lang_instr = {"fr": "Réponds en français", "en": "Answer in English", "es": "Responde en español"}
    prompt = f"""Professional trader. {today} — {asset_name}
Price: {pc:,.2f} | Change: {chg:+.2f}% | SMA5: {sma:,.2f}
5d prices: {', '.join([f'{p:,.2f}' for p in prices])}
News: {chr(10).join(news_list[:6])}
{lang_instr.get(lang,'Réponds en français')} avec emojis :
*SIGNAL*: BUY 🟢 ou SHORT 🔴 | *CONVICTION*: XX%
*TECHNIQUE*: 2 lines | *FUNDAMENTAL*: 2 lines
*TARGET*: price | *STOP LOSS*: level | *CONCLUSION*: 1 sentence
Max 1200 chars."""
    return call_groq(prompt, max_tokens=600, temperature=0.3)

def generate_market_score():
    """Score global du marché de 0 à 100"""
    try:
        data = yf.download(["BTC-USD","^GSPC","^IXIC","GC=F"], period="5d", interval="1d", progress=False)["Close"]
        chg = data.pct_change().iloc[-1] * 100
        scores = []
        for tk in ["BTC-USD","^GSPC","^IXIC","GC=F"]:
            c = float(chg[tk])
            scores.append(min(100, max(0, 50 + c * 5)))
        score = int(sum(scores) / len(scores))
        if score >= 70:
            sentiment = "🟢 *Haussier*"
            conseil = "Les marchés sont en forme. Momentum positif."
        elif score >= 45:
            sentiment = "🟡 *Neutre*"
            conseil = "Marchés indécis. Prudence et sélectivité."
        else:
            sentiment = "🔴 *Baissier*"
            conseil = "Pression vendeuse. Gestion du risque prioritaire."
        filled = "█" * (score // 10)
        empty = "░" * (10 - score // 10)
        bar = filled + empty
        return score, sentiment, conseil, bar
    except Exception as e:
        return 50, "🟡 *Neutre*", "Données indisponibles.", "█████░░░░░"

def generate_weekly_report(news_list, market_str, lang="fr"):
    today = now_paris().strftime('%d/%m/%Y')
    lang_instr = {"fr": "Réponds en français", "en": "Answer in English", "es": "Responde en español"}
    prompt = f"""Senior financial analyst. Week ending {today}.
MARKETS THIS WEEK: {market_str}
NEWS THIS WEEK: {chr(10).join(news_list)}
{lang_instr.get(lang,'Réponds en français')} avec emojis, format téléphone :
*BILAN DE LA SEMAINE* (5-6 points majeurs)
*ACTIFS GAGNANTS & PERDANTS* cette semaine
*TENDANCES À SURVEILLER* la semaine prochaine
*PROBABILITÉS* pour la semaine à venir
Max 3500 chars."""
    return call_groq(prompt, max_tokens=1100)

def generate_hidden_gem(news_list):
    today = now_paris().strftime('%d/%m/%Y')
    candidates = {
        "RENDER-USD":"Render (RNDR)","INJ-USD":"Injective (INJ)",
        "FET-USD":"Fetch.ai (FET)","OCEAN-USD":"Ocean Protocol",
        "AR-USD":"Arweave (AR)","ROSE-USD":"Oasis (ROSE)",
        "RKLB":"Rocket Lab","IONQ":"IonQ","ACHR":"Archer Aviation",
        "JOBY":"Joby Aviation","LUNR":"Intuitive Machines","SERV":"Serve Robotics",
    }
    tickers = list(candidates.keys())
    try:
        data = yf.download(tickers, period="30d", interval="1d", progress=False)["Close"]
        chg7 = data.pct_change(periods=7).iloc[-1] * 100
        chg30 = data.pct_change(periods=30).iloc[-1] * 100
        latest = data.iloc[-1]
        info = []
        for tk, name in candidates.items():
            try:
                p,c7,c30 = float(latest[tk]),float(chg7[tk]),float(chg30[tk])
                if not any(pd.isna(x) for x in [p,c7,c30]):
                    info.append(f"- {name}: {p:.4f} | 7d={c7:+.1f}% | 30d={c30:+.1f}%")
            except: continue
    except:
        return "Données indisponibles."
    prompt = f"""Specialist in undervalued assets. Today: {today}
ASSETS: {chr(10).join(info)}
NEWS: {chr(10).join(news_list[:8])}
Choose ONE with highest short-term explosion potential (1-4 weeks).
Respond in French with emojis:
🎰 *PÉPITE DU JOUR*: [Name]
*POURQUOI*: technical + fundamental + macro (3 points)
*POTENTIEL*: +XX% à +XX% | *HORIZON*: X semaines | *RISQUE*: niveau
*ACHETER SUR*: platform
⚠️ _Pas un conseil financier. Investis ce que tu peux perdre._
Max 1500 chars."""
    return call_groq(prompt, max_tokens=700, temperature=0.6)

# ================== PAPER TRADING ==================
def paper_get_portfolio(chat_id):
    return get_user(chat_id).get("paper_portfolio", {})

def paper_get_balance(chat_id):
    return get_user(chat_id).get("paper_balance", 10000.0)

def paper_buy(chat_id, ticker_key, amount_usd):
    asset = SIGNAL_ASSETS.get(ticker_key)
    if not asset:
        return False, "Actif inconnu."
    ticker, name = asset
    price = get_asset_price(ticker)
    if not price:
        return False, "Prix indisponible."
    balance = paper_get_balance(chat_id)
    if amount_usd > balance:
        return False, f"Solde insuffisant ({balance:,.2f}$)"
    qty = amount_usd / price
    users = load_users()
    uid = str(chat_id)
    if uid not in users:
        users[uid] = {}
    portfolio = users[uid].get("paper_portfolio", {})
    if ticker_key in portfolio:
        total_qty = portfolio[ticker_key]["qty"] + qty
        total_cost = portfolio[ticker_key]["cost"] + amount_usd
        portfolio[ticker_key] = {"qty": total_qty, "cost": total_cost, "name": name, "ticker": ticker}
    else:
        portfolio[ticker_key] = {"qty": qty, "cost": amount_usd, "name": name, "ticker": ticker}
    users[uid]["paper_portfolio"] = portfolio
    users[uid]["paper_balance"] = balance - amount_usd
    if "paper_history" not in users[uid]:
        users[uid]["paper_history"] = []
    users[uid]["paper_history"].append({
        "date": now_paris().strftime("%d/%m/%Y %H:%M"),
        "type": "BUY", "asset": name, "amount": amount_usd, "price": price, "qty": qty
    })
    save_users(users)
    return True, f"✅ *Achat exécuté*\n{name}: {qty:.4f} unités @ {price:,.2f}$\nCoût: {amount_usd:,.2f}$"

def paper_sell(chat_id, ticker_key, pct=100):
    asset = SIGNAL_ASSETS.get(ticker_key)
    if not asset:
        return False, "Actif inconnu."
    ticker, name = asset
    price = get_asset_price(ticker)
    if not price:
        return False, "Prix indisponible."
    users = load_users()
    uid = str(chat_id)
    portfolio = users.get(uid, {}).get("paper_portfolio", {})
    if ticker_key not in portfolio:
        return False, "Tu ne possèdes pas cet actif."
    pos = portfolio[ticker_key]
    qty_sell = pos["qty"] * (pct / 100)
    proceeds = qty_sell * price
    pnl = proceeds - (pos["cost"] * pct / 100)
    pnl_pct = (pnl / (pos["cost"] * pct / 100)) * 100 if pos["cost"] > 0 else 0
    if pct == 100:
        del portfolio[ticker_key]
    else:
        portfolio[ticker_key]["qty"] -= qty_sell
        portfolio[ticker_key]["cost"] -= pos["cost"] * pct / 100
    users[uid]["paper_portfolio"] = portfolio
    users[uid]["paper_balance"] = users[uid].get("paper_balance", 10000) + proceeds
    if "paper_history" not in users[uid]:
        users[uid]["paper_history"] = []
    users[uid]["paper_history"].append({
        "date": now_paris().strftime("%d/%m/%Y %H:%M"),
        "type": "SELL", "asset": name, "amount": proceeds, "price": price, "pnl": pnl
    })
    save_users(users)
    emoji = "🟢" if pnl >= 0 else "🔴"
    return True, (f"✅ *Vente exécutée*\n{name}: {qty_sell:.4f} unités @ {price:,.2f}$\n"
                  f"Reçu: {proceeds:,.2f}$ | {emoji} P&L: {pnl:+,.2f}$ ({pnl_pct:+.1f}%)")

def paper_portfolio_summary(chat_id):
    portfolio = paper_get_portfolio(chat_id)
    balance = paper_get_balance(chat_id)
    if not portfolio:
        return f"💰 *Solde cash*: {balance:,.2f}$\n\n_Aucune position ouverte._"
    lines = [f"💰 *Solde cash*: {balance:,.2f}$\n\n📋 *POSITIONS OUVERTES*"]
    total_value = balance
    total_cost = 0
    for key, pos in portfolio.items():
        price = get_asset_price(pos["ticker"]) or 0
        value = pos["qty"] * price
        pnl = value - pos["cost"]
        pnl_pct = (pnl / pos["cost"]) * 100 if pos["cost"] > 0 else 0
        e = "🟢" if pnl >= 0 else "🔴"
        lines.append(f"{e} *{pos['name']}*: {value:,.2f}$ ({pnl_pct:+.1f}%)")
        total_value += value
        total_cost += pos["cost"]
    initial = 10000.0
    total_pnl = total_value - initial
    total_pnl_pct = (total_pnl / initial) * 100
    e2 = "🟢" if total_pnl >= 0 else "🔴"
    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"{e2} *Valeur totale*: {total_value:,.2f}$")
    lines.append(f"{e2} *P&L total*: {total_pnl:+,.2f}$ ({total_pnl_pct:+.1f}%)")
    return "\n".join(lines)

# ================== ALERTES ==================
def check_alerts():
    users = load_users()
    for uid, user in users.items():
        alertes = user.get("alertes", [])
        triggered = []
        remaining = []
        for a in alertes:
            price = get_asset_price(a.get("ticker", "BTC-USD"))
            if price is None:
                remaining.append(a)
                continue
            cond = a.get("cond", "above")
            if (cond == "above" and price >= a["price"]) or (cond == "below" and price <= a["price"]):
                triggered.append((a, price))
            else:
                remaining.append(a)
        if triggered:
            users[uid]["alertes"] = remaining
            save_users(users)
            for a, price in triggered:
                e = "🚀" if a.get("cond") == "above" else "📉"
                send_message(int(uid),
                    f"🔔 *ALERTE DÉCLENCHÉE !*\n\n"
                    f"{e} *{a['asset']}* a atteint *{price:,.2f}$*\n"
                    f"_(Seuil fixé : {a['price']:,.2f}$)_",
                    reply_markup=main_menu(int(uid))
                )

# ================== COMMANDES ==================
def premium_lock(chat_id):
    send_message(chat_id,
        f"🔒 *Fonctionnalité Premium*\n\nDébloque tout pour *{PRIX_MENSUEL}/mois* :\n"
        f"📈 Signaux • 📊 RSI • 🎰 Pépite • 📊 Paper Trading • 🔔 Alertes\n\n"
        f"⚡ Activation quasi-instantanée",
        reply_markup={"inline_keyboard": [
            [{"text": f"👑 Passer Premium — {PRIX_MENSUEL}/mois", "url": PAYMENT_LINK}],
            [{"text": "🔙 Retour", "callback_data": "/menu_retour"}]
        ]}
    )

def cmd_accueil(chat_id, name=""):
    lang = get_lang(chat_id)
    tr = LANGS.get(lang, LANGS["fr"])
    if is_premium(chat_id):
        now = now_paris()
        h = now.hour
        sal = tr["morning"][0] if 5<=h<12 else tr["morning"][1] if 12<=h<18 else tr["morning"][2]
        msg = (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{tr['welcome_title']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{sal}, *{name}* 👋\n\n"
            f"{tr['tools']}\n\n"
            f"📰 *Actu* — Résumé + direction des marchés\n"
            f"📈 *Signaux* — BUY/SHORT sur 14 actifs\n"
            f"📊 *RSI* — 9 actifs en temps réel\n"
            f"🏆 *Top 5* — Meilleures actions du jour\n"
            f"🎰 *Pépite* — Actif sous-coté à fort potentiel\n"
            f"💬 *Citation* — Sagesse des grands traders\n"
            f"🔔 *Alertes* — Notifications sur tes prix cibles\n"
            f"📊 *Paper Trading* — Investis sans risque\n"
            f"📅 *Score marché* — Santé globale en 1 chiffre\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌅 Briefing auto chaque matin à *8h00*\n"
            f"📅 Bilan hebdo chaque *dimanche soir*\n"
            f"✔️ Vérifié par des professionnels de la finance\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        msg = (
            f"🏠 *ASSISTANT MARCHÉ FINANCIER*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆓 *GRATUIT* — Actu marché quotidienne\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👑 *PREMIUM — {PRIX_MENSUEL}/mois*\n"
            f"✅ Signaux BUY/SHORT — 14 actifs (crypto + actions)\n"
            f"✅ RSI — 9 actifs en temps réel\n"
            f"✅ Paper Trading — Entraîne-toi sans risque\n"
            f"✅ Alertes de prix personnalisées\n"
            f"✅ Score marché quotidien\n"
            f"✅ Pépite du jour + Citation exclusive\n"
            f"✅ Briefing auto 8h + Bilan hebdo dimanche\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 PayPal • ⚡ Accès quasi-instantané • 🛎️ SAV 7j/7\n\n"
            f"⬇️ *Commence ou passe Premium :*"
        )
    send_message(chat_id, msg, reply_markup=main_menu(chat_id))

def cmd_start(chat_id, name=""):
    register_user(chat_id, name)
    cmd_accueil(chat_id, name)

def cmd_welcome_premium(chat_id, name):
    send_message(chat_id, "✨ ✨ ✨\n\n*Bienvenue dans le cercle Premium.*\n\n✨ ✨ ✨")
    time.sleep(1)
    quote = get_daily_quote()
    send_message(chat_id,
        f"━━━━━━━━━━━━━━━━━━━━\n💎 *TON ACCÈS VIP EST ACTIF*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Tu rejoins une sélection d'investisseurs qui reçoivent chaque jour les meilleures analyses, "
        f"vérifiées par des professionnels de la finance.\n\n"
        f"🌅 Dès demain matin à *8h00*, ton briefing t'attendra.\n"
        f"📅 Chaque dimanche soir, ton bilan de la semaine.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n💬 *Citation du jour*\n\n_{quote}_\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⬇️ *Explore tes outils exclusifs :*",
        reply_markup=main_menu(chat_id)
    )

def cmd_moncompte(chat_id):
    user = get_user(chat_id)
    if is_admin(chat_id):
        send_message(chat_id, "🛡️ *COMPTE ADMIN*\nAccès illimité.",
            reply_markup={"inline_keyboard": [[{"text": "🔙 Retour", "callback_data": "/menu_retour"}]]})
    elif is_premium(chat_id):
        exp = user.get("expiry", "Illimité")
        balance = user.get("paper_balance", 10000)
        alertes = len(user.get("alertes", []))
        send_message(chat_id,
            f"━━━━━━━━━━━━━━━━━━━━\n💎 *CARTE MEMBRE PREMIUM*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *{user.get('name','Membre')}*\n"
            f"🏆 Statut : *Premium Actif* ✅\n"
            f"📅 Valable jusqu'au : *{exp}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Paper Trading : *{balance:,.2f}$*\n"
            f"🔔 Alertes actives : *{alertes}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"_Merci de faire partie du cercle Premium._ 🙏",
            reply_markup={"inline_keyboard": [
                [{"text": "🛎️ SAV", "callback_data": "/sav"}],
                [{"text": "🔙 Retour", "callback_data": "/menu_retour"}]
            ]}
        )
    else:
        send_message(chat_id,
            f"👤 *TON COMPTE*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Nom : *{user.get('name','Membre')}*\nStatut : 🆓 Gratuit\n\n"
            f"Passe Premium pour tout débloquer ⚡",
            reply_markup={"inline_keyboard": [
                [{"text": f"👑 Passer Premium — {PRIX_MENSUEL}/mois", "url": PAYMENT_LINK}],
                [{"text": "🔙 Retour", "callback_data": "/menu_retour"}]
            ]}
        )

def cmd_actu(chat_id):
    lang = get_lang(chat_id)
    send_message(chat_id, "⏳ *Analyse en cours...* (~30s) ☕")
    news = get_news()
    market = get_market_data()
    summary = generate_summary(news, market, lang)
    send_message(chat_id, f"📊 *RÉSUMÉ MARCHÉ — {now_paris().strftime('%d/%m/%Y %H:%M')}*\n\n{summary}")
    if not is_premium(chat_id):
        send_message(chat_id,
            f"🔒 *Veux-tu aller plus loin ?*\n\nSignaux BUY/SHORT • RSI • Paper Trading • Alertes prix",
            reply_markup={"inline_keyboard": [
                [{"text": f"👑 Premium — {PRIX_MENSUEL}/mois", "url": PAYMENT_LINK}],
                [{"text": "🔙 Menu", "callback_data": "/menu_retour"}]
            ]}
        )
    else:
        send_message(chat_id, "🔄", reply_markup=main_menu(chat_id))

def cmd_signal(chat_id, asset_key):
    if not is_premium(chat_id): return premium_lock(chat_id)
    asset = SIGNAL_ASSETS.get(asset_key)
    if not asset:
        send_message(chat_id, "❌ Actif non reconnu.", reply_markup=menu_signaux()); return
    ticker, name = asset
    lang = get_lang(chat_id)
    send_message(chat_id, f"⏳ *Analyse {name}...*")
    news = get_news()
    signal = generate_trade_signal(name, ticker, news, lang)
    send_message(chat_id, f"📈 *SIGNAL {name} — {now_paris().strftime('%d/%m/%Y %H:%M')}*\n\n{signal}")
    send_message(chat_id, "🔄 *Autre signal ?*", reply_markup=menu_signaux())

def cmd_rsi(chat_id, asset_key):
    if not is_premium(chat_id): return premium_lock(chat_id)
    asset = RSI_ASSETS.get(asset_key)
    if not asset:
        send_message(chat_id, "❌ Actif non reconnu.", reply_markup=menu_rsi()); return
    ticker, name = asset
    send_message(chat_id, f"⏳ *RSI {name}...*")
    try:
        val = compute_rsi(ticker)
        if val is None:
            send_message(chat_id, "❌ Données insuffisantes."); return
        if val < 30:
            zone = "🟢 SURVENTE — Zone haussière potentielle"
            bar = "🟩🟩🟩⬜⬜⬜⬜⬜⬜⬜"
            conseil = "Signal d'achat possible"
        elif val > 70:
            zone = "🔴 SURACHAT — Zone baissière potentielle"
            bar = "🟩🟩🟩🟩🟩🟩🟩🟥🟥🟥"
            conseil = "Risque de retournement"
        else:
            zone = "⚪ NEUTRE — Pas de signal fort"
            bar = "🟩🟩🟩🟩🟩⬜⬜⬜⬜⬜"
            conseil = "Attendre < 30 ou > 70"
        send_message(chat_id,
            f"📊 *RSI (14) — {name}*\n\n{bar}\nValeur : *{val:.1f} / 100*\n\n"
            f"Zone : {zone}\n💡 _{conseil}_\n\n_RSI<30=survente | RSI>70=surachat_")
    except Exception as e:
        print(e); send_message(chat_id, "❌ Erreur RSI.")
    send_message(chat_id, "🔄 *Autre RSI ?*", reply_markup=menu_rsi())

def cmd_top(chat_id):
    if not is_premium(chat_id): return premium_lock(chat_id)
    send_message(chat_id, "⏳ *Chargement...*")
    send_message(chat_id, get_top5())
    send_message(chat_id, "🔄", reply_markup=main_menu(chat_id))

def cmd_chance(chat_id):
    if not is_premium(chat_id): return premium_lock(chat_id)
    send_message(chat_id, "🎰 *Recherche de la pépite... (~30s)*")
    try:
        gem = generate_hidden_gem(get_news())
        send_message(chat_id, f"🎰 *PÉPITE DU JOUR — {now_paris().strftime('%d/%m/%Y %H:%M')}*\n\n{gem}")
    except Exception as e:
        print(e); send_message(chat_id, "❌ Erreur.")
    send_message(chat_id, "🔄", reply_markup=main_menu(chat_id))

def cmd_quote(chat_id):
    if not is_premium(chat_id): return premium_lock(chat_id)
    send_message(chat_id,
        f"💬 *CITATION DU JOUR — {now_paris().strftime('%d/%m/%Y')}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n{get_daily_quote()}\n\n━━━━━━━━━━━━━━━━━━━━",
        reply_markup={"inline_keyboard": [[{"text": "🔙 Menu", "callback_data": "/menu_retour"}]]}
    )

def cmd_score(chat_id):
    if not is_premium(chat_id): return premium_lock(chat_id)
    score, sentiment, conseil, bar = generate_market_score()
    send_message(chat_id,
        f"📅 *SCORE MARCHÉ — {now_paris().strftime('%d/%m/%Y')}*\n\n"
        f"┌─────────────────┐\n"
        f"│  {bar}  │\n"
        f"│     *{score}/100*          │\n"
        f"└─────────────────┘\n\n"
        f"Sentiment : {sentiment}\n"
        f"💡 _{conseil}_",
        reply_markup={"inline_keyboard": [[{"text": "🔙 Retour", "callback_data": "/menu_outils"}]]}
    )

def cmd_performance(chat_id):
    if not is_premium(chat_id): return premium_lock(chat_id)
    user = get_user(chat_id)
    joined = user.get("expiry")
    if joined:
        exp_date = datetime.strptime(joined, "%Y-%m-%d")
        start = exp_date - timedelta(days=30)
    else:
        start = now_paris() - timedelta(days=30)
    try:
        data = yf.download(["BTC-USD","^GSPC","NVDA"], period="30d", interval="1d", progress=False)["Close"]
        chg = {}
        for tk in ["BTC-USD","^GSPC","NVDA"]:
            vals = data[tk].dropna().values
            if len(vals) >= 2:
                chg[tk] = ((vals[-1] - vals[0]) / vals[0]) * 100
        btc_chg = chg.get("BTC-USD", 0)
        sp_chg = chg.get("^GSPC", 0)
        nvda_chg = chg.get("NVDA", 0)
        e_btc = "🟢" if btc_chg >= 0 else "🔴"
        e_sp = "🟢" if sp_chg >= 0 else "🔴"
        e_nv = "🟢" if nvda_chg >= 0 else "🔴"
        balance = user.get("paper_balance", 10000)
        paper_pnl = ((balance - 10000) / 10000) * 100
        e_paper = "🟢" if paper_pnl >= 0 else "🔴"
        send_message(chat_id,
            f"📈 *PERFORMANCE 30 DERNIERS JOURS*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *MARCHÉS*\n"
            f"{e_btc} Bitcoin : *{btc_chg:+.1f}%*\n"
            f"{e_sp} S&P 500 : *{sp_chg:+.1f}%*\n"
            f"{e_nv} Nvidia : *{nvda_chg:+.1f}%*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *TON PAPER TRADING*\n"
            f"{e_paper} P&L : *{paper_pnl:+.1f}%*\n"
            f"💰 Solde : *{balance:,.2f}$* (départ 10 000$)\n"
            f"━━━━━━━━━━━━━━━━━━━━",
            reply_markup={"inline_keyboard": [[{"text": "🔙 Retour", "callback_data": "/menu_outils"}]]}
        )
    except Exception as e:
        print(e); send_message(chat_id, "❌ Erreur performance.")

def cmd_avis(chat_id, name=""):
    if not is_premium(chat_id): return premium_lock(chat_id)
    user = get_user(chat_id)
    if user.get("avis_done"):
        send_message(chat_id, "⭐ *Tu as déjà laissé un avis. Merci !* 🙏",
            reply_markup={"inline_keyboard": [[{"text": "🔙 Retour", "callback_data": "/menu_outils"}]]})
        return
    send_message(chat_id,
        f"⭐ *DONNE TON AVIS*\n\n"
        f"Ton retour nous aide à améliorer le bot et rassure les nouveaux membres.\n\n"
        f"*Comment notes-tu ton expérience ?*",
        reply_markup={"inline_keyboard": [
            [{"text": "⭐⭐⭐⭐⭐ Excellent",  "callback_data": "/avis_5"},
             {"text": "⭐⭐⭐⭐ Bien",         "callback_data": "/avis_4"}],
            [{"text": "⭐⭐⭐ Correct",        "callback_data": "/avis_3"},
             {"text": "⭐⭐ Peut mieux faire", "callback_data": "/avis_2"}],
            [{"text": "🔙 Retour",             "callback_data": "/menu_outils"}],
        ]}
    )

def cmd_avis_note(chat_id, name, note):
    stars = "⭐" * note
    set_user_field(chat_id, "avis_done", True)
    set_user_field(chat_id, "avis_note", note)
    send_message(chat_id,
        f"{stars} *Merci pour ton avis !*\n\n"
        f"_Si tu as un commentaire à ajouter, écris-le maintenant._\n"
        f"_(ou appuie sur Retour pour ignorer)_",
        reply_markup={"inline_keyboard": [[{"text": "🔙 Retour", "callback_data": "/menu_outils"}]]}
    )
    set_user_field(chat_id, "sav_motif", f"[AVIS {note}★]")
    send_message(TELEGRAM_CHAT_ID,
        f"⭐ *NOUVEL AVIS REÇU*\n\n"
        f"👤 {name} | Note : {stars}\n"
        f"ID : `{chat_id}`"
    )

def cmd_alerte_new(chat_id):
    if not is_premium(chat_id): return premium_lock(chat_id)
    send_message(chat_id,
        "🔔 *NOUVELLE ALERTE DE PRIX*\n\n"
        "Écris ton alerte dans ce format :\n\n"
        "`alerte btc 100000 above`\n"
        "_→ Préviens-moi quand BTC dépasse 100 000$_\n\n"
        "`alerte eth 2000 below`\n"
        "_→ Préviens-moi quand ETH passe sous 2 000$_\n\n"
        "Actifs disponibles : btc, eth, bnb, sol, xrp, gold, aapl, nvda, msft, tsla, amzn, googl, meta, amd",
        reply_markup={"inline_keyboard": [[{"text": "🔙 Retour", "callback_data": "/menu_alertes"}]]}
    )
    set_user_field(chat_id, "sav_motif", "[ALERTE_NEW]")

def cmd_alerte_del(chat_id, idx):
    users = load_users()
    uid = str(chat_id)
    alertes = users.get(uid, {}).get("alertes", [])
    if 0 <= idx < len(alertes):
        removed = alertes.pop(idx)
        users[uid]["alertes"] = alertes
        save_users(users)
        send_message(chat_id, f"✅ Alerte supprimée : *{removed['asset']}* @ {removed['price']:,.2f}$",
            reply_markup=menu_alertes(chat_id))
    else:
        send_message(chat_id, "❌ Alerte introuvable.", reply_markup=menu_alertes(chat_id))

def parse_alerte(chat_id, text):
    """Parse 'alerte btc 100000 above' -> add alert"""
    parts = text.strip().lower().split()
    if len(parts) < 3:
        return False
    asset_key = parts[1] if len(parts) > 1 else ""
    asset = SIGNAL_ASSETS.get(asset_key)
    if not asset:
        return False
    try:
        price = float(parts[2])
    except:
        return False
    cond = parts[3] if len(parts) > 3 else "above"
    if cond not in ["above", "below"]:
        cond = "above"
    ticker, name = asset
    users = load_users()
    uid = str(chat_id)
    if uid not in users:
        users[uid] = {}
    if "alertes" not in users[uid]:
        users[uid]["alertes"] = []
    users[uid]["alertes"].append({"asset": name, "ticker": ticker, "price": price, "cond": cond})
    save_users(users)
    cond_fr = "dépasse" if cond == "above" else "passe sous"
    send_message(chat_id,
        f"✅ *Alerte créée !*\n\n"
        f"🔔 {name} — Alerte quand le prix *{cond_fr} {price:,.2f}$*\n\n"
        f"Tu recevras une notification automatiquement.",
        reply_markup=menu_alertes(chat_id)
    )
    return True

def parse_paper_order(chat_id, text):
    """Parse 'buy btc 500' or 'sell btc 100'"""
    parts = text.strip().lower().split()
    if len(parts) < 3:
        return False
    action = parts[0]
    asset_key = parts[1]
    try:
        amount = float(parts[2])
    except:
        return False
    if action == "buy":
        ok, msg = paper_buy(chat_id, asset_key, amount)
        send_message(chat_id, msg, reply_markup=menu_paper(chat_id))
        return True
    elif action == "sell":
        ok, msg = paper_sell(chat_id, asset_key, int(amount) if amount <= 100 else 100)
        send_message(chat_id, msg, reply_markup=menu_paper(chat_id))
        return True
    return False

def cmd_paper_info(chat_id):
    if not is_premium(chat_id): return premium_lock(chat_id)
    send_message(chat_id,
        "📊 *PAPER TRADING*\n\n"
        "Entraîne-toi à investir avec *10 000$ virtuels* — zéro risque réel.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "*ACHETER*\n`buy btc 500` → Achète 500$ de Bitcoin\n"
        "`buy aapl 200` → Achète 200$ d'Apple\n\n"
        "*VENDRE*\n`sell btc 100` → Vend 100% de ta position BTC\n"
        "`sell nvda 50` → Vend 50% de ta position Nvidia\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Actifs : btc, eth, bnb, sol, xrp, gold, aapl, nvda, msft, tsla, amzn, googl, meta, amd",
        reply_markup=menu_paper(chat_id)
    )

# ================== SAV ==================
def cmd_sav(chat_id, name=""):
    send_message(chat_id,
        f"🛎️ *SERVICE CLIENT*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*Pour quel motif nous contacter ?*",
        reply_markup={"inline_keyboard": [
            [{"text": "🔧 Problème technique",   "callback_data": "/sav_tech"}],
            [{"text": "💳 Problème de paiement", "callback_data": "/sav_paiement"}],
            [{"text": "💡 Suggestion",            "callback_data": "/sav_suggestion"}],
            [{"text": "❓ Autre",                 "callback_data": "/sav_autre"}],
            [{"text": "🔙 Retour",               "callback_data": "/menu_retour"}],
        ]}
    )

def cmd_sav_motif(chat_id, name, motif):
    motifs = {
        "tech":       "🔧 Problème technique",
        "paiement":   "💳 Problème de paiement",
        "suggestion": "💡 Suggestion",
        "autre":      "❓ Autre demande",
    }
    titre = motifs.get(motif, "❓ Demande")
    set_user_field(chat_id, "sav_motif", titre)
    send_message(chat_id,
        f"{titre}\n\n📝 *Décris ton problème ci-dessous.*\n_L'équipe te répond directement ici._",
        reply_markup={"inline_keyboard": [[{"text": "🔙 Retour SAV", "callback_data": "/sav"}]]}
    )

def notify_admin_sav(chat_id, name, text):
    user = get_user(chat_id)
    motif = user.get("sav_motif", "Non précisé")
    plan = "👑 Premium" if is_premium(chat_id) else "🆓 Gratuit"
    send_message(TELEGRAM_CHAT_ID,
        f"🛎️ *NOUVEAU TICKET SAV*\n━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *{name}* | {plan}\n🆔 `{chat_id}`\n📂 {motif}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n💬 _{text}_\n\n"
        f"↩️ Répondre : `/repondre {chat_id} [message]`"
    )

# ================== ADMIN ==================
def cmd_admin(chat_id, text):
    if not is_admin(chat_id): return
    parts = text.strip().split()
    cmd = parts[0]
    if cmd == "/addpremium" and len(parts) >= 4:
        expiry = add_premium(parts[1], parts[2], int(parts[3]))
        send_message(chat_id, f"✅ Premium activé : {parts[2]} ({parts[1]}) jusqu'au {expiry}")
        cmd_welcome_premium(int(parts[1]), parts[2])
    elif cmd == "/removepremium" and len(parts) >= 2:
        remove_premium(parts[1]); send_message(chat_id, f"✅ Premium supprimé pour {parts[1]}")
    elif cmd == "/repondre" and len(parts) >= 3:
        msg = " ".join(parts[2:])
        send_message(int(parts[1]), f"📩 *Réponse du Service Client*\n\n{msg}\n\n_Tape /sav pour nous recontacter._")
        send_message(chat_id, f"✅ Réponse envoyée à {parts[1]}")
    elif cmd == "/listusers":
        users = load_users()
        lines = [f"👥 *UTILISATEURS ({len(users)})*\n"]
        for uid, u in users.items():
            plan = "👑" if u.get("plan") == "premium" else "🆓"
            lines.append(f"{plan} {u.get('name','?')} | {uid} | exp: {u.get('expiry','—')}")
        send_message(chat_id, "\n".join(lines))
    elif cmd == "/stats":
        users = load_users()
        total = len(users)
        prem = sum(1 for u in users.values() if u.get("plan") == "premium")
        rev = prem * float(PRIX_MENSUEL.replace("€",""))
        send_message(chat_id,
            f"📈 *STATS BOT*\n\n👥 Total: {total}\n👑 Premium: {prem}\n🆓 Gratuit: {total-prem}\n💰 Revenus estimés: {rev:.2f}€/mois")
    else:
        send_message(chat_id,
            "🛠️ *COMMANDES ADMIN*\n\n"
            "`/addpremium [id] [nom] [jours]`\n`/removepremium [id]`\n"
            "`/repondre [id] [message]`\n`/listusers`\n`/stats`")

# ================== AI WALLET PUBLIC ==================
AI_WALLET_FILE = "ai_wallet.json"
AI_WALLET_INITIAL = 10000.0
AI_MAX_POSITION_PCT = 0.20   # max 20% du portefeuille par actif
AI_STOP_LOSS_PCT    = 0.08   # stop loss automatique à -8%
AI_TAKE_PROFIT_PCT  = 0.18   # take profit à +18%

AI_TRADABLE = {
    "btc":   ("BTC-USD",  "₿ Bitcoin"),
    "eth":   ("ETH-USD",  "🔷 Ethereum"),
    "sol":   ("SOL-USD",  "🔵 Solana"),
    "nvda":  ("NVDA",     "🟢 Nvidia"),
    "aapl":  ("AAPL",     "🍎 Apple"),
    "msft":  ("MSFT",     "🔵 Microsoft"),
    "tsla":  ("TSLA",     "🚗 Tesla"),
    "meta":  ("META",     "📘 Meta"),
    "amzn":  ("AMZN",     "📦 Amazon"),
    "gold":  ("GC=F",     "🥇 Or"),
}

def load_ai_wallet():
    if os.path.exists(AI_WALLET_FILE):
        with open(AI_WALLET_FILE, "r") as f:
            return json.load(f)
    # Création initiale
    wallet = {
        "balance": AI_WALLET_INITIAL,
        "portfolio": {},
        "history": [],
        "created": now_paris().strftime("%d/%m/%Y"),
        "last_trade": None,
        "total_trades": 0,
        "winning_trades": 0,
    }
    save_ai_wallet(wallet)
    return wallet

def save_ai_wallet(wallet):
    with open(AI_WALLET_FILE, "w") as f:
        json.dump(wallet, f, indent=2)

def ai_wallet_total_value(wallet):
    total = wallet["balance"]
    for key, pos in wallet.get("portfolio", {}).items():
        price = get_asset_price(pos["ticker"]) or pos.get("buy_price", 0)
        total += pos["qty"] * price
    return total

def ai_wallet_pnl(wallet):
    total = ai_wallet_total_value(wallet)
    pnl = total - AI_WALLET_INITIAL
    pnl_pct = (pnl / AI_WALLET_INITIAL) * 100
    return pnl, pnl_pct

def ai_get_technicals(ticker):
    """RSI, MACD, SMA20/50, volume, volatilité, support/résistance"""
    try:
        data = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        if data.empty or len(data) < 20:
            return {}
        close = data["Close"]
        if hasattr(close, "columns"): close = close.iloc[:, 0]
        close = pd.Series([float(v) for v in close.values.flatten()]).dropna()
        volume = data["Volume"]
        if hasattr(volume, "columns"): volume = volume.iloc[:, 0]
        vol_s = pd.Series([float(v) for v in volume.values.flatten()]).dropna()

        # RSI 14
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = float((100 - 100/(1 + gain/loss)).iloc[-1])

        # SMA 20 / 50
        sma20 = float(close.rolling(20).mean().iloc[-1])
        sma50 = float(close.rolling(min(50,len(close))).mean().iloc[-1])

        # MACD 12/26/9
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_val = float((ema12 - ema26).iloc[-1])
        macd_sig = float((ema12 - ema26).ewm(span=9).mean().iloc[-1])

        # Volume ratio vs moyenne 20j
        avg_vol = float(vol_s.tail(20).mean())
        vol_ratio = float(vol_s.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0

        # Volatilité 14j
        volatility = float(close.pct_change().dropna().tail(14).std() * 100)

        # Variations
        current = float(close.iloc[-1])
        chg1d  = (current - float(close.iloc[-2]))  / float(close.iloc[-2])  * 100 if len(close)>=2  else 0
        chg7d  = (current - float(close.iloc[-7]))  / float(close.iloc[-7])  * 100 if len(close)>=7  else 0
        chg30d = (current - float(close.iloc[-30])) / float(close.iloc[-30]) * 100 if len(close)>=30 else 0

        # Support / Résistance 20j
        high20 = float(close.tail(20).max())
        low20  = float(close.tail(20).min())

        return {
            "rsi": round(rsi, 1),
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2),
            "vs_sma20": "dessus" if current > sma20 else "dessous",
            "vs_sma50": "dessus" if current > sma50 else "dessous",
            "macd_cross": "haussier" if macd_val > macd_sig else "baissier",
            "vol_ratio": round(vol_ratio, 2),
            "volatility": round(volatility, 2),
            "chg1d": round(chg1d, 2),
            "chg7d": round(chg7d, 2),
            "chg30d": round(chg30d, 2),
            "resistance": round(high20, 2),
            "support": round(low20, 2),
            "dist_resist": round((high20 - current)/current*100, 2),
            "dist_support": round((current - low20)/current*100, 2),
        }
    except Exception as e:
        print(f"Erreur technicals {ticker}: {e}")
        return {}

def generate_ai_trade_decision(news_list, market_str, wallet):
    now = now_paris()

    # Résumé du portefeuille actuel
    portfolio_str = ""
    for key, pos in wallet.get("portfolio", {}).items():
        price = get_asset_price(pos["ticker"]) or pos.get("buy_price", 0)
        is_short = pos.get("type") == "SHORT"
        if is_short:
            pnl_pct = (pos["buy_price"] - price) / pos["buy_price"] * 100
        else:
            pnl_pct = (price - pos["buy_price"]) / pos["buy_price"] * 100
        portfolio_str += f"  - {pos['name']} ({pos.get('type','LONG')}): qty={pos['qty']:.4f} | entry={pos['buy_price']:,.2f}$ | actuel={price:,.2f}$ | P&L={pnl_pct:+.1f}%\n"

    # Indicateurs techniques pour tous les actifs
    tech_str = ""
    for key, (ticker, name) in AI_TRADABLE.items():
        t = ai_get_technicals(ticker)
        if t:
            tech_str += (
                f"  {name} [{key}]: RSI={t['rsi']} | MACD={t['macd_cross']} | "
                f"SMA20={t['vs_sma20']} | SMA50={t['vs_sma50']} | Vol x{t['vol_ratio']} | "
                f"1j={t['chg1d']:+.1f}% 7j={t['chg7d']:+.1f}% 30j={t['chg30d']:+.1f}% | "
                f"Support={t['support']} Résist={t['resistance']}\n"
            )

    total_val = ai_wallet_total_value(wallet)
    win_rate = (wallet["winning_trades"] / wallet["total_trades"] * 100) if wallet["total_trades"] > 0 else 0
    hist_str = "\n".join([
        f"  {h['date']} | {h['type']}{' SHORT' if h.get('short') else ''} | {h['asset']} | P&L={h.get('pnl_pct',0):+.1f}% | {h.get('reason','')}"
        for h in wallet.get("history", [])[-6:]
    ]) or "  Aucun"

    prompt = f"""Tu es une IA de trading quantitatif autonome. Ta mission : maximiser un portefeuille virtuel de façon disciplinée.
Heure Paris : {now.strftime('%d/%m/%Y %H:%M')}

═══ PORTEFEUILLE ═══
Cash : {wallet['balance']:,.2f}$ | Total : {total_val:,.2f}$
Winrate : {win_rate:.0f}% sur {wallet['total_trades']} trades
Positions :
{portfolio_str or "  Aucune position ouverte"}

═══ HISTORIQUE (6 derniers) ═══
{hist_str}

═══ INDICATEURS TECHNIQUES (RSI · MACD · SMA · Volume) ═══
{tech_str}

═══ MARCHÉS ═══
{market_str}

═══ ACTUALITÉS (analyse fondamentale) ═══
{chr(10).join(news_list[:10])}

═══ RÈGLES ═══
1. Max 20% du portefeuille par position
2. Stop loss dur -8% et take profit +18% (gérés automatiquement)
3. VENTE ANTICIPÉE si news très négative sur position en bénéfice → emergency_sell=true (protection capital prioritaire)
4. SHORT autorisé si signal baissier fort (RSI>72 + MACD baissier + news négative confirmée)
5. COVER (clôturer un short) si le signal baissier s'inverse
6. Ratio risque/gain min 1:2 SAUF urgence news
7. Conviction < 60% → HOLD obligatoire
8. Max 3 décisions par appel
9. Apprends de tes erreurs passées (historique ci-dessus)

═══ RÉPONSE (JSON strict, rien d'autre) ═══
{{
  "decisions": [
    {{
      "action": "BUY"|"SELL"|"SHORT"|"COVER"|"HOLD",
      "asset_key": "btc",
      "amount_usd": 800,
      "sell_pct": 100,
      "emergency_sell": false,
      "reason": "Raison courte max 90 chars",
      "conviction": 75,
      "technical_basis": "RSI=28 survente + MACD haussier",
      "fundamental_basis": "Adoption BTC par ETF record"
    }}
  ],
  "analyse": "Contexte marché actuel en 2 phrases"
}}
Si aucune opportunité → decisions: [{{"action":"HOLD","reason":"..."}}]"""

    try:
        raw = call_groq(prompt, max_tokens=700, temperature=0.25)
        raw = raw.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].replace("json","").strip() if len(parts) > 1 else parts[0]
        # Cherche le premier { et le dernier }
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
    except Exception as e:
        print(f"Erreur JSON décision IA: {e}")
        return {"decisions": [{"action": "HOLD", "reason": "Parse error"}], "analyse": ""}

def ai_execute_trades(wallet, decisions):
    executed = []
    for d in decisions:
        action = d.get("action","HOLD").upper()
        if action == "HOLD": continue
        asset_key = d.get("asset_key","")
        asset = AI_TRADABLE.get(asset_key)
        if not asset: continue
        ticker, name = asset
        price = get_asset_price(ticker)
        if not price: continue
        reason    = d.get("reason","")
        conviction = d.get("conviction", 50)
        emergency = d.get("emergency_sell", False)
        tech      = d.get("technical_basis","")
        fund      = d.get("fundamental_basis","")
        portfolio = wallet.get("portfolio", {})
        total_val = ai_wallet_total_value(wallet)

        # ── BUY (LONG) ──
        if action == "BUY":
            amount = min(float(d.get("amount_usd", 500)), wallet["balance"])
            amount = min(amount, total_val * AI_MAX_POSITION_PCT)
            if amount < 10: continue
            qty = amount / price
            short_key = f"{asset_key}_short"
            # Ferme le short inverse automatiquement
            if short_key in portfolio:
                pos = portfolio.pop(short_key)
                short_pnl = (pos["buy_price"] - price) * pos["qty"]
                wallet["balance"] += pos["qty"] * pos["buy_price"] + short_pnl
                wallet["total_trades"] += 1
                if short_pnl >= 0: wallet["winning_trades"] += 1
                executed.append({"type":"COVER","asset":name,"amount":pos["qty"]*price,"price":price,"qty":pos["qty"],"pnl":short_pnl,"pnl_pct":(short_pnl/(pos["buy_price"]*pos["qty"]))*100,"reason":"Auto-cover","conviction":100,"short":True,"tech":"","fund":""})
                portfolio = wallet.get("portfolio",{})
            if asset_key in portfolio:
                tq = portfolio[asset_key]["qty"] + qty
                tc = portfolio[asset_key]["qty"] * portfolio[asset_key]["buy_price"] + amount
                portfolio[asset_key].update({"qty": tq, "buy_price": tc/tq})
            else:
                portfolio[asset_key] = {"qty":qty,"buy_price":price,"name":name,"ticker":ticker,"type":"LONG","date":now_paris().strftime("%d/%m/%Y %H:%M")}
            wallet["portfolio"] = portfolio
            wallet["balance"] -= amount
            wallet["total_trades"] += 1
            executed.append({"type":"BUY","asset":name,"amount":amount,"price":price,"qty":qty,"pnl":0,"pnl_pct":0,"reason":reason,"conviction":conviction,"emergency":False,"short":False,"tech":tech,"fund":fund})

        # ── SHORT ──
        elif action == "SHORT":
            amount = min(float(d.get("amount_usd", 500)), wallet["balance"])
            amount = min(amount, total_val * AI_MAX_POSITION_PCT)
            if amount < 10: continue
            short_key = f"{asset_key}_short"
            if short_key in portfolio: continue  # déjà short
            qty = amount / price
            portfolio[short_key] = {"qty":qty,"buy_price":price,"name":name,"ticker":ticker,"type":"SHORT","date":now_paris().strftime("%d/%m/%Y %H:%M")}
            wallet["portfolio"] = portfolio
            wallet["balance"] -= amount
            wallet["total_trades"] += 1
            executed.append({"type":"SHORT","asset":name,"amount":amount,"price":price,"qty":qty,"pnl":0,"pnl_pct":0,"reason":reason,"conviction":conviction,"emergency":False,"short":True,"tech":tech,"fund":fund})

        # ── COVER (clôture short) ──
        elif action == "COVER":
            short_key = f"{asset_key}_short"
            if short_key not in portfolio: continue
            pos = portfolio.pop(short_key)
            pnl = (pos["buy_price"] - price) * pos["qty"]
            proceeds = pos["qty"] * pos["buy_price"] + pnl
            pnl_pct = pnl / (pos["buy_price"] * pos["qty"]) * 100 if pos["qty"] > 0 else 0
            wallet["portfolio"] = portfolio
            wallet["balance"] += proceeds
            wallet["total_trades"] += 1
            if pnl >= 0: wallet["winning_trades"] += 1
            executed.append({"type":"COVER","asset":name,"amount":proceeds,"price":price,"qty":pos["qty"],"pnl":pnl,"pnl_pct":pnl_pct,"reason":reason,"conviction":conviction,"emergency":False,"short":True,"tech":tech,"fund":fund})

        # ── SELL (long, avec possible urgence news) ──
        elif action == "SELL":
            if asset_key not in portfolio: continue
            pos = portfolio[asset_key]
            sell_pct = min(100, max(1, int(d.get("sell_pct", 100))))
            qty_sell = pos["qty"] * (sell_pct / 100)
            proceeds = qty_sell * price
            pnl = proceeds - pos["buy_price"] * qty_sell
            pnl_pct = pnl / (pos["buy_price"] * qty_sell) * 100 if qty_sell > 0 else 0
            if sell_pct >= 100: del portfolio[asset_key]
            else: portfolio[asset_key]["qty"] -= qty_sell
            wallet["portfolio"] = portfolio
            wallet["balance"] += proceeds
            wallet["total_trades"] += 1
            if pnl >= 0: wallet["winning_trades"] += 1
            executed.append({"type":"SELL","asset":name,"amount":proceeds,"price":price,"qty":qty_sell,"pnl":pnl,"pnl_pct":pnl_pct,"reason":reason,"conviction":conviction,"emergency":emergency,"short":False,"tech":tech,"fund":fund})

    return executed

def ai_check_stops(wallet):
    """Stop loss -8% et take profit +18%, gère LONG et SHORT"""
    auto_closed = []
    portfolio = dict(wallet.get("portfolio", {}))
    for key, pos in list(portfolio.items()):
        price = get_asset_price(pos["ticker"])
        if not price: continue
        is_short = pos.get("type") == "SHORT"
        pnl_pct = ((pos["buy_price"] - price) if is_short else (price - pos["buy_price"])) / pos["buy_price"] * 100
        reason = None
        if pnl_pct <= -(AI_STOP_LOSS_PCT * 100):   reason = f"🛑 Stop loss {pnl_pct:.1f}%"
        elif pnl_pct >= (AI_TAKE_PROFIT_PCT * 100): reason = f"✅ Take profit +{pnl_pct:.1f}%"
        if reason:
            if is_short:
                pnl = (pos["buy_price"] - price) * pos["qty"]
                proceeds = pos["qty"] * pos["buy_price"] + pnl
            else:
                proceeds = pos["qty"] * price
                pnl = proceeds - pos["buy_price"] * pos["qty"]
            del portfolio[key]
            wallet["portfolio"] = portfolio
            wallet["balance"] += proceeds
            wallet["total_trades"] += 1
            if pnl >= 0: wallet["winning_trades"] += 1
            auto_closed.append({"type":"COVER" if is_short else "SELL","asset":pos["name"],"amount":proceeds,"price":price,"qty":pos["qty"],"pnl":pnl,"pnl_pct":pnl_pct,"reason":reason,"conviction":100,"emergency":False,"short":is_short,"tech":"","fund":""})
    return auto_closed

def ai_run_analysis():
    """Analyse + trade IA — appelée plusieurs fois par jour"""
    print(f"🤖 Analyse IA {now_paris().strftime('%H:%M')}")
    wallet = load_ai_wallet()
    news = get_news()
    market = get_market_data()

    auto_closed = ai_check_stops(wallet)
    result = generate_ai_trade_decision(news, market, wallet)
    executed = ai_execute_trades(wallet, result.get("decisions", []))
    all_trades = auto_closed + executed
    analyse = result.get("analyse", "")

    now_str = now_paris().strftime("%d/%m/%Y %H:%M")
    for tr in all_trades:
        wallet["history"].append({
            "date": now_str, "type": tr["type"], "asset": tr["asset"],
            "price": tr["price"], "qty": tr["qty"], "amount": tr["amount"],
            "pnl": tr.get("pnl",0), "pnl_pct": tr.get("pnl_pct",0),
            "reason": tr["reason"], "conviction": tr.get("conviction",50),
            "short": tr.get("short",False), "emergency": tr.get("emergency",False),
            "tech": tr.get("tech",""), "fund": tr.get("fund",""),
        })
    wallet["last_trade"] = now_str
    save_ai_wallet(wallet)

    if not all_trades:
        print(f"IA HOLD — {analyse[:60] if analyse else 'RAS'}")
        return

    total_val = ai_wallet_total_value(wallet)
    pnl, pnl_pct = ai_wallet_pnl(wallet)
    e = "🟢" if pnl >= 0 else "🔴"
    icons = {"BUY":"📥","SELL":"📤","SHORT":"🔻","COVER":"🔼"}
    lines = [f"🤖 *WALLET IA — {now_paris().strftime('%d/%m/%Y %H:%M')}*\n"]
    if analyse: lines.append(f"📊 _{analyse}_\n")
    for tr in all_trades:
        ic = icons.get(tr["type"],"•")
        short_tag  = " _(short)_"      if tr.get("short")     else ""
        emerg_tag  = " ⚠️ _urgence_"  if tr.get("emergency") else ""
        pnl_str    = f" | P&L *{tr.get('pnl_pct',0):+.1f}%*" if tr["type"] in ["SELL","COVER"] else ""
        lines.append(f"{ic} *{tr['type']} {tr['asset']}*{short_tag} @ {tr['price']:,.2f}${pnl_str}{emerg_tag}")
        lines.append(f"   💡 _{tr['reason']}_")
        if tr.get("tech"):  lines.append(f"   📊 _{tr['tech']}_")
        if tr.get("fund"):  lines.append(f"   📰 _{tr['fund']}_")
    lines.append(f"\n{e} *Wallet : {total_val:,.2f}$* ({pnl_pct:+.1f}% depuis création)")
    msg = "\n".join(lines)

    users = load_users()
    for target in set([TELEGRAM_CHAT_ID] + list(users.keys())):
        try:
            send_message(int(target), msg, reply_markup={"inline_keyboard":[[{"text":"📊 Voir le Wallet IA","callback_data":"/aiwallet"}]]})
        except: pass
    print(f"✅ IA: {len(all_trades)} trades | {total_val:,.2f}$")

def ai_daily_trade():
    ai_run_analysis()


def cmd_ai_wallet(chat_id):
    """Affiche le wallet IA — accessible à TOUS"""
    wallet = load_ai_wallet()
    total = ai_wallet_total_value(wallet)
    pnl, pnl_pct = ai_wallet_pnl(wallet)
    e = "🟢" if pnl >= 0 else "🔴"
    win_rate = (wallet["winning_trades"] / wallet["total_trades"] * 100) if wallet["total_trades"] > 0 else 0

    lines = [
        f"🤖 *WALLET IA — PERFORMANCE PUBLIQUE*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📅 Créé le : *{wallet.get('created','—')}*",
        f"💰 Capital départ : *10 000$*",
        f"🕐 Dernier trade : *{wallet.get('last_trade','—')}*",
        f"",
        f"━━━ 📊 RÉSUMÉ ━━━",
        f"{e} Valeur actuelle : *{total:,.2f}$*",
        f"{e} P&L total : *{pnl:+,.2f}$ ({pnl_pct:+.1f}%)*",
        f"🎯 Winrate : *{win_rate:.0f}%* sur *{wallet['total_trades']} trades*",
        f"",
    ]

    portfolio = wallet.get("portfolio", {})
    if portfolio:
        lines.append("━━━ 💼 POSITIONS OUVERTES ━━━")
        for key, pos in portfolio.items():
            price = get_asset_price(pos["ticker"]) or pos["buy_price"]
            is_short = pos.get("type") == "SHORT"
            pos_pnl = ((pos["buy_price"] - price) if is_short else (price - pos["buy_price"])) / pos["buy_price"] * 100
            ep = "🟢" if pos_pnl >= 0 else "🔴"
            tag = " 🔻SHORT" if is_short else ""
            lines.append(f"{ep} *{pos['name']}*{tag} — {pos_pnl:+.1f}% (entrée {pos.get('date','—')})")
        lines.append("")

    history = wallet.get("history", [])
    if history:
        lines.append("━━━ 📋 DERNIERS TRADES ━━━")
        icons = {"BUY":"📥","SELL":"📤","SHORT":"🔻","COVER":"🔼"}
        for h in reversed(history[-8:]):
            ic = icons.get(h["type"],"•")
            short_tag = " _(short)_" if h.get("short") else ""
            emerg_tag = " ⚠️" if h.get("emergency") else ""
            pnl_str = f" ({h.get('pnl_pct',0):+.1f}%)" if h["type"] in ["SELL","COVER"] else ""
            lines.append(f"{ic} {h['date']} — *{h['asset']}*{short_tag}{pnl_str}{emerg_tag}")
            lines.append(f"   _{h.get('reason','')}_")
            if h.get("tech"):  lines.append(f"   📊 _{h['tech']}_")
            if h.get("fund"):  lines.append(f"   📰 _{h['fund']}_")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("_L'IA analyse les marchés 3x/jour et trade en autonomie._")
    lines.append("_Elle utilise RSI, MACD, SMA, volume et actualités._")
    lines.append("_Inspire-toi de ses trades — mais fais ta propre analyse !_")

    send_message(chat_id, "\n".join(lines), reply_markup={
        "inline_keyboard": [
            [{"text": "🔄 Actualiser", "callback_data": "/aiwallet"}],
            [{"text": "👑 Rejoindre Premium", "url": PAYMENT_LINK}] if not is_premium(chat_id)
             else [{"text": "🔙 Menu", "callback_data": "/menu_retour"}],
        ]
    })



auto_sent_today = None
weekly_sent_this_week = None

def check_auto_send():
    global auto_sent_today, weekly_sent_this_week
    now = now_paris()
    today = now.strftime('%Y-%m-%d')
    week = now.strftime('%Y-%W')

    # Briefing quotidien à 8h
    if now.hour == 8 and now.minute == 0 and auto_sent_today != today:
        auto_sent_today = today
        print("Envoi auto 8h...")
        try:
            users = load_users()
            targets = [TELEGRAM_CHAT_ID] + [uid for uid, u in users.items() if u.get("plan") == "premium"]
            news = get_news(); market = get_market_data(); quote = get_daily_quote()
            summary = generate_summary(news, market)
            for target in set(targets):
                tid = int(target)
                ud = users.get(str(target), {}); uname = ud.get("name", "")
                lang = ud.get("lang", "fr")
                sal = LANGS[lang]["morning"][0]
                send_message(tid, f"{sal} *{uname}* 👋\n\n💬 _{quote}_\n\n━━━━━━━━━━━━━━━━━━━━\nTon briefing du matin 👇")
                send_message(tid, f"📊 *RÉSUMÉ MARCHÉ — {now.strftime('%d/%m/%Y')}*\n\n{summary}")
                send_message(tid, "⬇️", reply_markup=main_menu(tid))
        except Exception as e:
            print(f"Erreur 8h: {e}")

    # Bilan hebdomadaire le dimanche à 19h
    if now.weekday() == 6 and now.hour == 19 and now.minute == 0 and weekly_sent_this_week != week:
        weekly_sent_this_week = week
        print("Envoi bilan hebdo dimanche...")
        try:
            users = load_users()
            targets = [TELEGRAM_CHAT_ID] + [uid for uid, u in users.items() if u.get("plan") == "premium"]
            news = get_news(); market = get_market_data()
            for target in set(targets):
                tid = int(target)
                ud = users.get(str(target), {}); lang = ud.get("lang","fr")
                report = generate_weekly_report(news, market, lang)
                send_message(tid, f"📅 *BILAN HEBDOMADAIRE — Semaine du {now.strftime('%d/%m/%Y')}*\n\n{report}")
                send_message(tid, "🔄", reply_markup=main_menu(tid))
        except Exception as e:
            print(f"Erreur bilan hebdo: {e}")

    # Trading IA : 9h30 (ouverture EU), 14h30 (ouverture US), 20h (après clôture US/bilan soir)
    for trigger_h, trigger_m in [(9,30),(14,30),(20,0)]:
        trigger_key = f"ai_{trigger_h}_{trigger_m}_{today}"
        if now.hour == trigger_h and now.minute == trigger_m and now.second < 3:
            flag_key = f"ai_ran_{trigger_h}h{trigger_m}"
            if not globals().get(flag_key + "_" + today):
                globals()[flag_key + "_" + today] = True
                try:
                    ai_run_analysis()
                except Exception as e:
                    print(f"Erreur IA {trigger_h}h{trigger_m}: {e}")


    if now.second < 3 and now.minute % 5 == 0:
        try:
            check_alerts()
        except Exception as e:
            print(f"Erreur alertes: {e}")

# ================== ROUTING ==================
def handle_command(chat_id, text, user_name=""):
    t_low = text.strip().lower()

    # Admin
    if any(text.startswith(c) for c in ["/addpremium","/removepremium","/listusers","/stats","/repondre","/admin"]):
        cmd_admin(chat_id, text); return

    # Commandes principales
    if t_low == "/start":                    cmd_start(chat_id, user_name)
    elif t_low in ["/help","/accueil"]:      cmd_accueil(chat_id, user_name)
    elif t_low == "/actu":                   cmd_actu(chat_id)
    elif t_low == "/top":                    cmd_top(chat_id)
    elif t_low == "/chance":                 cmd_chance(chat_id)
    elif t_low == "/quote":                  cmd_quote(chat_id)
    elif t_low == "/aiwallet":                cmd_ai_wallet(chat_id)
    elif t_low == "/score":                  cmd_score(chat_id)
    elif t_low == "/performance":            cmd_performance(chat_id)
    elif t_low == "/avis":                   cmd_avis(chat_id, user_name)
    elif t_low == "/moncompte":              cmd_moncompte(chat_id)
    elif t_low == "/premium":
        send_message(chat_id,
            f"👑 *PASSER PREMIUM — {PRIX_MENSUEL}/mois*\n\nTout ce qui est inclus :\n"
            f"✅ Signaux BUY/SHORT • ✅ RSI • ✅ Paper Trading\n"
            f"✅ Alertes prix • ✅ Pépite du jour • ✅ Score marché\n"
            f"✅ Briefing 8h + Bilan dimanche • ✅ Analyses illimitées\n\n"
            f"1️⃣ Clique ci-dessous → 2️⃣ Paie via PayPal → 3️⃣ Envoie la confirmation ici\n"
            f"⚡ Accès activé quasi-instantanément",
            reply_markup={"inline_keyboard": [
                [{"text": f"💳 S'abonner — {PRIX_MENSUEL}/mois", "url": PAYMENT_LINK}],
                [{"text": "🔙 Retour", "callback_data": "/menu_retour"}]
            ]}
        )
    # Menus
    elif t_low == "/menu_signaux":           send_message(chat_id, "📈 *Choisis un actif :*", reply_markup=menu_signaux())
    elif t_low == "/menu_rsi":               send_message(chat_id, "📊 *Choisis un actif :*", reply_markup=menu_rsi())
    elif t_low == "/menu_outils":            send_message(chat_id, "🧰 *Tes outils :*", reply_markup=menu_outils())
    elif t_low == "/menu_compte":            send_message(chat_id, "⚙️ *Ton compte :*", reply_markup=menu_compte())
    elif t_low == "/menu_langue":            send_message(chat_id, "🌐 *Choisis ta langue :*", reply_markup=menu_langue())
    elif t_low == "/menu_alertes":           send_message(chat_id, "🔔 *Tes alertes :*", reply_markup=menu_alertes(chat_id))
    elif t_low == "/menu_paper":             cmd_paper_info(chat_id)
    elif t_low == "/menu_retour":            send_message(chat_id, "🔄", reply_markup=main_menu(chat_id))
    elif t_low == "/noop":                   pass
    # Signaux
    elif t_low.startswith("/signal "):       cmd_signal(chat_id, t_low.replace("/signal ","").strip())
    # RSI
    elif t_low.startswith("/rsi"):
        parts = t_low.split()
        cmd_rsi(chat_id, parts[1] if len(parts) > 1 else "btc")
    # Paper trading
    elif t_low == "/paper_portfolio":
        if not is_premium(chat_id): return premium_lock(chat_id)
        send_message(chat_id, paper_portfolio_summary(chat_id), reply_markup=menu_paper(chat_id))
    elif t_low == "/paper_buy":
        if not is_premium(chat_id): return premium_lock(chat_id)
        send_message(chat_id, "📥 *ACHETER*\n\nFormat : `buy [actif] [montant$]`\nEx : `buy btc 500`\nEx : `buy nvda 200`",
            reply_markup={"inline_keyboard": [[{"text": "🔙 Retour", "callback_data": "/menu_paper"}]]})
        set_user_field(chat_id, "sav_motif", "[PAPER_BUY]")
    elif t_low == "/paper_sell":
        if not is_premium(chat_id): return premium_lock(chat_id)
        send_message(chat_id, "📤 *VENDRE*\n\nFormat : `sell [actif] [%]`\nEx : `sell btc 100` (vend 100%)\nEx : `sell tsla 50` (vend 50%)",
            reply_markup={"inline_keyboard": [[{"text": "🔙 Retour", "callback_data": "/menu_paper"}]]})
        set_user_field(chat_id, "sav_motif", "[PAPER_SELL]")
    elif t_low == "/paper_perf":
        if not is_premium(chat_id): return premium_lock(chat_id)
        cmd_performance(chat_id)
    elif t_low == "/paper_reset":
        if not is_premium(chat_id): return premium_lock(chat_id)
        set_user_field(chat_id, "paper_balance", 10000.0)
        set_user_field(chat_id, "paper_portfolio", {})
        set_user_field(chat_id, "paper_history", [])
        send_message(chat_id, "🔄 *Paper Trading réinitialisé à 10 000$*", reply_markup=menu_paper(chat_id))
    # Alertes
    elif t_low == "/alerte_new":             cmd_alerte_new(chat_id)
    elif t_low.startswith("/alerte_del "):
        try:
            idx = int(t_low.split()[1])
            cmd_alerte_del(chat_id, idx)
        except: send_message(chat_id, "❌ Erreur.", reply_markup=menu_alertes(chat_id))
    # SAV
    elif t_low == "/sav":                    cmd_sav(chat_id, user_name)
    elif t_low in ["/sav_tech","/sav_paiement","/sav_suggestion","/sav_autre"]:
        cmd_sav_motif(chat_id, user_name, t_low.replace("/sav_",""))
    # Avis
    elif t_low.startswith("/avis_"):
        try:
            note = int(t_low.replace("/avis_",""))
            cmd_avis_note(chat_id, user_name, note)
        except: pass
    # Langue
    elif t_low.startswith("/lang "):
        lang = t_low.replace("/lang ","").strip()
        if lang in LANGS:
            set_user_field(chat_id, "lang", lang)
            flags = {"fr":"🇫🇷 Français","en":"🇬🇧 English","es":"🇪🇸 Español"}
            send_message(chat_id, f"✅ Langue changée : *{flags[lang]}*", reply_markup=main_menu(chat_id))
    # Messages libres
    else:
        user = get_user(chat_id)
        motif = user.get("sav_motif", "")

        # Paper trading orders
        if motif in ["[PAPER_BUY]", "[PAPER_SELL]"] or t_low.startswith(("buy ","sell ")):
            if parse_paper_order(chat_id, text):
                set_user_field(chat_id, "sav_motif", "")
                return

        # Alertes
        if motif == "[ALERTE_NEW]" or t_low.startswith("alerte "):
            if parse_alerte(chat_id, text):
                set_user_field(chat_id, "sav_motif", "")
                return

        # SAV / paiement
        notify_admin_sav(chat_id, user_name, text)
        set_user_field(chat_id, "sav_motif", "")
        if not is_premium(chat_id):
            send_message(chat_id,
                "⚡ *Message reçu !*\n\nTon paiement va être vérifié et ton accès activé quasi-instantanément.\nMerci 🙏",
                reply_markup=main_menu(chat_id))
        else:
            send_message(chat_id,
                "✅ *Message envoyé !*\n\nNotre équipe te répondra directement ici. 🙏",
                reply_markup=main_menu(chat_id))

# ================== BOUCLE PRINCIPALE ==================
def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset: params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=35)
        return r.json().get("result", [])
    except:
        return []

print("🤖 Bot démarré !")
print("Fonctionnalités : Signaux(14) • RSI(9) • Paper Trading • Alertes • Score • Hebdo • Langues(FR/EN/ES)")

offset = None
while True:
    try:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            if "callback_query" in update:
                cq = update["callback_query"]
                answer_callback(cq["id"])
                cid = cq["message"]["chat"]["id"]
                uname = cq["message"]["chat"].get("first_name", "")
                print(f"Bouton: {cq['data'][:30]} | {cid}")
                handle_command(cid, cq["data"], uname)
            elif "message" in update:
                msg = update["message"]
                txt = msg.get("text", "")
                cid = msg["chat"]["id"]
                uname = msg["chat"].get("first_name", "")
                if txt:
                    print(f"Message: {txt[:30]} | {cid}")
                    handle_command(cid, txt, uname)
        check_auto_send()
        time.sleep(1)
    except Exception as e:
        print(f"Erreur boucle: {e}")
        time.sleep(5)
