# Quant Developer Evaluation Assignment

This project is an end-to-end analytical application designed to ingest, process, and visualize real-time cryptocurrency tick data from Binance. It provides traders and researchers with key analytics to identify market-making, arbitrage, and statistical opportunities. 

The application is built with a Python backend (Flask, Flask-SocketIO) and a pure JavaScript frontend (Chart.js), backed by a SQLite database for data storage. 

## 🚀 Features

* **Real-time Data Ingestion**: Connects to Binance WebSocket streams to ingest live trade data for multiple symbols. 
* **Persistent Storage**: Saves all incoming tick data into a local SQLite database (`tick_data.db`). 
* **Live Analytics Dashboard**: A single-page application that updates charts and stats in real-time as new data arrives. 
* **Quantitative Analysis**:
    * **Pairwise Regression (OLS)**: Calculates hedge ratio, R-squared, and spread. 
    * **Spread Z-Score**: Computes a rolling Z-score of the spread for mean-reversion analysis. 
    * **Rolling Correlation**: Calculates the rolling correlation between two assets.
    * **ADF Test**: (Demo) A placeholder for the Augmented Dickey-Fuller test for stationarity. 
* **Interactive Controls**: Users can add/remove symbols, select pairs for analysis, and adjust timeframes. 
* **Data Export**: Download processed tick data as CSV or JSON. 
* **Test Data Generation**: Includes built-in tools to generate historical and live *test* data for development and demonstration.

## 🏛️ Architecture

The application runs as a single, monolithic Python process using Flask.

* **Backend**: `app.py` (Flask + Flask-SocketIO)
    * Serves the main `index.html` page.
    * **REST API**: Provides endpoints for calculating analytics (`/api/calculate-analytics`), exporting data (`/api/export-data`), and controlling data collection.
    * **WebSocket (SocketIO)**: Manages the connection with the frontend, pushing new `tick_data` events to the client in real-time.
    * **Data Ingestion (`BinanceDataIngestion`)**: A background thread (defined in `app.py`) connects to the Binance WebSocket, normalizes data, saves it to the database, and emits ticks to the frontend via SocketIO.
    * **Analytics (`QuantitativeAnalytics`)**: A class (defined in `app.py`) that uses Pandas and Numpy to perform OLS, z-score, and correlation calculations on data fetched from the database.
* **Frontend**: `index.html`, `style.css`, `app.js`
    * Uses **Socket.IO-client** to receive live `tick_data` events.
    * Uses **Chart.js** (with `chartjs-adapter-date-fns`) for all interactive visualizations.
    * Uses `fetch` to call the backend's REST API for on-demand analytics.
* **Database**: `tick_data.db` (SQLite)
    * A simple, file-based database used to store all incoming tick data.

## 🛠️ Setup and Installation

### Prerequisites
* Python 3.8+
* `pip` (Python package installer)

### Running the Application

1.  **Clone the Repository**
    ```sh
    git clone <your-repo-url>
    cd <your-project-folder>
    ```

2.  **Create a Virtual Environment** (Recommended)
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**
    Install all required packages from `requirements.txt`. 
    ```sh
    pip install -r requirements.txt
    ```

4.  **Run the Application**
    The application can be started with a single command: 
    ```sh
    python app.py
    ```

5.  **Access the Dashboard**
    Open your web browser and navigate to:
    [http://localhost:5000](http://localhost:5000)

    The application will automatically start generating live test data for `BTCUSDT` and `ETHUSDT` for demonstration purposes. You can start/stop real data collection from the sidebar.

## 📊 Analytics Methodology

Analytics are calculated via the `/api/calculate-analytics` endpoint in `app.py`.

* **Data Resampling**: Tick data is first resampled into the user-selected timeframe (e.g., `1min`) using `pandas.DataFrame.resample().ohlc()`. 
* **Hedge Ratio (OLS)**: The `pairwise_regression` function performs an Ordinary Least Squares (OLS) regression using `numpy` to find the slope (hedge ratio) and intercept between the 'close' prices of two assets.
* **Spread & Z-Score**: The spread is calculated as `spread = price_2 - (hedge_ratio * price_1)`. A rolling z-score is then computed on this spread series to identify deviations from the mean.
* **ADF & Correlation**: *Note: For this project, the ADF test and rolling correlation return randomized demo data to ensure the frontend is functional, as seen in the `/api/calculate-analytics` route in `app.py`.*

## 🤖 AI Usage Transparency

(Per assignment requirements , please fill this section in with your own experience.)

> **Example:** I used Gemini to...
> * Help structure the Flask application and SocketIO integration.
> * Generate boilerplate code for the `README.md` file.
> * Debug issues with Chart.js time-series axis formatting.
> * Suggest the `numpy`-based manual OLS calculation.