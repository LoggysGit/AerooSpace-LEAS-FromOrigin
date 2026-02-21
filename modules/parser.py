# - Dependences -
import os
import re
import math
import json
import datetime
from datetime import datetime, timedelta, timezone as dt_tz
from dateutil.relativedelta import relativedelta
import httpx
#import asyncio
# - Dotenv -
from dotenv import load_dotenv
load_dotenv()
# - Tools -
import geomag
import ephem
import skyfield.api as sf

# - Constants & Defines -
PROMPTS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'prompts.json')
# Altitude to Pressure Mapping
PRESSURE_LEVELS = ["1000hPa", "925hPa", "850hPa", "700hPa", "500hPa", "300hPa", "250hPa", "100hPa", "50hPa", "10hPa"]
HISTORY_WINDOW_YEARS = 5
SPACETRACK_LIMIT = 5 # FOR TESTING (20)
# - Keys -
NASA_KEY = os.getenv("NASA_API_KEY")
SPACETRACK_LOGIN = os.getenv("SPACETRACK_USER")
SPACETRACK_PASSW = os.getenv("SPACETRACK_PASSWORD")
WAQI_TOKEN = os.getenv("WAQI_TOKEN")
AVWX_TOKEN = os.getenv("AVWX_TOKEN")
# - Refers -
APIS = {
    # NASA: Solar flares and Radiation (Space Weather)
    "NASA_DONKI": "https://api.nasa.gov/DONKI/",
    # Space-Track: TLE Data for debris and satellites
    "SPACETRACK_AUTH": "https://www.space-track.org/ajaxauth/login",
    "SPACETRACK_QUERY": f"https://www.space-track.org/basicspacedata/query/class/gp/EPOCH/%3Enow-30/MEAN_MOTION/%3E11.25/format/json/limit/{SPACETRACK_LIMIT}",
    # OpenMeteo: High altitude wind, temp and air density (Pressure levels)
    "METEO": "https://api.open-meteo.com/v1/forecast",
    "AQI_TRENDS": "https://air-quality-api.open-meteo.com/v1/air-quality?",
    # OpenStreetMap: RevQVBoxLayout,erse geocoding (City/Country name)
    "OSM": "https://nominatim.openstreetmap.org/reverse",
    # OpenTopo: Surface elevation (SRTM 30m model)
    "OPENTOPO": "https://api.opentopodata.org/v1/srtm30m",
    # WAQI: Ground air quality sensors (Chemical composition)
    "WAQI": "https://api.waqi.info/feed/geo:",
    # Flights
    "AVIATION_TRAFFIC": "https://opensky-network.org/api/states/all",
}

