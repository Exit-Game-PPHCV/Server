from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import json
import os

app = Flask(__name__)

latest_sensor_data = {}

# --- MQTT SETUP ---
def on_connect(client, userdata, flags, rc):
    print("Mit MQTT-Broker verbunden!")
    client.subscribe("zigbee2mqtt/+")

def on_message(client, userdata, msg):
    global aktuelle_temperatur
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        
        if 'temperature' in payload:
            aktuelle_temperatur = f"{payload['temperature']} °C"
            print(f"Neue Temperatur: {aktuelle_temperatur}")
    except Exception as e:
        print("Fehler beim Auslesen der Daten:", e)

broker_adresse = os.environ.get('MQTT_BROKER', 'mqtt')

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(broker_adresse, 1883, 60)
    client.loop_start() 
except Exception as e:
    print("Konnte keine MQTT-Verbindung aufbauen:", e)

@app.route("/")
def helloWorld():
    return render_template("index.html")
@app.route("/game")
def game():
    return render_template("game.html")
@app.route('/game-complete', methods=['POST'])
def game_complete():
    data = request.get_json()
    print(f"Erfolg: Task {data.get('task')} abgeschlossen.")
    return jsonify({"status": "success", "received": data}), 200
@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    # Eine API-Route, damit du die Daten auf einer Webseite anzeigen kannst
    return jsonify(latest_sensor_data)