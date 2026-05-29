# Code-Dokumentation – ESP32 #1: Potentiometer- und LDR-Modul

## 1. Übersicht

Diese Datei beschreibt den Code für den ersten ESP32 im Flight Simulator Exit Game. Der Mikrocontroller ist für zwei Rätsel zuständig:

* das Frequenz-Rätsel mit drei Potentiometern
* das Laser-/LDR-Rätsel mit einem Fotosensor

Beide Rätsel werden direkt auf dem ESP32 ausgewertet. Der Server bekommt also nicht dauerhaft alle einzelnen Sensorwerte geschickt, sondern nur das jeweilige Ergebnis als Boolean-Wert. Dadurch bleibt die Hardware-Logik nah am Mikrocontroller, während der Flask-Server nur den übergeordneten Spielablauf verarbeitet.

Die Kommunikation mit dem Raspberry Pi erfolgt über Zigbee. Damit die Zustände möglichst einfach in Zigbee2MQTT und später in Flask verarbeitet werden können, werden die Boolean-Werte als virtuelle Zigbee-Steckdosen dargestellt.

---

## 2. Aufgabe des ESP32 im Spiel

Der ESP32 #1 übernimmt im Spiel zwei physische Aufgaben, die zur Wiederherstellung der Flugzeugsysteme gehören.

| Rätsel            | Bedeutung im Spiel                                             | Technische Umsetzung                                                 |
| ----------------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| Frequenz-Rätsel   | Das Funkgerät bzw. die Antenne muss korrekt eingestellt werden | Drei Potentiometer müssen in zufällige Zielbereiche gedreht werden   |
| Laser-/LDR-Rätsel | Ein optischer Datenstrom muss wiederhergestellt werden         | Ein Laser muss so ausgerichtet werden, dass er den LDR-Sensor trifft |

Der ESP32 arbeitet dabei als eigenständiges Rätselmodul. Er liest die Sensoren aus, entscheidet lokal, ob ein Rätsel gelöst wurde, und sendet anschließend nur den fertigen Status an das restliche System.

---

## 3. Zigbee-Endpunkte für die Statuswerte

Zu Beginn des Codes werden zwei Zigbee-Endpunkte definiert:

```cpp
#define ZB_ENDPOINT_PUZZLE_SOLVED 1
#define ZB_ENDPOINT_LDR_SOLVED    2
```

Diese Endpunkte werden anschließend als `ZigbeePowerOutlet` angelegt:

```cpp
ZigbeePowerOutlet zbPuzzleSolved = ZigbeePowerOutlet(ZB_ENDPOINT_PUZZLE_SOLVED);
ZigbeePowerOutlet zbLdrSolved    = ZigbeePowerOutlet(ZB_ENDPOINT_LDR_SOLVED);
```

Die Idee dahinter ist, einfache Boolean-Zustände als virtuelle Steckdosen abzubilden. Eine Steckdose ist entweder an oder aus. Genau dieses Prinzip passt gut zu den Rätselzuständen.

| Boolean        | Zigbee-Endpunkt | Bedeutung                                       |
| -------------- | --------------- | ----------------------------------------------- |
| `puzzleSolved` | EP 1            | Das Potentiometer-/Frequenz-Rätsel wurde gelöst |
| `ldrSolved`    | EP 2            | Das Laser-/LDR-Rätsel wurde gelöst              |

Dabei gilt:

```text
false = Steckdose AUS
true  = Steckdose AN
```

Der Vorteil ist, dass Zigbee2MQTT diese Zustände direkt als `ON` oder `OFF` weitergeben kann. Der Flask-Server muss dadurch keine analogen Sensorwerte interpretieren, sondern bekommt nur die spielrelevanten Ergebnisse.

---

## 4. Hardware-Pinbelegung

Der Code verwendet drei analoge Eingänge für die Potentiometer und drei LEDs als direktes Feedback für die Spieler.

```cpp
const int SENSOR_PINS[3] = {4, 5, 0};
const int LED_PINS[3]    = {20, 21, 22};
```

Zusätzlich gibt es den LDR-Sensor und eine eigene Status-LED für das Laser-Rätsel:

```cpp
const int LDR_PIN = 6;
const int LDR_LED_PIN = 23;
```

Die Pinbelegung ist damit:

