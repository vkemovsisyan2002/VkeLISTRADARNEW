import json
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CF_CLEARANCE = os.getenv("CF_CLEARANCE")  # Кука для обхода Cloudflare
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

  print("Запуск браузера с внедрением доверенной куки Cloudflare...")
  html_content = ""
  page_title = ""
  try:
    with sync_playwright() as p:
      browser = p.chromium.launch(
          headless=True,
          args=[
              "--disable-blink-features=AutomationControlled",
              "--no-sandbox",
              "--disable-setuid-sandbox",
          ],
      )
      context = browser.new_context(
          user_agent=(
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
              " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
          ),
          viewport={"width": 1280, "height": 800},
      )

      # Внедряем куку cf_clearance, чтобы Cloudflare сразу пустил без проверки
      if CF_CLEARANCE:
        context.add_cookies([{
            "name": "cf_clearance",
            "value": CF_CLEARANCE,
            "domain": ".list.am",
            "path": "/",
        }])
        print("Кука cf_clearance успешно внедрена.")
      else:
        print("Внимание: CF_CLEARANCE не найден в секретах GitHub!")

      page = context.new_page()
      page.goto(URL, timeout=60000, wait_until="domcontentloaded")
      page.wait_for_timeout(5000)

      page_title = page.title()
      html_content = page.content()
      browser.close()
  except Exception as e:
    print(f"Ошибка выполнения браузера: {e}")
    return

  print(f"📄 Заголовок страницы: {page_title}")

  soup = BeautifulSoup(html_content, "html.parser")
  seen = load_seen()
  new_seen = set(seen)

  items = soup.find_all("a", href=lambda x: x and "/item/" in x)

  found_new = []
  all_found_ids = set()

  for item in items:
    href = item.get("href")
    if not href:
      continue
    parts = href.split("/")
    for i, part in enumerate(parts):
      if part == "item" and i + 1 < len(parts):
        ad_id = parts[i + 1].split("?")[0]
        if ad_id:
          all_found_ids.add(ad_id)
          if ad_id not in seen:
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

  print(f"📊 Всего найдено объявлений на странице: {len(all_found_ids)}")
  print(f"🔥 Из них новых: {len(found_new)}")

  if len(seen) == 0:
    if len(all_found_ids) > 0:
      save_seen(all_found_ids)
      print(f"База инициализирована! Сохранено квартир: {len(all_found_ids)}")
    else:
      print(
          "⚠️ Найдено 0 объявлений. Проверьте, правильная ли кука cf_clearance."
      )
    return

  if len(found_new) == 0:
    print("✅ Новых объявлений нет, база актуальна.")
  else:
    for ad_id, title, full_url in reversed(found_new):
      msg = (
          f"🏠 <b>Новая квартира в Ереване!</b>\n\n{title}\n\n🔗"
          f" <a href='{full_url}'>Посмотреть на List.am</a>"
      )
      print(f"Отправка объявления {ad_id} в Telegram...")
      res = send_telegram(msg)
      print(f"Ответ Telegram: {res}")

  save_seen(new_seen)
  print("Готово.")


if __name__ == "__main__":
  main()
