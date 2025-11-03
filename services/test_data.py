import threading
import time
import random
from datetime import datetime, timedelta
from database.models import Database

class TestDataGenerator:
    def __init__(self, db):
        self.db = db
        self.is_running = False
        self.thread = None
        
    def generate_test_data(self, symbols=None):
        """Generate realistic test data for development"""
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
            # Generate some historical data
            for i in range(100):
                timestamp = (datetime.now() - timedelta(minutes=100-i)).isoformat()
                price = base_price * (1 + random.uniform(-0.02, 0.02))
                size = random.uniform(0.1, 5.0)
                self.db.save_tick(symbol, timestamp, price, size)
                
        print(f"Generated test data for {len(symbols)} symbols")
    
    def start_live_test_data(self, symbols=None):
        """Start generating live test data"""
        if symbols is None:
            symbols = ['btcusdt', 'ethusdt']
            
        self.is_running = True
        
        def generate_loop():
            base_prices = {
                'btcusdt': 60000,
                'ethusdt': 3500
            }
            
            while self.is_running:
                for symbol in symbols:
                    base_price = base_prices.get(symbol, 100)
                    price = base_price * (1 + random.uniform(-0.01, 0.01))
                    size = random.uniform(0.1, 2.0)
                    timestamp = datetime.now().isoformat()
                    self.db.save_tick(symbol, timestamp, price, size)
                    
                    # Simulate WebSocket callback
                    from app import socketio
                    socketio.emit('tick_data', [{
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'price': price,
                        'size': size
                    }])
                
                time.sleep(1)  # Generate data every second
        
        self.thread = threading.Thread(target=generate_loop)
        self.thread.daemon = True
        self.thread.start()
        print("Started live test data generation")
    
    def stop_live_test_data(self):
        """Stop generating live test data"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("Stopped live test data generation")