| Komponente          | Pin     |
| ------------------- | ------- |
| Potentiometer 1     | GPIO 4  |
| Potentiometer 2     | GPIO 5  |
| Potentiometer 3     | GPIO 0  |
| LED Potentiometer 1 | GPIO 20 |
| LED Potentiometer 2 | GPIO 21 |
| LED Potentiometer 3 | GPIO 22 |
| LDR-Sensor          | GPIO 6  |
| LDR-Status-LED      | GPIO 23 |

Die Sensorwerte werden mit `analogRead()` ausgelesen. Beim ESP32 liegen die analogen Werte typischerweise im Bereich von 0 bis 4095.

---

## 5. Potentiometer-Rätsel

Das Potentiometer-Rätsel besteht aus drei Sensoren, die jeweils in einen bestimmten Zielbereich gebracht werden müssen. Die Zielbereiche werden zufällig erzeugt, damit das Rätsel nicht jedes Mal identisch ist.

Für jeden Sensor wird ein eigener Bereich berechnet:

```cpp
targetMin[i] = random(ADC_MIN, ADC_MAX - TARGET_WIDTH);
targetMax[i] = targetMin[i] + TARGET_WIDTH;
```

Die Breite eines Zielbereichs ist festgelegt durch:

```cpp
const int TARGET_WIDTH = 200;
```

Ein Zielbereich umfasst also 200 ADC-Werte. Wenn ein Potentiometer innerhalb seines Zielbereichs liegt, leuchtet die zugehörige LED. Liegt es außerhalb, bleibt die LED aus.

Die Prüfung übernimmt diese Funktion:

```cpp
bool inTarget(int i, int value) {
  return value >= targetMin[i] && value <= targetMax[i];
}
```

Im laufenden Spiel wird jeder der drei Sensoren nacheinander ausgelesen:

```cpp
int value = analogRead(SENSOR_PINS[i]);
```

Danach wird geprüft, ob der Wert im Zielbereich liegt:

```cpp
if (inTarget(i, value)) {
  digitalWrite(LED_PINS[i], HIGH);
} else {
  digitalWrite(LED_PINS[i], LOW);
  allCorrect = false;
}
```

Erst wenn alle drei Potentiometer gleichzeitig richtig eingestellt sind, wird das Rätsel als gelöst markiert:

```cpp
puzzleSolved = allCorrect;
```

Damit wird aus drei einzelnen Sensorwerten ein einziger Statuswert, der später an den Server weitergegeben wird.

---

## 6. Spielzustände des Potentiometer-Rätsels

Für das Potentiometer-Rätsel wird eine einfache State Machine genutzt. Sie macht den Ablauf übersichtlich und trennt die normale Spielphase von der Erfolgsanzeige.

```cpp
enum GameState {
  PLAYING,
  SUCCESS_BLINK,
  SUCCESS_HOLD
};
```

### PLAYING

In diesem Zustand läuft das Rätsel normal. Die Potentiometer werden ausgelesen, die LEDs zeigen den aktuellen Status an und nach Ablauf der Rundenzeit werden neue Zielbereiche erzeugt.

```cpp
const unsigned long ROUND_TIME_MS = 30000;
```

Das bedeutet, dass alle 30 Sekunden neue Zielbereiche entstehen, wenn das Rätsel bis dahin nicht gelöst wurde.

### SUCCESS_BLINK

Sobald alle drei Potentiometer korrekt eingestellt sind, wechselt das Programm in den Erfolgszustand `SUCCESS_BLINK`.

```cpp
const unsigned long BLINK_TIME_MS = 5000;
```

In dieser Phase blinken alle drei LEDs gemeinsam für fünf Sekunden. Dadurch bekommen die Spieler ein klares sichtbares Feedback, dass das Rätsel gelöst wurde.

### SUCCESS_HOLD

Nach der Blinkphase bleiben alle drei LEDs dauerhaft eingeschaltet.

```cpp
const unsigned long HOLD_TIME_MS = 1200000;
```

Dieser Zustand hält längere Zeit an. Dadurch bleibt das gelöste Rätsel stabil sichtbar und der Server kann den Zustand zuverlässig weiterverarbeiten.

---

## 7. Laser-/LDR-Rätsel

Das zweite Rätsel verwendet einen LDR-Sensor. Der Sensor misst, ob ausreichend Licht auf ihn trifft. Im Spiel bedeutet das, dass der Laser korrekt über die Spiegel auf den Empfänger ausgerichtet wurde.

