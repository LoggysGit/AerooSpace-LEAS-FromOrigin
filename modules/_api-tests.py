# - Tools -
import os
import math
import json
import datetime
from datetime import datetime, timedelta, timezone as dt_tz
from dateutil.relativedelta import relativedelta
import asyncio
import httpx
# - Dotenv -
from dotenv import load_dotenv
load_dotenv()
# - Parse Dependences -
import geomag
import ephem
import skyfield.api as sf

# - Constants & Defines -
# Altitude to Pressure Mapping
PRESSURE_LEVELS = ["1000hPa", "925hPa", "850hPa", "700hPa", "500hPa", "300hPa", "250hPa", "100hPa", "50hPa", "10hPa"]
HISTORY_WINDOW_YEARS = 5
SPACETRACK_LIMIT = 10
# - Keys -
NASA_KEY = os.getenv("NASA_API_KEY")
SPACETRACK_LOGIN = os.getenv("SPACETRACK_USER")
SPACETRACK_PASSW = os.getenv("SPACETRACK_PASSWORD")
NOTAM_KEY = os.getenv("FAA_NOTAM_KEY")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")
WAQI_TOKEN = os.getenv("WAQI_TOKEN")
AVWX_TOKEN = os.getenv("AVWX_TOKEN")
# - Refers -
APIS = {
    # NASA: Solar flares and Radiation (Space Weather)
    "NASA_DONKI": "https://api.nasa.gov/DONKI/",
    # Space-Track: TLE Data for debris and satellites
    "SPACETRACK_AUTH": "https://www.space-track.org/ajaxauth/login",
    "SPACETRACK_QUERY": f"https://www.space-track.org/basicspacedata/query/class/gp/EPOCH/%3Enow-30/MEAN_MOTION/%3E11.25/format/json/limit/{SPACETRACK_LIMIT}",
    # OpenWeather: Ground level pressure, humidity and icons
    "OPENWEATHER": "https://api.openweathermap.org/data/2.5/weather",
    # OpenMeteo: High altitude wind, temp and air density (Pressure levels)
    "METEO": "https://api.open-meteo.com/v1/forecast",
    "AQI_TRENDS": "https://air-quality-api.open-meteo.com/v1/air-quality?",
    # OpenStreetMap: RevQVBoxLayout,erse geocoding (City/Country name)
    "OSM": "https://nominatim.openstreetmap.org/reverse",
    # OpenTopo: Surface elevation (SRTM 30m model)
    "OPENTOPO": "https://api.opentopodata.org/v1/srtm30m",
    # WAQI: Ground air quality sensors (Chemical composition)
    "WAQI": "https://api.waqi.info/feed/geo:",
    # NOTAMs & Flights
    "AVIATION_TRAFFIC": "https://opensky-network.org/api/states/all",
    "AVIATION_NOTAM": "https://avwx.rest/api/notam/"
}

input_data = {
        "cosmodrome": "custom",
        "coordinates": [43.4224, 77.0062],
        "timestamp": "2026-02-09T12:00:00Z",
        "timezone": "UTC+5"
 }

# = Data =
data = {
        "location": {
            "name": "-",              # From OSM - Country-City
        },
        "wind_profile": [],           # [Altitude (m), Speed (m/s), Direction (deg), Temp (C)]
        "aqi": {"pm2_5": None, "pm10": None, "no2": None, "so2": None, "o3": None, "co": None},
        "aqi_trends": [],
        "weather_summary": {
            "pressure_surface": None, # Pressure on surface
            "average_humidity": None, # Humidity in lower atmosphere
            "cloud_cover": None,      # In % (Critical for optical tracking)
            "visibility": None,       # In meters
            "forecast_7d": [],        # Forecast on 7 days (Week)
            "weather_normal": []      # Weather normal for YEAR_ARCHIVE years
        },
        "space_environment": {
            "kp_index": None,         # From NASA (0-9)
            "xray_flux": None,        # From NASA (Solar flares)

            "mag_declination": None,  # From WMM (Degrees)
            "sun_pos": [],            # [Azimuth, Elevation]
            "moon_pos": [],           # [Azimuth, Elevation]
            "objects": []             # List of TLE/Debris from Space-Track
        },
        "surface": {
            "height_msl": None,       # Height
            "slope_degree": None,     # Surface flatness
            "terrain_type": "-"       # Soil/Rock/Water
        },
        "aviation": {
            "notams": [],             # Active warnings
            "shedules": [],           # Fights
            "airspace_status": "-"    # Open/Closed
        }
}

