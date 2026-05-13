from flask import render_template, jsonify, request

from extensions import app, socketio
from game_state import state
from subtitles import emit_subtitle


@app.route("/")
def helloWorld():
    return render_template("index.html")


@app.route("/game")
def game():
    return render_template("game.html", is_done=state.cable)


@app.route('/game-complete', methods=['POST'])
def game_complete():
    if not (state.neigung and state.temparatur):
        return jsonify({"status": "error", "message": "Task locked: initial tasks required"}), 403

    data = request.get_json()

    state.cable_count += 1

    if state.cable_count >= 3:
        state.cable = True
        # Notify the Cockpit UI via WebSocket that the task is done
        socketio.emit('task_update', {'task': 'wires', 'status': 'complete'})

        # Trigger the next subtitle sequence (Laser)
        emit_subtitle("laser_task")

        print(f"Erfolg: Task {data.get('task')} nach 3 Durchläufen abgeschlossen.")
        return jsonify({"status": "success", "count": state.cable_count}), 200
    else:
        print(f"Fortschritt: Task Durchlauf {state.cable_count}/3.")
        return jsonify({"status": "progress", "count": state.cable_count}), 200


@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    return jsonify(state.latest_sensor_data)


@app.route("/gyro")
def gyro():
    return render_template("gyro.html")


@app.route("/landing")
def landing_game():
    return render_template("landing.html")
