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

class DataControlManager:
    # = Input =
    input_data = {
        "coordinates": [0, 0],
        "timestamp": "2000-01-01T12:00:00Z",
    }

    def setInput(lat, lon, time):
        global input_data
        input_data["coordinates"] = [lat, lon]
        input_data["timestamp"] = time

    # = Data =
    data = {
        "location": {
            "name": "",      # From OSM
            "elevation": 0   # From OpenTopo
        },
        "wind_profile": [
            # [Altitude (m), Speed (m/s), Direction (deg), Temp (C)]
            [10, 5.2, 180, 15], 
            [100, 7.1, 185, 14],
            [200, 7.1, 185, 14],
            [500, 7.1, 185, 14],
            [1000, 7.1, 185, 14],
            [2000, 7.1, 185, 14],
            [3500, 7.1, 185, 14],
            [5000, 7.1, 185, 14],
            [10000, 7.1, 185, 14],
            [20000, 7.1, 185, 14],
            [25000, 7.1, 185, 14],
            [30000, 7.1, 185, 14],
        ],
        "aqi": {
            "pm2_5": 0,
            "pm10": 0,
            "no2": 0,
            "so2": 0,
            "o3": 0,
            "co": 0
        },
        "weather_summary": {
            "pressure_surface": 0, # Pressure on surface
            "average_humidity": 0, # Humidity in lower atmosphere
            "cloud_cover": 0,      # In % (Critical for optical tracking)
            "visibility": 0,       # In meters
            "forecast_7d": [
                "Sunny",
                "Cloudy",
                "Rainy",
                "Snowy",
                "Cloudy",
                "Sunny",
                "Sunny"
            ]
        },
        "space_environment": {
            "kp_index": 0,         # From NASA (0-9)
            "xray_flux": 0,        # From NASA (Solar flares)
            "mag_declination": 0,  # From WMM (Degrees)
            "sun_pos": [0, 0],     # [Azimuth, Elevation]
            "moon_pos": [0, 0],    # [Azimuth, Elevation]
            "objects_in_radius": [] # List of TLE/Debris from Space-Track
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

    # Main Fetch
    async def fetchAllData():
        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [
            ]
    
            # Start Parsing
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Assemble final Data Packet
            results = {
            }
            
            return results