def utc_time(input_time, timezone):
    raw_offset = timezone.replace("UTC", "").strip()
    try: offset_hours = int(raw_offset)
    except ValueError: offset_hours = 0
        
    clean_iso = input_time.replace("Z", "")
    dt_local = datetime.fromisoformat(clean_iso)
    
    dt_utc = dt_local - timedelta(hours=offset_hours)
    
    dt_utc = dt_utc.replace(tzinfo=dt_tz.utc)
    
    return dt_utc

# ================================= OPERATIONAL FUNCTIONS (<14 DAYS) ==============================================

async def parse_meteo_op(lat, lon): # ------------------- OPEN-METEO - DATA: [Wind Profile, Summary, Forecast] -------------------
    forecast = 7
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
        "forecast_days": forecast
    }

    # Meters-Pressure Mapping [Pa-m]
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

                # --- Forecast 7d (Weathercode) ---
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
                
                print(f"[V] Success! Wind profile updated for {len(PRESSURE_LEVELS)} levels.")
            else:
                print(f"[!] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[X] Connection Error: {e}")

async def parse_waqi_op(lat, lon): # ------------------- WAQI - DATA: [AQI: pm2_5, pm10, no2, so2, o3, co] -------------------
    url = APIS["WAQI"] + f"{lat};{lon}/"
    params = {"token": WAQI_TOKEN}

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
                    
                    print(f"[V] Success! AQI data updated.")
                else:
                    print(f"[!] WAQI Error: {res.get('data')}")
            else:
                print(f"[!] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[X] Connection Error: {e}")

async def parse_donki(): # ------------------- NASA DONKI - DATA: [Space: kp_index, xray_flux] -------------------
    url_gst = APIS["NASA_DONKI"] + "GST" # Geomagnetic Storms
    url_flr = APIS["NASA_DONKI"] + "FLR" # Solar Flares
    
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
                    # Last flare class (- if no flares)
                    last_flare = flr_data[-1].get('classType', '-')
                    data["space_environment"]["xray_flux"] = last_flare

            print(f"[V] Success! NASA Data updated.")
                
        except Exception as e:
            print(f"[X] NASA Connection Error: {e}")

async def get_spacetrack_op(): # ------------------- SPACE-TRACK - DATA: [Space: objects (TLE/Debris)] -------------------
    auth_data = {
        "identity": SPACETRACK_LOGIN,
        "password": SPACETRACK_PASSW
    }

    async with httpx.AsyncClient() as client:
        try:
            print("[*] Authenticating with Space-Track...")
            auth_resp = await client.post(APIS["SPACETRACK_AUTH"], data=auth_data)
            
            if auth_resp.status_code == 200 and "set-cookie" in auth_resp.headers:
                print("[+] Authentication successful. Fetching TLE data...")
                cookies = auth_resp.cookies
                tle_resp = await client.get(APIS["SPACETRACK_QUERY"], cookies=cookies)
                
                if tle_resp.status_code == 200:
                    tle_data = tle_resp.json()
                    print(f"[V] Reсieved {len(tle_data)} space objects from Space-Track.")
                    return tle_data
                else:
                    print(f"[!] TLE API Error: {tle_resp.status_code}")
                    return []
            else:
                print(f"[-] Authentication Failed: {auth_resp.status_code}")
                return []
                
        except Exception as e:
            print(f"[X] Space-Track Connection Error: {e}")
            return []

