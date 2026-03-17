import json

import requests
from FaaSr_py.client.py_client_stubs import faasr_log, faasr_put_file, faasr_secret


def geocode_city(city: str, api_key: str) -> tuple[float, float, str]:
    """
    Convert a city name to geographic coordinates using the OpenWeather Geocoding API.

    Args:
        city: The name of the city to geocode.
        api_key: The OpenWeather API key.

    Returns:
        A tuple of (latitude, longitude, full_location_name).
    """
    geocoding_url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": city,
        "limit": 1,
        "appid": api_key,
    }

    try:
        response = requests.get(geocoding_url, params=params, timeout=20)
        response.raise_for_status()

        results = response.json()
        if not results:
            raise ValueError(f"No geocoding results found for city: {city}")

        location = results[0]
        lat = location["lat"]
        lon = location["lon"]
        name = location["name"]
        country = location.get("country", "")
        state = location.get("state", "")

        full_name = f"{name}, {state}, {country}" if state else f"{name}, {country}"

        return lat, lon, full_name

    except Exception as e:
        faasr_log(f"Error geocoding city {city}: {e}")
        raise e


def build_weather_url(lat: float, lon: float, api_key: str) -> str:
    """
    Build the URL for the OpenWeather API 3.0 One Call endpoint.

    Args:
        lat: The latitude of the location.
        lon: The longitude of the location.
        api_key: The OpenWeather API key.

    Returns:
        The URL to fetch weather data from.
    """
    base_url = "https://api.openweathermap.org/data/3.0/onecall"
    return f"{base_url}?lat={lat}&lon={lon}&units=metric&appid={api_key}"


def fetch_weather_data(url: str, output_name: str) -> dict:
    """
    Fetch weather data from the OpenWeather API 3.0 and save it to a local file.

    Args:
        url: The URL to fetch weather data from.
        output_name: The name of the file to save the data to.

    Returns:
        The weather data as a dictionary.
    """
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        weather_data = response.json()

        with open(output_name, "w") as f:
            json.dump(weather_data, f, indent=2)

        return weather_data

    except Exception as e:
        faasr_log(f"Error fetching weather data from {url}: {e}")
        raise e


def get_weather_data(folder_name: str, output_name: str, city: str):
    """
    Fetch current weather data from OpenWeather API 3.0 using a secret API key
    and upload it to an S3 bucket.

    This function demonstrates the use of faasr_secret() to securely retrieve
    API credentials. It uses the API key for two API calls:
    1. Geocoding API to convert city name to coordinates
    2. One Call API 3.0 to fetch comprehensive weather data

    Args:
        folder_name: The name of the folder to upload the data to.
        output_name: The name of the file to upload the data to.
        city: The name of the city to get weather data for.
    """

    # 1. Get the API key from the secret store using faasr_secret
    faasr_log("Retrieving OpenWeather API key from secret store")
    api_key = faasr_secret("OPENWEATHER_API_KEY")
    faasr_log("Successfully retrieved API key")

    # 2. Geocode the city name to coordinates
    faasr_log(f"Geocoding city: {city}")
    lat, lon, full_location_name = geocode_city(city, api_key)
    faasr_log(f"Geocoded {city} to coordinates: lat={lat}, lon={lon} ({full_location_name})")

    # 3. Build the weather API URL using coordinates
    url = build_weather_url(lat, lon, api_key)
    faasr_log(f"Fetching weather data for {full_location_name}")

    # 4. Fetch the weather data and save to local file
    weather_data = fetch_weather_data(url, output_name)
    
    current = weather_data.get("current", {})
    temp = current.get("temp", "N/A")
    description = current.get("weather", [{}])[0].get("description", "N/A")
    
    faasr_log(f"Fetched weather data: {full_location_name}, Temp: {temp}°C, {description}")

    # 5. Upload the file to the S3 bucket
    faasr_put_file(
        local_file=output_name,
        remote_folder=folder_name,
        remote_file=output_name,
    )

    faasr_log(f"Uploaded weather data to {folder_name}/{output_name}")
