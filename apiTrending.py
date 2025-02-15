import time
from flask import Flask, jsonify
import json
import requests
from datetime import datetime, timedelta
from collections import Counter
from apscheduler.schedulers.background import BackgroundScheduler
import logging

app = Flask(__name__)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

MATCHED_JSON_PATH = "matched_news.json"
TELEGRAM_BOT_TOKEN = "7731319192:AAHMFf44SLzMRrJZ8LoXkymPlBLCcJUOslg"
CHAT_ID = "-1002407497809"
NEWS_CHAT_ID = "-1002200056411"


def load_matched_news():
    try:
        with open(MATCHED_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def filter_trending_saham(days, max_saham=50):
    def count_saham(start_hours_ago, end_hours_ago):
        now = datetime.now()
        start_time = now - timedelta(hours=start_hours_ago)
        end_time = now - timedelta(hours=end_hours_ago)
        saham_counter = Counter()
        for news in load_matched_news():
            news_date = datetime.strptime(news["date"], "%Y-%m-%d %H:%M:%S")
            if end_time <= news_date < start_time:
                for saham in news["saham"]:
                    saham_counter[saham] += 1
        return saham_counter

    current_counter = count_saham(0, 24 * days)
    previous_counter = count_saham(24 * days, 48 * days)

    trending_saham = [saham for saham, _ in current_counter.most_common(max_saham)]
    saham_stats = []

    news_data = load_matched_news()
    for saham in trending_saham:
        berita_list = []
        for news in news_data:
            if saham in news["saham"]:
                berita_list.append(
                    {"title": news["title"], "url": news["url"], "date": news["date"]}
                )

        saham_stats.append(
            {
                "code": saham,
                "count": current_counter[saham],
                "previous_count": previous_counter.get(saham, 0),
                "change": current_counter[saham] - previous_counter.get(saham, 0),
                "percent_change": round(
                    (
                        (current_counter[saham] - previous_counter.get(saham, 0))
                        / max(previous_counter.get(saham, 1), 1)
                    )
                    * 100,
                    2,
                ),
                "status": (
                    "📈 Naik"
                    if current_counter[saham] > previous_counter.get(saham, 0)
                    else (
                        "📉 Turun"
                        if current_counter[saham] < previous_counter.get(saham, 0)
                        else "➡️ Stabil"
                    )
                ),
                "berita": berita_list,
            }
        )

    return saham_stats, sum(current_counter.values())


with open("kode_saham.json", "r", encoding="utf-8") as f:
    saham_data = json.load(f)

saham_dict = {saham["code"]: saham["label"] for saham in saham_data}


def send_trending_saham():
    saham_stats, _ = filter_trending_saham(1)

    message = f"📈 *50 Saham Trending*\n1️⃣ *24 Jam Terakhir:*\n\n"

    message += "\n".join(
        [
            f"{i+1}. {s['code']} - {saham_dict.get(s['code'], 'Unknown')} "
            f"(Total Data: {s['count']}, "
            f"Change: {s['percent_change']}% {'📈' if s['change'] > 0 else '📉' if s['change'] < 0 else '➡️'})"
            for i, s in enumerate(saham_stats)
        ]
    )
    send_telegram_message(message)


import time


def send_news_saham():
    # Mendapatkan saham yang sedang trending, diurutkan sesuai hasil filtering
    saham_stats, _ = filter_trending_saham(1, 10)
    saham_news = {}

    for saham_info in saham_stats:
        code = saham_info["code"]
        berita_list = saham_info.get("berita", [])

        if code not in saham_news:
            saham_news[code] = []

        for berita in berita_list:
            title = berita["title"]
            url = berita["url"]
            date = berita["date"]
            saham_news[code].append(f"    📅 {date}\n    🔗 [{title}]({url})")

    # Mengirim berita maksimal 5 per chat berdasarkan urutan dari hasil filtering
    for saham_info in saham_stats:
        code = saham_info["code"]
        if code in saham_news:
            berita_list = saham_news[code]
            for i in range(0, len(berita_list), 5):
                batch = berita_list[i : i + 5]
                message = (
                    f"📰 *Berita Saham Terbaru:*\n📌 *{code}*\n"
                    + "\n".join(batch)
                    + "\n\n"
                )
                print(message + "\n\n\n")
                send_news_telegram_message(message)
                time.sleep(5)


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        logger.info(
            f"Sent message to CHAT_ID: {CHAT_ID} - Status Code: {response.status_code}"
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message: {e}")


def send_news_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": NEWS_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        logger.info(
            f"Sent message to NEWS_CHAT_ID: {NEWS_CHAT_ID} - Status Code: {response.status_code}"
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send news message: {e}")


@app.route("/api/trending-saham/<int:days>", methods=["GET"])
def api_trending_saham(days):
    saham_stats, total_data = filter_trending_saham(days)
    return jsonify({"total_data": total_data, "trending_saham": saham_stats})


scheduler = BackgroundScheduler()
if not scheduler.get_jobs():
    scheduler.add_job(send_trending_saham, "interval", minutes=60)
    scheduler.add_job(send_news_saham, "interval", minutes=60)
scheduler.start()

if __name__ == "__main__":
    try:
        send_trending_saham()
        send_news_saham()
        app.run(host="0.0.0.0", port=9000, debug=False, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
