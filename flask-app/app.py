from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import time
import random
import os

app = Flask(__name__)
socketio = SocketIO(app, max_decode_packets=500)

SUBTITLES = {
    "intro": [
        {"time": 0, "text": "Verdammt! Hast du das gesehen?!"},
        {"time": 2000, "text": "Das Generator-Steuergerät ist uns gerade um die Ohren geflogen."},
        {"time": 5500, "text": "Massive Überspannung im Netz – die Sicherungen haben fast alles gekappt!"},
        {"time": 9500, "text": "Wir segeln nur noch und der Autopilot ist weg."},
        {"time": 13000, "text": "Schau dir mal die Warnmeldungen an:"},
        {"time": 15500, "text": "Die Kühlung ist tot, die Hardware glüht uns weg!"},
        {"time": 19000, "text": "Behalt die rote LED am rechten Board im Auge!"},
        {"time": 22500, "text": "Sobald der Alarm schrillt, musst du den Sensor da drüben kühlen –"},
        {"time": 26500, "text": "nimm das Kältespray oder fächel Luft zu, egal was, aber lass die Temperatur nicht steigen!"},
        {"time": 33000, "text": "Achtung, starke Seitenwinde! Wir kommen vom Kurs ab."},
        {"time": 37000, "text": "Schau auf das Dashboard: Wenn der Kurskorrektur-Alarm auslöst, schnapp dir sofort das Steuer-Handy."},
        {"time": 42000, "text": "Die Pfeile auf dem Cockpit-Bildschirm zeigen dir, in welche Richtung wir driften."},
        {"time": 46000, "text": "Neige das Handy vorsichtig in genau diese Richtung, um gegenzusteuern, bis der Balken voll ist."},
        {"time": 51000, "text": "Wir müssen zwingend auf Kurs bleiben, während wir die Systeme flicken."},
        {"time": 55000, "text": "Los, an die Arbeit!"},
        {"time": 59000, "text": ""}
    ],
    "cable_task": [
        {"time": 0, "text": "Mist, die Funk-Hardware kriegt keinen Strom."},
        {"time": 3000, "text": "Da, schau dir die Bescherung an: Die Leitungen sind physisch getrennt."},
        {"time": 7500, "text": "Hier, nimm die Patch-Kabel! Wir müssen die Brücke manuell flicken."},
        {"time": 11500, "text": "Achte genau auf den Farbcode und verbinde die Enden digital."},
        {"time": 15500, "text": "Beeil dich, ohne Funk wissen die da unten nicht mal, dass wir noch in der Luft sind!"},
        {"time": 21000, "text": ""}
    ],
    "laser_task": [
        {"time": 0, "text": "Ich krieg immer noch keine Daten auf das Keypad – der Glasfaser-Bus ist gestört!"},
        {"time": 5000, "text": "Siehst du den Laser da? Wir müssen den Strahl irgendwie in den Empfänger leiten."},
        {"time": 9500, "text": "Nimm die Spiegel und lenk das Licht so um die Ecken, dass es exakt den LDR-Sensor trifft."},
        {"time": 14500, "text": "Millimeterarbeit, Captain! Erst wenn der Strahl die Daten überträgt, wird das Keypad freigeschaltet."},
        {"time": 20000, "text": ""}
    ],
    "antenna_task": [
        {"time": 0, "text": "Ich hör nur Rauschen auf den Ohren, die Antenne hat sich beim Einschlag völlig verstellt."},
        {"time": 5000, "text": "Hier, der Regler gehört dir. Dreh an dem Potentiometer und such die Frequenz."},
        {"time": 9500, "text": "Achte auf die drei grünen LEDs – wenn alle drei dauerhaft leuchten,"},
        {"time": 13000, "text": "haben wir einen sauberen Kanal. Ganz vorsichtig..."},
        {"time": 17000, "text": ""}
    ],
    "keypad_task": [
        {"time": 0, "text": "Da! Der Autopilot ist endlich wieder online."},
        {"time": 4000, "text": "Schnell jetzt, gib die Koordinaten ein und bring uns auf Kurs, bevor der Landeanflug beginnt!"},
        {"time": 10000, "text": "Du musst die Verschlüsselungen im Bordbuch sofort knacken –"},
        {"time": 14000, "text": "und pass bloß auf: Ein einziger Tippfehler und das System lässt uns von vorne beginnen!"},
        {"time": 20000, "text": ""}
    ],
    "landing_task": [
        {"time": 0, "text": "Der Tower hat uns! Wir beginnen den Sinkflug aus 8000 Metern."},
        {"time": 5000, "text": "Captain, du musst jetzt die Höhe über den Steuerbildschirm steuern."},
        {"time": 10000, "text": "Halt das Flugzeug exakt in dem Kasten auf dem Bildschirm!"},
        {"time": 15000, "text": "Konzentrier dich: Der Kasten wird immer kleiner, je näher wir dem Boden kommen –"},
        {"time": 20000, "text": "am Ende ist er nur noch ein Drittel so groß."},
        {"time": 24000, "text": "Wenn du den Rahmen verlierst, reißt uns der Aufwind wieder 500 Meter hoch."},
        {"time": 30000, "text": ""}
    ],
    "landing_success": [
        {"time": 0, "text": "Wir sind unten! Captain, das war Millimeterarbeit unter extremem Druck."},
        {"time": 5000, "text": "Wir haben es tatsächlich geschafft, das war eine absolute Meisterleistung!!!"},
        {"time": 11000, "text": "Willkommen in Singapur."},
        {"time": 15000, "text": ""}
    ]
}

