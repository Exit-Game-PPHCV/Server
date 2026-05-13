import json
import time

from extensions import socketio, mqtt_client
from config import MQTT_TOPIC
from game_state import state


def inactivity_monitor():
    """Hintergrund-Task: Erkennt, ob das Handy aus ist / Verbindung verloren hat."""
    while True:
        socketio.sleep(0.5)
        # Wenn über 1 Sekunde keine Daten vom Handy kamen
        if time.time() - state.last_sensor_receive_time > 5.0:
            payload = json.dumps({"brightness_10": 90, "brightness_11": 90})
            try:
                mqtt_client.publish(MQTT_TOPIC, payload)
                # Auch das Cockpit UI zentrieren!
                socketio.emit('cockpit_gyro', {'pitch': 0, 'roll': 0})
            except Exception:
                pass


socketio.start_background_task(inactivity_monitor)
