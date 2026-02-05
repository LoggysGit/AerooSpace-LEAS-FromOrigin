# - Tools -
import asyncio
import httpx
import os
# - Dotenv -
from dotenv import load_dotenv
load_dotenv()
# - Parse Dependences -
import geomag

# - Constants & Defines -
# Altitude to Pressure Mapping
PRESSURE_LEVELS = ["1000hPa", "925hPa", "850hPa", "700hPa", "500hPa", "300hPa", "250hPa", "100hPa", "50hPa", "10hPa"]
FORECAST_WINDOW = 7
GROUND_CHECK_RADIUS = 50
SPACE_CHECK_RADIUS = 250
# - Keys -
NASA_KEY = os.getenv("NASA_API_KEY")
SPACETRACK_LOGIN = os.getenv("SPACETRACK_USER")
SPACETRACK_PASSW = os.getenv("SPACETRACK_PASSWORD")
NOTAM_KEY = os.getenv("FAA_NOTAM_KEY")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")
WAQI_TOKEN = os.getenv("WAQI_TOKEN")
# - Refers -
APIS = {
    # NASA: Solar flares and Radiation (Space Weather)
    "NASA_DONKI": "https://api.nasa.gov/DONKI/notifications",
    # Space-Track: TLE Data for debris and satellites
    "SPACETRACK_AUTH": "https://www.space-track.org/ajaxauth/login",
    "SPACETRACK_QUERY": "https://www.space-track.org/basicspacedata/query/class/tle_latest/ORDINAL/1/format/json",
    # OpenWeather: Ground level pressure, humidity and icons
    "OPENWEATHER": "https://api.openweathermap.org/data/2.5/weather",
    # OpenMeteo: High altitude wind, temp and air density (Pressure levels)
    "METEO": "https://api.open-meteo.com/v1/forecast",
    # OpenStreetMap: Reverse geocoding (City/Country name)
    "OSM": "https://nominatim.openstreetmap.org/reverse",
    # OpenTopo: Surface elevation (SRTM 30m model)
    "OPENTOPO": "https://api.opentopodata.org/v1/srtm30m",
    # WAQI: Ground air quality sensors (Chemical composition)
    "WAQI": "https://api.waqi.info/feed/geo:",
    # FAA: NOTAMs (Airspace closures)
    "NOTAM": "https://notams.aim.faa.gov/notamSearch/search"
}

input_data = {
        "cosmodrome": "custom",
        "coordinates": [45.964, 63.305],
        "timestamp": "2000-01-01T12:00:00Z",
        "timezone": "UTC+0"
    }

# = Data =
data = {
        "location": {
            "name": "",            # From OSM - Country-City
        },
        "wind_profile": [],        # [Altitude (m), Speed (m/s), Direction (deg), Temp (C)]
        "aqi": {"pm2_5": 0, "pm10": 0, "no2": 0, "so2": 0, "o3": 0, "co": 0},
        "weather_summary": {
            "pressure_surface": 0, # Pressure on surface
            "average_humidity": 0, # Humidity in lower atmosphere
            "cloud_cover": 0,      # In % (Critical for optical tracking)
            "visibility": 0,       # In meters
            "forecast_7d": []      # Forecast on 7 days (Week)
        },
        "space_environment": {
            "kp_index": 0,         # From NASA (0-9)
            "xray_flux": 0,        # From NASA (Solar flares)
            "mag_declination": 0,  # From WMM (Degrees)
            "sun_pos": [0, 0],     # [Azimuth, Elevation]
            "moon_pos": [0, 0],    # [Azimuth, Elevation]
            "objects": []          # List of TLE/Debris from Space-Track
        },
        "surface": {
            "height_msl": 0,
            "slope_degree": 0,     # Surface flatness
            "terrain_type": ""     # Soil/Rock/Water
        },
        "aviation": {
            "notams": [],          # Active warnings
            "airspace_status": ""  # Open/Closed
        }
}

async def parse_osm(): # ======================= PARSING OSM - DATA: [Location: Name] ===============================
    lat, lon = input_data["coordinates"]
    
    # Параметры запроса
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",      # Формат ответа
        "addressdetails": 1,   # Просим подробности адреса
        "accept-language": "en" # Чтобы всегда было на английском
    }
    
    # Заголовки (ОБЯЗАТЕЛЬНО для Nominatim)
    headers = {
        "User-Agent": "AeroSpaceMissionControl/1.0 (contact: your@email.com)"
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"[*] Requesting OSM for: {lat}, {lon}...")
            response = await client.get(APIS["OSM"], params=params, headers=headers)
            
            if response.status_code == 200:
                res = response.json()
                
                # Извлекаем компоненты адреса
                address = res.get("address", {})
                
                # Логика сборки строки "Country-City"
                country = address.get("country", "Unknown Country")
                # Пробуем город, если нет - город поменьше, если нет - район
                city = address.get("city", 
                           address.get("town", 
                           address.get("village", 
                           address.get("state", "Open Space"))))
                
                data["location"]["name"] = f"{country}-{city}"
                
                print(f"[+] Success! Location identified as: {data['location']['name']}")
            else:
                print(f"[!] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[!] Connection Error: {e}")

async def parse_opentopo(): # ===================== PARSING OPENTOPO - DATA: [Location: elevation] ==================
    lat, lon = input_data["coordinates"]
    
    params = {
        "locations": f"{lat},{lon}"
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"[*] Requesting Elevation for: {lat}, {lon}...")
            response = await client.get(APIS["OPENTOPO"], params=params)
            
            if response.status_code == 200:
                res = response.json()
                
                if res.get("results"):
                    elevation = res["results"][0].get("elevation", 0)
                    
                    elevation = round(elevation, 1)

                    data["surface"]["height_msl"] = elevation
                    
                    print(f"[+] Success! Elevation: {elevation} meters")
                else:
                    print("[!] No elevation results found.")
            else:
                print(f"[!] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[!] Connection Error: {e}")

asyncio.run(parse_osm())
asyncio.run(parse_opentopo())
print("\nFinal Data Object:")
print(data)