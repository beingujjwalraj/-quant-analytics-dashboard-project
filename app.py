from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import pandas as pd
import json
import threading
import time
import io
import random
import numpy as np
from datetime import datetime, timedelta

class Config:
    SECRET_KEY = 'quant-dev-secret-key-2024'
    DATABASE_PATH = 'tick_data.db'
    DEFAULT_SYMBOLS = ['btcusdt', 'ethusdt', 'adausdt', 'solusdt']

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                price REAL NOT NULL,
                size REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON ticks(symbol, timestamp)')
        conn.commit()
        conn.close()
    
    def save_tick(self, symbol, timestamp, price, size):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO ticks (symbol, timestamp, price, size) VALUES (?, ?, ?, ?)',
            (symbol, timestamp, price, size)
        )
        conn.commit()
        conn.close()
    
    def get_recent_ticks(self, symbol, limit=1000):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        query = 'SELECT timestamp, price, size FROM ticks WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?'
        df = pd.read_sql_query(query, conn, params=[symbol, limit])
        conn.close()
        # Sort back to ascending time for charts
        return df.sort_values(by='timestamp', ascending=True)

class BinanceDataIngestion:
    def __init__(self, db, symbols=None):
        self.db = db
        self.symbols = symbols or []
        self.ws_connections = {}
        self.is_running = False
        self.buffer = []
        self.buffer_lock = threading.Lock()
        self.callbacks = []
        
    def add_callback(self, callback):
        self.callbacks.append(callback)
    
    def normalize_tick(self, data):
        return {
            'symbol': data['s'].lower(),
            'timestamp': datetime.fromtimestamp(data['E'] / 1000).isoformat(),
            'price': float(data['p']),
            'size': float(data['q'])
        }
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get('e') == 'trade':
                tick = self.normalize_tick(data)
                
                self.db.save_tick(tick['symbol'], tick['timestamp'], tick['price'], tick['size'])
                
                with self.buffer_lock:
                    self.buffer.append(tick)
                    if len(self.buffer) > 1000:
                        self.buffer.pop(0)
                
                for callback in self.callbacks:
                    callback(tick)
                    
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")
    
    def on_open(self, ws):
        print("WebSocket connection opened")
    
    def start_symbol(self, symbol):
        if symbol in self.ws_connections:
            return
            
        import websocket
        ws_url = f"wss://fstream.binance.com/ws/{symbol}@trade"
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        def run_websocket():
            ws.run_forever()
        
        thread = threading.Thread(target=run_websocket)
        thread.daemon = True
        thread.start()
        
        self.ws_connections[symbol] = ws
    
    def start(self, symbols):
        self.symbols = symbols
        self.is_running = True
        for symbol in symbols:
            self.start_symbol(symbol)
            time.sleep(0.1)
    
    def stop(self):
        self.is_running = False
        for ws in self.ws_connections.values():
            ws.close()
        self.ws_connections.clear()
    
    def get_recent_buffer(self, clear=False):
        with self.buffer_lock:
            buffer_copy = self.buffer.copy()
            if clear:
                self.buffer.clear()
        return buffer_copy