def get_current_subtitle_sequence():
    if keypad:
        return "landing_task"
    if frequenz:
        return "keypad_task"
    if laser:
        return "antenna_task"
    if cable:
        return "laser_task"
    if neigung and temparatur:
        return "cable_task"
    return "intro"

def emit_subtitle(seq_id):
    """Emittiert eine Subtitle-Sequenz und setzt den Cooldown-Timer."""
    global last_subtitle_end_time
    sequence = SUBTITLES[seq_id]
    # Berechne wann die Sequenz endet (letzter Subtitle-Zeitpunkt)
    max_time = max(s['time'] for s in sequence) if sequence else 0
    last_subtitle_end_time = time.time() + (max_time / 1000.0)
    socketio.emit('play_subtitle_sequence', {'sequence': sequence, 'id': seq_id})


latest_sensor_data = {}

keypad = False
frequenz = False
temparatur = False
neigung = False
cable = False
laser = False
autopilot = False
temperature_alarm_active = True
cable_count = 0
 
last_send_time = 0
MQTT_TOPIC = "zigbee2mqtt/servo/set"

# --- Neigung Challenge System ---
neigung_challenge_active = False
neigung_challenge_data = None   # {'axis': 'pitch'|'roll', 'target': int, 'direction': str}
neigung_hold_start = None
NEIGUNG_HOLD_DURATION = 3.0     # Sekunden halten
NEIGUNG_INTERVAL = 100          # ~1.5 Minuten zwischen Challenges
last_neigung_challenge_time = 0

# --- Task-Priorität ---
game_finished = False           # True nach erfolgreicher Landung
last_subtitle_end_time = 0      # Wann die letzte Subtitle-Sequenz endet
SUBTITLE_COOLDOWN = 5           # Sekunden Cooldown nach Subtitle bevor neue Challenge

# --- Inaktivitäts-Erkennung ---
last_sensor_receive_time = time.time()



# --- MQTT SETUP ---
def on_connect(client, userdata, connect_flags, reason_code, properties):
    if reason_code == 0:
        print("Mit MQTT-Broker verbunden!")
        client.subscribe("zigbee2mqtt/+")
    else:
        print(f"Verbindungsfehler: {reason_code}")

