from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import os

app = Flask(__name__)

latest_sensor_data = {}

nfc = False
temparatur = False
cable = False
neigung = False

progress = 0
def checkProgress():
    for check in [nfc, temparatur, cable, neigung]:
        if check:
            progress += 25



# --- MQTT SETUP ---
def on_connect(client, userdata, connect_flags, reason_code, properties):
    if reason_code == 0:
        print("Mit MQTT-Broker verbunden!")
        client.subscribe("zigbee2mqtt/+")
    else:
        print(f"Verbindungsfehler: {reason_code}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        latest_sensor_data[msg.topic] = payload
        if 'temperature' in payload:
            print(f"Neue Temperatur auf {msg.topic}: {payload['temperature']} °C")
    except Exception as e:
        print("Fehler beim Auslesen der Daten:", e)

broker_adresse = os.environ.get('MQTT_BROKER', 'mqtt')

client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
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
    cable = True
    print(f"Erfolg: Task {data.get('task')} abgeschlossen.")
    return jsonify({"status": "success", "received": data}), 200
@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    return jsonify(latest_sensor_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)