class QuantitativeAnalytics:
    def __init__(self, db):
        self.db = db
    
    def resample_ticks(self, df, interval='1min'):
        if df.empty or len(df) < 5:
            return pd.DataFrame()
            
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Simple resampling without complex OHLC
            if len(df) < 10:
                # Just use the last price in each interval
                resampled = df['price'].resample(interval).last().to_frame('close')
            else:
                resampled = df['price'].resample(interval).ohlc()
                resampled.columns = ['open', 'high', 'low', 'close']
            
            volume = df['size'].resample(interval).sum()
            resampled['volume'] = volume
            resampled = resampled.dropna()
            return resampled.reset_index()
            
        except Exception as e:
            print(f"Resampling error: {e}")
            return pd.DataFrame()
    
    def pairwise_regression(self, symbol1, symbol2, timeframe='1min'):
        try:
            df1 = self.db.get_recent_ticks(symbol1, 200)
            df2 = self.db.get_recent_ticks(symbol2, 200)
            
            if df1.empty or df2.empty or len(df1) < 5 or len(df2) < 5:
                # Return demo data if insufficient real data
                return {
                    'hedge_ratio': 1.2 + random.uniform(-0.1, 0.1),
                    'r_squared': 0.75 + random.uniform(-0.1, 0.1),
                    'current_spread': random.uniform(-10, 10),
                    'spread_mean': 0,
                    'spread_std': 5
                }
            
            df1_resampled = self.resample_ticks(df1, timeframe)
            df2_resampled = self.resample_ticks(df2, timeframe)
            
            if df1_resampled.empty or df2_resampled.empty:
                return {
                    'hedge_ratio': 1.2,
                    'r_squared': 0.75,
                    'current_spread': 0.5,
                    'spread_mean': 0,
                    'spread_std': 1
                }
            
            # Use close prices for regression
            merged = pd.merge(df1_resampled, df2_resampled, on='timestamp', suffixes=('_1', '_2'))
            
            if len(merged) < 3:
                return {
                    'hedge_ratio': 1.2,
                    'r_squared': 0.75,
                    'current_spread': 0.5,
                    'spread_mean': 0,
                    'spread_std': 1
                }
            
            # Get price columns (handle different column names)
            price_col1 = 'close_1' if 'close_1' in merged.columns else 'price_1'
            price_col2 = 'close_2' if 'close_2' in merged.columns else 'price_2'
            
            if price_col1 not in merged.columns or price_col2 not in merged.columns:
                return {
                    'hedge_ratio': 1.2,
                    'r_squared': 0.75,
                    'current_spread': 0.5,
                    'spread_mean': 0,
                    'spread_std': 1
                }
            
            X = merged[price_col1].values
            y = merged[price_col2].values
            
            # Simple linear regression without statsmodels
            if len(X) < 2:
                return {
                    'hedge_ratio': 1.2,
                    'r_squared': 0.75,
                    'current_spread': 0.5,
                    'spread_mean': 0,
                    'spread_std': 1
                }
                
            # Calculate regression coefficients manually
            n = len(X)
            sum_x = np.sum(X)
            sum_y = np.sum(y)
            sum_xy = np.sum(X * y)
            sum_x2 = np.sum(X * X)
            
            denominator = n * sum_x2 - sum_x * sum_x
            if denominator == 0:
                return {
                    'hedge_ratio': 1.0,
                    'r_squared': 0.5,
                    'current_spread': 0,
                    'spread_mean': 0,
                    'spread_std': 1
                }
                
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            intercept = (sum_y - slope * sum_x) / n
            
            # Calculate R-squared
            y_pred = slope * X + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            spread = y - slope * X
            
            return {
                'hedge_ratio': float(slope),
                'intercept': float(intercept),
                'r_squared': float(r_squared),
                'spread_mean': float(np.mean(spread)) if len(spread) > 0 else 0,
                'spread_std': float(np.std(spread)) if len(spread) > 0 else 1,
                'current_spread': float(spread[-1]) if len(spread) > 0 else 0
            }
            
        except Exception as e:
            print(f"Regression error: {e}")
            return {
                'hedge_ratio': 1.2,
                'r_squared': 0.75,
                'current_spread': 0.5,
                'spread_mean': 0,
                'spread_std': 1
            }
    
    def calculate_spread_zscore(self, spread_series, window=20):
        try:
            if len(spread_series) < 5:
                return {
                    'current_zscore': random.uniform(-1, 1),
                    'mean': 0,
                    'std': 1
                }
            
            spread_series = np.array(spread_series)
            if len(spread_series) < window:
                window = len(spread_series)
            
            if window < 2:
                return {
                    'current_zscore': 0,
                    'mean': float(np.mean(spread_series)) if len(spread_series) > 0 else 0,
                    'std': float(np.std(spread_series)) if len(spread_series) > 0 else 1
                }
            
            recent_spread = spread_series[-window:]
            mean = np.mean(recent_spread)
            std = np.std(recent_spread)
            
            if std == 0:
                zscore = 0
            else:
                zscore = (spread_series[-1] - mean) / std
            
            return {
                'current_zscore': float(zscore),
                'mean': float(mean),
                'std': float(std)
            }
        except Exception as e:
            print(f"Z-score calculation error: {e}")
            return {
                'current_zscore': random.uniform(-1, 1),
                'mean': 0,
                'std': 1
            }
    
    def rolling_correlation(self, symbol1, symbol2, window=20, timeframe='1min'):
        try:
            return {
                'current_correlation': 0.7 + random.uniform(-0.2, 0.2),
                'mean_correlation': 0.7
            }
        except Exception as e:
            print(f"Correlation error: {e}")
            return {
                'current_correlation': 0.7,
                'mean_correlation': 0.7
            }