def on_message(client, userdata, msg):
    """Verarbeitet alle MQTT-Nachrichten von Zigbee-Geräten.
    Erwartete Payload-Keys:
    - temperature (float)     → Cockpit-Anzeige + Alarm-Logik
    - temperatureAlarm (bool) → Kühl-Task Status
    - ldrSolved (bool)        → Laser-Task
    - puzzleSolved (bool)     → Frequenz/Antennen-Task
    - keypadSolved (bool)     → Keypad-Task → Landung
    - autopilot (bool)        → Autopilot-Status
    Neigung kommt NICHT über MQTT → WebSocket von /gyro Seite
    """
    global temparatur, laser, frequenz, keypad, autopilot, temperature_alarm_active
    global last_neigung_challenge_time, neigung_challenge_active
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        latest_sensor_data[msg.topic] = payload

        # --- ZIGBEE2MQTT NATIVE TRANSLATION ---
        # Wenn native ESP32-Zigbee Geräte genutzt werden, senden sie Standard-Endpoints (state_l1, state_l2 = "ON"/"OFF").
        # Wir übersetzen diese anhand des Gerätenamens (Topic) in unsere Spiel-Variablen:
        topic_name = msg.topic.split('/')[-1].lower()
        
        # ESP 1: Laser & Frequenzen
        if 'laser' in topic_name or 'frequenz' in topic_name:
            if 'state_1' in payload: payload['puzzleSolved'] = (payload['state_1'] == 'ON')
            if 'state_2' in payload: payload['ldrSolved'] = (payload['state_2'] == 'ON')
            
        # ESP 2: Keypad & Temperatur
        elif 'keypad' in topic_name or 'temp' in topic_name:
            if 'state_1' in payload: payload['keypadSolved'] = (payload['state_1'] == 'ON')
            if 'state_2' in payload: payload['temperatureAlarm'] = (payload['state_2'] == 'ON')

        socketio.emit('mqtt_update', {'topic': msg.topic, 'data': payload})

        # --- Temperaturalarm (bool, kann wiederholt an/aus gehen) ---
        # PRIORITÄT: Unterdrückt während Neigung-Challenge, Finale oder Spielende
        if 'temperatureAlarm' in payload:
            alarm_active = bool(payload['temperatureAlarm'])
            
            if alarm_active != temperature_alarm_active:
                temperature_alarm_active = alarm_active
                if neigung_challenge_active or keypad or game_finished:
                    print(f"Temperaturalarm {'aktiv' if alarm_active else 'gelöst'} - UNTERDRÜCKT (andere Task aktiv)")
                else:
                    socketio.emit('temperature_alarm', {'active': alarm_active})
                    if alarm_active:
                        print("TEMPERATURALARM AKTIV - Sensor überhitzt!")
                    else:
                        print("Temperaturalarm aufgelöst - Sensor abgekühlt.")
            
            # TASK-ABSCHLUSS ROBUST GEMACHT:
            # Wir prüfen bei jedem Payload, ob der Alarm AUS ist.
            # Falls ja, gilt der Task als bestanden - egal ob er sich gerade erst geändert hat oder nicht!
            if not alarm_active and not temparatur:
                temparatur = True
                print("Kühl-Task als erledigt markiert! Warte auf passenden Zeitpunkt für Neigung-Challenge.")

        # --- Laser-Task (LDR-Sensor) ---
        if 'ldrSolved' in payload:
            if not laser and payload['ldrSolved'] == True:
                laser = True
                seq_id = "antenna_task"
                emit_subtitle(seq_id)
                print("Laser-Task abgeschlossen - Antennen-Task gestartet.")

        # --- Frequenz/Antennen-Task (Potentiometer-Puzzle) ---
        if 'puzzleSolved' in payload:
            if not frequenz and payload['puzzleSolved'] == True:
                frequenz = True
                socketio.emit('frequenz_update', {'frequenz': True})
                seq_id = "keypad_task"
                emit_subtitle(seq_id)
                print("Antennen-Task abgeschlossen - Keypad-Task gestartet.")

        # --- Keypad-Task → Finale startet, wiederkehrende Tasks stoppen ---
        if 'keypadSolved' in payload:
            if not keypad and payload['keypadSolved'] == True:
                keypad = True
                # Aktive Neigung-Challenge sofort beenden
                if neigung_challenge_active:
                    neigung_challenge_active = False
                    socketio.emit('neigung_challenge_complete')
                # Aktiven Temp-Alarm beenden
                if temperature_alarm_active:
                    socketio.emit('temperature_alarm', {'active': False})
                
                socketio.emit('start_landing_sequence')
                print("FINALE: Keypad gelöst - Alle wiederkehrenden Tasks gestoppt - Landing gestartet.")

        # --- Autopilot ---
        if 'autopilot' in payload:
            autopilot = bool(payload['autopilot'])
            socketio.emit('autopilot_update', {'status': autopilot})
            print(f"Autopilot Status: {'ON' if autopilot else 'OFF'}")
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
    return render_template("game.html", is_done=cable)
