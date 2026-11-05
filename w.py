import os
import time
from datetime import datetime, timedelta
from collections import defaultdict

import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

REQUEST_TIMEOUT = 15
HISTORY_DAYS = 3650
CACHE_TTL_SECONDS = 6 * 60 * 60

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Умный прогноз погоды</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
            color: #fff; min-height: 100vh; padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 {
            text-align: center; font-size: 2.3em; margin-bottom: 20px;
            background: linear-gradient(90deg, #f7971e, #ffd200);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .search-box { display: flex; gap: 10px; margin-bottom: 25px; }
        .search-box input {
            flex: 1; min-width: 0; padding: 15px 20px; border: 1px solid rgba(255,255,255,.15);
            border-radius: 30px; font-size: 16px; background: rgba(255,255,255,.1); color: #fff;
        }
        .search-box button {
            padding: 15px 28px; border: 0; border-radius: 30px;
            background: linear-gradient(90deg, #f7971e, #ffd200);
            color: #1a1a2e; font-weight: bold; cursor: pointer;
        }
        .card {
            background: rgba(255,255,255,.06); backdrop-filter: blur(10px);
            border-radius: 20px; padding: 22px; margin-bottom: 18px;
            border: 1px solid rgba(255,255,255,.1);
        }
        .current-weather { display: grid; grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)); gap: 12px; margin-top: 16px; }
        .item, .stat-item { text-align: center; padding: 15px; background: rgba(255,255,255,.05); border-radius: 15px; }
        .value { font-size: 27px; font-weight: bold; margin-top: 6px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 15px; }
        .number { font-size: 30px; font-weight: bold; color: #ffd200; }
        .table-wrap { overflow-x: auto; }
        .forecast-table { width: 100%; border-collapse: collapse; margin-top: 15px; min-width: 700px; }
        .forecast-table th { text-align: left; padding: 10px; border-bottom: 2px solid rgba(255,255,255,.15); opacity: .75; font-size: 12px; }
        .forecast-table td { padding: 10px; border-bottom: 1px solid rgba(255,255,255,.07); white-space: nowrap; }
        .loading { text-align: center; padding: 45px; opacity: .8; }
        .error { background: rgba(255,0,0,.15); border-radius: 15px; padding: 20px; color: #ff9b9b; }
        .note { opacity: .7; font-size: 13px; line-height: 1.5; margin-top: 12px; }
        @media (max-width: 600px) {
            h1 { font-size: 1.8em; }
            .search-box { flex-direction: column; }
            .search-box button { width: 100%; }
            .card { padding: 16px; }
        }
    </style>
</head>
<body>
<div class="container">
    <h1>🌤️ Умный прогноз</h1>
    <div class="search-box">
        <input type="text" id="cityInput" placeholder="Введите город..." value="Bayazitovo">
        <button id="searchButton" type="button">🔍 Узнать</button>
    </div>
    <div id="result"><div class="loading">Загружаем данные...</div></div>
</div>
<script>
    const resultElement = document.getElementById('result');
    const cityInput = document.getElementById('cityInput');

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, function (char) {
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]);
        });
    }

    async function getWeather() {
        const city = cityInput.value.trim();
        if (!city) {
            resultElement.innerHTML = '<div class="error">Введите название города.</div>';
            return;
        }

        resultElement.innerHTML = '<div class="loading">⏳ Загружаем данные...</div>';
        document.getElementById('searchButton').disabled = true;

        try {
            const response = await fetch('/api/forecast?city=' + encodeURIComponent(city));
            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || 'Не удалось получить данные.');
            }
            renderWeather(data);
        } catch (error) {
            resultElement.innerHTML = '<div class="error">❌ ' + escapeHtml(error.message || 'Ошибка подключения') + '</div>';
        } finally {
            document.getElementById('searchButton').disabled = false;
        }
    }

    function renderWeather(data) {
        const current = data.current;
        const stats = data.stats;
        const forecast = data.forecast || [];

        let html = '<div class="card"><h2>📍 ' + escapeHtml(data.city) + '</h2>' +
            '<div class="current-weather">' +
            '<div class="item"><div>🌡️ Средняя</div><div class="value">' + escapeHtml(current.temp_mean) + '°C</div></div>' +
            '<div class="item"><div>🔥 Максимум</div><div class="value">' + escapeHtml(current.temp_max) + '°C</div></div>' +
            '<div class="item"><div>❄️ Минимум</div><div class="value">' + escapeHtml(current.temp_min) + '°C</div></div>' +
            '<div class="item"><div>🌧️ Осадки</div><div class="value">' + escapeHtml(current.precip) + ' мм</div></div>' +
            '<div class="item"><div>📝 Погода</div><div class="value" style="font-size:19px">' + escapeHtml(current.weather) + '</div></div>' +
            '</div><div class="note">Последние доступные наблюдения: ' + escapeHtml(current.date) + '</div></div>';

        html += '<div class="card"><h3>📊 Историческая статистика за ' + escapeHtml(stats.years) + ' лет</h3>' +
            '<div class="stats">' +
            '<div class="stat-item"><div class="number">' + escapeHtml(stats.max_all) + '°C</div><div>Максимум</div></div>' +
            '<div class="stat-item"><div class="number">' + escapeHtml(stats.min_all) + '°C</div><div>Минимум</div></div>' +
            '<div class="stat-item"><div class="number">' + escapeHtml(stats.days) + '</div><div>Дней наблюдений</div></div>' +
            '</div></div>';

        html += '<div class="card"><h3>📅 Климатическая оценка на 30 дней</h3>' +
            '<div class="note">Это оценка по средним историческим значениям за соответствующие даты, а не точный метеорологический прогноз.</div>' +
            '<div class="table-wrap"><table class="forecast-table"><thead><tr><th>День</th><th>Дата</th><th>Средняя</th><th>Макс</th><th>Мин</th><th>Осадки</th><th>Оценка</th></tr></thead><tbody>';

        forecast.forEach(function (item) {
            const label = item.day === 1 ? 'Завтра' : 'Через ' + item.day + ' дн.';
            html += '<tr><td><strong>' + label + '</strong></td>' +
                '<td>' + escapeHtml(item.date) + '</td>' +
                '<td>' + escapeHtml(item.temp_mean) + '°C</td>' +
                '<td>' + escapeHtml(item.temp_max) + '°C</td>' +
                '<td>' + escapeHtml(item.temp_min) + '°C</td>' +
                '<td>' + escapeHtml(item.precip) + ' мм</td>' +
                '<td>' + escapeHtml(item.weather) + '</td></tr>';
        });

        html += '</tbody></table></div></div>';
        resultElement.innerHTML = html;
    }

    document.getElementById('searchButton').addEventListener('click', getWeather);
    cityInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') getWeather();
    });
    getWeather();