async def get_nearest_icao(lat:float, lon:float):
    url = f"https://avwx.rest/api/station/near/{lat},{lon}"
    headers = {"Authorization": f"BEARER {AVWX_TOKEN}"}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                result = resp.json()
                if isinstance(result, list) and len(result) > 0:
                    icao = result[0].get('station', {}).get('icao')
                    if icao:
                        return icao
                print(f"[-] No station found for coords: {lat}, {lon}")
            else:
                print(f"[!] Station lookup API error: {resp.status_code}")
        except Exception as e:
            print(f"[X] Station lookup connection failed: {e}")
    
    return None
async def parse_notams(lat, lon):
    pass

async def parse_flights(lat, lon, radius_km=200):
    lat_delta = radius_km / 111.1
    # Longitude degree length: 111.1 * cos(latitude)
    lon_delta = radius_km / (111.1 * math.cos(math.radians(lat)))

    # Define Bounding Box
    params = {
        "lamin": lat - lat_delta,
        "lamax": lat + lat_delta,
        "lomin": lon - lon_delta,
        "lomax": lon + lon_delta
    }

    print("[*] Recieving flights...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(APIS["AVIATION_TRAFFIC"], params=params, timeout=10.0)
            
            if resp.status_code == 200:
                states = resp.json().get("states") or []
                flights = []
                
                for s in states:
                    flights.append({
                        "callsign": s[1].strip() or "N/A", # Aircraft ID
                        "altitude_m": s[7],                # Geometric Altitude (meters)
                        "velocity_ms": s[9],               # Ground Speed (m/s)
                        "heading": s[10],                  # Track angle (degrees)
                        "on_ground": s[8]                  # True if taxiing/parked
                    })
                
                data["aviation"]["shedules"] = flights
                print(f"[V] Success! Flight shedules updated.")
        except Exception as e: print(f"[X] Flights API Error: {e}")

# ================================= STRATEGIC FUNCTIONS (>14 DAYS) ==============================================

async def get_weather_normal(lat, lon, target_time):
    all_history = []

    print(f"[*] Calculating weather normal...")
    async with httpx.AsyncClient() as client:
        for i in range(1, HISTORY_WINDOW_YEARS + 1):
            past_year = target_time.year - i
            # 3-Day Bias from target data
            start_d = (target_time - timedelta(days=1)).replace(year=past_year).strftime("%Y-%m-%d")
            end_d = (target_time + timedelta(days=1)).replace(year=past_year).strftime("%Y-%m-%d")
            
            url = (
                f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
                f"&start_date={start_d}&end_date={end_d}"
                f"&hourly=temperature_2m,surface_pressure,wind_speed_10m,cloud_cover"
            )
            
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    h = resp.json().get("hourly", {})
                    all_history.append(h)
            except Exception as e:
                print(f"[!] Archive fetch error for year {past_year}: {e}")

    # Average
    if all_history:
        avg_temp = sum([sum(y['temperature_2m'])/len(y['temperature_2m']) for y in all_history]) / len(all_history)
        avg_clouds = sum([sum(y['cloud_cover'])/len(y['cloud_cover']) for y in all_history]) / len(all_history)
        avg_press = sum([sum(y['surface_pressure'])/len(y['surface_pressure']) for y in all_history]) / len(all_history)

        data["weather_summary"]["weather_normal"] = {
            "temp_norm": round(avg_temp, 1),
            "cloud_norm": round(avg_clouds, 0),
            "pressure_norm": round(avg_press, 1)
        }
        print(f"[V] Weather normal calculated based on {HISTORY_WINDOW_YEARS} years of history.")

async def get_aqi_trends(target_time):
    date_str = target_time.strftime("%Y-%m-%d")
    target_hour = target_time.hour

    lat, lon = input_data['coordinates']
    fetch_address = (
        f"{APIS['AQI_TRENDS']}latitude={lat}&longitude={lon}"
        f"&hourly=pm2_5,pm10,carbon_monoxide,ozone,nitrogen_dioxide,sulphur_dioxide"
        f"&start_date={date_str}&end_date={date_str}"
    )

    async with httpx.AsyncClient() as client:
        try:
            print(f">[*] Fetching AQI Forecast for {date_str}...")
            resp = await client.get(fetch_address)
            
            if resp.status_code == 200:
                forecast_data = resp.json()
                
                h_data = forecast_data.get("hourly", {})
                
                trend = {
                    "pm2_5": h_data.get("pm2_5", [])[target_hour],
                    "pm10": h_data.get("pm10", [])[target_hour],
                    "no2": h_data.get("nitrogen_dioxide", [])[target_hour],
                    "so2": h_data.get("sulphur_dioxide", [])[target_hour],
                    "o3": h_data.get("ozone", [])[target_hour],
                    "co": h_data.get("carbon_monoxide", [])[target_hour]
                }
                print(f">[V] AQI Forecast retrieved for {date_str}.")

                return trend
            else:
                print(f">[!] AQI Trends API Error: {resp.status_code}")
                return []
                
        except Exception as e:
            print(f">[X] AQI Trends Connection Error: {e}")
            return []

async def predict_donki(target_time):
    pass

async def process_space_objects(lat, lon, target_time, objects):
    ts = sf.load.timescale()
    t = ts.from_datetime(target_time.replace(tzinfo=dt_tz.utc))

    observer = sf.wgs84.latlon(lat, lon)
    
    print("[*] Processing TLE data...")
    processed = []
    for obj in objects:
        try:
            line1 = obj['TLE_LINE1']
            line2 = obj['TLE_LINE2']
            satellite = sf.EarthSatellite(line1, line2, obj['OBJECT_NAME'], ts)
            
            # Position Projection
            difference = satellite - observer
            topocentric = difference.at(t)
            
            # Azimuth, Alt & Distance
            alt, az, distance = topocentric.altaz()
            az_val, alt_val, dist_val = float(az.degrees), float(alt.degrees), float(distance.km)
            
            processed.append({
                    "name": str(obj['OBJECT_NAME']),
                    "norad_id": str(obj['NORAD_CAT_ID']),
                    "type": str(obj['OBJECT_TYPE']),
                    "rcs": str(obj['RCS_SIZE']),
                    "position_prediction": {
                        "azimuth": round(az_val, 2),
                        "elevation": round(alt_val, 2),
                        "range_km": round(dist_val, 2)
                    },
                    "is_visible": alt_val > 0 # Can we see it physically
                })
            print(">[V] TLE Object processed")
        except Exception as e:
            print(f">[!] TLE Object process error: {e}")
            continue

    processed.sort(key=lambda x: x['position_prediction']['range_km']) # Sort by nearest
    data["space_environment"]["objects"] = processed

# ================================= FUNCTIONS WITHOUT TIME DEPENDENCE ==============================================

async def parse_osm(lat, lon): # ------------------- OSM - DATA: [Location: Name] -------------------
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
        "accept-language": "en"
    }
    headers = {
        "User-Agent": "AerooSpaceCompetitionLEASFromOrigin/1.0"
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"[*] Requesting OSM for: {lat}, {lon}...")
            response = await client.get(APIS["OSM"], params=params, headers=headers)
            
            if response.status_code == 200:
                res = response.json()
                
                address = res.get("address", {})
                
                country = address.get("country", "Unknown Country")
                # Town ?-> Village ?-> State ?-> "Open Space"
                city = address.get("city", 
                           address.get("town", 
                           address.get("village", 
                           address.get("state", "Open Space"))))
                
                data["location"]["name"] = f"{country}-{city}"
                
                print(f"[V] Success! Location identified.")
            else:
                print(f"[!] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[X] Connection Error: {e}")

