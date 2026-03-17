# Weather API Secrets Workflow

## Table of Contents

- [Key Topics](#key-topics)
- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Understanding the Secrets Feature](#understanding-the-secrets-feature)
  - [What are Workflow Secrets?](#what-are-workflow-secrets)
  - [How Secrets Work in FaaSr](#how-secrets-work-in-faasr)
  - [Security Best Practices](#security-best-practices)
- [Getting an OpenWeather API Key](#getting-an-openweather-api-key)
- [Writing our Functions](#writing-our-functions)
  - [1. Get Weather Data Using Secrets](#1-get-weather-data-using-secrets)
  - [2. Process Weather Data](#2-process-weather-data)
  - [3. Plot Weather Data](#3-plot-weather-data)
- [Building our Workflow](#building-our-workflow)
  - [1. Set Up our Compute Server](#1-set-up-our-compute-server)
  - [2. Set Up our Data Store](#2-set-up-our-data-store)
  - [3. Configure Workflow Secrets](#3-configure-workflow-secrets)
  - [4. Add our Functions](#4-add-our-functions)
  - [5. Connect our Functions](#5-connect-our-functions)
  - [6. Finalize our Workflow Configuration](#6-finalize-our-workflow-configuration)
- [Storing Secrets in GitHub](#storing-secrets-in-github)
- [Download and Invoke the Workflow](#download-and-invoke-the-workflow)

## Key Topics

- Using `faasr_secret()` to securely access API keys
- Configuring workflow secrets in the FaaSr Workflow Builder
- Storing secrets in GitHub Actions
- Fetching hourly forecast data from external APIs
- Processing time-series JSON data
- Creating time-series visualizations
- Working with 96 hourly timestamps

## Introduction

The Weather API Secrets Workflow demonstrates how to use FaaSr's secrets management feature to securely access API keys and credentials in your workflows. This tutorial shows a common real-world scenario: fetching hourly forecast data from a third-party API (OpenWeather) that requires an API key, then processing and visualizing that data.

```mermaid
flowchart LR
  01["Get Weather Data<br/>(4-day hourly forecast<br/>using secret API key)"]
  02["Process Weather Data<br/>(96 hourly timestamps)"]
  03["Plot Weather Data<br/>(time-series visualization)"]

  01 --> 02
  02 --> 03
```

This workflow demonstrates:

- Securely retrieving API keys using `faasr_secret()`
- Fetching 4-day hourly forecast data from OpenWeather API (96 timestamps)
- Processing time-series JSON data
- Creating time-series visualizations with matplotlib

**Note:** This feature is currently only supported on GitHub Actions.

## Prerequisites

This example assumes you:

1. Completed the FaaSr tutorial ([https://faasr.io/FaaSr-Docs/tutorial/](https://faasr.io/FaaSr-Docs/tutorial/))
2. Have a GitHub account with a `FaaSr-workflow` repository set up

## Understanding the Secrets Feature

### What are Workflow Secrets?

Workflow secrets allow you to securely store and access sensitive information like API keys, passwords, and credentials in your FaaSr workflows. Instead of hardcoding these values in your code (which is insecure), you:

1. Define which secrets your workflow needs in the workflow configuration
2. Store the actual secret values in your GitHub repository settings
3. Access the secrets at runtime using the `faasr_secret()` function

### How Secrets Work in FaaSr

The FaaSr secrets system has three main components:

1. **Workflow Configuration**: In the workflow builder GUI, you can list any secrets that your workflow must access

2. **GitHub Secrets Store**: Where the actual secret values are stored securely in your repository settings

3. **`faasr_secret()` API**: The Python function you call in your code to retrieve secret values at runtime

When you register your workflow, FaaSr automatically injects the secrets from your GitHub repository into the workflow actions, making them available through the `faasr_secret()` API.

### Security Best Practices

- **Never commit secrets to your code**: Always use `faasr_secret()` to retrieve them at runtime
- **Use descriptive secret names**: Make it clear what each secret is for (e.g., `OPENWEATHER_API_KEY` instead of `KEY1`)
- **Rotate secrets regularly**: Update secret values periodically for better security
- **Grant minimal permissions**: Only add secrets that your workflow actually needs

## Getting an OpenWeather API Key

To use this workflow, you'll need an API key from OpenWeather with access to the Hourly Forecast API:

1. Visit [https://openweathermap.org/api](https://openweathermap.org/api)
2. Click "Sign Up" to create an account
3. Subscribe to a plan that includes the "Hourly Forecast" API (this requires a paid subscription)
4. After signing in, navigate to **API Keys** ([https://home.openweathermap.org/api_keys](https://home.openweathermap.org/api_keys))
5. Copy your API key (or generate a new one)
6. Keep this key handy - you'll need it when setting up GitHub secrets

**Important:** The Hourly Forecast API (`forecast/hourly`) is part of the Professional Collections and requires a paid subscription. The free tier only includes current weather and 5-day/3-hour forecast. For more details, see [https://openweathermap.org/price](https://openweathermap.org/price).

Alternatively, if you want to use the free tier, you can modify this workflow to use the 5-day/3-hour forecast API (`forecast`) instead by changing the endpoint in the code.

## Writing our Functions

### 1. Get Weather Data Using Secrets

The first function demonstrates the key feature of this tutorial: using `faasr_secret()` to securely retrieve an API key. The complete function can be found in [01_get_weather_data.py](./python/01_get_weather_data.py).

First, we import the necessary modules, including `faasr_secret`:

```python
import requests
from FaaSr_py.client.py_client_stubs import faasr_log, faasr_put_file, faasr_secret
```

Next, we write a helper function to build the OpenWeather API URL for the hourly forecast endpoint:

```python
def build_url(lat: str, lon: str, api_key: str) -> str:
    """
    Build the URL for the OpenWeather API hourly forecast endpoint.

    Args:
        lat: The latitude coordinate.
        lon: The longitude coordinate.
        api_key: The OpenWeather API key.

    Returns:
        The URL to fetch hourly forecast data from.
    """
    base_url = "https://pro.openweathermap.org/data/2.5/forecast/hourly"
    return f"{base_url}?lat={lat}&lon={lon}&appid={api_key}&units=metric"
```

We also need a function to fetch the weather data and save it to a local file:

```python
def fetch_weather_data(url: str, output_name: str) -> dict:
    """
    Fetch weather data from the OpenWeather API and save it to a local file.

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
            import json
            json.dump(weather_data, f, indent=2)

        return weather_data

    except Exception as e:
        faasr_log(f"Error fetching weather data from {url}: {e}")
        raise e
```

Now for the main function that demonstrates using `faasr_secret()`:

```python
def get_weather_data(folder_name: str, output_name: str, lat: str, lon: str, location_name: str):
    """
    Fetch 4-day hourly forecast data from OpenWeather API using a secret API key
    and upload it to an S3 bucket.

    This function demonstrates the use of faasr_secret() to securely retrieve
    API credentials.

    Args:
        folder_name: The name of the folder to upload the data to.
        output_name: The name of the file to upload the data to.
        lat: The latitude coordinate.
        lon: The longitude coordinate.
        location_name: A descriptive name for the location (for logging).
    """

    # 1. Get the API key from the secret store using faasr_secret
    faasr_log("Retrieving OpenWeather API key from secret store")
    api_key = faasr_secret("OPENWEATHER_API_KEY")
    faasr_log("Successfully retrieved API key")

    # 2. Build the URL
    url = build_url(lat, lon, api_key)
    faasr_log(f"Fetching 4-day hourly forecast data for {location_name} (lat={lat}, lon={lon})")

    # 3. Fetch the weather data and save to local file
    weather_data = fetch_weather_data(url, output_name)
    city_name = weather_data.get('city', {}).get('name', 'Unknown')
    num_timestamps = len(weather_data.get('list', []))
    faasr_log(f"Fetched hourly forecast data for {city_name}: {num_timestamps} timestamps")

    # 4. Upload the file to the S3 bucket
    faasr_put_file(
        local_file=output_name,
        remote_folder=folder_name,
        remote_file=output_name,
    )

    faasr_log(f"Uploaded forecast data to {folder_name}/{output_name}")
```

**Key Points:**

- `faasr_secret("OPENWEATHER_API_KEY")` retrieves the secret value from the secure store
- The secret name must exactly match what you configure in your workflow and GitHub
- The function returns the secret value as a string
- If the secret doesn't exist or can't be accessed, `faasr_secret()` will raise an error
- The hourly forecast API uses geographic coordinates (lat/lon) instead of city names
- The API returns up to 96 hourly timestamps (4 days)

### 2. Process Weather Data

The second function processes the hourly forecast data from OpenWeather API. The complete function can be found in [02_process_weather_data.py](./python/02_process_weather_data.py).

First, our imports:

```python
import json

from FaaSr_py.client.py_client_stubs import faasr_get_file, faasr_log, faasr_put_file
```

We need a function to download the raw forecast data:

```python
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
```

Next, we extract time-series metrics from the 96 hourly timestamps. The OpenWeather hourly forecast API returns a `list` array containing forecast data for each hour:

```python
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
```

A function to save the processed data:

```python
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
```

Finally, the main processing function:

```python
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
```

**Key Points:**

- The hourly forecast API returns a `list` array with up to 96 hourly forecasts
- We extract time-series data (arrays) for each metric across all timestamps
- The `pop` field represents probability of precipitation (0-1), which we convert to percentage

### 3. Plot Weather Data

The third function creates a time-series visualization of the hourly forecast data. The complete function can be found in [03_plot_weather_data.py](./python/03_plot_weather_data.py).

First, our imports including matplotlib and datetime utilities:

```python
import json
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from FaaSr_py.client.py_client_stubs import faasr_get_file, faasr_log, faasr_put_file
```

We need a function to get the processed data:

```python
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
```

The visualization function creates a 2x2 grid of time-series plots showing the hourly forecast data:

```python
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

    # Temperature Forecast (with Feels Like)
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
```

Finally, the main plotting function:

```python
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
```

**Key Points:**

- The visualization shows time-series data with dates on the x-axis
- We use `matplotlib.dates` to format datetime labels
- Each subplot shows a different forecast metric over the 4-day period
- The fill_between creates shaded areas under the curves for better readability

## Building our Workflow

Now that we have written our functions, we are ready to build the workflow using the FaaSr Workflow Builder: [https://faasr.io/FaaSr-workflow-builder/](https://faasr.io/FaaSr-workflow-builder/).

The final workflow file can be found in [WeatherAPISecrets.json](./WeatherAPISecrets.json). You can visualize this workflow by clicking **Upload** from the Workflow Builder and importing from its GitHub URL: [https://github.com/FaaSr/FaaSr-Functions/blob/main/WeatherAPISecrets/WeatherAPISecrets.json](https://github.com/FaaSr/FaaSr-Functions/blob/main/WeatherAPISecrets/WeatherAPISecrets.json).

### 1. Set Up our Compute Server

After opening the Workflow Builder, click **Edit Compute Servers**. Enter your GitHub username for **UserName**, `FaaSr-workflow` for **ActionRepoName**, and `main` for **Branch**.

### 2. Set Up our Data Store

Click **Edit Data Stores**. Enter the endpoint, bucket, and region for your S3-compatible data store. For the tutorial, you can use:

- **Endpoint**: `https://play.min.io`
- **Bucket**: `faasr`
- **Region**: `us-east-1`

### 3. Configure Workflow Secrets

This is the key step for this tutorial! Click **Workflow Settings**, then scroll down to the **Workflow Secrets** section.

Click **Add secret** and enter `OPENWEATHER_API_KEY` in the text field. This tells FaaSr that your workflow needs access to a secret with this name.

**Important:** The secret name you enter here must:

1. Match exactly what you use in `faasr_secret()` in your code
2. Match exactly what you name the secret in your GitHub repository settings

### 4. Add our Functions

#### Get Weather Data Function

Navigate to **Edit Actions/Functions** and create a new action called `GetWeatherData`.

Configure it as follows:

- **Function Name**: `get_weather_data`
- **Language**: `Python`
- **Compute Server**: `GH`

Add the following arguments:

- `folder_name`: `WeatherAPISecrets`
- `output_name`: `raw_weather_data.json`
- `lat`: `45.5152` (Portland, OR latitude)
- `lon`: `-122.6784` (Portland, OR longitude)
- `location_name`: `Portland, OR`

To use a different location, find its coordinates at [https://www.latlong.net/](https://www.latlong.net/) or use OpenWeather's Geocoding API.

Set **Function's Git Repo/Path** to the repository and folder containing your functions, for example:
`FaaSr/FaaSr-Functions/WeatherAPISecrets/python`

Leave **Function's Action Container** blank.

#### Process Weather Data Function

Create a new action called `ProcessWeatherData`.

Configure it as follows:

- **Function Name**: `process_weather_data`
- **Language**: `Python`
- **Compute Server**: `GH`

Add the following arguments:

- `folder_name`: `WeatherAPISecrets`
- `input_name`: `raw_weather_data.json`
- `output_name`: `processed_weather_data.json`

Set **Function's Git Repo/Path** to the same repository as before:
`FaaSr/FaaSr-Functions/WeatherAPISecrets/python`

#### Plot Weather Data Function

Create a new action called `PlotWeatherData`.

Configure it as follows:

- **Function Name**: `plot_weather_data`
- **Language**: `Python`
- **Compute Server**: `GH`

Add the following arguments:

- `folder_name`: `WeatherAPISecrets`
- `input_name`: `processed_weather_data.json`
- `output_name`: `weather_visualization.png`

Set **Function's Git Repo/Path** to:
`FaaSr/FaaSr-Functions/WeatherAPISecrets/python`

Under **Python Packages for the Function**, add `matplotlib`.

### 5. Connect our Functions

Now we need to define the invocation paths:

1. Navigate to the `GetWeatherData` function
2. Scroll to **Next Actions to Invoke**
3. Click **Add New InvokeNext** and select `ProcessWeatherData`
4. Navigate to the `ProcessWeatherData` function
5. Click **Add New InvokeNext** and select `PlotWeatherData`

The workflow should now look like this:

![Workflow layout](../assets/weather-api-secrets-workflow-layout.png)

### 6. Finalize our Workflow Configuration

Click **Workflow Settings**. Set:

- **Workflow Name**: `WeatherAPISecrets`
- **Entry Point**: `GetWeatherData`

Verify that your **Workflow Secrets** section shows `OPENWEATHER_API_KEY`.

Click **Download** and download the `WeatherAPISecrets.json` file.

## Storing Secrets in GitHub

Before you can invoke your workflow, you must store your OpenWeather API key in your GitHub repository settings. This is how FaaSr accesses the secret value at runtime.

### Steps to Add Secrets in GitHub

1. Navigate to your `FaaSr-workflow` repository on GitHub
2. Click **Settings**
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. For the **Name**, enter exactly: `OPENWEATHER_API_KEY`
6. For the **Value**, paste your OpenWeather API key that you obtained earlier
7. Click **Add secret**

**Important Notes:**

- The secret name must match exactly what you configured in the Workflow Builder (case-sensitive)
- The secret name must match exactly what you use in `faasr_secret()` in your code
- GitHub encrypts all secrets and they cannot be viewed after creation (you can only update or delete them)

## Download and Invoke the Workflow

### Register the Workflow

1. Upload your `WeatherAPISecrets.json` file to your `FaaSr-workflow` repository
2. Navigate to your repository's **Actions** tab
3. From the left-hand menu, select the **(FAASR REGISTER)** workflow
4. Click **Run workflow**
5. Enter `WeatherAPISecrets.json` as the filename
6. Click **Run workflow**
7. Wait for the registration to complete

You should see three new workflows appear in the left-hand menu:

- `WeatherAPISecrets-GetWeatherData`
- `WeatherAPISecrets-ProcessWeatherData`
- `WeatherAPISecrets-PlotWeatherData`

### Invoke the Workflow

1. In the **Actions** tab, select **(FAASR INVOKE)** from the left-hand menu
2. Click **Run workflow**
3. Enter `WeatherAPISecrets.json` as the filename
4. Click **Run workflow**
5. Monitor the workflow execution by clicking on each function in the left-hand menu

### View the Output

After successful invocation, your S3 bucket should contain:

```plaintext
your-bucket/
├── FaaSrLog/
│   └── (log files)
└── WeatherAPISecrets/
    ├── raw_weather_data.json
    ├── processed_weather_data.json
    └── weather_visualization.png
```

The final visualization `weather_visualization.png` shows four time-series plots:

- Temperature forecast (actual and "feels like" over 4 days)
- Humidity forecast (hourly humidity percentage)
- Precipitation probability (chance of rain/snow each hour)
- Wind speed forecast (hourly wind speed in m/s)

## Using the Free API Alternative

If you don't have access to the Hourly Forecast API (paid tier), you can modify this workflow to use the free 5-day/3-hour forecast API:

1. In `01_get_weather_data.py`, change the base URL:

   ```python
   base_url = "https://api.openweathermap.org/data/2.5/forecast"
   ```

2. Update the function signature to use city name instead of lat/lon:

   ```python
   def build_url(city: str, api_key: str) -> str:
       base_url = "https://api.openweathermap.org/data/2.5/forecast"
       return f"{base_url}?q={city}&appid={api_key}&units=metric"
   ```

3. Update the workflow JSON arguments to use `city` instead of `lat`, `lon`, and `location_name`

4. Adjust `03_plot_weather_data.py` to handle 40 timestamps (5 days × 8 per day) instead of 96

The `faasr_secret()` API usage remains exactly the same!

## Troubleshooting

### Common Issues with Secrets

1. **"Secret not found" error**
   - Verify the secret name matches exactly in: your code, workflow JSON, and GitHub settings
   - Check that the secret is stored in the correct GitHub repository
   - Ensure the secret name is spelled correctly (case-sensitive)

2. **"Unauthorized" API errors**
   - Verify your OpenWeather API key is valid
   - If using the hourly forecast API, ensure your subscription includes it
   - Check that you haven't exceeded API rate limits
   - Make sure the API key is correctly copied to GitHub secrets (no extra spaces)

3. **"404 Not Found" API errors**
   - This usually means the hourly forecast API is not available with your API key
   - Either upgrade to a paid plan or use the free 5-day/3-hour forecast API (see above)

4. **Workflow fails during registration**
   - Ensure your workflow JSON includes the `"Secrets"` field
   - Verify that `"UseSecretStore": true` is set in your compute server configuration
   - Check that you're using GitHub Actions as your compute server (secrets are only supported on GitHub Actions)

### Getting Help

If you encounter issues:

- Check the FaaSrLog files in your S3 bucket for detailed error messages
- Review the GitHub Actions workflow run logs
- Visit the FaaSr documentation: [https://faasr.io/FaaSr-Docs/](https://faasr.io/FaaSr-Docs/)
- Join the FaaSr community for support

## Summary

In this tutorial, you learned how to:

✓ Use `faasr_secret()` to securely access API keys in your workflow functions
✓ Configure workflow secrets in the FaaSr Workflow Builder
✓ Store secrets in GitHub Actions for secure access
✓ Fetch hourly forecast data from external APIs that require authentication
✓ Process time-series JSON data from API responses
✓ Create time-series visualizations with matplotlib
✓ Handle 96 hourly timestamps across a 4-day forecast period

The secrets management feature is essential for building real-world workflows that interact with external services, databases, and APIs. By following these patterns, you can securely access any credentials your workflows need without exposing sensitive information in your code.