</script>
</body>
</html>
"""

session = requests.Session()
cache = {}


def safe_get_json(url, params=None):
    """Выполняет HTTP-запрос с таймаутом и проверкой ответа."""
    try:
        response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise RuntimeError("Сервис погоды не ответил вовремя.") from exc
    except requests.RequestException as exc:
        raise RuntimeError("Не удалось подключиться к сервису погоды.") from exc
    except ValueError as exc:
        raise RuntimeError("Сервис погоды вернул некорректный ответ.") from exc


def get_coordinates(city):
    data = safe_get_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "ru", "format": "json"}
    )
    results = data.get("results") or []
    if not results:
        return None

    result = results[0]
    return {
        "lat": result["latitude"],
        "lon": result["longitude"],
        "name": result["name"]
    }


def get_historical_data(lat, lon, days=HISTORY_DAYS):
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    data = safe_get_json(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,weathercode",
            "timezone": "auto"
        }
    )

    daily = data.get("daily")
    if not daily or not daily.get("time"):
        return None

    weather_data = []
    fields = (
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "precipitation_sum",
        "weathercode"
    )

    for index, date_text in enumerate(daily["time"]):
        values = {}
        for field in fields:
            column = daily.get(field) or []
            values[field] = column[index] if index < len(column) else None

        if any(values[field] is None for field in fields):
            continue

        weather_data.append({
            "time": datetime.fromisoformat(date_text),
            "temp_max": float(values["temperature_2m_max"]),
            "temp_min": float(values["temperature_2m_min"]),
            "temp_mean": float(values["temperature_2m_mean"]),
            "precipitation": float(values["precipitation_sum"]),
            "weathercode": int(values["weathercode"])
        })

    return weather_data or None


def build_model(historical_data):
    """Собирает климатические средние по месяцу и дню, не смешивая високосные даты."""
    totals = defaultdict(lambda: {
        "mean": 0.0, "max": 0.0, "min": 0.0, "precip": 0.0, "count": 0
    })

    for day in historical_data:
        key = (day["time"].month, day["time"].day)
        bucket = totals[key]
        bucket["mean"] += day["temp_mean"]
        bucket["max"] += day["temp_max"]
        bucket["min"] += day["temp_min"]
        bucket["precip"] += day["precipitation"]
        bucket["count"] += 1

    model = {}
    for key, values in totals.items():
        count = values["count"]
        model[key] = {
            "mean": values["mean"] / count,
            "max": values["max"] / count,
            "min": values["min"] / count,
            "precip": values["precip"] / count
        }

    return model


def predict_from_model(model, target_date):
    key = (target_date.month, target_date.day)
    values = model.get(key)

    # Если 29 февраля отсутствует в истории, используем среднее соседних дат.
    if values is None and key == (2, 29):
        before = model.get((2, 28))
        after = model.get((3, 1))
        if before and after:
            values = {
                field: (before[field] + after[field]) / 2
                for field in ("mean", "max", "min", "precip")
            }

    if values is None:
        return 0.0, 0.0, 0.0, 0.0

    return values["mean"], values["max"], values["min"], values["precip"]


def get_weather_description(code):
    codes = {
        0: "☀️ Ясно", 1: "🌤️ Малооблачно", 2: "⛅ Переменная облачность",
        3: "☁️ Пасмурно", 45: "🌫️ Туман", 48: "🌫️ Изморозевый туман",
        51: "🌦️ Лёгкая морось", 53: "🌦️ Морось", 55: "🌧️ Сильная морось",
        61: "🌧️ Небольшой дождь", 63: "🌧️ Дождь", 65: "🌧️ Сильный дождь",
        71: "❄️ Небольшой снег", 73: "❄️ Снег", 75: "❄️ Сильный снег",
        80: "🌦️ Ливень", 81: "🌧️ Ливень", 82: "🌧️ Сильный ливень",
        95: "⛈️ Гроза", 96: "⛈️ Гроза с градом", 99: "⛈️ Сильная гроза"
    }
    return codes.get(code, "❓ Неизвестно")


def describe_climate(temp_max, precip):
    if temp_max > 25:
        description = "☀️ Жарко"
    elif temp_max > 18:
        description = "🌤️ Тепло"
    elif temp_max > 10:
        description = "⛅ Прохладно"
    elif temp_max > 0:
        description = "☁️ Холодно"
    else:
        description = "❄️ Мороз"

    if precip > 5:
        description += " 🌧️"
    elif precip > 1:
        description += " 🌦️"
    return description


def get_forecast_data(city):
    location = get_coordinates(city)
    if not location:
        return {"error": "Город не найден. Проверьте название и попробуйте снова."}

    cache_key = (round(location["lat"], 4), round(location["lon"], 4))
    now = time.time()
    cached = cache.get(cache_key)

    if cached and now - cached["created"] < CACHE_TTL_SECONDS:
        historical = cached["historical"]
        model = cached["model"]
    else:
        historical = get_historical_data(location["lat"], location["lon"])
        if not historical:
            return {"error": "Для этого места пока нет доступных исторических данных."}

        model = build_model(historical)
        cache[cache_key] = {
            "created": now,
            "historical": historical,
            "model": model
        }

    latest = historical[-1]
    today = datetime.now().date()
    forecast = []

    for day_number in range(1, 31):
        future_date = today + timedelta(days=day_number)
        temp_mean, temp_max, temp_min, precip = predict_from_model(model, future_date)

        forecast.append({
            "day": day_number,
            "date": future_date.strftime("%d.%m"),
            "temp_mean": round(temp_mean, 1),
            "temp_max": round(temp_max, 1),
            "temp_min": round(temp_min, 1),
            "precip": round(precip, 1),
            "weather": describe_climate(temp_max, precip)
        })

    all_max = [item["temp_max"] for item in historical]
    all_min = [item["temp_min"] for item in historical]

    return {
        "city": location["name"],
        "current": {
            "date": latest["time"].strftime("%d.%m.%Y"),
            "temp_mean": round(latest["temp_mean"], 1),
            "temp_max": round(latest["temp_max"], 1),
            "temp_min": round(latest["temp_min"], 1),
            "precip": round(latest["precipitation"], 1),
            "weather": get_weather_description(latest["weathercode"])
        },
        "stats": {
            "days": len(historical),
            "years": len({item["time"].year for item in historical}),
            "max_all": round(max(all_max), 1),
            "min_all": round(min(all_min), 1)
        },
        "forecast": forecast
    }


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/forecast")
def api_forecast():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "Укажите город: /api/forecast?city=Москва"}), 400

    try:
        data = get_forecast_data(city)
        if "error" in data:
            return jsonify(data), 404
        return jsonify(data)
    except RuntimeError as exc:
        app.logger.warning("Weather API error: %s", exc)
        return jsonify({"error": str(exc)}), 502
    except Exception:
        app.logger.exception("Unexpected error while building forecast")
        return jsonify({"error": "Внутренняя ошибка сервера. Попробуйте позже."}), 500


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