async def parse_opentopo(lat, lon, m=55):  # -------------------  OSM - DATA: [Surface: *] -------------------
    delta = m * 0.00001
    
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
                    dist = m * 2 # 2 * delta (m)
                    dz_dx = (h_e - h_w) / dist
                    dz_dy = (h_n - h_s) / dist

                    # Slope in degrees
                    slope = math.degrees(math.atan(math.sqrt(dz_dx**2 + dz_dy**2)))

                    data["surface"]["height_msl"] = round(h_c, 2)
                    data["surface"]["slope_degree"] = round(slope, 2)
                    
                    # terrain-type Logic
                    if h_c < 0: data["surface"]["terrain_type"] = "Water / Sea Level"
                    elif slope > 13: data["surface"]["terrain_type"] = "Mountainous / Rough"
                    else: data["surface"]["terrain_type"] = "Flat Plain"

                    print(f"[V] Success! Surface profile updated.")
                else:
                    print("[!] Not enough points for slope calculation.")
            else:
                print(f"[!] API Error: {response.status_code}")
                
        except Exception as e:
            print(f"[X] Connection Error: {e}")

async def calculate_local(lat, lon, alt, target_utc_time): # ------------------- LOCAL CALCULATING [Magnetosphere, Sun, Moon] -------------------
    try:
        print(f"[*] Calculating celestial and magnetic data for {target_utc_time}...")
        
        # --- Sun & Moon ---
        observer = ephem.Observer()
        observer.lat = str(lat)
        observer.lon = str(lon)
        observer.elevation = alt
        observer.date = target_utc_time
        
        sun = ephem.Sun(observer)
        moon = ephem.Moon(observer)
        
        data["space_environment"]["sun_pos"] = [
            round(math.degrees(sun.az), 2), 
            round(math.degrees(sun.alt), 2)
        ]
        
        data["space_environment"]["moon_pos"] = [
            round(math.degrees(moon.az), 2), 
            round(math.degrees(moon.alt), 2)
        ]

        # --- WMM (2 Different calculation methods) ---
        try:
            gm = geomag.geomag.GeoMag() 
            mag = gm.GeoMag(lat, lon, alt * 3.28084, time=target_utc_time.year + target_utc_time.month/12) # Alt in feet
            dec = mag.dec
        except: dec = geomag.declination(lat, lon, alt) 
            
        data["space_environment"]["mag_declination"] = round(dec, 2)

        print(f"[V] Local calculations complete.")
        
    except Exception as e:
        print(f"[X] Calculation Error: {e}")

