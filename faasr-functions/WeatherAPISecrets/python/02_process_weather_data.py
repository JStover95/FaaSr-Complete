import json

from FaaSr_py.client.py_client_stubs import faasr_get_file, faasr_log, faasr_put_file


def get_input_data(folder_name: str, input_name: str) -> dict:
    """
    Get the input weather data from the FaaSr bucket and return it as a dictionary.

    Args:
        folder_name: The name of the folder to get the input data from.
        input_name: The name of the input file to get the data from.

    Returns:
        A dictionary containing the weather data.
    """
    faasr_get_file(
        local_file=input_name,
        remote_folder=folder_name,
        remote_file=input_name,
    )
    
    with open(input_name, "r") as f:
        return json.load(f)


def extract_weather_metrics(weather_data: dict) -> dict:
    """
    Extract hourly forecast metrics from the OpenWeather API response.

    Args:
        weather_data: The raw hourly forecast data from OpenWeather API.

    Returns:
        A dictionary containing extracted time-series metrics.
    """
    city_info = weather_data.get("city", {})
    forecast_list = weather_data.get("list", [])
    
    timestamps = []
    temperatures = []
    feels_like_temps = []
    humidity_values = []
    pressure_values = []
    wind_speeds = []
    precipitation_probs = []
    descriptions = []
    
    for entry in forecast_list:
        timestamps.append(entry.get("dt_txt", ""))
        temperatures.append(entry.get("main", {}).get("temp", 0))
        feels_like_temps.append(entry.get("main", {}).get("feels_like", 0))
        humidity_values.append(entry.get("main", {}).get("humidity", 0))
        pressure_values.append(entry.get("main", {}).get("pressure", 0))
        wind_speeds.append(entry.get("wind", {}).get("speed", 0))
        precipitation_probs.append(entry.get("pop", 0) * 100)
        descriptions.append(entry.get("weather", [{}])[0].get("description", "N/A"))
    
    metrics = {
        "city": city_info.get("name", "Unknown"),
        "country": city_info.get("country", "Unknown"),
        "lat": city_info.get("coord", {}).get("lat", 0),
        "lon": city_info.get("coord", {}).get("lon", 0),
        "timestamps": timestamps,
        "temperature": temperatures,
        "feels_like": feels_like_temps,
        "humidity": humidity_values,
        "pressure": pressure_values,
        "wind_speed": wind_speeds,
        "precipitation_probability": precipitation_probs,
        "descriptions": descriptions,
        "num_timestamps": len(timestamps),
    }
    
    return metrics


def save_processed_data(folder_name: str, output_name: str, metrics: dict) -> None:
    """
    Save the processed weather metrics to a local file and upload to S3.

    Args:
        folder_name: The name of the folder to save the output data to.
        output_name: The name of the output file to save the data to.
        metrics: The processed weather metrics.
    """
    with open(output_name, "w") as f:
        json.dump(metrics, f, indent=2)

    faasr_put_file(
        local_file=output_name,
        remote_folder=folder_name,
        remote_file=output_name,
    )


def process_weather_data(folder_name: str, input_name: str, output_name: str):
    """
    Process weather data by extracting key metrics.

    Args:
        folder_name: The name of the folder to get the input data from and save output to.
        input_name: The name of the input file to get the data from.
        output_name: The name of the output file to save the processed data to.
    """
    # 1. Get the input data
    weather_data = get_input_data(folder_name, input_name)
    faasr_log(f"Loaded weather data from {folder_name}/{input_name}")

    # 2. Extract weather metrics
    metrics = extract_weather_metrics(weather_data)
    faasr_log(f"Extracted {metrics['num_timestamps']} hourly forecasts for "
              f"{metrics['city']}, {metrics['country']}")

    # 3. Save the processed data
    save_processed_data(folder_name, output_name, metrics)
    faasr_log(f"Uploaded processed data to {folder_name}/{output_name}")
