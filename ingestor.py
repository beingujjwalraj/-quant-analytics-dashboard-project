# File: ingestor.py
import websocket
import json
import time
from threading import Thread, Lock
from datetime import datetime

# Import our database setup
from app.database import SessionLocal, init_db
from app.models import Tick

# --- Configuration ---
# You can add more symbols here
SYMBOLS_TO_SUBSCRIBE = ["btcusdt", "ethusdt"] 
BINANCE_WEBSOCKET_URL = "wss://fstream.binance.com/stream?streams="
# --- End Configuration ---

# A thread-safe list to buffer ticks before batch inserting
TICK_BUFFER = []
BUFFER_LOCK = Lock()
BUFFER_SIZE = 100  # Commit to DB every 100 ticks

def get_stream_url():
    """Generates the full stream URL for all symbols."""
    streams = [f"{sym.lower()}@trade" for sym in SYMBOLS_TO_SUBSCRIBE]
    return f"{BINANCE_WEBSOCKET_URL}{'/'.join(streams)}"

def on_message(ws, message):
    """Callback function when a message is received."""
    try:
        data = json.loads(message)
        
        # Check if it's a trade message
        if data.get('e') == 'trade' or data.get('data', {}).get('e') == 'trade':
            trade_data = data.get('data', data) # Handle combined stream format
            
            tick = Tick(
                timestamp=datetime.utcfromtimestamp(trade_data['T'] / 1000.0),
                symbol=trade_data['s'],
                price=float(trade_data['p']),
                size=float(trade_data['q'])
            )
            
            # Add tick to buffer safely
            with BUFFER_LOCK:
                TICK_BUFFER.append(tick)
                
    except Exception as e:
        print(f"Error processing message: {e}\nMessage: {message}")

def on_error(ws, error):
    print(f"WebSocket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("### WebSocket Closed ###")

def on_open(ws):
    print("### WebSocket Opened ###")
    print(f"Subscribing to: {', '.join(SYMBOLS_TO_SUBSCRIBE)}")

def run_websocket_client():
    """Runs the WebSocket client."""
    ws_url = get_stream_url()
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

def batch_insert_ticks():
    """
    A separate thread function to periodically 
    insert ticks from the buffer into the database.
    """
    global TICK_BUFFER
    session = SessionLocal()
    
    while True:
        try:
            time.sleep(2)  # Process buffer every 2 seconds
            
            ticks_to_insert = []
            
            # Safely move ticks from global buffer to local list
            with BUFFER_LOCK:
                if len(TICK_BUFFER) > 0:
                    ticks_to_insert = TICK_BUFFER
                    TICK_BUFFER = []
            
            if len(ticks_to_insert) > 0:
                session.add_all(ticks_to_insert)
                session.commit()
                print(f"Committed {len(ticks_to_insert)} ticks to database.")
                
        except Exception as e:
            print(f"Error in batch insert: {e}")
            session.rollback()

if __name__ == "__main__":
    # 1. Initialize the database and create tables
    print("Initializing database...")
    init_db()
    print("Database initialized.")
    
    # 2. Start the batch insert thread
    insert_thread = Thread(target=batch_insert_ticks, daemon=True)
    insert_thread.start()
    
    # 3. Start the WebSocket client in the main thread
    print("Starting WebSocket client...")
    run_websocket_client()