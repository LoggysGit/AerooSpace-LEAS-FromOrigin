import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

APIS = {
    "NASA": "https://api.nasa.gov/insight_weather/",
    "METEO": "https://api.open-meteo.com/v1/forecast",
    "AIR": "https://air-quality-api.open-meteo.com/v1/air-quality",
    "ELEVATION": "https://api.opentopodata.org/v1/test-dataset",
    "GEO": "https://nominatim.openstreetmap.org/reverse"
}

NASA_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

async def fetch_all_data(lat, lon):
    async with httpx.AsyncClient(timeout=10.0) as client:

        tasks = [
            # 1. Weather
            client.get(APIS["METEO"], params={
                "latitude": lat, "longitude": lon,
                "current": ["temperature_2m", "relative_humidity_2m", "surface_pressure"],
                "hourly": "temperature_2m", "forecast_days": 14
            }),
            
            # 2. Air
            client.get(APIS["AIR"], params={
                "latitude": lat, "longitude": lon,
                "current": ["european_aqi", "pm2_5", "nitrogen_dioxide", "ozone"]
            }),
            
            # 3. Relief
            client.get(APIS["ELEVATION"], params={
                "locations": f"{lat},{lon}"
            }),
            
            # 4. Geo
            client.get(APIS["GEO"], params={
                "lat": lat, "lon": lon, "format": "json"
            }, headers={"User-Agent": "AerooSpace_B2B_App"})
        ]

        # Start Parsing
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assemble final Data Packet
        results = {
            "location": responses[3].json() if not isinstance(responses[3], Exception) else "Unknown",
            "weather": responses[0].json() if not isinstance(responses[0], Exception) else None,
            "air": responses[1].json() if not isinstance(responses[1], Exception) else None,
            "surface": responses[2].json() if not isinstance(responses[2], Exception) else None
        }
        
        return results