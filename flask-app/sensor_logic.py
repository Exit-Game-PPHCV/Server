import json
import random
import time

from extensions import socketio, mqtt_client
from config import MQTT_TOPIC, NEIGUNG_HOLD_DURATION, NEIGUNG_INTERVAL, SUBTITLE_COOLDOWN
from game_state import state
from subtitles import emit_subtitle


def start_neigung_challenge():
    # Nicht starten wenn Finale läuft oder Spiel vorbei
    if state.keypad or state.game_finished:
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
    state.neigung_challenge_data = {'axis': axis, 'target': target, 'direction': direction}
    state.neigung_challenge_active = True
    state.neigung_hold_start = None
    state.last_neigung_challenge_time = time.time()
    socketio.emit('neigung_challenge', state.neigung_challenge_data)
    print(f"Neigung-Challenge: {axis} → {direction} (Servo {target})")


@socketio.on('sensor_data')
def handle_sensor_data(data):
    current_time = time.time()
    state.last_sensor_receive_time = current_time
    if current_time - state.last_send_time < 0.05:
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
        mqtt_client.publish(MQTT_TOPIC, payload)
    except Exception as e:
        print(f"MQTT Publish Fehler: {e}")

    # --- Neigung Challenge ---
    # Nicht wenn Finale/Spielende
    if state.game_finished or state.keypad:
        state.last_send_time = current_time
        return

    # Neue Challenge starten wenn Zeit abgelaufen + kein Subtitle läuft
    if state.temparatur and not state.neigung_challenge_active:
        subtitle_safe = (current_time - state.last_subtitle_end_time) > SUBTITLE_COOLDOWN
        if state.last_neigung_challenge_time > 0 and current_time - state.last_neigung_challenge_time >= NEIGUNG_INTERVAL and subtitle_safe:
            start_neigung_challenge()

    # Aktive Challenge prüfen
    if state.neigung_challenge_active and state.neigung_challenge_data:
        axis = state.neigung_challenge_data['axis']
        target = state.neigung_challenge_data['target']
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
            if state.neigung_hold_start is None:
                state.neigung_hold_start = current_time
            hold_duration = current_time - state.neigung_hold_start
            progress = min(hold_duration / NEIGUNG_HOLD_DURATION, 1.0)
            socketio.emit('neigung_progress', {'progress': progress})
            if hold_duration >= NEIGUNG_HOLD_DURATION:
                state.neigung_challenge_active = False
                state.neigung_hold_start = None
                socketio.emit('neigung_challenge_complete')
                print("Neigung-Challenge abgeschlossen!")
                if not state.neigung:
                    state.neigung = True
                    print("Neigung-Task erstmals abgeschlossen!")
                    if state.temparatur:
                        emit_subtitle("cable_task")
                        print("Beide Initial-Tasks abgeschlossen - Kabel-Task gestartet.")
        else:
            if state.neigung_hold_start is not None:
                state.neigung_hold_start = None
                socketio.emit('neigung_progress', {'progress': 0})

    state.last_send_time = current_time
