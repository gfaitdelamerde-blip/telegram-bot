"""Lance ce script UNE FOIS sur Railway pour remettre le wallet à zéro."""
import json
from datetime import datetime

wallet = {
    "balance": 10000.0,
    "portfolio": {},
    "history": [],
    "created": datetime.now().strftime("%d/%m/%Y"),
    "last_trade": None,
    "total_trades": 0,
    "winning_trades": 0,
}
with open("ai_wallet.json", "w") as f:
    json.dump(wallet, f, indent=2)
print("✅ Wallet IA réinitialisé à 10 000$")