Der LDR-Wert wird in der Funktion `updateLdr()` gelesen:

```cpp
int ldrValue = analogRead(LDR_PIN);
```

Dieser Wert wird mit einem Schwellwert verglichen:

```cpp
const int LDR_THRESHOLD = 3750;
```

Wenn der gemessene Wert mindestens so groß wie dieser Schwellwert ist, wird das LDR-Rätsel als gelöst markiert:

```cpp
if (ldrValue >= LDR_THRESHOLD) {
  ldrSolved = true;
}
```

Die passende Status-LED zeigt den Zustand direkt am Aufbau an:

```cpp
if (ldrSolved) {
  digitalWrite(LDR_LED_PIN, HIGH);
} else {
  digitalWrite(LDR_LED_PIN, LOW);
}
```

Der Wert `ldrSolved` wird nach erfolgreicher Lösung nicht automatisch wieder auf `false` zurückgesetzt. Das passt zum Spielprinzip, da das Laser-Rätsel nach dem erfolgreichen Treffen des Sensors dauerhaft als abgeschlossen gelten soll.

---

## 8. Zigbee-Initialisierung

Die Zigbee-Kommunikation wird in der Funktion `setupZigbee()` vorbereitet.

Zunächst werden Hersteller- und Modellnamen gesetzt:

```cpp
zbPuzzleSolved.setManufacturerAndModel("EscapeGame", "PuzzleSolved");
zbLdrSolved.setManufacturerAndModel("EscapeGame", "LdrSolved");
```

Danach werden beide virtuellen Steckdosen als Zigbee-Endpunkte registriert:

```cpp
Zigbee.addEndpoint(&zbPuzzleSolved);
Zigbee.addEndpoint(&zbLdrSolved);
```

Anschließend startet der ESP32 als Zigbee-Router:

```cpp
Zigbee.begin(ZIGBEE_ROUTER);
```

Das Programm wartet, bis eine Verbindung zum Zigbee-Netzwerk besteht:

```cpp
while (!Zigbee.connected()) {
  Serial.print(".");
  delay(100);
}
```

Erst wenn diese Verbindung steht, läuft die eigentliche Spiellogik weiter. Dadurch wird sichergestellt, dass die späteren Statuswerte auch tatsächlich an das Zigbee-Netzwerk gesendet werden können.

---

## 9. Senden der Boolean-Werte

Der Code sendet die beiden Boolean-Zustände auf zwei Arten: bei Änderungen und zusätzlich regelmäßig als Wiederholung.

### 9.1 Senden bei Statusänderung

Die Funktion `sendBooleanOutletsToZigbee()` prüft, ob sich einer der beiden relevanten Werte geändert hat:

```cpp
bool changed =
  firstZigbeeSend ||
  puzzleSolved != lastSentPuzzleSolved ||
  ldrSolved != lastSentLdrSolved;
```

Wenn sich nichts geändert hat, wird auch nichts gesendet. Dadurch wird das Zigbee-Netzwerk nicht unnötig belastet.

Wenn sich ein Wert geändert hat, wird `sendBooleanOutletsToZigbeeForced()` aufgerufen. Dort werden die virtuellen Steckdosen entsprechend gesetzt:

```cpp
zbPuzzleSolved.setState(puzzleSolved);
zbLdrSolved.setState(ldrSolved);
```

### 9.2 Regelmäßiger Heartbeat

Zusätzlich wird der aktuelle Zustand alle fünf Sekunden erneut gesendet:

```cpp
const unsigned long ZIGBEE_ROUTINE_SEND_INTERVAL_MS = 5000;
```

Dieser regelmäßige Heartbeat macht das System robuster. Auch wenn eine Nachricht verloren geht oder ein Dienst später wieder verbunden wird, wird der aktuelle Zustand spätestens nach wenigen Sekunden erneut übertragen.

---

## 10. Ablauf im `setup()`

Im `setup()` wird das Modul vorbereitet. Der Ablauf ist:

1. Serielle Ausgabe starten
2. Zufallsgenerator initialisieren
3. LED-Pins als Ausgänge setzen
4. LDR-LED vorbereiten
5. Zigbee starten und Verbindung abwarten
6. erste Zielbereiche für die Potentiometer erzeugen
7. Anfangszustand an Zigbee senden
8. Timer für den regelmäßigen Heartbeat starten

