from flask import Flask
import json
import requests
from datetime import datetime
from collections import Counter
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

MATCHED_JSON_PATH = "matched_news.json"
TELEGRAM_BOT_TOKEN = "7731319192:AAHMFf44SLzMRrJZ8LoXkymPlBLCcJUOslg"
CHAT_ID = "-1002407497809"


def load_matched_news():
    try:
        with open(MATCHED_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def filter_trending_saham(days, max_saham=50):
    now = datetime.now()
    matched_news = load_matched_news()
    saham_counter = Counter()

    for news in matched_news:
        news_date = datetime.strptime(news["date"], "%Y-%m-%d %H:%M:%S")
        if (now - news_date).days < days:
            for saham in news["saham"]:
                saham_counter[saham] += 1

    trending_saham = [saham for saham, _ in saham_counter.most_common(max_saham)]
    return trending_saham


def send_trending_saham():
    trending_1_day = filter_trending_saham(1)

    message = "📈 *50 Saham Trending*\n" "1️⃣ *24 Jam Terakhir:*\n" + "\n".join(
        trending_1_day
    )

    send_telegram_message(message)


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)


# Setup scheduler untuk kirim pesan setiap 30 menit
scheduler = BackgroundScheduler()
if not scheduler.get_jobs():
    scheduler.add_job(send_trending_saham, "interval", minutes=30)
scheduler.start()


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=9000, debug=False, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
