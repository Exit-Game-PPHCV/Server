import json

from extensions import mqtt_client, socketio
from config import MQTT_BROKER
from game_state import state
from subtitles import emit_subtitle
from sensor_logic import start_neigung_challenge


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
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        state.latest_sensor_data[msg.topic] = payload

        # --- ZIGBEE2MQTT NATIVE TRANSLATION ---
        # Wenn native ESP32-Zigbee Geräte genutzt werden, senden sie Standard-Endpoints (state_l1, state_l2 = "ON"/"OFF").
        # Wir übersetzen diese anhand des Gerätenamens (Topic) in unsere Spiel-Variablen:
        topic_name = msg.topic.split('/')[-1].lower()

        # ESP 1: Laser & Frequenzen
        if 'laser' in topic_name or 'frequenz' in topic_name:
            if 'state_l1' in payload: payload['ldrSolved'] = (payload['state_l1'] == 'ON')
            if 'state_l2' in payload: payload['puzzleSolved'] = (payload['state_l2'] == 'ON')

        # ESP 2: Keypad & Temperatur
        elif 'keypad' in topic_name or 'temp' in topic_name:
            if 'state_l1' in payload: payload['keypadSolved'] = (payload['state_l1'] == 'ON')
            if 'state_l2' in payload: payload['temperatureAlarm'] = (payload['state_l2'] == 'ON')

        socketio.emit('mqtt_update', {'topic': msg.topic, 'data': payload})

        # --- Temperaturalarm (bool, kann wiederholt an/aus gehen) ---
        # PRIORITÄT: Unterdrückt während Neigung-Challenge, Finale oder Spielende
        if 'temperatureAlarm' in payload:
            alarm_active = bool(payload['temperatureAlarm'])
            if alarm_active != state.temperature_alarm_active:
                state.temperature_alarm_active = alarm_active
                if state.neigung_challenge_active or state.keypad or state.game_finished:
                    print(f"Temperaturalarm {'aktiv' if alarm_active else 'gelöst'} - UNTERDRÜCKT (andere Task aktiv)")
                else:
                    socketio.emit('temperature_alarm', {'active': alarm_active})
                    if alarm_active:
                        print("TEMPERATURALARM AKTIV - Sensor überhitzt!")
                    else:
                        print("Temperaturalarm aufgelöst - Sensor abgekühlt.")
                if not alarm_active and not state.temparatur:
                    state.temparatur = True
                    print("Kühl-Task abgeschlossen.")
                    # Erste Neigung-Challenge starten
                    state.last_neigung_challenge_time = 0
                    start_neigung_challenge()
                    print("Erste Neigung-Challenge gestartet.")

        # --- Laser-Task (LDR-Sensor) ---
        if 'ldrSolved' in payload:
            if not state.laser and payload['ldrSolved'] == True:
                state.laser = True
                emit_subtitle("antenna_task")
                print("Laser-Task abgeschlossen - Antennen-Task gestartet.")

        # --- Frequenz/Antennen-Task (Potentiometer-Puzzle) ---
        if 'puzzleSolved' in payload:
            if not state.frequenz and payload['puzzleSolved'] == True:
                state.frequenz = True
                socketio.emit('frequenz_update', {'frequenz': True})
                emit_subtitle("keypad_task")
                print("Antennen-Task abgeschlossen - Keypad-Task gestartet.")

        # --- Keypad-Task → Finale startet, wiederkehrende Tasks stoppen ---
        if 'keypadSolved' in payload:
            if not state.keypad and payload['keypadSolved'] == True:
                state.keypad = True
                # Aktive Neigung-Challenge sofort beenden
                if state.neigung_challenge_active:
                    state.neigung_challenge_active = False
                    socketio.emit('neigung_challenge_complete')
                # Aktiven Temp-Alarm beenden
                if state.temperature_alarm_active:
                    socketio.emit('temperature_alarm', {'active': False})
                socketio.emit('start_landing_sequence')
                emit_subtitle("landing_task")
                print("FINALE: Keypad gelöst - Alle wiederkehrenden Tasks gestoppt - Landing gestartet.")

        # --- Autopilot ---
        if 'autopilot' in payload:
            state.autopilot = bool(payload['autopilot'])
            socketio.emit('autopilot_update', {'status': state.autopilot})
            print(f"Autopilot Status: {'ON' if state.autopilot else 'OFF'}")
    except Exception as e:
        print("Fehler beim Auslesen der Daten:", e)


mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()
except Exception as e:
    print("Konnte keine MQTT-Verbindung aufbauen:", e)