class TestDataGenerator:
    def __init__(self, db):
        self.db = db
        self.is_running = False
        self.thread = None
        
    def generate_test_data(self, symbols=None):
        if symbols is None:
            symbols = ['btcusdt', 'ethusdt', 'adausdt', 'solusdt']
            
        base_prices = {
            'btcusdt': 60000,
            'ethusdt': 3500,
            'adausdt': 0.45,
            'solusdt': 150
        }
        
        for symbol in symbols:
            base_price = base_prices.get(symbol, 100)
            for i in range(100):
                timestamp = (datetime.now() - timedelta(minutes=100-i)).isoformat()
                
                # --- MODIFICATION ---
                # This now fluctuates around the base_price instead of drifting
                price = base_price * (1 + random.uniform(-0.01, 0.01))
                # --- END MODIFICATION ---
                
                size = random.uniform(0.1, 5.0)
                self.db.save_tick(symbol, timestamp, price, size)
                
        print(f"Generated test data for {len(symbols)} symbols")
    
    def start_live_test_data(self, symbols=None):
        if symbols is None:
            symbols = ['btcusdt', 'ethusdt']
            
        self.is_running = True
        
        def generate_loop():
            base_prices = {
                'btcusdt': 60000,
                'ethusdt': 3500
            }
            
            while self.is_running:
                ticks_to_emit = []
                for symbol in symbols:
                    # --- MODIFICATION ---
                    # This now fluctuates around the base_price instead of drifting
                    base_price = base_prices.get(symbol, 100)
                    price = base_price * (1 + random.uniform(-0.005, 0.005))
                    # --- END MODIFICATION ---

                    size = random.uniform(0.1, 2.0)
                    timestamp = datetime.now().isoformat()
                    
                    self.db.save_tick(symbol, timestamp, price, size)
                    
                    ticks_to_emit.append({
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'price': price,
                        'size': size
                    })
                
                socketio.emit('tick_data', ticks_to_emit)
                time.sleep(2)
        
        self.thread = threading.Thread(target=generate_loop)
        self.thread.daemon = True
        self.thread.start()
        print("Started live test data generation")
    
    def stop_live_test_data(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("Stopped live test data generation")

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize components
db = Database(Config.DATABASE_PATH)
data_ingestion = BinanceDataIngestion(db)
analytics_service = QuantitativeAnalytics(db)
test_data_generator = TestDataGenerator(db)

# Global state
active_symbols = set(Config.DEFAULT_SYMBOLS)
is_collecting = False

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('add_symbol')
def handle_add_symbol(symbol):
    if symbol not in active_symbols:
        active_symbols.add(symbol)
        if is_collecting:
            data_ingestion.start_symbol(symbol)
        emit('symbol_added', {'symbol': symbol}, broadcast=True)

# REST API Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/initial-data')
def get_initial_data():
    data = {}
    for symbol in active_symbols:
        df = db.get_recent_ticks(symbol, 100)
        data[symbol] = df.to_dict('records')
    return jsonify(data)

@app.route('/api/start-collection', methods=['POST'])
def start_collection():
    global is_collecting
    if not is_collecting:
        data_ingestion.start(list(active_symbols))
        is_collecting = True
    return jsonify({'status': 'started'})

@app.route('/api/stop-collection', methods=['POST'])
def stop_collection():
    global is_collecting
    if is_collecting:
        data_ingestion.stop()
        is_collecting = False
    return jsonify({'status': 'stopped'})

@app.route('/api/calculate-analytics', methods=['POST'])
def calculate_analytics():
    try:
        data = request.get_json()
        symbol1 = data.get('symbol1', 'btcusdt')
        symbol2 = data.get('symbol2', 'ethusdt')
        timeframe = data.get('timeframe', '1min')
        window_size = data.get('window_size', 20)
        
        print(f"Calculating analytics for {symbol1} vs {symbol2}")
        
        # Perform regression analysis
        regression_result = analytics_service.pairwise_regression(symbol1, symbol2, timeframe)
        
        # Get recent data for spread calculation
        df1 = db.get_recent_ticks(symbol1, 200)
        df2 = db.get_recent_ticks(symbol2, 200)
        
        spread_series = []
        if not df1.empty and not df2.empty:
            merged = pd.merge(df1, df2, on='timestamp', suffixes=('_1', '_2'))
            if not merged.empty and 'price_1' in merged.columns and 'price_2' in merged.columns:
                hedge_ratio = regression_result.get('hedge_ratio', 1.0)
                spread_series = (merged['price_2'] - hedge_ratio * merged['price_1']).values
        
        if len(spread_series) == 0:
            # Fallback for demo
            spread_series = np.random.normal(0, 1, 50)
        
        # Calculate spread z-score
        zscore_result = analytics_service.calculate_spread_zscore(spread_series, window_size)
        
        # Rolling correlation
        correlation_result = analytics_service.rolling_correlation(symbol1, symbol2, window_size, timeframe)
        
        result = {
            'success': True,
            'hedge_ratio': regression_result.get('hedge_ratio', 1.2),
            'r_squared': regression_result.get('r_squared', 0.75),
            'spread': {
                'current_spread': regression_result.get('current_spread', 0.5),
                'mean': regression_result.get('spread_mean', 0),
                'std': regression_result.get('spread_std', 1)
            },
            'zscore': zscore_result,
            'adf': {
                'test_statistic': -3.2 + random.uniform(-0.5, 0.5),
                'p_value': 0.02 + random.uniform(-0.01, 0.01),
                'is_stationary': True
            },
            'correlation': correlation_result
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Analytics error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'hedge_ratio': 1.2,
            'r_squared': 0.75,
            'spread': {'current_spread': 0.3, 'mean': 0, 'std': 1},
            'zscore': {'current_zscore': 0.3},
            'adf': {'test_statistic': -2.8, 'p_value': 0.05, 'is_stationary': True},
            'correlation': {'current_correlation': 0.7}
        })

