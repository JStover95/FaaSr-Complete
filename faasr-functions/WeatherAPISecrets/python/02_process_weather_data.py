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
    Extract key weather metrics from the OpenWeather API 3.0 response.

    Args:
        weather_data: The raw weather data from OpenWeather API 3.0.

    Returns:
        A dictionary containing extracted metrics.
    """
    current = weather_data.get("current", {})
    daily = weather_data.get("daily", [{}])[0] if weather_data.get("daily") else {}
    
    metrics = {
        "lat": weather_data.get("lat", 0),
        "lon": weather_data.get("lon", 0),
        "timezone": weather_data.get("timezone", "Unknown"),
        "temperature": current.get("temp", 0),
        "feels_like": current.get("feels_like", 0),
        "temp_min": daily.get("temp", {}).get("min", 0),
        "temp_max": daily.get("temp", {}).get("max", 0),
        "humidity": current.get("humidity", 0),
        "pressure": current.get("pressure", 0),
        "wind_speed": current.get("wind_speed", 0),
        "uvi": current.get("uvi", 0),
        "clouds": current.get("clouds", 0),
        "visibility": current.get("visibility", 0),
        "description": current.get("weather", [{}])[0].get("description", "N/A"),
        "icon": current.get("weather", [{}])[0].get("icon", "01d"),
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
    faasr_log(f"Extracted metrics for {metrics['city']}, {metrics['country']}: "
              f"{metrics['temperature']}°C, {metrics['description']}")

    # 3. Save the processed data
    save_processed_data(folder_name, output_name, metrics)
    faasr_log(f"Uploaded processed data to {folder_name}/{output_name}")