print("=== Starting API Tests ===")

greenvich_time = utc_time(input_data["timestamp"], input_data["timezone"])

async def parse_all(input_time):
    lat, lon = input_data["coordinates"]
    time_delta = input_time - datetime.now(dt_tz.utc)
    # OSM & OpenTopo
    await parse_osm(lat, lon)
    await parse_opentopo(lat, lon)
    # OpenMeteo
    await parse_meteo_op(lat, lon)
    await get_weather_normal(lat, lon, input_time)
    # WAQI
    await parse_waqi_op(lat, lon)
    print(f"[*] Fetching AQI History for {HISTORY_WINDOW_YEARS} years")
    for i in range(1, HISTORY_WINDOW_YEARS + 1):
        past_time = input_time - relativedelta(years=i)
        archive_data = await get_aqi_trends(past_time)

        if archive_data:
            data["aqi_trends"].append({
                "date": past_time.strftime("%Y-%m-%d"),
                "content": archive_data
            })
    # NASA X
    await parse_donki()
    await predict_donki(input_time)
    # Space Track
    tle = await get_spacetrack_op()
    await process_space_objects(lat, lon, input_time, tle)
    # Magnetosphere & Sun/Moon
    await calculate_local(lat, lon, data["surface"]["height_msl"], input_time)
    # NOTAMs & Flights
    await parse_notams(lat, lon)
    await parse_flights(lat, lon)

asyncio.run(parse_all(greenvich_time))
print("\n=== Final Data Object ===")
print(json.dumps(data, indent=2, ensure_ascii=False)) # Test JSON Debug