@app.route('/game-complete', methods=['POST'])
def game_complete():
    global cable, cable_count
    if not (neigung and temparatur):
        return jsonify({"status": "error", "message": "Task locked: initial tasks required"}), 403
    
    data = request.get_json()
    
    cable_count += 1
    
    if cable_count >= 3:
        cable = True
        # Notify the Cockpit UI via WebSocket that the task is done
        socketio.emit('task_update', {'task': 'wires', 'status': 'complete'})
        
        # Trigger the next subtitle sequence (Laser)
        seq_id = "laser_task"
        emit_subtitle(seq_id)
        
        print(f"Erfolg: Task {data.get('task')} nach 3 Durchläufen abgeschlossen.")
        return jsonify({"status": "success", "count": cable_count}), 200
    else:
        print(f"Fortschritt: Task Durchlauf {cable_count}/3.")
        return jsonify({"status": "progress", "count": cable_count}), 200
@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    return jsonify(latest_sensor_data)

class DummyMsg:
    pass

@app.route('/test-trigger')
def test_trigger():
    sensor = request.args.get('sensor')
    state = request.args.get('state')
    topic = request.args.get('topic', 'zigbee2mqtt/test')
    
    if sensor and state:
        msg = DummyMsg()
        msg.topic = topic
        payload = {}
        if state.upper() == 'ON':
            payload[sensor] = True
        elif state.upper() == 'OFF':
            payload[sensor] = False
        else:
            payload[sensor] = state

        msg.payload = json.dumps(payload).encode('utf-8')
        on_message(None, None, msg)
        return f"Simulated: {topic} -> {sensor} = {state} <br><br><button onclick=\"location.href='/test'\">Zurück zum Test-Menü</button>"
    return "Error: Missing sensor or state"

@app.route('/test')
def test_page():
    return """
    <html><body style="font-family: sans-serif; padding: 20px;">
    <h1>Sensoren Manuell Triggern</h1>
    <style>button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; }</style>
    
    <h3>Temperatur (ESP 2)</h3>
    <button onclick="location.href='/test-trigger?sensor=temperatureAlarm&state=ON'">🌡️ Temp Heiß (ON) - Alarm auslösen</button>
    <button onclick="location.href='/test-trigger?sensor=temperatureAlarm&state=OFF'">❄️ Temp Kühl (OFF) - Task lösen</button>

    <h3>Laser (ESP 1)</h3>
    <button onclick="location.href='/test-trigger?sensor=ldrSolved&state=ON'">🔦 Laser Gelöst (ON)</button>
    
    <h3>Frequenz (ESP 1)</h3>
    <button onclick="location.href='/test-trigger?sensor=puzzleSolved&state=ON'">📻 Frequenz Gelöst (ON)</button>
    
    <h3>Keypad (ESP 2)</h3>
    <button onclick="location.href='/test-trigger?sensor=keypadSolved&state=ON'">🔢 Keypad Gelöst (ON) - Finale starten</button>
    
    <h3>Autopilot</h3>
    <button onclick="location.href='/test-trigger?sensor=autopilot&state=ON'">✈️ Autopilot ON</button>
    <button onclick="location.href='/test-trigger?sensor=autopilot&state=OFF'">✈️ Autopilot OFF</button>
    
    <br><br><hr><br>
    <a href="/">Zurück zum Hauptspiel (Cockpit)</a>
    </body></html>
    """