class DataControlManager:
    spaceport_def = False

    def __init__(self): pass

    # = Input =
    input_data = {
        "spaceport": "custom",
        "coordinates": [0, 0],
        "target_timestamp": "2026-01-01T00:00:00Z",
        "request_time": "2026-01-01T00:00:00Z",
        "timezone": "UTC+0"
    }

    def setInput(self, spaceport, lat, lon, time, utc_zone):
        self.spaceport_def = (not spaceport == "custom")
        self.input_data["spaceport"] = spaceport
        self.input_data["coordinates"] = [lat, lon]
        self.input_data["target_timestamp"] = time
        self.input_data["request_time"] = datetime.utcnow().isoformat() + "Z"
        self.input_data["timezone"] = utc_zone

    def updatePredicted(self, parameters):
        try:
            match = re.search(r'(\{.*\}|\[.*\])', parameters, re.DOTALL)
            if match:
                clean_json = match.group(1)
                self.predicted = json.loads(clean_json)
            else: print("[P] JSON not found in the prediction response: ", parameters)
        except json.JSONDecodeError as e: print(f"[P] Predicted Data Parsing Error: {e}")

    def utc_time(self, input_time, timezone):
        raw_offset = timezone.replace("UTC", "").strip()
        try: offset_hours = int(raw_offset)
        except ValueError: offset_hours = 0

        clean_iso = input_time.replace("Z", "")
        dt_local = datetime.fromisoformat(clean_iso)

        dt_utc = dt_local - timedelta(hours=offset_hours)
        dt_utc = dt_utc.replace(tzinfo=dt_tz.utc)

        return dt_utc
    
    # = Data Structures =
    data = {
        "location": {
            "name": "-",              # From OSM - Country-City
        },
        "wind_profile_now": [],       # [Altitude (m), Speed (m/s), Direction (deg), Temp (C)]
        "aqi_now": {"pm2_5": None, "pm10": None, "no2": None, "so2": None, "o3": None, "co": None},
        "aqi_trends": [],
        "weather_summary": {
            "pressure_surface": None, # Pressure on surface
            "average_humidity": None, # Humidity in lower atmosphere
            "cloud_cover": None,      # In % (Critical for optical tracking)
            "visibility": None,       # In meters
            "forecast_7d": [],        # Forecast on 7 days (Week)
            "weather_normal": []      # Weather normal for HISTORY_WINDOW_YEARS years
        },
        "space_environment": {
            "kp_index_now": None,     # From NASA (0-9)
            "xray_flux_now": None,    # From NASA (Solar flares)
            "donki_trends": [],       # DONKI trendss
            "mag_declination_pr":None,# From WMM (Degrees)
            "sun_pos_pr": [],         # [Azimuth, Elevation]
            "moon_pos_pr": [],        # [Azimuth, Elevation]
            "objects_predicted": []   # List of TLE/Debris from Space-Track
        },
        "surface": {
            "height_msl": None,       # Height
            "slope_degree": None,     # Surface flatness
            "terrain_type": "-"       
        },
        "aviation": {
            "shedules_now": []        # Fights
        }
    }

    predicted = {
    "pressure_pr": float,
    "visibility_pr": int, # Base on pressure, temperature, cloud_cover, aqi and historical cloudiness
    "cloud_cover_pr": int,
    "humidity_pr": int,
    "temperature_pr": float,
    "flare_pr": float, # Probability 0-100 based on recent M/X flare frequency
    "aqi_pr": float, # Predicted AQI
    "avg_wind_speed_pr": float,
    "max_wind_speed_pr": float,
    "kp_pr": float,
    "wind_degrees_pr": [], # 10 values for different altitudes
    "prediction_confidence": int # Overall confidence in the prediction (0-100)%
    }
    # ================================== API REQUESTS ==================================

    # -------------- OPERATIONAL FUNCTIONS --------------

    async def parseMeteo(self, lat, lon): # --- OPEN-METEO - DATA: [Wind Profile, Summary, Forecast] ---
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
                    self.data["weather_summary"]["pressure_surface"] = h.get("surface_pressure", [0])[0]
                    self.data["weather_summary"]["average_humidity"] = h.get("relativehumidity_2m", [0])[0]
                    self.data["weather_summary"]["cloud_cover"] = h.get("cloudcover", [0])[0]
                    self.data["weather_summary"]["visibility"] = h.get("visibility", [0])[0]

                    # --- Forecast 7d (Weathercode) ---
                    self.data["weather_summary"]["forecast_7d"] = d.get("weathercode", [])

                    # --- Wind Profile ---
                    new_profile = []
                    for p in PRESSURE_LEVELS:
                        alt = pressure_map.get(p, 0)
                        speed = h.get(f"windspeed_{p}", [0])[0]
                        direction = h.get(f"winddirection_{p}", [0])[0]
                        temp = h.get(f"temperature_{p}", [0])[0]

                        # [Altitude (m), Speed (m/s), Direction (deg), Temp (C)]
                        new_profile.append([alt, speed, direction, temp])

                    self.data["wind_profile_now"] = new_profile

                    print(f"[V] Success! Wind profile updated for {len(PRESSURE_LEVELS)} levels.")
                else:
                    print(f"[!] API Error: {response.status_code}")

            except Exception as e:
                print(f"[X] Connection Error: {e}")

    async def parseWAQI(self, lat, lon): # --- WAQI - DATA: [AQI: pm2_5, pm10, no2, so2, o3, co] ---
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

                        self.data["aqi_now"]["pm2_5"] = iaqi.get("pm25", {}).get("v", None)
                        self.data["aqi_now"]["pm10"] = iaqi.get("pm10", {}).get("v", None)
                        self.data["aqi_now"]["no2"] = iaqi.get("no2", {}).get("v", None)
                        self.data["aqi_now"]["so2"] = iaqi.get("so2", {}).get("v", None)
                        self.data["aqi_now"]["o3"] = iaqi.get("o3", {}).get("v", None)
                        self.data["aqi_now"]["co"] = iaqi.get("co", {}).get("v", None)

                        print(f"[V] Success! AQI data updated.")
                    else: print(f"[!] WAQI Error: {res.get('data')}")
                else: print(f"[!] API Error: {response.status_code}")
            except Exception as e: print(f"[X] Connection Error: {e}")

    async def parseDONKI(self): # --- NASA DONKI - DATA: [kp_index, xray_flux] ---
        # Yesterday - now
        now = datetime.now()
        start_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        params = {
            "startDate": start_date,
            "api_key": NASA_KEY
        }

        async with httpx.AsyncClient() as client:
            try:
                print("[*] Requesting REAL-TIME NASA Space Weather...")
                gst_resp = await client.get(APIS["NASA_DONKI"] + "GST", params=params)
                flr_resp = await client.get(APIS["NASA_DONKI"] + "FLR", params=params)

                self.data["space_environment"]["kp_index_now"] = 0
                self.data["space_environment"]["xray_flux_now"] = "A0.0" 

                # Kp-index
                if gst_resp.status_code == 200:
                    gst_data = gst_resp.json()
                    if gst_data:
                        last_storm = gst_data[-1]
                        all_kp = [item.get('kpIndex', 0) for item in last_storm.get('allKpIndex', [])]
                        if all_kp: self.data["space_environment"]["kp_index_now"] = all_kp[-1] # Actual
                # Solar Flares
                if flr_resp.status_code == 200:
                    flr_data = flr_resp.json()
                    if flr_data: self.data["space_environment"]["xray_flux_now"] = flr_data[-1].get('classType', 'B')

                print(f"[V] Success! Space Weather is synced with current time.")
            except Exception as e:
                print(f"[X] NASA Connection Error: {e}")

    async def getSpaceTrack(self): # --- SPACE-TRACK - DATA: [Space: objects (TLE/Debris)] ---
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

    async def getNearestICAO(self, lat:float, lon:float): # --- [X] ICAO NEAR COORINATESDS ---
        url = f"https://avwx.rest/api/station/near/{lat},{lon}"
        headers = {"Authorization": f"BEARER {AVWX_TOKEN}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    result = resp.json()
                    if isinstance(result, list) and len(result) > 0:
                        icao = result[0].get('station', {}).get('icao')
                        if icao: return icao
                    print(f"[-] No station found for coords: {lat}, {lon}")
                else:
                    print(f"[!] Station lookup API error: {resp.status_code}")
            except Exception as e:
                print(f"[X] Station lookup connection failed: {e}")

        return None

    async def parseFlights(self, lat, lon, radius_km=200): # --- FLIGHTS NEAR lat, lon ---
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

                    self.data["aviation"]["shedules_now"] = flights
                    print(f"[V] Success! Flight shedules updated.")
                else: print(f"[!] Flights API Error: {resp.status_code}")
            except Exception as e: print(f"[X] Flights API Error: {e}")

    # -------------- STRATEGIC FUNCTIONS --------------

    async def getWeatherNormal(self, lat, lon, target_time):
        all_history_points = []
        print(f"[*] Fetching historical context for {HISTORY_WINDOW_YEARS} years...")
        async with httpx.AsyncClient() as client:
            for i in range(1, HISTORY_WINDOW_YEARS + 1):
                # 3-day window around the same date in past years
                past_year = target_time.year - i
                start_d = (target_time - timedelta(days=1)).replace(year=past_year).strftime("%Y-%m-%d")
                end_d = (target_time + timedelta(days=1)).replace(year=past_year).strftime("%Y-%m-%d")
                url = (
                    f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
                    f"&start_date={start_d}&end_date={end_d}"
                    f"&hourly=temperature_2m,surface_pressure,cloud_cover,relative_humidity_2m"
                )
                try:
                    resp = await client.get(url, timeout=10.0)
                    if resp.status_code == 200:
                        h = resp.json().get("hourly", {})
                        if h:
                            # Average the values over the 3 days
                            year_stat = {
                                "year": past_year,
                                "temperature": round(sum(h['temperature_2m'])/len(h['temperature_2m']), 1),
                                "pressure": round(sum(h['surface_pressure'])/len(h['surface_pressure']), 1),
                                "cloud_cover": round(sum(h['cloud_cover'])/len(h['cloud_cover']), 0),
                                "humidity": round(sum(h['relative_humidity_2m'])/len(h['relative_humidity_2m']), 0)
                            }
                            all_history_points.append(year_stat)
                            print(f"[>V] Year {past_year} data loaded.")
                except Exception as e: print(f"[>!] Year {past_year} fetch error: {e}")
        self.data["weather_summary"]["weather_normal"] = all_history_points
        print(f"[V] Loaded {len(all_history_points)} historical data points.")

    async def getAQITrends(self, target_time):
        date_str = target_time.strftime("%Y-%m-%d")
        target_hour = target_time.hour

        lat, lon = self.input_data['coordinates']
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

    async def predictDONKI(self, target_time):
        trends = []

        print(f"[*] Analyzing solar trends for the last {HISTORY_WINDOW_YEARS} years...")

        async with httpx.AsyncClient() as client:
            for i in range(1, HISTORY_WINDOW_YEARS + 1):
                start_dt = target_time - relativedelta(years=i, days=3)
                end_dt = target_time - relativedelta(years=i) + relativedelta(days=3)

                params = {
                    "startDate": start_dt.strftime("%Y-%m-%d"),
                    "endDate": end_dt.strftime("%Y-%m-%d"),
                    "api_key": NASA_KEY
                }

                try:
                    # Check Solar Flares (FLR) for that historical window
                    resp = await client.get(APIS["NASA_DONKI"] + "FLR", params=params)

                    if resp.status_code == 200:
                        flares = resp.json()
                        # Count flares and find the strongest one in that window
                        count = len(flares)
                        strongest = "N/A"
                        if count > 0:
                            # Sorting by class: X > M > C > B
                            strongest = sorted([f.get('classType', 'B') for f in flares])[-1]

                        trends.append({
                            "year": start_dt.year,
                            "flare_count": count,
                            "peak_class": strongest,
                            "flares": [
                                {
                                    "peak_time": f["peakTime"],
                                    "class": f["classType"],
                                    "location": f["sourceLocation"],
                                    "region": f["activeRegionNum"]
                                } 
                                for f in flares]
                        })
                    else: print(f">[!] NASA DONKI API Error for year {start_dt.year}: {resp.status_code}")

                except Exception as e:
                    print(f">[X] Trend error for year {start_dt.year}: {e}")
                    continue
        self.data["space_environment"]["donki_trends"] = trends
        print(f"[V] Trend analysis complete. {len(trends)} years processed.")

    async def processSpaceObjects(self, lat, lon, target_time, objects):
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
                        "is_visible": alt_val > 500 # Can we see it physically (or will be in 10 minutes)
                    })
                print(">[V] TLE Object processed")
            except Exception as e:
                print(f">[!] TLE Object process error: {e}")
                continue

        processed.sort(key=lambda x: x['position_prediction']['range_km']) # Sort by nearest
        self.data["space_environment"]["objects_predicted"] = processed

    # -------------- FUNCTIONS WITHOUT TIME DEPENDENCE --------------

    async def parseOSM(self, lat, lon): # ------------------- OSM - DATA: [Location: Name] -------------------
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

                    self.data["location"]["name"] = f"{country}-{city}"

                    print(f"[V] Success! Location identified.")
                else:
                    print(f"[!] API Error: {response.status_code}")

            except Exception as e:
                print(f"[X] Connection Error: {e}")

    async def parseOpenTopo(self, lat, lon, m=55):  # -------------------  OSM - DATA: [Surface: *] -------------------
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
                        h_c, h_n, h_s, h_e, h_w = [h if h is not None else 0.0 for h in [h_c, h_n, h_s, h_e, h_w]]

                        # Calculate gradients
                        dist = m * 2 # 2 * delta (m)
                        dz_dx = (h_e - h_w) / dist
                        dz_dy = (h_n - h_s) / dist

                        # Slope in degrees
                        slope = math.degrees(math.atan(math.sqrt(dz_dx**2 + dz_dy**2)))

                        self.data["surface"]["height_msl"] = round(h_c, 2)
                        self.data["surface"]["slope_degree"] = round(slope, 2)

                        # terrain-type Logic
                        if h_c < 0: self.data["surface"]["terrain_type"] = "Sea Level"
                        elif slope > 13: self.data["surface"]["terrain_type"] = "Mountainous"
                        else: self.data["surface"]["terrain_type"] = "Flat Plain"

                        print(f"[V] Success! Surface profile updated.")
                    else:
                        print("[!] Not enough points for slope calculation.")
                else:
                    print(f"[!] API Error: {response.status_code}")

            except Exception as e:
                print(f"[X] Connection Error: {e}")

    async def calculateLocal(self, lat, lon, alt, target_utc_time): # ------------------- LOCAL CALCULATING [Magnetosphere, Sun, Moon] -------------------
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

            self.data["space_environment"]["sun_pos_pr"] = [
                round(math.degrees(sun.az), 2), 
                round(math.degrees(sun.alt), 2)
            ]

            self.data["space_environment"]["moon_pos_pr"] = [
                round(math.degrees(moon.az), 2), 
                round(math.degrees(moon.alt), 2)
            ]

            # --- WMM ---
            try:
                gm = geomag.geomag.GeoMag() 
                mag = gm.GeoMag(lat, lon, alt * 3.28084, time=target_utc_time.year + target_utc_time.month/12) # Alt in feet
                dec = mag.dec
            except: dec = 0

            self.data["space_environment"]["mag_declination_pr"] = round(dec, 2)

            print(f"[V] Local calculations complete.")

        except Exception as e:
            print(f"[X] Calculation Error: {e}")

    def calculate_aqi(self, aqi_data):
        limits = {
            "pm2_5": 25, "pm10": 50, "no2": 40, 
            "so2": 20, "o3": 100, "co": 10000
        }
        indices = []
        for substance, limit in limits.items():
            val = aqi_data.get(substance)
            if val is not None:
                # % from limit
                indices.append((val / limit) * 100)

        return int(max(indices)) if indices else 0

    def getLCS(self, pressure_surf, visibility, cloud_cover, min_wind_temp, avg_humidity, max_wind_speed, kp, xray, latitude_rad, height_msl, slope_degree, s5_coef, magnetosphere_bias, debris_count, wind_penalty, aqi):
        s1 = (100 - abs((1013.25 - pressure_surf) / 2)) * 0.4 + (min(100, visibility / 100)) * 0.3 + ((100 * (1 - cloud_cover / 100)) * (1 - 0.5 * (int(min_wind_temp < -10) + int(avg_humidity / 100 > 0.7)))) * 0.3
        s2 = ((33 - max_wind_speed) * 3) - wind_penalty - (aqi/15)
        s3 = (100 * math.exp(-0.15 * kp)) - xray - debris_count*2 - abs(magnetosphere_bias)
        s4 = 100 * math.cos(latitude_rad) + (height_msl / 500) - (20 * max(0, slope_degree - 2))
        s5 = 100 - (50 * s5_coef)

        s1 = s1 if s1 >= 0 else 0
        s2 = s2 if s2 >= 0 else 0
        s3 = s3 if s3 >= 0 else 0
        s4 = s4 if s4 >= 0 else 0
        s5 = s5 if s5 >= 0 else 0

        r1 = 1 if max_wind_speed < 30 else 0
        r2 = 1 if kp < 7 else 0
        r3 = 1 if visibility > 4000 else 0

        lcs = round((0.35 * s1 + 0.25 * s2 + 0.15 * s3 + 0.15 * s4 + 0.1 * s5) * r1 * r2 * r3, 2)
        return f"""
CALCULATION:
(Si MINIMUM = 0)
1. S1 = [100 - (abs(1013.25 - {pressure_surf}) / 2)] * 0.4 + [min(100, {visibility} / 100)] * 0.3 + [(100 * (1 - {cloud_cover}/100)) * (1 - 0.5 * (int({min_wind_temp} < -10) + int({avg_humidity}/100 > 0.7)))] * 0.3 = {s1}
2. S2 = (33 - {max_wind_speed}) * 3 - {wind_penalty} - {aqi} / 15 = {s2}
3. S3 = (100 * exp(-0.15 * {kp})) - {xray} - {debris_count}*2 - abs({magnetosphere_bias}) = {s3}
4. S4 = 100 * cos({latitude_rad}) + ({height_msl} / 500) - (20 * max(0, {slope_degree} - 2)) = {s4}
5. S5 = max(0, 100 - (50 * {s5_coef})) = {s5}
6. R1 = {max_wind_speed} < 30 = {r1}; R2 = {kp} < 7 = {r2}; R3 = {visibility} > 4000 = {r3}
7. LCS = (0.35 * {s1} + 0.25 * {s2} + 0.15 * {s3} + 0.15 * {s4} + 0.1 * {s5}) * {r1} * {r2} * {r3} = {lcs}
 => LCS IS {lcs} <=
"""

    def form_lcs(self, data):
        # Main (S1)
        press = int(data["pressure_pr"]) if "pressure_pr" in data else 0
        vis = int(data["visibility_pr"]) if "visibility_pr" in data else 0
        clouds = int(data["cloud_cover_pr"]) if "cloud_cover_pr" in data else 0
        # AQI
        aqi_value = int(data["aqi_pr"]) if "aqi_pr" in data else 0
        # Winds
        min_wind_temp = int(data["min_wind_temp_pr"]) if "min_wind_temp_pr" in data else 0
        max_wind_speed = int(data["max_wind_speed_pr"]) if "max_wind_speed_pr" in data else 0
        avg_wind_speed = int(data["avg_wind_speed_pr"]) if "avg_wind_speed_pr" in data else 0
        
        wind_degrees = data["wind_degrees_pr"] if "wind_degrees_pr" in data else []
        
        wind_penalty = 0
        if isinstance(wind_degrees, list) and len(wind_degrees) > 0:
            for di in range(1, len(wind_degrees)):
                theta_delta = abs(wind_degrees[di] - wind_degrees[0])
                act = 1 if theta_delta < 45 else 0
                penalty = (0.7 - math.cos(math.radians(theta_delta))) * avg_wind_speed * act
                wind_penalty += penalty
        wind_penalty = int(wind_penalty)
        # Humidity
        avg_humidity = int(data["humidity_pr"]) if "humidity_pr" in data else 0
        # KP
        kp = int(data["kp_pr"]) if "kp_pr" in data else 0
        # Xray
        xray = data["flare_pr"] if "flare_pr" in data else "A0.0"
        xray_map = {'X': 80, 'M': 30, 'C': 5, 'B': 1, 'A': 0}
        x_char = str(xray)[0].upper() if isinstance(xray, str) and len(xray) > 0 else 'A'
        xray_value = int(xray_map.get(x_char, 0))
        # Debris
        debris_count = int(len(self.data["space_environment"]["objects_predicted"]))
        # Mgsph 
        magn = self.data["space_environment"]["mag_declination_pr"] if "mag_declination_pr" in self.data["space_environment"] else 0
        # Surface
        latitude_rad = float(math.radians(self.input_data["coordinates"][0]))
        height_msl = int(self.data["surface"]["height_msl"]) if "height_msl" in self.data["surface"] else 0
        slope_degree = int(self.data["surface"]["slope_degree"]) if "slope_degree" in self.data["surface"] else 0
        if self.input_data["spaceport"] != "custom": slope_degree = 0
        # Coefficient for terrain type
        s5_coef = 0 # PLACEHOLDER

        return self.getLCS(
            press, vis, clouds, min_wind_temp, avg_humidity, 
            max_wind_speed, kp, xray_value, latitude_rad, 
            height_msl, slope_degree, s5_coef, magn, 
            debris_count, wind_penalty, aqi_value
        )
    # ================================== MAIN ====================================
    
    async def fetchAllData(self):
        lat, lon = self.input_data["coordinates"]
        target_time, tz = self.input_data["target_timestamp"], self.input_data["timezone"]
        input_time = self.utc_time(target_time, tz)
        #time_delta = input_time - datetime.now(dt_tz.utc)
        # OSM & OpenTopo
        await self.parseOSM(lat, lon)
        await self.parseOpenTopo(lat, lon)
        # OpenMeteo
        await self.parseMeteo(lat, lon)
        await self.getWeatherNormal(lat, lon, input_time)
        # WAQI
        await self.parseWAQI(lat, lon)
        print(f"[*] Fetching AQI History for {HISTORY_WINDOW_YEARS} years")
        for i in range(1, HISTORY_WINDOW_YEARS + 1):
            past_time = input_time - relativedelta(years=i)
            archive_data = await self.getAQITrends(past_time)
            if archive_data:
                self.data["aqi_trends"].append({
                    "date": past_time.strftime("%Y-%m-%d"),
                    "content": archive_data
                })
        # NASA X
        await self.parseDONKI()
        await self.predictDONKI(input_time)
        # Space Track
        tle = await self.getSpaceTrack()
        await self.processSpaceObjects(lat, lon, input_time, tle)
        # Magnetosphere & Sun/Moon
        await self.calculateLocal(lat, lon, self.data["surface"]["height_msl"], input_time)
        # Flights
        await self.parseFlights(lat, lon)
    
    # ================================== OUTPUT FUNCTIONS ==================================

    def getFetchedData(self): return self.data

    def getLCSReport(self): return self.form_lcs(self.predicted)

    def getPredictionPrompt(self):
        return f"""
ROLE: You are an Advanced Space Launch Weather Predictor.
TODAY IS {self.input_data["request_time"]}.
CONTEXT: Calculate the LIKELY conditions for {self.input_data["target_timestamp"]} from the current state.
HISTORICAL WINDOW: {HISTORY_WINDOW_YEARS} years.

INPUT DATA:
{{
    "location": "{self.data['location']['name']}",
    "coordinates": {self.input_data['coordinates']}, // Lat, Lon
    "current_state": {{
        "pressure": {self.data["weather_summary"]["pressure_surface"]},
        "humidity": {self.data["weather_summary"]["average_humidity"]},
        "clouds": {self.data["weather_summary"]["cloud_cover"]},
        "visibility": {self.data["weather_summary"]["visibility"]},
        "kp": {self.data["space_environment"]["kp_index_now"]},
        "xray": "{self.data["space_environment"]["xray_flux_now"]}",
        "aqi_current": {self.data["aqi_now"] if self.data["aqi_now"] else "null"}
    }},
    "historical_normals": {self.data["weather_summary"]["weather_normal"]},
    "aqi_history": {self.data["aqi_trends"]},
    "solar_activity_history": {self.data["space_environment"]["donki_trends"]},
    "current_wind_profile": {self.data["wind_profile_now"]} // IMPORTANT: This parameter is list of lists [Altitude(m), Speed(m/s), Direction(deg), Temp(C)]
}}

TASK:
1. Compare "current_state" with "historical_normals". 
2. If pressure is lower than normal, predict potential storm/wind increase.
3. If solar activity (DONKI) shows a cluster of flares, predict higher KP/X-ray probability.
4. Estimate wind profile for T+24h by extrapolating current shear trends.
CRITICAL LOGIC RULES:
- PARAMETER ISOLATION: A missing value in one category (e.g., Space Environment) must NOT cause a None value in another (e.g., Weather Summary).
- INTERPOLATION: If current_state has a null, use the trend: (Average of Historical Normals) + (Global Seasonal Shift in region).
- NO CASCADING FAILURES: Fill every possible field. Use None only as a last resort for that specific field alone.

RETURN ONLY A VALID JSON OBJECT:
{{
    "pressure_pr": float,
    "visibility_pr": int, // Base on pressure, temperature, cloud_cover, aqi and historical cloudiness
    "cloud_cover_pr": int, // Cloud cover prediction in percentage
    "humidity_pr": int,
    "temperature_pr": float,
    "flare_pr": float, // Predicted X-ray class (A, B, C, M, X) and number (e.g., M2.5)
    "aqi_pr": float, // Predicted AQI
    "avg_wind_speed_pr": float,
    "max_wind_speed_pr": float,
    "kp_pr": float,
    "wind_degrees_pr": [int, int, int, int, int, int, int, int, int, int] // 10 values for different altitudes
    "prediction_confidence": int // Overall confidence in the prediction (0-100)%
}}
"""
                
    def getEstimatingPrompt(self):
        with open(PROMPTS_JSON_PATH, 'r', encoding='utf-8') as f: prompts = json.load(f)
        overall_prompt = f'''
{prompts["main_prompt"]}
---------------------------------------
USER'S INPUT:
{json.dumps(self.input_data)}
---------------------------------------
HISTORY_WINDOW_YEARS = {HISTORY_WINDOW_YEARS}
===================
{prompts["sow"]}
---------------------------------------
FETCHED DATA:
{json.dumps(self.data)}
---------------------------------------
{prompts["formula_explanation"]}
{self.getLCSReport()}
---------------------------------------
PREDICTED DATA FOR {self.input_data["target_timestamp"]}:
{self.predicted}
IT WAS USED FOOR CALCULATING THE LCS VALUE
PREDICTION CONFIDENCE: {self.predicted.get("prediction_confidence", 0)}%
---------------------------------------
{prompts["output_format"]}
        '''
        return overall_prompt