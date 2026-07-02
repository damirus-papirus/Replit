import requests
import json
import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = 
CORS(app)

# ============ HTML ИНТЕРФЕЙС ============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌤️ Умный прогноз погоды</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { text-align: center; font-size: 2.5em; margin-bottom: 20px; background: linear-gradient(90deg, #f7971e, #ffd200); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .search-box { display: flex; gap: 10px; margin-bottom: 30px; }
        .search-box input { flex: 1; padding: 15px 20px; border: none; border-radius: 30px; font-size: 16px; background: rgba(255,255,255,0.1); color: #fff; }
        .search-box button { padding: 15px 30px; border: none; border-radius: 30px; background: linear-gradient(90deg, #f7971e, #ffd200); color: #1a1a2e; font-weight: bold; cursor: pointer; }
        .card { background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border-radius: 20px; padding: 25px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.1); }
        .current-weather { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
        .current-weather .item { text-align: center; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 15px; }
        .current-weather .item .value { font-size: 28px; font-weight: bold; margin-top: 5px; }
        .forecast-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .forecast-table th { text-align: left; padding: 10px; border-bottom: 2px solid rgba(255,255,255,0.1); opacity: 0.7; font-size: 12px; }
        .forecast-table td { padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stats .stat-item { text-align: center; padding: 15px; background: rgba(255,255,255,0.03); border-radius: 15px; }
        .stats .stat-item .number { font-size: 32px; font-weight: bold; color: #ffd200; }
        .loading { text-align: center; padding: 50px; opacity: 0.7; }
        .error { background: rgba(255,0,0,0.2); border-radius: 15px; padding: 20px; text-align: center; color: #ff6b6b; }
        @media (max-width: 600px) { h1 { font-size: 1.8em; } .search-box { flex-direction: column; } .current-weather { grid-template-columns: repeat(2, 1fr); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌤️ Умный прогноз</h1>
        <div class="search-box">
            <input type="text" id="cityInput" placeholder="Введите город..." value="Bayazitovo">
            <button onclick="getWeather()">🔍 Узнать</button>
        </div>
        <div id="result">
            <div class="loading">Введите город и нажмите "Узнать"</div>
        </div>
    </div>

    <script>
        function getWeather() {
            const city = document.getElementById('cityInput').value.trim();
            if (!city) { alert('Введите название города'); return; }

            document.getElementById('result').innerHTML = '<div class="loading">⏳ Загружаем данные...</div>';

            fetch(`/api/forecast?city=${encodeURIComponent(city)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('result').innerHTML = `<div class="error">❌ ${data.error}</div>`;
                        return;
                    }
                    renderWeather(data);
                })
                .catch(() => {
                    document.getElementById('result').innerHTML = '<div class="error">❌ Ошибка подключения</div>';
                });
        }

        function renderWeather(data) {
            const current = data.current;
            const stats = data.stats;
            const forecast = data.forecast;

            let html = `
                <div class="card">
                    <h2 style="margin-bottom:15px;">📍 ${data.city}</h2>
                    <div class="current-weather">
                        <div class="item"><div class="label">🌡️ Средняя</div><div class="value">${current.temp_mean}°C</div></div>
                        <div class="item"><div class="label">🔥 Максимум</div><div class="value">${current.temp_max}°C</div></div>
                        <div class="item"><div class="label">❄️ Минимум</div><div class="value">${current.temp_min}°C</div></div>
                        <div class="item"><div class="label">🌧️ Осадки</div><div class="value">${current.precip} мм</div></div>
                        <div class="item" style="grid-column: span 2;"><div class="label">📝 Погода</div><div class="value" style="font-size:20px;">${current.weather}</div></div>
                    </div>
                    <div style="margin-top:15px;font-size:14px;opacity:0.7;">📅 ${current.date}</div>
                </div>

                <div class="card">
                    <h3>📊 Статистика за ${stats.years} лет</h3>
                    <div class="stats">
                        <div class="stat-item"><div class="number">${stats.max_all}°C</div><div style="opacity:0.7;font-size:14px;">Максимум</div></div>
                        <div class="stat-item"><div class="number">${stats.min_all}°C</div><div style="opacity:0.7;font-size:14px;">Минимум</div></div>
                        <div class="stat-item"><div class="number">${stats.days}</div><div style="opacity:0.7;font-size:14px;">Дней</div></div>
                    </div>
                </div>

                <div class="card">
                    <h3>📅 Прогноз на 30 дней</h3>
                    <table class="forecast-table">
                        <thead><tr><th>День</th><th>Дата</th><th>Средняя</th><th>Макс</th><th>Мин</th><th>Осадки</th><th>Погода</th></tr></thead>
                        <tbody>
            `;

            forecast.forEach((f, index) => {
                const labels = ['Завтра', 'Через 2д', 'Через 3д', 'Через 4д', 'Через 5д', 'Через 6д', 'Через 7д'];
                const label = index < 7 ? labels[index] : `+${f.day}д`;
                html += `
                    <tr>
                        <td><strong>${label}</strong></td>
                        <td>${f.date}</td>
                        <td>${f.temp_mean}°C</td>
                        <td><span style="color:#ff6b6b;">${f.temp_max}°C</span></td>
                        <td><span style="color:#74b9ff;">${f.temp_min}°C</span></td>
                        <td>${f.precip} мм</td>
                        <td>${f.weather}</td>
                    </tr>
                `;
            });

            html += `</tbody></table></div>`;
            document.getElementById('result').innerHTML = html;
        }

        document.addEventListener('DOMContentLoaded', getWeather);
    </script>
</body>
</html>
"""

# ============ ОСНОВНЫЕ ФУНКЦИИ ============

def get_coordinates(city):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ru&format=json"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get('results'):
            result = data['results'][0]
            return {'lat': result['latitude'], 'lon': result['longitude'], 'name': result['name']}
    except:
        pass
    return None

def get_historical_data(lat, lon, days=3650):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date.strftime('%Y-%m-%d')}&end_date={end_date.strftime('%Y-%m-%d')}&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,weathercode&timezone=auto"
    
    try:
        response = requests.get(url)
        data = response.json()
        if 'daily' not in data:
            return None
        
        daily = data['daily']
        weather_data = []
        for i in range(len(daily['time'])):
            weather_data.append({
                'time': datetime.fromisoformat(daily['time'][i]),
                'temp_max': daily['temperature_2m_max'][i],
                'temp_min': daily['temperature_2m_min'][i],
                'temp_mean': daily['temperature_2m_mean'][i],
                'precipitation': daily['precipitation_sum'][i],
                'weathercode': daily['weathercode'][i]
            })
        return weather_data
    except:
        return None

def build_model(historical_data):
    model = {
        'mean': [0] * 366,
        'max': [0] * 366,
        'min': [0] * 366,
        'precip': [0] * 366,
        'counts': [0] * 366
    }
    
    for d in historical_data:
        day_of_year = d['time'].timetuple().tm_yday - 1
        model['mean'][day_of_year] += d['temp_mean']
        model['max'][day_of_year] += d['temp_max']
        model['min'][day_of_year] += d['temp_min']
        model['precip'][day_of_year] += d['precipitation']
        model['counts'][day_of_year] += 1
    
    for i in range(366):
        if model['counts'][i] > 0:
            model['mean'][i] /= model['counts'][i]
            model['max'][i] /= model['counts'][i]
            model['min'][i] /= model['counts'][i]
            model['precip'][i] /= model['counts'][i]
    
    model['years'] = len(set(d['time'].year for d in historical_data))
    model['total_days'] = len(historical_data)
    return model

def predict_from_model(model, target_date):
    day_of_year = target_date.timetuple().tm_yday - 1
    return model['mean'][day_of_year], model['max'][day_of_year], model['min'][day_of_year], model['precip'][day_of_year]

def get_weather_description(code):
    codes = {0: "☀️ Ясно", 1: "🌤️ Малооблачно", 2: "⛅ Переменная облачность", 3: "☁️ Пасмурно", 45: "🌫️ Туман", 61: "🌧️ Дождь", 63: "🌧️ Дождь", 65: "🌧️ Сильный дождь", 71: "❄️ Снег", 80: "🌧️ Ливень", 81: "🌧️ Ливень", 95: "⛈️ Гроза"}
    return codes.get(code, "❓ Неизвестно")

cache = {'city': None, 'data': None, 'model': None}

def get_forecast_data(city):
    if cache['city'] == city and cache['data']:
        historical = cache['data']
        model = cache['model']
    else:
        location = get_coordinates(city)
        if not location:
            return {'error': 'Город не найден'}
        
        historical = get_historical_data(location['lat'], location['lon'], days=3650)
        if not historical:
            return {'error': 'Не удалось загрузить данные'}
        
        model = build_model(historical)
        cache['city'] = city
        cache['data'] = historical
        cache['model'] = model
    
    last_date = historical[-1]['time']
    forecast = []
    
    for day in range(30):
        future_date = last_date + timedelta(days=day+1)
        temp_mean, temp_max, temp_min, precip = predict_from_model(model, future_date)
        
        if temp_max > 25:
            weather_icon = "☀️ Жарко"
        elif temp_max > 18:
            weather_icon = "🌤️ Тепло"
        elif temp_max > 10:
            weather_icon = "⛅ Прохладно"
        elif temp_max > 0:
            weather_icon = "☁️ Холодно"
        else:
            weather_icon = "❄️ Мороз"
        
        if precip > 5:
            weather_icon += " 🌧️"
        elif precip > 1:
            weather_icon += " 🌦️"
        
        forecast.append({
            'day': day + 1,
            'date': future_date.strftime('%d.%m'),
            'temp_mean': round(temp_mean, 1),
            'temp_max': round(temp_max, 1),
            'temp_min': round(temp_min, 1),
            'precip': round(precip, 1),
            'weather': weather_icon
        })
    
    temps_max = [d['temp_max'] for d in historical]
    temps_min = [d['temp_min'] for d in historical]
    
    return {
        'city': city,
        'current': {
            'date': historical[-1]['time'].strftime('%d.%m.%Y'),
            'temp_mean': round(historical[-1]['temp_mean'], 1),
            'temp_max': round(historical[-1]['temp_max'], 1),
            'temp_min': round(historical[-1]['temp_min'], 1),
            'precip': round(historical[-1]['precipitation'], 1),
            'weather': get_weather_description(int(historical[-1]['weathercode']))
        },
        'stats': {
            'days': len(historical),
            'years': len(set(d['time'].year for d in historical)),
            'max_all': round(max(temps_max), 1),
            'min_all': round(min(temps_min), 1)
        },
        'forecast': forecast
    }

# ============ РОУТЫ ============

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/forecast')
def api_forecast():
    city = request.args.get('city', '').strip()
    if not city:
        return jsonify({'error': 'Укажите город: ?city=Москва'}), 400
    
    data = get_forecast_data(city)
    if 'error' in data:
        return jsonify(data), 404
    
    return jsonify(data)

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})

# ============ ЗАПУСК ============

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
