"""Считает живые значки для профиля организации.

Значения кладутся в profile/badges/*.json в формате конечной точки shields,
README ссылается на них через img.shields.io/endpoint. Так число тестов
и состояние конвейеров не приходится править руками: их пересчитывает
работа badges.yml по расписанию.

Запросы идут к публичному API и работают без токена; в работе токен всё же
передаётся, иначе шестьдесят запросов в час кончаются на середине прогона.
"""

import json
import os
import pathlib
import re
import urllib.error
import urllib.request

ORG = "mireacrm"
SERVICES = [
    "gateway", "core-service", "client-service", "booking-service", "catalog-service",
    "inventory-service", "billing-service", "notification-service", "analytics-service",
]
LIBS = ["go-common", "py-common", "proto", "contracts-go", "contracts-py", "deploy"]

OUT = pathlib.Path(__file__).parent / "badges"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

TEST_FILE = re.compile(r"(^|/)(.*_test\.go|test_.*\.py|.*_test\.py)$")
TEST_FUNC = re.compile(r"^(func Test[A-Z_]|\s*(async )?def test_)", re.M)


def get(url, raw=False):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "mireacrm-badges"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            body = r.read()
        return body.decode("utf-8") if raw else json.loads(body)
    except urllib.error.HTTPError as error:
        print(f"  {error.code} на {url}")
        return None


def badge(name, label, message, color):
    payload = {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
        "labelColor": "24292F",
        "style": "flat-square",
        "cacheSeconds": 3600,
    }
    (OUT / f"{name}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{name}: {label} — {message}")


def pipelines():
    green = 0
    for repo in SERVICES:
        runs = get(f"https://api.github.com/repos/{ORG}/{repo}/actions/runs"
                   f"?branch=main&event=push&per_page=1")
        items = (runs or {}).get("workflow_runs") or []
        if items and items[0].get("conclusion") == "success":
            green += 1
    total = len(SERVICES)
    color = "brightgreen" if green == total else ("orange" if green else "red")
    badge("pipelines", "конвейеры", f"{green}/{total} зелёных", color)


def languages():
    totals = {}
    for repo in SERVICES + LIBS:
        for name, size in (get(f"https://api.github.com/repos/{ORG}/{repo}/languages") or {}).items():
            totals[name] = totals.get(name, 0) + size
    code = sum(totals.get(name, 0) for name in ("Go", "Python"))
    if not code:
        return
    share = {name: round(totals.get(name, 0) * 100 / code) for name in ("Go", "Python")}
    badge("languages", "код", f"Go {share['Go']}% · Python {share['Python']}%", "1F6FEB")


def tests():
    total = 0
    for repo in SERVICES + ["go-common", "py-common"]:
        tree = get(f"https://api.github.com/repos/{ORG}/{repo}/git/trees/main?recursive=1")
        for item in (tree or {}).get("tree", []):
            if item["type"] != "blob" or not TEST_FILE.search(item["path"]):
                continue
            source = get(f"https://raw.githubusercontent.com/{ORG}/{repo}/main/{item['path']}", raw=True)
            total += len(TEST_FUNC.findall(source or ""))
    badge("tests", "тестов", str(total), "1F6FEB")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    pipelines()
    languages()
    tests()
