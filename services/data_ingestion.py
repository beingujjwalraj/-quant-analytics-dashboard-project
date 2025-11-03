import websocket
import json
import threading
import time
from datetime import datetime

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