import json

import matplotlib.pyplot as plt
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
    Create a visualization of the weather data.

    Args:
        metrics: The processed weather metrics.
        output_name: The name of the output file to save the plot to.
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle(
        f"Weather Data for {metrics['city']}, {metrics['country']}\n"
        f"{metrics['description'].title()}",
        fontsize=16,
        fontweight="bold",
    )

    # Temperature comparison
    ax1 = axes[0, 0]
    temps = [metrics["temp_min"], metrics["temperature"], metrics["temp_max"]]
    labels = ["Min", "Current", "Max"]
    colors = ["#3498db", "#e74c3c", "#e67e22"]
    bars = ax1.bar(labels, temps, color=colors, alpha=0.7)
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_title("Temperature")
    ax1.grid(True, alpha=0.3, axis="y")
    
    for bar, temp in zip(bars, temps):
        height = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{temp:.1f}°C",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    # Humidity and Pressure
    ax2 = axes[0, 1]
    ax2_twin = ax2.twinx()
    
    x_pos = [0, 1]
    humidity_bar = ax2.bar(x_pos[0], metrics["humidity"], color="#16a085", alpha=0.7, width=0.4)
    pressure_bar = ax2_twin.bar(x_pos[1], metrics["pressure"], color="#8e44ad", alpha=0.7, width=0.4)
    
    ax2.set_ylabel("Humidity (%)", color="#16a085")
    ax2_twin.set_ylabel("Pressure (hPa)", color="#8e44ad")
    ax2.set_title("Humidity & Pressure")
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(["Humidity", "Pressure"])
    ax2.tick_params(axis="y", labelcolor="#16a085")
    ax2_twin.tick_params(axis="y", labelcolor="#8e44ad")
    ax2.set_ylim(0, 100)
    
    ax2.text(x_pos[0], metrics["humidity"], f"{metrics['humidity']}%", 
             ha="center", va="bottom", fontweight="bold")
    ax2_twin.text(x_pos[1], metrics["pressure"], f"{metrics['pressure']} hPa", 
                  ha="center", va="bottom", fontweight="bold")

    # Feels Like vs Actual Temperature
    ax3 = axes[1, 0]
    categories = ["Actual", "Feels Like"]
    values = [metrics["temperature"], metrics["feels_like"]]
    colors_temp = ["#e74c3c", "#f39c12"]
    bars = ax3.bar(categories, values, color=colors_temp, alpha=0.7)
    ax3.set_ylabel("Temperature (°C)")
    ax3.set_title("Temperature Perception")
    ax3.grid(True, alpha=0.3, axis="y")
    
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax3.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{val:.1f}°C",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    # Wind Speed
    ax4 = axes[1, 1]
    wind_categories = ["Wind Speed"]
    wind_values = [metrics["wind_speed"]]
    bars = ax4.bar(wind_categories, wind_values, color="#27ae60", alpha=0.7)
    ax4.set_ylabel("Wind Speed (m/s)")
    ax4.set_title("Wind Speed")
    ax4.grid(True, alpha=0.3, axis="y")
    
    for bar, val in zip(bars, wind_values):
        height = bar.get_height()
        ax4.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{val:.1f} m/s",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

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
