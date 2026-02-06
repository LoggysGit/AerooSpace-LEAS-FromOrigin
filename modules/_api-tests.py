# - Tools -
import asyncio
import httpx
import os
import math
# - Dotenv -
from dotenv import load_dotenv
load_dotenv()
# - Parse Dependences -
import geomag

# - Constants & Defines -
# Altitude to Pressure Mapping
PRESSURE_LEVELS = ["1000hPa", "925hPa", "850hPa", "700hPa", "500hPa", "300hPa", "250hPa", "100hPa", "50hPa", "10hPa"]
FORECAST_WINDOW = 14
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
    # OpenStreetMap: RevQVBoxLayout,erse geocoding (City/Country name)
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
        "coordinates": [43.4224, 77.0062],
        "timestamp": "2026-02-16T12:00:00Z",
        "timezone": "UTC+0"
    }

# = Data =
data = {
        "location": {
            "name": "-",            # From OSM - Country-City
        },
        "wind_profile": [],        # [Altitude (m), Speed (m/s), Direction (deg), Temp (C)]
        "aqi": {"pm2_5": None, "pm10": None, "no2": None, "so2": None, "o3": None, "co": None},
        "weather_summary": {
            "pressure_surface": None, # Pressure on surface
            "average_humidity": None, # Humidity in lower atmosphere
            "cloud_cover": None,      # In % (Critical for optical tracking)
            "visibility": None,       # In meters
            "forecast_7d": []      # Forecast on 7 days (Week)
        },
        "space_environment": {
            "kp_index": None,         # From NASA (0-9)
            "xray_flux": None,        # From NASA (Solar flares)
            "mag_declination": None,  # From WMM (Degrees)
            "sun_pos": [0, 0],     # [Azimuth, Elevation]
            "moon_pos": [0, 0],    # [Azimuth, Elevation]
            "objects": []          # List of TLE/Debris from Space-Track
        },
        "surface": {
            "height_msl": None,
            "slope_degree": None,     # Surface flatness
            "terrain_type": "-"     # Soil/Rock/Water
        },
        "aviation": {
            "notams": [],          # Active warnings
            "airspace_status": "-"  # Open/Closed
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

async def parse_opentopo(): 
    lat, lon = input_data["coordinates"]
    delta = 50 * 0.00001
    
    # 5 Dots
    locs = [
        f"{lat},{lon}",           # Center [0]
        f"{lat + delta},{lon}",   # North  [1]
        f"{lat - delta},{lon}",   # South  [2]
        f"{lat},{lon + delta}",   # East   [3]
        f"{lat},{lon - delta}"    # West   [4]
    ]

    params = {
        "locations": "|".join(locs)
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"[*] Requesting Elevation & Slope for: {lat}, {lon}...")
            response = await client.get(APIS["OPENTOPO"], params=params)
            
            if response.status_code == 200:
                res = response.json().get("results", [])
                
                if len(res) == 5:
                    # Height values
                    h_c = res[0]['elevation'] # C
                    h_n = res[1]['elevation'] # N
                    h_s = res[2]['elevation'] # S
                    h_e = res[3]['elevation'] # E
                    h_w = res[4]['elevation'] # W

                    # Calculate gradients
                    dist = 111.0 # 2 * delta (m)
                    dz_dx = (h_e - h_w) / dist
                    dz_dy = (h_n - h_s) / dist

                    # Slope in degrees
                    slope = math.degrees(math.atan(math.sqrt(dz_dx**2 + dz_dy**2)))

                    data["surface"]["height_msl"] = round(h_c, 1)
                    data["surface"]["slope_degree"] = round(slope, 2)
                    
                    # terrain-type Logic
                    if h_c < 0:
                        data["surface"]["terrain_type"] = "Water / Sea Level"
                    elif slope > 13:
                        data["surface"]["terrain_type"] = "Mountainous / Rough"
                    else:
                        data["surface"]["terrain_type"] = "Flat Plain"

                    print(f"[+] Elevation: {h_c}m, Slope: {data['surface']['slope_degree']}°")
                else:
                    print("[!] Not enough points for slope calculation.")
            else:
                print(f"[!] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[!] Connection Error: {e}")

async def parse_meteo(): # ===================== PARSING OPEN-METEO - DATA: [Wind Profile, Summary, Forecast] ==================
    lat, lon = input_data["coordinates"]
    
    # 1. Формируем список параметров для всех уровней давления
    # Нам нужны: temp, windspeed, winddirection для каждого уровня из PRESSURE_LEVELS
    hourly_params = [
        "surface_pressure", "relativehumidity_2m", "cloudcover", "visibility"
    ]
    for p in PRESSURE_LEVELS:
        hourly_params.append(f"temperature_{p}")
        hourly_params.append(f"windspeed_{p}")
        hourly_params.append(f"winddirection_{p}")

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": hourly_params,
        "daily": "weathercode",
        "wind_speed_unit": "ms",
        "timezone": "UTC",
        "forecast_days": 7
    }

    # Meters-Pressure Mapping
    pressure_map = {
        "1000hPa": 100, "925hPa": 750, "850hPa": 1500, "700hPa": 3000,
        "500hPa": 5500, "300hPa": 9000, "250hPa": 10500, "100hPa": 16000,
        "50hPa": 20000, "10hPa": 31000
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"[*] Requesting Atmospheric Data for: {lat}, {lon}...")
            response = await client.get(APIS["METEO"], params=params)
            
            if response.status_code == 200:
                res = response.json()
                h = res.get("hourly", {})
                d = res.get("daily", {})

                # --- Weather Summary ---
                data["weather_summary"]["pressure_surface"] = h.get("surface_pressure", [0])[0]
                data["weather_summary"]["average_humidity"] = h.get("relativehumidity_2m", [0])[0]
                data["weather_summary"]["cloud_cover"] = h.get("cloudcover", [0])[0]
                data["weather_summary"]["visibility"] = h.get("visibility", [0])[0]

                # --- Forecast 7d ---
                # Weathercode
                data["weather_summary"]["forecast_7d"] = d.get("weathercode", [])

                # --- Wind Profile ---
                new_profile = []
                for p in PRESSURE_LEVELS:
                    alt = pressure_map.get(p, 0)
                    speed = h.get(f"windspeed_{p}", [0])[0]
                    direction = h.get(f"winddirection_{p}", [0])[0]
                    temp = h.get(f"temperature_{p}", [0])[0]
                    
                    # [Altitude (m), Speed (m/s), Direction (deg), Temp (C)]
                    new_profile.append([alt, speed, direction, temp])
                
                data["wind_profile"] = new_profile
                
                print(f"[+] Success! Wind profile updated for {len(PRESSURE_LEVELS)} levels.")
            else:
                print(f"[!] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[!] Connection Error: {e}")

async def parse_waqi(): # ===================== PARSING WAQI - DATA: [AQI: pm2_5, pm10, no2, so2, o3, co] ==================
    lat, lon = input_data["coordinates"]
    token = WAQI_TOKEN
    
    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/"
    params = {"token": token}

    async with httpx.AsyncClient() as client:
        try:
            print(f"[*] Requesting Air Quality for: {lat}, {lon}...")
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                res = response.json()
                if res.get("status") == "ok":
                    iaqi = res["data"].get("iaqi", {})
                    
                    data["aqi"]["pm2_5"] = iaqi.get("pm25", {}).get("v", None)
                    data["aqi"]["pm10"] = iaqi.get("pm10", {}).get("v", None)
                    data["aqi"]["no2"] = iaqi.get("no2", {}).get("v", None)
                    data["aqi"]["so2"] = iaqi.get("so2", {}).get("v", None)
                    data["aqi"]["o3"] = iaqi.get("o3", {}).get("v", None)
                    data["aqi"]["co"] = iaqi.get("co", {}).get("v", None)
                    
                    print(f"[+] Success! AQI data updated. PM2.5: {data['aqi']['pm2_5']}")
                else:
                    print(f"[!] WAQI Error: {res.get('data')}")
            else:
                print(f"[!] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[!] Connection Error: {e}")

async def parse_nasa(): # ===================== PARSING NASA DONKI - DATA: [Space: kp_index, xray_flux] ==================
    url_gst = "https://api.nasa.gov/DONKI/GST" # Geomagnetic Storms
    url_flr = "https://api.nasa.gov/DONKI/FLR" # Solar Flares
    
    params = {"api_key": NASA_KEY}

    async with httpx.AsyncClient() as client:
        try:
            print("[*] Requesting NASA Space Weather...")

            gst_resp = await client.get(url_gst, params=params)
            flr_resp = await client.get(url_flr, params=params)
            
            # Kp-index
            if gst_resp.status_code == 200:
                gst_data = gst_resp.json()
                if gst_data:
                    # Last storm's max Kp-index (0 if no storms)
                    last_storm = gst_data[-1]
                    all_kp = [all_items.get('kpIndex', 0) for all_items in last_storm.get('allKpIndex', [])]
                    data["space_environment"]["kp_index"] = max(all_kp) if all_kp else 0
            
            # X-ray Flux (B, C, M, X)
            if flr_resp.status_code == 200:
                flr_data = flr_resp.json()
                if flr_data:
                    # Last flare class (0 if no flares)
                    last_flare = flr_data[-1].get('classType', '0')
                    data["space_environment"]["xray_flux"] = last_flare

            print(f"[+] NASA Data: Kp={data['space_environment']['kp_index']}, Flare={data['space_environment']['xray_flux']}")
                
        except Exception as e:
            print(f"[!] NASA Connection Error: {e}")

async def parse_spacetrack(): # ===================== PARSING SPACE-TRACK - DATA: [Space: objects (TLE/Debris)] ==================
    auth_data = {
        "identity": SPACETRACK_LOGIN,
        "password": SPACETRACK_PASSW
    }

    async with httpx.AsyncClient() as client:
        try:
            print("[*] Authenticating with Space-Track...")
            auth_resp = await client.post(APIS["SPACETRACK_AUTH"], data=auth_data)
            
            if auth_resp.status_code == 200 and "set-cookie" in auth_resp.headers:
                print("[*] Authentication successful. Fetching TLE data...")
                cookies = auth_resp.cookies
                tle_resp = await client.get(APIS["SPACETRACK_QUERY"], cookies=cookies)
                
                if tle_resp.status_code == 200:
                    tle_data = tle_resp.json()
                    data["space_environment"]["objects"] = tle_data
                    print(f"[+] Retrieved {len(tle_data)} space objects from Space-Track.")
                else:
                    print(f"[!] TLE API Error: {tle_resp.status_code}")
            else:
                print(f"[!] Authentication Failed: {auth_resp.status_code}")
                
        except Exception as e:
            print(f"[!] Space-Track Connection Error: {e}")

print("=== Starting API Tests ===")

asyncio.run(parse_osm())
asyncio.run(parse_opentopo())
asyncio.run(parse_meteo())
asyncio.run(parse_waqi())
asyncio.run(parse_nasa())
asyncio.run(parse_spacetrack())

print("\nFinal Data Object:")
print(data)