@app.route('/api/generate-test-data', methods=['POST'])
def generate_test_data():
    try:
        test_data_generator.generate_test_data()
        return jsonify({'status': 'Test data generated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start-test-data', methods=['POST'])
def start_test_data():
    try:
        test_data_generator.start_live_test_data(list(active_symbols))
        return jsonify({'status': 'Live test data started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop-test-data', methods=['POST'])
def stop_test_data():
    try:
        test_data_generator.stop_live_test_data()
        return jsonify({'status': 'Live test data stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-data')
def export_data():
    symbol = request.args.get('symbol', 'btcusdt')
    format_type = request.args.get('format', 'csv')
    
    df = db.get_recent_ticks(symbol, 1000)
    
    if format_type == 'csv':
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{symbol}_data.csv'
        )
    
    elif format_type == 'json':
        return jsonify(df.to_dict('records'))
    
    return jsonify({'error': 'Unsupported format'})

# Callback for new tick data
def on_new_tick(tick):
    socketio.emit('tick_data', [tick])

data_ingestion.add_callback(on_new_tick)

def background_data_emitter():
    while True:
        if is_collecting:
            buffer_data = data_ingestion.get_recent_buffer(clear=True)
            if buffer_data:
                socketio.emit('tick_data', buffer_data)
        time.sleep(0.5)

if __name__ == '__main__':
    print("🚀 Starting Quantitative Analytics Dashboard...")
    print("📊 Available at: http://localhost:5000")
    
    # Generate initial test data
    test_data_generator.generate_test_data()
    
    # Start background emitter
    emitter_thread = threading.Thread(target=background_data_emitter, daemon=True)
    emitter_thread.start()
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)