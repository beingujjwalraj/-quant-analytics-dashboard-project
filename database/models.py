import sqlite3
import json
import pandas as pd
from datetime import datetime

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol1 TEXT NOT NULL,
                symbol2 TEXT,
                analysis_type TEXT NOT NULL,
                result_json TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                condition TEXT NOT NULL,
                symbol TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                triggered BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON ticks(symbol, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticks_time ON ticks(timestamp)')
        
        conn.commit()
        conn.close()
    
    def save_tick(self, symbol, timestamp, price, size):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO ticks (symbol, timestamp, price, size) VALUES (?, ?, ?, ?)',
            (symbol, timestamp, price, size)
        )
        conn.commit()
        conn.close()
    
    def get_recent_ticks(self, symbol, limit=1000):
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT timestamp, price, size 
            FROM ticks 
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        df = pd.read_sql_query(query, conn, params=[symbol, limit])
        conn.close()
        return df
    
    def get_ticks_time_range(self, symbol, start_time, end_time):
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT timestamp, price, size 
            FROM ticks 
            WHERE symbol = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        '''
        df = pd.read_sql_query(query, conn, params=[symbol, start_time, end_time])
        conn.close()
        return df