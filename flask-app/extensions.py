from flask import Flask
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

app = Flask(__name__)
socketio = SocketIO(app, max_decode_packets=500)
mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
