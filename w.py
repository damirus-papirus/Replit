import requests
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============ КЕШ (чтобы не качать данные каждый раз) ============
cache = {
    'data': None,
    'city': None,
    'model': None,
    'last_update': None
}

# ============ ФУНКЦИИ ============

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

def get_forecast_data(city):
    # Проверяем кеш
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
        
        # Сохраняем в кеш
        cache['city'] = city
        cache['data'] = historical
        cache['model'] = model
        cache['last_update'] = datetime.now()
    
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

@app.route('/')
def index():
    return '''
    <h1>🌤️ Умный прогноз погоды</h1>
    <p>Используйте API: <code>/api/forecast?city=Название</code></p>
    <p>Пример: <a href="/api/forecast?city=Moscow">/api/forecast?city=Moscow</a></p>
    '''

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

if __name__ == '__main__':
    print("🚀 Сервер готов к продакшну!")
    app.run(host='0.0.0.0', port=5000)
