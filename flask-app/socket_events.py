from extensions import socketio
from game_state import state
from subtitles import emit_subtitle, get_current_subtitle_sequence


@socketio.on('connect')
def handle_connect():
    # Reset progress only if the task was not yet fully completed
    if not state.cable:
        state.cable_count = 0

    initial_state = {
        'autopilot': state.autopilot,
        'sensors': state.latest_sensor_data,
        'cable_task_complete': state.cable,
        'frequenz': state.frequenz,
        'gyro_task_complete': state.neigung,
        'temp_task_complete': state.temparatur,
        'temperature_alarm_active': state.temperature_alarm_active
    }
    socketio.emit('initial_state', initial_state)
    print("Cockpit verbunden - Initialer Status synchronisiert. Warte auf Start-Signal.")


@socketio.on('request_start')
def handle_request_start():
    print("Start-Signal empfangen - Spiel beginnt.")
    seq_id = get_current_subtitle_sequence()
    emit_subtitle(seq_id)


@socketio.on('repeat_transmission')
def handle_repeat_transmission():
    seq_id = get_current_subtitle_sequence()
    emit_subtitle(seq_id)


@socketio.on('landing_complete')
def handle_landing_complete():
    state.game_finished = True
    # Alles aufräumen
    if state.neigung_challenge_active:
        socketio.emit('neigung_challenge_complete')
    if state.temperature_alarm_active:
        socketio.emit('temperature_alarm', {'active': False})
    emit_subtitle("landing_success")
    socketio.emit('game_finished')
    print("=== SPIEL BEENDET - Landung erfolgreich ===")
