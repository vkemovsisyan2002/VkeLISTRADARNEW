import json
import os
from bs4 import BeautifulSoup
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
URL = "https://www.list.am/category/60?n=2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2C13%2C11&cmtype=0&crc=1"
SEEN_FILE = "seen_ads.json"


def send_telegram(text):
  api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  payload = {
      "chat_id": CHANNEL_ID,
      "text": text,
      "parse_mode": "HTML",
      "disable_web_page_preview": False,
  }
  try:
    response = requests.post(api_url, json=payload, timeout=10)
    return response.json()
  except Exception as e:
    print(f"Ошибка отправки в Telegram: {e}")
    return {}


def load_seen():
  if os.path.exists(SEEN_FILE):
    try:
      with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))
    except:
      return set()
  return set()


def save_seen(seen):
  seen_list = list(seen)[-500:]
  with open(SEEN_FILE, "w", encoding="utf-8") as f:
    json.dump(seen_list, f, ensure_ascii=False, indent=2)


def main():
  if not os.path.exists(SEEN_FILE):
    save_seen(set())

  # Расширенные заголовки настоящего браузера, чтобы List.am не блокировал
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept": (
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
      ),
      "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
      "Accept-Encoding": "gzip, deflate, br",
      "Referer": "https://www.list.am/",
      "DNT": "1",
      "Connection": "keep-alive",
      "Upgrade-Insecure-Requests": "1",
      "Sec-Fetch-Dest": "document",
      "Sec-Fetch-Mode": "navigate",
      "Sec-Fetch-Site": "same-origin",
      "Sec-Fetch-User": "?1",
  }

  print("Запрос к List.am с имитацией браузера...")
  try:
    resp = requests.get(URL, headers=headers, timeout=15)
  except Exception as e:
    print(f"Ошибка соединения с List.am: {e}")
    return

  print(f"Статус ответа List.am: {resp.status_code}")
  if resp.status_code != 200:
    print(
        f"Защита List.am всё еще блочит (код {resp.status_code}). Пропускаем"
        " цикл."
    )
    return

  soup = BeautifulSoup(resp.text, "html.parser")
  seen = load_seen()
  new_seen = set(seen)

  items = soup.find_all("a", href=lambda x: x and x.startswith("/item/"))
  print(f"Найдено ссылок на странице: {len(items)}")

  found_new = []

  for item in items:
    href = item.get("href")
    parts = href.split("/")
    if len(parts) > 2:
      ad_id = parts[2]
      if ad_id not in seen:
        title = item.text.strip().replace("\n", " ")
        title = " ".join(title.split())
        full_url = f"https://www.list.am{href}"
        found_new.append((ad_id, title, full_url))
        new_seen.add(ad_id)

  if len(seen) == 0 and len(found_new) > 0:
    print(
        "Первый запуск: инициализация базы объявлений без отправки в канал..."
    )
    save_seen(new_seen)
    print("База успешно инициализирована!")
    return

  for ad_id, title, full_url in reversed(found_new):
    msg = (
        f"🏠 <b>Новая квартира в Ереване!</b>\n\n{title}\n\n🔗"
        f" <a href='{full_url}'>Посмотреть на List.am</a>"
    )
    print(f"Отправка объявления {ad_id}...")
    res = send_telegram(msg)
    print(f"Ответ Telegram: {res}")

  save_seen(new_seen)
  print(f"Готово. Отправлено новых объявлений: {len(found_new)}")


if __name__ == "__main__":
  main()