Nach dem `setup()` ist der ESP32 bereit für den Spielbetrieb.

---

## 11. Ablauf im `loop()`

Die Hauptschleife übernimmt dauerhaft die eigentliche Arbeit des Moduls. Bei jedem Durchlauf werden mehrere Aufgaben ausgeführt:

1. Der LDR-Sensor wird ausgelesen.
2. Das Potentiometer-Rätsel wird abhängig vom aktuellen Zustand verarbeitet.
3. Die Boolean-Werte werden bei Änderungen an Zigbee gesendet.
4. Alle fünf Sekunden wird der aktuelle Zustand zusätzlich erneut gesendet.

Die Struktur bleibt bewusst einfach. Der ESP32 kümmert sich nur um seine lokale Hardware und meldet dem restlichen System die fertigen Ergebnisse.

---

## 12. Datenfluss

Der Datenfluss dieses Moduls lässt sich so zusammenfassen:

```text
Potentiometer / LDR
        ↓
ESP32 liest Sensorwerte
        ↓
ESP32 wertet die Rätsel lokal aus
        ↓
puzzleSolved / ldrSolved werden gesetzt
        ↓
virtuelle Zigbee-Steckdosen werden aktualisiert
        ↓
Zigbee2MQTT übersetzt die Zustände in MQTT-Nachrichten
        ↓
Flask-Server verarbeitet die Events im Spielzustand
```

Der Server muss also nicht wissen, welche genauen ADC-Werte die Sensoren gerade liefern. Er bekommt nur die Information, ob ein Rätsel gelöst wurde. Das reduziert die Datenmenge und hält die Verantwortlichkeiten klar getrennt.

---

## 13. Technische Einordnung

Der Code folgt dem Grundprinzip der gesamten Systemarchitektur: Hardware-nahe Logik läuft direkt auf dem ESP32, während der zentrale Server den globalen Spielzustand verwaltet.

Der ESP32 #1 ist damit ein eigenständiges Rätselmodul. Er erkennt selbstständig, ob das Frequenz-Rätsel oder das Laser-Rätsel abgeschlossen wurde, gibt den Spielern direktes Feedback über LEDs und sendet die Ergebnisse über Zigbee weiter.

Besonders wichtig ist dabei die Umsetzung der Boolean-Werte als virtuelle Steckdosen. Dadurch kann ein einfaches Ja/Nein-Ergebnis mit Standard-Zigbee-Mechanismen übertragen werden, ohne ein eigenes Kommunikationsformat entwickeln zu müssen.

---

## 14. Wichtige Statusvariablen

| Variable                    | Bedeutung                                                         |
| --------------------------- | ----------------------------------------------------------------- |
| `puzzleSolved`              | Wird `true`, wenn alle drei Potentiometer im Zielbereich liegen   |
| `ldrSolved`                 | Wird `true`, wenn der LDR-Sensor ausreichend Licht erkennt        |
| `blinkState`                | Speichert den aktuellen Blinkzustand während der Erfolgsanimation |
| `currentState`              | Speichert den aktuellen Zustand des Potentiometer-Rätsels         |
| `lastSentPuzzleSolved`      | Merkt sich den zuletzt gesendeten Zustand von `puzzleSolved`      |
| `lastSentLdrSolved`         | Merkt sich den zuletzt gesendeten Zustand von `ldrSolved`         |
| `firstZigbeeSend`           | Sorgt dafür, dass beim Start einmal sicher gesendet wird          |
| `lastZigbeeRoutineSendTime` | Zeitstempel für den regelmäßigen Zigbee-Heartbeat                 |

---

## 15. Zusammenfassung

`Sensor_zigbee.ino` verbindet zwei physische Rätsel in einem ESP32-Programm: das Potentiometer-basierte Frequenz-Rätsel und das Laser-/LDR-Rätsel. Beide Aufgaben werden direkt auf dem Mikrocontroller ausgewertet. Die Spieler erhalten Feedback über LEDs, während der Server nur die fertigen Boolean-Zustände empfängt.

Durch die Darstellung dieser Boolean-Werte als virtuelle Zigbee-Steckdosen fügt sich der Code gut in die restliche Architektur ein. Der Raspberry Pi kann die Zustände über Zigbee2MQTT und MQTT empfangen, ohne die Details der lokalen Sensorauswertung kennen zu müssen.
