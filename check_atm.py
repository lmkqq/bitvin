import os
import re
import requests
from playwright.sync_api import sync_playwright

URL = "https://www.bitomat.com/ru/bitomaty/bitkoin-bankomat-vinnytsia"
STATE_FILE = "last_value.txt"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


def fetch_cash_amount() -> int:
    # Сумма подгружается на сайте через JavaScript уже после загрузки
    # страницы, поэтому обычный requests её не видит — открываем страницу
    # в настоящем (headless) браузере и ждём, пока JS её отрисует.
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)

        html = ""
        match = None
        # Пробуем до 10 раз с паузами — если число ещё не отрисовалось,
        # ждём ещё. Требуем минимум 3 цифры подряд, чтобы не зацепить
        # случайную одиночную цифру из ещё не прогруженного плейсхолдера.
        for _ in range(10):
            html = page.content()
            match = re.search(
                r"Доступная наличность сейчас[^\d]{0,80}(\d{3,}[\d\s]*)", html
            )
            if match:
                break
            page.wait_for_timeout(1500)

        browser.close()

    if not match:
        raise RuntimeError(
            "Не нашёл сумму на странице даже после рендеринга JS — "
            "возможно, сайт поменял вёрстку, нужно проверять вручную."
        )
    raw = match.group(1)
    return int(re.sub(r"\s", "", raw))


def send_telegram(text: str) -> None:
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(api_url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    resp.raise_for_status()


def load_last_value():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return int(content) if content else None


def save_last_value(value: int) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(str(value))


def main():
    current = fetch_cash_amount()
    previous = load_last_value()

    if previous is None:
        save_last_value(current)
        print(f"Первый запуск. Сохранил текущее значение: {current}")
        return

    if current != previous:
        diff = current - previous
        sign = "+" if diff > 0 else ""
        text = (
            "💰 Изменился баланс биткоин-банкомата (Винница, ул. Зодчих, 2)\n"
            f"Было: {previous}\n"
            f"Стало: {current}\n"
            f"Изменение: {sign}{diff}"
        )
        send_telegram(text)
        save_last_value(current)
        print("Отправлено уведомление:", text)
    else:
        print("Без изменений:", current)


if __name__ == "__main__":
    main()