@app.route("/gyro")
def gyro():
    return render_template("gyro.html")

@app.route("/landing")
def landing_game():
    return render_template("landing.html")

@socketio.on('connect')
def handle_connect():
    global cable, cable_count
    # Reset progress only if the task was not yet fully completed
    if not cable:
        cable_count = 0
    
    initial_state = {
        'autopilot': autopilot,
        'sensors': latest_sensor_data,
        'cable_task_complete': cable,
        'frequenz': frequenz,
        'gyro_task_complete': neigung,
        'temp_task_complete': temparatur,
        'temperature_alarm_active': temperature_alarm_active
    }
    socketio.emit('initial_state', initial_state)
    print("Cockpit verbunden - Initialer Status synchronisiert. Warte auf Start-Signal.")

@socketio.on('request_start')
def handle_request_start():
    print("Start-Signal empfangen - Spiel beginnt.")
    seq_id = get_current_subtitle_sequence()
    
    # Bugfix: Falls durch "missgeschicke" das Keypad schon gelöst war, 
    # MÜSSEN wir den Browser zwingen, jetzt die Seite zu wechseln!
    if seq_id == "landing_task" or keypad:
        socketio.emit('start_landing_sequence')
    else:
        emit_subtitle(seq_id)

@socketio.on('landing_ready')
def handle_landing_ready():
    print("Landing Page ist bereit - spiele Landing Audio ab.")
    emit_subtitle("landing_task")

@socketio.on('repeat_transmission')
def handle_repeat_transmission():
    seq_id = get_current_subtitle_sequence()
    emit_subtitle(seq_id)

@socketio.on('landing_complete')
def handle_landing_complete():
    global game_finished
    game_finished = True
    # Alles aufräumen
    if neigung_challenge_active:
        socketio.emit('neigung_challenge_complete')
    if temperature_alarm_active:
        socketio.emit('temperature_alarm', {'active': False})
    seq_id = "landing_success"
    emit_subtitle(seq_id)
    socketio.emit('game_finished')
    print("=== SPIEL BEENDET - Landung erfolgreich ===")



# --- Neigung Challenge Funktionen ---
def start_neigung_challenge():
    global neigung_challenge_active, neigung_challenge_data, neigung_hold_start, last_neigung_challenge_time
    # Nicht starten wenn Finale läuft oder Spiel vorbei
    if keypad or game_finished:
        print("Neigung-Challenge unterdrückt (Finale/Spielende).")
        return
    axis = random.choice(['pitch', 'roll'])
    # Ziel: 65-85 oder 95-115 (Totzone ±5 um 90 vermeiden)
    if random.random() < 0.5:
        target = random.randint(65, 85)
    else:
        target = random.randint(95, 115)
    if axis == 'pitch':
        direction = 'up' if target > 90 else 'down'
    else:
        direction = 'right' if target > 90 else 'left'
    neigung_challenge_data = {'axis': axis, 'target': target, 'direction': direction}
    neigung_challenge_active = True
    neigung_hold_start = None
    last_neigung_challenge_time = time.time()
    socketio.emit('neigung_challenge', neigung_challenge_data)
    print(f"Neigung-Challenge: {axis} → {direction} (Servo {target})")

