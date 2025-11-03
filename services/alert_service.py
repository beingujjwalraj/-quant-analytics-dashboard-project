import threading
import time
from datetime import datetime

class AlertService:
    def __init__(self):
        self.alerts = []
        self.triggered_alerts = []
        self.is_monitoring = False
        self.alert_callbacks = []
    
    def add_alert_callback(self, callback):
        self.alert_callbacks.append(callback)
    
    def create_alert(self, name, condition, symbol, threshold):
        alert = {
            'id': len(self.alerts) + 1,
            'name': name,
            'condition': condition,
            'symbol': symbol,
            'threshold': threshold,
            'is_active': True,
            'triggered': False,
            'created_at': datetime.now().isoformat()
        }
        self.alerts.append(alert)
        return alert
    
    def remove_alert(self, alert_id):
        self.alerts = [alert for alert in self.alerts if alert['id'] != alert_id]
    
    def check_price_alert(self, tick_data):
        triggered = []
        for alert in self.alerts:
            if not alert['is_active'] or alert['triggered']:
                continue
                
            if alert['symbol'] == tick_data['symbol']:
                price = tick_data['price']
                threshold = alert['threshold']
                
                if alert['condition'] == 'above' and price > threshold:
                    alert['triggered'] = True
                    alert['triggered_at'] = datetime.now().isoformat()
                    alert['triggered_price'] = price
                    triggered.append(alert.copy())
                    
                elif alert['condition'] == 'below' and price < threshold:
                    alert['triggered'] = True
                    alert['triggered_at'] = datetime.now().isoformat()
                    alert['triggered_price'] = price
                    triggered.append(alert.copy())
        
        for alert in triggered:
            for callback in self.alert_callbacks:
                callback(alert)
        
        return triggered
    
    def start_monitoring(self):
        self.is_monitoring = True
    
    def stop_monitoring(self):
        self.is_monitoring = False