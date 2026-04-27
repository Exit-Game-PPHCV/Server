from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)

latest_sensor_data = {}

nfc = False
temparatur = False
cable = False
neigung = False
autopilot = False
frequenz = False
 
last_send_time = 0
MQTT_TOPIC = "zigbee2mqtt-data"

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
        
        socketio.emit('mqtt_update', {'topic': msg.topic, 'data': payload})
        
        if 'temperature' in payload:
            print(f"Neue Temperatur auf {msg.topic}: {payload['temperature']} °C")
        
        # Check for autopilot status
        if 'autopilot' in payload:
            global autopilot
            autopilot = bool(payload['autopilot'])
            socketio.emit('autopilot_update', {'status': autopilot})
            print(f"Autopilot Status: {'ON' if autopilot else 'OFF'}")
        if 'frequenz' in payload:
            frequenz = payload['frequenz']
            socketio.emit('frequenz_update', {'frequenz': frequenz})
            print(f"Frequenz: {frequenz}")
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
    global cable
    cable = True
    # Notify the Cockpit UI via WebSocket that the task is done
    socketio.emit('task_update', {'task': 'wires', 'status': 'complete'})
    print(f"Erfolg: Task {data.get('task')} abgeschlossen.")
    return jsonify({"status": "success", "received": data}), 200
@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    return jsonify(latest_sensor_data)

@app.route("/gyro")
def gyro():
    return render_template("gyro.html")
@socketio.on('connect')
def handle_connect():
    initial_state = {
        'autopilot': autopilot,
        'sensors': latest_sensor_data,
        'cable_task_complete': cable,
        'frequenz': frequenz
    }
    socketio.emit('initial_state', initial_state)
    print("Cockpit verbunden - Initialer Status synchronisiert.")

@socketio.on('sensor_data')
def handle_sensor_data(data):
    global last_send_time
    current_time = time.time()
    if current_time - last_send_time < 0.05:
        return
    pitch = data.get('pitch', 0)
    roll = data.get('roll', 0)

    pitch = max(-45, min(45, pitch))
    roll = max(-45, min(45, roll))
    
    socketio.emit('cockpit_gyro', {'pitch': pitch, 'roll': roll})

    servo_pitch = int(45 + ((pitch + 45) * (135 - 45) / 90))
    servo_roll = int(45 + ((roll + 45) * (135 - 45) / 90))

    payload = json.dumps({"pitch_servo": servo_pitch, "roll_servo": servo_roll})
    
    try:
        client.publish(MQTT_TOPIC, payload)
        print(f"Gesendet an Zigbee: {payload}")
    except Exception as e:
        print(f"MQTT Publish Fehler: {e}")
    
    last_send_time = current_time

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)