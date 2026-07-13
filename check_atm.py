import os
import re
import requests

URL = "https://www.bitomat.com/ru/bitomaty/bitkoin-bankomat-vinnytsia"
STATE_FILE = "last_value.txt"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


def fetch_cash_amount() -> int:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    resp = requests.get(URL, headers=headers, timeout=20)
    resp.raise_for_status()
    html = resp.text

    # Ищем число сразу после фразы "Доступная наличность сейчас"
    match = re.search(r"Доступная наличность сейчас[^\d]{0,80}(\d[\d\s]*)", html)
    if not match:
        raise RuntimeError(
            "Не нашёл сумму на странице. Возможно, сайт отдаёт её через JS, "
            "и обычный requests её не видит — тогда нужен вариант с headless-браузером."
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
