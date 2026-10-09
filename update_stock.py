#!/usr/bin/env python3
"""
Обновляет stock.json свежим стоком Blox Fruits с https://fruityblox.com/stock.

Запуск:
  python update_stock.py

Ничего, кроме стандартного Python, не нужно. Если сток получить не удалось,
stock.json не трогается, а скрипт завершается с ошибкой.
"""
import json
import os
import re
import sys
import time
import urllib.request

URL = "https://fruityblox.com/stock"
# Честно представляемся, чтобы владельцы сайта видели, кто и зачем ходит
UA = "bloxstock-updater/1.0 (personal stock page; contact: https://funpay.com/users/13621606/)"
HERE = os.path.dirname(os.path.abspath(__file__))
STOCK_FILE = os.path.join(HERE, "stock.json")
DEFAULT_LINK = "https://funpay.com/users/13621606/"
HOURS = {"normal": 4, "mirage": 2}  # как часто меняется сток, часов (по UTC)
NAME_RE = re.compile(r"^[A-Za-z0-9 +'\-]{1,30}$")


def fetch_html():
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse_stock(html):
    """Достаёт списки фруктов из данных, встроенных в страницу."""
    text = html.replace('\\"', '"')
    start = text.find('"normal":[')
    if start < 0:
        sys.exit("Не нашёл сток на странице: возможно, сайт изменился.")
    dec = json.JSONDecoder()
    result = {}
    pos = start
    for kind in ("normal", "mirage"):
        key = f'"{kind}":'
        pos = text.find(key, pos)
        if pos < 0:
            sys.exit(f"Не нашёл раздел {kind} на странице.")
        items, end = dec.raw_decode(text, pos + len(key))
        names = [str(i.get("name", "")).strip() for i in items if isinstance(i, dict)]
        if not names or len(names) > 20 or not all(NAME_RE.match(n) for n in names):
            sys.exit(f"Раздел {kind} выглядит странно, не обновляю: {names!r}")
        result[kind] = names
        pos = end
    return result


def load_old():
    try:
        with open(STOCK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def main():
    new = parse_stock(fetch_html())
    old = load_old()
    now = int(time.time() * 1000)
    data = {"link": old.get("link") or DEFAULT_LINK}
    changed = False
    for kind, hours in HOURS.items():
        period = hours * 3600 * 1000
        last_reset = now // period * period
        at = old.get(kind + "At") or 0
        # Обновляем, если сток другой или наступил новый период (сток мог остаться тем же)
        if new[kind] != old.get(kind) or at < last_reset:
            at = now
            changed = True
        data[kind] = new[kind]
        data[kind + "At"] = at
    data = {k: data[k] for k in ("link", "normal", "normalAt", "mirage", "mirageAt")}

    if changed:
        with open(STOCK_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(f"Обычный: {', '.join(new['normal'])}")
    print(f"Мираж:   {', '.join(new['mirage'])}")
    print("stock.json обновлён" if changed else "Изменений нет")

    # Сообщаем GitHub Actions, нужно ли публиковать сайт заново
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    main()
