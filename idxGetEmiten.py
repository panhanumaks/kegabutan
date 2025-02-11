import time
import json
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import random
import requests

BOT_TOKEN = "7731319192:AAHMFf44SLzMRrJZ8LoXkymPlBLCcJUOslg"
CHAT_ID = "-1002277216398"


def send_telegram_message(message):
    """Mengirim pesan ke Telegram bot"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logger.info("Notifikasi dikirim ke Telegram")
    except requests.exceptions.RequestException as e:
        logger.error(f"Gagal mengirim notifikasi: {e}")


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Path untuk menyimpan hasil scraping
NEWS_JSON_PATH = "news_data.json"
MATCHED_JSON_PATH = "matched_news.json"
SAHAM_JSON_PATH = "saham_data.json"


# Load existing news data to avoid duplicates
def load_existing_news():
    try:
        with open(NEWS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_saham_data():
    try:
        with open(SAHAM_JSON_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_news_data():
    now = datetime.now()
    filtered_news = []
    seen_titles = set()

    for news in collected_news.values():
        if (
            now - datetime.strptime(news["date"], "%Y-%m-%d %H:%M:%S")
        ).days < 7 and news["title"] not in seen_titles:
            filtered_news.append(news)
            seen_titles.add(news["title"])

    with open(NEWS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(filtered_news, f, ensure_ascii=False, indent=4)


def save_matched_news():
    with open(MATCHED_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(matched_news, f, ensure_ascii=False, indent=4)


def convert_time(date_str):
    now = datetime.now()
    if "detik" in date_str:
        seconds = int(date_str.split()[0])
        return now - timedelta(seconds=seconds)
    elif "menit" in date_str:
        minutes = int(date_str.split()[0])
        return now - timedelta(minutes=minutes)
    elif "jam" in date_str:
        hours = int(date_str.split()[0])
        return now - timedelta(hours=hours)
    elif "hari" in date_str:
        days = int(date_str.split()[0])
        return now - timedelta(days=days)
    return None


def scrape_google_news(query, start_page, end_page):
    logger.info(
        f"Mencari berita untuk: {query}, dari halaman {start_page} sampai {end_page}"
    )

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    collected_news = {}

    for page in range(start_page, end_page + 1):
        start_index = (page - 1) * 10
        search_url = f"https://www.google.com/search?q={query}&tbm=nws&tbs=qdr:d&start={start_index}"
        driver.get(search_url)

        logger.info(f"Mencari berita untuk: {query}, dari halaman {page}")

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".SoaBEf"))
            )
            news_cards = driver.find_elements(By.CSS_SELECTOR, ".SoaBEf")

            for card in news_cards:
                try:
                    title_element = card.find_element(By.CSS_SELECTOR, ".nDgy9d")
                    url_element = card.find_element(By.CSS_SELECTOR, "a")
                    date_element = card.find_element(By.CSS_SELECTOR, ".OSrXXb")

                    title = title_element.text.strip()
                    url = url_element.get_attribute("href").strip()
                    date_str = date_element.text.strip()
                    date = convert_time(date_str)

                    if url not in collected_news:
                        collected_news[url] = {
                            "url": url,
                            "title": title,
                            "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        logger.info(f"[{date_str}] {title} - {url}")
                        check_and_save_matched_news(title, url, date)
                except Exception as e:
                    logger.warning(f"Gagal mengambil berita: {e}")

            save_news_data()
        except Exception as e:
            error_message = (
                f"⚠️ *Scraping Error!* ⚠️\n\nError fetching news: page {start_index}"
            )
            send_telegram_message(error_message)
            logger.error(f"Error fetching news: page {start_index}")
            time.sleep(random.uniform(120, 900))
    driver.quit()
    save_news_data()


def check_and_save_matched_news(title, url, date):
    saham_list = load_saham_data()
    matched_saham = [saham for saham in saham_list if saham in title]

    if matched_saham and not any(news["title"] == title for news in matched_news):
        matched_news.append(
            {
                "url": url,
                "title": title,
                "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                "saham": matched_saham,
            }
        )

    matched_news.sort(key=lambda x: x["date"], reverse=True)
    save_matched_news()


def get_saham_data():
    logger.info("Mengambil data saham dari IDX...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(
            "https://www.idx.co.id/id/data-pasar/ringkasan-perdagangan/ringkasan-saham"
        )

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "footer__row-count__select"))
        )
        time.sleep(random.uniform(2, 4))

        dropdown = driver.find_element(By.CLASS_NAME, "footer__row-count__select")
        select = Select(dropdown)
        select.select_by_value("-1")  # Tampilkan semua data
        time.sleep(random.uniform(2, 4))

        table = driver.find_element(By.ID, "vgt-table")
        rows = table.find_elements(By.XPATH, ".//tbody/tr")

        saham_data = [row.find_element(By.XPATH, ".//td[1]/span").text for row in rows]

        with open("saham_data.json", "w", encoding="utf-8") as f:
            json.dump(saham_data, f, ensure_ascii=False, indent=4)

        logger.info("Data berhasil disimpan ke saham_data.json")
        send_telegram_message("*Scraping Data Saham Berhasil!*")

        return saham_data

    except Exception as e:
        logger.error(f"Scraping gagal: {e}")
        try:
            with open("listEmiten.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("File listEmiten.json tidak ditemukan.")
            return []
    finally:
        driver.quit()


def load_existing_matched_news():
    try:
        with open(MATCHED_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


if __name__ == "__main__":
    while True:
        send_telegram_message("*Scraping Dimulai!*")
        get_saham_data()
        collected_news = {news["url"]: news for news in load_existing_news()}
        matched_news = load_existing_matched_news()

        for start in range(1, 2001, 200):
            end = min(start + 199, 2000)
            send_telegram_message(f"*Scraping Dimulai dari Halaman {start} - {end}!*")
            scrape_google_news("saham", start, end)
            send_telegram_message(
                f"✅ *Scraping Selesai! 🎉*\nTelah fetch {start} - {end} halaman berita saham terbaru!"
            )
            time.sleep(random.uniform(60, 180))

        send_telegram_message(
            f"Menunggu 5 - 10 menit sebelum scraping ulang dari halaman 1..."
        )
        time.sleep(random.uniform(300, 600))
