from extensions import app, socketio

# Reihenfolge wichtig: jedes Modul registriert beim Import seine Decorator-Handler.
import mqtt_handlers   # noqa: F401  - MQTT-Setup + on_connect/on_message + connect()
import routes          # noqa: F401  - @app.route Handler
import socket_events   # noqa: F401  - @socketio.on Handler
import sensor_logic    # noqa: F401  - @socketio.on('sensor_data') + start_neigung_challenge
import background      # noqa: F401  - startet inactivity_monitor

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
