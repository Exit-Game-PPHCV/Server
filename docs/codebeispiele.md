# Codebeispiele & Logik-Aufteilung

Dieses Dokument beleuchtet die Kommunikation zwischen den verschiedenen Geräten und zeigt, wie die Spiellogik zwischen den Edge-Geräten (ESP32) und dem zentralen Server (Flask) aufgeteilt ist.

## 1. Verteilung der Spiellogik (Edge vs. Server)

Ein zentrales Designprinzip der Architektur ist die **sinnvolle Aufteilung der Logik**:
- **ESP32 (Edge)**: Übernehmen die *lokale* Rätsel-Logik. Sie lesen nicht nur Sensoren aus, sondern werten diese auch aus (z.B. "Ist der eingegebene Code richtig?", "Sind die Potentiometer im Zielbereich?"). Sie senden nur das fertige, aggregierte Ergebnis (Booleans) an den Server, was den Netzwerkverkehr und die Serverlast extrem reduziert.
- **Flask (Server)**: Ist die *Single Source of Truth* für den übergeordneten Spielzustand. Er weiß, welches Rätsel gerade aktiv ist, steuert den narrativen Fortschritt (Subtitles) und kümmert sich um komplexe Mathematik (wie Gyro-zu-Servo), für die die ESPs bewusst "dumm" gehalten werden.

---

## 2. ESP32 #2: Keypad-Auswertung (Lokale Logik)

Anstatt jeden Tastendruck über das Zigbee-Netzwerk an den Server zu senden, wertet der ESP32 den Code selbständig aus. Der Server erfährt nur das finale Ergebnis, ob das Rätsel gelöst wurde.

*Datei: `Keypad-TemperaturAlarm_ESP-main/ESP2_zigbee.ino`*
```cpp
void checkInputCode() {
  // Lokale Auswertung direkt auf dem Mikrocontroller
  if (inputCode == correctCode) {
    keypadSolved = true;
  } else {
    keypadSolved = false;
  }
  
  // Senden des aggregierten Status über den "Zigbee-Hack"
  sendStateToZigbee();
}

void sendStateToZigbeeForced() {
  // Jeder Boolean wird als eigene smarte Steckdose gesteuert.
  // false = aus (OFF), true = an (ON)
  zbKeypadSolved.setState(keypadSolved);
  zbTemperatureAlarm.setState(temperatureAlarm);
}
```

---

## 3. ESP32 #1: Frequenz-Rätsel (Lokale Logik)

Auch hier kennt der Server keine rohen analogen ADC-Werte der drei Potentiometer. Der ESP32 generiert selbständig zufällige Zielbereiche für jede Spielrunde und prüft, ob die Spieler diese getroffen haben.

*Datei: `Potentiometer-LDR_ESP-main/Sensor_zigbee.ino`*
```cpp
bool allCorrect = true;

for (int i = 0; i < SENSOR_COUNT; i++) {
  int value = analogRead(SENSOR_PINS[i]);

  // Prüfen, ob der Sensorwert im lokal generierten Zielbereich liegt
  if (value >= targetMin[i] && value <= targetMax[i]) {
    digitalWrite(LED_PINS[i], HIGH);
  } else {
    digitalWrite(LED_PINS[i], LOW);
    allCorrect = false; // Ein Poti ist falsch
  }
}

puzzleSolved = allCorrect;

// Senden des Ergebnisses an den Server via simuliertem Zigbee-PowerOutlet
zbPuzzleSolved.setState(puzzleSolved);
```

---

## 4. Flask Server: Zentrale State Machine

Der Flask-Server empfängt die aggregierten Booleans der ESPs über MQTT (weitergeleitet von Zigbee2MQTT). Hier läuft die zentrale State Machine, die anhand dieser Events entscheidet, wie das Spiel voranschreitet.

*Datei: `flask-app/app.py`*
```python
# Event-Handler für eingehende Sensor-Daten via MQTT
def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    
    # Auslesen der simulierten Steckdosen-Zustände (ON/OFF)
    if 'state_1' in payload:
        global keypadSolved
        keypadSolved = (payload['state_1'] == 'ON')
        
    # Überprüfen des Spiel-Fortschritts nach jedem Event
    check_game_progress()

def check_game_progress():
    global current_subtitle_index
    
    # Die Server-Logik verknüpft Hardware-Events mit der Narrativen
    if current_subtitle_index == 12 and puzzleSolved:
        # Frequenz-Rätsel wurde vom ESP als gelöst gemeldet -> Gehe zum Keypad
        current_subtitle_index = 13
        socketio.emit('subtitle_update', get_current_subtitle_sequence())
```

---

## 5. End-to-End: Die Servo-Steuerung

Bei der Steuerung des Modellflugzeugs (Aktor) ist die Logik-Verteilung exakt umgekehrt: Der empfangende ESP32 ist extrem "dumm" und führt nur Befehle aus, während der Server die gesamte Mathematik (Clamping, Offsets, Helligkeits-Mapping) übernimmt.

### Schritt A: Smartphone an Server (WebSocket)
Das Smartphone liest den Gyroskop-Sensor aus und pusht die rohen Winkel direkt an den Server.

*Datei: (Architekturkonzept)*
```javascript
window.addEventListener('deviceorientation', function(event) {
    let pitch = event.beta;
    let roll = event.gamma;
    
    // Senden per WebSocket an Flask (Echtzeit, extrem geringe Latenz)
    socket.emit('sensor_data', { pitch: pitch, roll: roll });
});
```

### Schritt B: Server-Logik & MQTT Publish
Flask empfängt die Daten über Socket.IO, bereitet sie mathematisch auf und publiziert sie als Zigbee-Befehle auf dem MQTT-Broker.

*Datei: `flask-app/app.py`*
```python
@socketio.on('sensor_data')
def handle_sensor_data(data):
    pitch = data.get('pitch', 0)
    roll = data.get('roll', 0)

    # Server-seitige Mathematik: Winkel auf +/-35 Grad begrenzen 
    # und auf Servo-Winkel (90 = Mitte) umrechnen
    pitch_servo = max(-35, min(35, int(pitch))) + 90
    roll_servo = max(-35, min(35, int(roll))) + 90

    # Als "Helligkeit" für die simulierten dimmbaren Zigbee-Lampen verpacken
    payload = {
        "brightness_10": pitch_servo,
        "brightness_11": roll_servo
    }
    
    # Über MQTT an Zigbee2MQTT senden
    mqtt_client.publish('zigbee2mqtt/servo/set', json.dumps(payload))
```

### Schritt C: ESP32 führt aus (Edge Aktor)
Der ESP32 empfängt den Helligkeitswert und gibt ihn stumpf an die Servo-Pins weiter.

*Datei: `Flugzeug-ESP-main/Flugzeug.ino`*
```cpp
// Callback für simuliertes dimmbares Licht (Endpoint 10 = Pitch)
zigbeeDevice1.onLightChange([](bool state, uint8_t level) {
  if (state) {
    // 'level' = Helligkeitswert von 0 bis 254.
    // Der Server hat die Mathematik bereits erledigt, 
    // der ESP schreibt den Wert 1:1 auf den Servo-Motor.
    servo1.write(level);
  }
});
```
