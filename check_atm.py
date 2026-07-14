import os
import requests

API_URL = "https://shitcoins.club/atms/getAtmsData"
ATM_ID = 1393  # банкомат: ул. Зодчих, 2, Винница
STATE_FILE = "last_value.txt"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


def fetch_cash_amount() -> float:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    resp = requests.get(API_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    atm = next((a for a in data if a.get("id") == ATM_ID), None)
    if atm is None:
        raise RuntimeError(f"Банкомат с id={ATM_ID} не найден в ответе API")

    balances = atm.get("balances", {})
    currency_code = atm.get("currency_code", "UAH")
    amount = balances.get(currency_code)
    if amount is None:
        raise RuntimeError(
            f"Не нашёл баланс в валюте {currency_code} для банкомата {ATM_ID}"
        )
    return float(amount), currency_code


def send_telegram(text: str) -> None:
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(api_url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    resp.raise_for_status()


def load_last_value():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return float(content) if content else None


def save_last_value(value: float) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(str(value))


def main():
    current, currency = fetch_cash_amount()
    previous = load_last_value()

    if previous is None:
        save_last_value(current)
        print(f"Первый запуск. Сохранил текущее значение: {current} {currency}")
        return

    if current != previous:
        diff = current - previous
        sign = "+" if diff > 0 else ""
        text = (
            "💰 Изменился баланс биткоин-банкомата (Винница, ул. Зодчих, 2)\n"
            f"Было: {previous:g} {currency}\n"
            f"Стало: {current:g} {currency}\n"
            f"Изменение: {sign}{diff:g} {currency}"
        )
        send_telegram(text)
        save_last_value(current)
        print("Отправлено уведомление:", text)
    else:
        print(f"Без изменений: {current} {currency}")


if __name__ == "__main__":
    main()
