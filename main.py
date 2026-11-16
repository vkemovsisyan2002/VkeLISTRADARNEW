import json
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
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

  print("Запуск браузера через Playwright...")
  html_content = ""
  try:
    with sync_playwright() as p:
      browser = p.chromium.launch(headless=True)
      context = browser.new_context(
          user_agent=(
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
              " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
          ),
          viewport={"width": 1280, "height": 800},
      )
      page = context.new_page()
      # Ждем полной загрузки сети и элементов
      page.goto(URL, timeout=60000, wait_until="networkidle")
      page.wait_for_timeout(5000)
      html_content = page.content()
      browser.close()
  except Exception as e:
    print(f"Ошибка выполнения браузера: {e}")
    return

  soup = BeautifulSoup(html_content, "html.parser")
  seen = load_seen()
  new_seen = set(seen)

  # Ищем любые ссылки на объявления
  items = soup.find_all("a", href=lambda x: x and "/item/" in x)
  print(f"Найдено ссылок на странице: {len(items)}")

  if len(items) == 0:
    print("Внимание: объявления не найдены.")
    return

  found_new = []

  for item in items:
    href = item.get("href")
    parts = href.split("/")
    for i, part in enumerate(parts):
      if part == "item" and i + 1 < len(parts):
        ad_id = parts[i + 1].split("?")[0]
        if ad_id and ad_id not in seen:
          title = item.text.strip().replace("\n", " ")
          title = " ".join(title.split())
          if not title:
            title = "Квартира в Ереване"
          full_url = (
              f"https://www.list.am{href}" if href.startswith("/") else href
          )
          found_new.append((ad_id, title, full_url))
          new_seen.add(ad_id)
        break

  if len(seen) == 0 and len(found_new) > 0:
    print(
        "Первый запуск: инициализация базы объявлений без отправки в канал..."
    )
    save_seen(new_seen)
    print(f"База успешно инициализирована! Сохранено квартир: {len(new_seen)}")
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
