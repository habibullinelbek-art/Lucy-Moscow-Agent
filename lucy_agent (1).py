#!/usr/bin/env python3
"""
Люся — агент по культурным мероприятиям Москвы.
Каждый четверг собирает афишу и постит в Telegram-канал.
Секреты читаются из переменных окружения (GitHub Actions Secrets).
"""

import anthropic
import requests
import json
import re
import os

ANTHROPIC_API_KEY   = os.environ["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"]
TELEGRAM_BOT_TOKEN  = os.environ["8788719924:AAEPcAwCDIwT3gbaItq29b_cAV2gDrtGktI"]
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@Lucy_Moscow_events")

SYSTEM_PROMPT = """Ты — Люся, саркастичный и ироничный гид по культурной жизни Москвы.
Ты обожаешь город, но не упустишь шанс пройтись острым словом по пафосным спектаклям,
заоблачным ценам и «уникальным» выставкам, которые повторяются каждый год.

Твой стиль: остроумно, с иронией, но без злобы. Как подруга, которая честно скажет,
стоит ли тратить на это выходные. Пишешь на русском, живо и по-человечески.

Форматируй каждое мероприятие по шаблону:

🎭 [эмодзи по типу] **Название**
📅 Дата и время
💰 Цена
👥 Участники/актёры (если есть)
📝 Краткое описание (1-2 предложения)
😏 *Комментарий Люси* — твоя ироничная реплика (1-2 предложения)
🔗 Ссылка

После всех мероприятий добавь подпись:
— Люся, ваш гид по московским культурным страданиям 🗺️
"""


def search_moscow_events(client):
    search_prompt = """Найди 5 актуальных культурных мероприятий Москвы на ближайшие выходные и следующую неделю.

Нужно по 1-2 мероприятия каждого типа:
- Спектакли (театр)
- Концерты
- Выставки

Для каждого найди: точное название, дата и время, цены на билеты,
актёры/исполнители/художники, краткое описание, ссылка на билеты.

Ищи на: afisha.ru, kudago.com, kassir.ru, ticketland.ru.
Только реальные мероприятия с реальными датами и ценами."""

    messages = [{"role": "user", "content": search_prompt}]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=messages
    )

    while response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"query": block.input.get("query", "")})
                })
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages
        )

    return "".join(b.text for b in response.content if hasattr(b, "text"))


def format_as_lucy(client, raw_events):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Вот данные о мероприятиях Москвы на эту неделю.
Отформатируй по шаблону, добавь саркастичные комментарии.
Начни с заголовка «Куда идти москвичу в четверг? 🗺️» и текущей датой.

{raw_events}"""
        }]
    )
    return response.content[0].text


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if len(text) > 4096:
        text = text[:4090] + "\n..."

    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code == 200:
        print("✅ Пост отправлен!")
        return True
    print(f"❌ Ошибка Telegram ({r.status_code}): {r.text}")
    # Fallback — plain text
    payload["parse_mode"] = ""
    payload["text"] = re.sub(r'\*\*?(.*?)\*\*?', r'\1', text)
    r2 = requests.post(url, json=payload, timeout=30)
    if r2.status_code == 200:
        print("✅ Отправлено (plain text)")
        return True
    return False


def run():
    print("🚀 Люся просыпается...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("🔍 Ищу мероприятия...")
    raw = search_moscow_events(client)
    print(f"📋 Получено {len(raw)} символов")

    print("✍️  Пишу пост...")
    post = format_as_lucy(client, raw)
    print("\n" + "="*50 + "\n" + post + "\n" + "="*50)

    print("📨 Отправляю в Telegram...")
    send_to_telegram(post)


if __name__ == "__main__":
    run()