@socketio.on('sensor_data')
def handle_sensor_data(data):
    global last_send_time, neigung, neigung_challenge_active, neigung_hold_start, last_sensor_receive_time
    current_time = time.time()
    last_sensor_receive_time = current_time
    if current_time - last_send_time < 0.05:
        return
    pitch = data.get('pitch', 0)
    roll = data.get('roll', 0)
    pitch = max(-35, min(35, pitch))
    roll = max(-35, min(35, roll))

    socketio.emit('cockpit_gyro', {'pitch': pitch, 'roll': roll})

    servo_pitch = int(pitch + 90)
    servo_roll = int(roll + 90)
    payload = json.dumps({"brightness_10": servo_pitch, "brightness_11": servo_roll})
    try:
        client.publish(MQTT_TOPIC, payload)
    except Exception as e:
        print(f"MQTT Publish Fehler: {e}")

    # --- Neigung Challenge ---
    # Nicht wenn Finale/Spielende
    if game_finished or keypad:
        last_send_time = current_time
        return
    
    # Die Logik zum Starten von Challenges wurde in den background_monitor verschoben,
    # damit sie auch triggert, wenn das Handy gerade keine Daten sendet (Idle/Standby).


    # Aktive Challenge prüfen
    if neigung_challenge_active and neigung_challenge_data:
        axis = neigung_challenge_data['axis']
        target = neigung_challenge_data['target']
        current_servo = servo_pitch if axis == 'pitch' else servo_roll
        target_offset = target - 90
        current_offset = current_servo - 90
        # Spieler muss mindestens so weit von 90 entfernt sein wie target, gleiche Richtung
        beyond = False
        if target_offset < 0:
            beyond = current_offset <= target_offset
        elif target_offset > 0:
            beyond = current_offset >= target_offset
        if beyond:
            if neigung_hold_start is None:
                neigung_hold_start = current_time
            hold_duration = current_time - neigung_hold_start
            progress = min(hold_duration / NEIGUNG_HOLD_DURATION, 1.0)
            socketio.emit('neigung_progress', {'progress': progress})
            if hold_duration >= NEIGUNG_HOLD_DURATION:
                neigung_challenge_active = False
                neigung_hold_start = None
                socketio.emit('neigung_challenge_complete')
                print("Neigung-Challenge abgeschlossen!")
                if not neigung:
                    neigung = True
                    print("Neigung-Task erstmals abgeschlossen!")
                    if temparatur:
                        seq_id = "cable_task"
                        emit_subtitle(seq_id)
                        print("Beide Initial-Tasks abgeschlossen - Kabel-Task gestartet.")
        else:
            if neigung_hold_start is not None:
                neigung_hold_start = None
                socketio.emit('neigung_progress', {'progress': 0})

    last_send_time = current_time

def background_monitor():
    """Hintergrund-Task: Prüft Inaktivität UND triggert neue Neigung-Challenges."""
    global last_sensor_receive_time, neigung_challenge_active
    while True:
        socketio.sleep(1.0)
        current_time = time.time()

        # 1. Handy-Inaktivität prüfen (Zentrieren wenn weg)
        if current_time - last_sensor_receive_time > 5.0:
            try:
                client.publish(MQTT_TOPIC, json.dumps({"brightness_10": 90, "brightness_11": 90}))
                socketio.emit('cockpit_gyro', {'pitch': 0, 'roll': 0})
            except Exception: pass

        # 2. Neigung-Challenges triggern (unabhängig davon ob das Handy gerade sendet)
        if temparatur and not neigung_challenge_active and not keypad and not game_finished:
            subtitle_safe = current_time > last_subtitle_end_time + SUBTITLE_COOLDOWN
            
            # Erste Challenge
            if last_neigung_challenge_time == 0:
                if subtitle_safe:
                    start_neigung_challenge()
            # Folge-Challenges
            elif current_time - last_neigung_challenge_time >= NEIGUNG_INTERVAL:
                if subtitle_safe:
                    start_neigung_challenge()

socketio.start_background_task(background_monitor)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)