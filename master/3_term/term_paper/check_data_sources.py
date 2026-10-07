"""
Проверка доступности API-источников для курсовой по прогнозированию вакансий.

Проверяет три источника:
1. trudvsem.ru («Работа в России») — вакансии
2. MOEX ISS — биржевые котировки/индексы
3. Yandex Wordstat (через новый Yandex Search API v2) — поисковый спрос

Перед запуском:
- Для Wordstat нужен API-ключ Yandex Cloud и folder_id.
  Получить: https://yandex.cloud/ru/docs/search-api/
  (Старый путь через Яндекс.Директ сейчас считается устаревшим —
  вся функциональность перенесена в Yandex Cloud Search API v2.)
- Установить зависимости: pip install requests --break-system-packages
"""

import os
import sys
import json
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()  # подхватывает переменные из .env в текущей директории
except ImportError:
    print(
        "Подсказка: установи python-dotenv (pip install python-dotenv "
        "--break-system-packages), чтобы .env читался автоматически. "
        "Пока используются только реальные переменные окружения."
    )

TIMEOUT = 15  # секунд на запрос


def test_trudvsem() -> dict:
    """Проверка открытого API 'Работа в России'. Авторизация не требуется."""
    url = "http://opendata.trudvsem.ru/api/v1/vacancies"
    params = {"offset": 0, "limit": 5, "text": "инженер"}
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        count = len(data.get("results", {}).get("vacancies", []))
        return {
            "source": "trudvsem.ru",
            "ok": True,
            "status_code": resp.status_code,
            "detail": f"получено {count} вакансий в тестовом запросе",
        }
    except requests.exceptions.RequestException as e:
        return {
            "source": "trudvsem.ru",
            "ok": False,
            "status_code": getattr(e.response, "status_code", None),
            "detail": str(e),
        }


def test_moex() -> dict:
    """Проверка открытого MOEX ISS API. Авторизация не требуется."""
    url = (
        "https://iss.moex.com/iss/engines/stock/markets/index/"
        "boards/SNDX/securities/IMOEX.json"
    )
    params = {"iss.meta": "off", "limit": 5}
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        rows = len(data.get("marketdata", {}).get("data", []))
        return {
            "source": "MOEX ISS",
            "ok": True,
            "status_code": resp.status_code,
            "detail": f"получено {rows} строк market data по IMOEX",
        }
    except requests.exceptions.RequestException as e:
        return {
            "source": "MOEX ISS",
            "ok": False,
            "status_code": getattr(e.response, "status_code", None),
            "detail": str(e),
        }


def test_wordstat(api_key: str | None, folder_id: str | None) -> dict:
    """
    Проверка Yandex Wordstat через новый Yandex Search API v2.
    Требует API-ключ Yandex Cloud и folder_id (переменные окружения
    YANDEX_API_KEY и YANDEX_FOLDER_ID).
    """
    if not api_key or not folder_id:
        return {
            "source": "Wordstat (Yandex Search API v2)",
            "ok": False,
            "status_code": None,
            "detail": (
                "пропущено: не заданы переменные окружения "
                "YANDEX_API_KEY / YANDEX_FOLDER_ID"
            ),
        }

    url = "https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "folderId": folder_id,
        "phrase": "вакансии аналитик",
        "numPhrases": 10,  # обязательное поле: 1..2000
    }
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return {
            "source": "Wordstat (Yandex Search API v2)",
            "ok": True,
            "status_code": resp.status_code,
            "detail": f"ответ получен, ключи верхнего уровня: {list(data.keys())}",
        }
    except requests.exceptions.RequestException as e:
        body_text = ""
        if getattr(e, "response", None) is not None:
            try:
                body_text = f" | тело ответа: {e.response.text}"
            except Exception:
                pass
        return {
            "source": "Wordstat (Yandex Search API v2)",
            "ok": False,
            "status_code": getattr(e.response, "status_code", None),
            "detail": str(e) + body_text,
        }


def main():
    results = []
    print("Проверка trudvsem.ru ...")
    results.append(test_trudvsem())

    print("Проверка MOEX ISS ...")
    results.append(test_moex())

    print("Проверка Wordstat (Yandex Search API v2) ...")
    results.append(
        test_wordstat(
            os.environ.get("YANDEX_API_KEY"),
            os.environ.get("YANDEX_FOLDER_ID"),
        )
    )

    print("\n" + "=" * 60)
    print("ИТОГИ ПРОВЕРКИ ДОСТУПНОСТИ ИСТОЧНИКОВ")
    print("=" * 60)
    for r in results:
        status = "OK" if r["ok"] else "НЕДОСТУПНО / ОШИБКА"
        print(f"\n[{status}] {r['source']}")
        print(f"  HTTP статус: {r['status_code']}")
        print(f"  Детали: {r['detail']}")

    print("\n" + "=" * 60)
    failed = [r["source"] for r in results if not r["ok"]]
    if failed:
        print(f"Требуют внимания: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("Все проверенные источники доступны.")


if __name__ == "__main__":
    main()