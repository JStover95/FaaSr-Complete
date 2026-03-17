import json
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from FaaSr_py.client.py_client_stubs import faasr_get_file, faasr_log, faasr_put_file


def get_input_data(folder_name: str, input_name: str) -> dict:
    """
    Get the processed weather data from the FaaSr bucket.

    Args:
        folder_name: The name of the folder to get the input data from.
        input_name: The name of the input file to get the data from.

    Returns:
        A dictionary containing the processed weather data.
    """
    faasr_get_file(
        local_file=input_name,
        remote_folder=folder_name,
        remote_file=input_name,
    )
    
    with open(input_name, "r") as f:
        return json.load(f)


def create_weather_visualization(metrics: dict, output_name: str) -> None:
    """
    Create a visualization of the 4-day hourly forecast data.

    Args:
        metrics: The processed hourly forecast metrics.
        output_name: The name of the output file to save the plot to.
    """
    datetime_objects = [datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts in metrics["timestamps"]]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f"4-Day Hourly Forecast for {metrics['city']}, {metrics['country']}\n"
        f"({metrics['num_timestamps']} hourly timestamps)",
        fontsize=16,
        fontweight="bold",
    )

    # Temperature Forecast
    ax1 = axes[0, 0]
    ax1.plot(datetime_objects, metrics["temperature"], 
             color="#e74c3c", linewidth=2, label="Temperature", alpha=0.8)
    ax1.plot(datetime_objects, metrics["feels_like"], 
             color="#f39c12", linewidth=2, linestyle="--", label="Feels Like", alpha=0.6)
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_title("Temperature Forecast")
    ax1.legend(loc="best")
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax1.tick_params(axis="x", rotation=45)

    # Humidity Forecast
    ax2 = axes[0, 1]
    ax2.fill_between(datetime_objects, metrics["humidity"], 
                     color="#16a085", alpha=0.5, label="Humidity")
    ax2.plot(datetime_objects, metrics["humidity"], 
             color="#16a085", linewidth=2, alpha=0.8)
    ax2.set_ylabel("Humidity (%)")
    ax2.set_title("Humidity Forecast")
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax2.tick_params(axis="x", rotation=45)

    # Precipitation Probability
    ax3 = axes[1, 0]
    ax3.fill_between(datetime_objects, metrics["precipitation_probability"], 
                     color="#3498db", alpha=0.5, label="Precipitation Prob.")
    ax3.plot(datetime_objects, metrics["precipitation_probability"], 
             color="#3498db", linewidth=2, alpha=0.8)
    ax3.set_ylabel("Precipitation Probability (%)")
    ax3.set_title("Precipitation Probability Forecast")
    ax3.set_ylim(0, 100)
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax3.tick_params(axis="x", rotation=45)

    # Wind Speed Forecast
    ax4 = axes[1, 1]
    ax4.fill_between(datetime_objects, metrics["wind_speed"], 
                     color="#27ae60", alpha=0.5, label="Wind Speed")
    ax4.plot(datetime_objects, metrics["wind_speed"], 
             color="#27ae60", linewidth=2, alpha=0.8)
    ax4.set_ylabel("Wind Speed (m/s)")
    ax4.set_title("Wind Speed Forecast")
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax4.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.savefig(output_name, dpi=150, bbox_inches="tight")
    plt.close()


def plot_weather_data(folder_name: str, input_name: str, output_name: str):
    """
    Create a visualization of the weather data.

    Args:
        folder_name: The name of the folder to get the input data from.
        input_name: The name of the input file to get the data from.
        output_name: The name of the output file to save the plot to.
    """
    # 1. Get the input data
    metrics = get_input_data(folder_name, input_name)
    faasr_log(f"Loaded processed weather data from {folder_name}/{input_name}")

    # 2. Create the visualization
    create_weather_visualization(metrics, output_name)
    faasr_log("Created weather visualization")

    # 3. Upload the plot to S3
    faasr_put_file(
        local_file=output_name,
        remote_folder=folder_name,
        remote_file=output_name,
    )
    faasr_log(f"Uploaded visualization to {folder_name}/{output_name}")
