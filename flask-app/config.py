import os

MQTT_TOPIC = "zigbee2mqtt/servo/set"
MQTT_BROKER = os.environ.get('MQTT_BROKER', 'mqtt')

# --- Neigung Challenge System ---
NEIGUNG_HOLD_DURATION = 3.0     # Sekunden halten
NEIGUNG_INTERVAL = 180          # 3 Minuten zwischen Challenges

# --- Task-Priorität ---
SUBTITLE_COOLDOWN = 5           # Sekunden Cooldown nach Subtitle bevor neue Challenge
