import time

from extensions import socketio
from game_state import state


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
        {"time": 33000, "text": "Und als wäre das nicht genug: Die Kiste kippt uns weg!"},
        {"time": 37000, "text": "Schau auf das Modellflugzeug vor dir."},
        {"time": 40000, "text": "Nimm das Handy als Steuerknüppel und bring die Flügel sofort wieder in die Waagerechte."},
        {"time": 45000, "text": "Erst wenn das Modell gerade steht und die 'Stable'-LED leuchtet, haben wir wieder eine stabile Fluglage."},
        {"time": 50500, "text": "Halt uns stabil, während wir versuchen, die Systeme nacheinander zu flicken."},
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
    if state.keypad:
        return "landing_task"
    if state.frequenz:
        return "keypad_task"
    if state.laser:
        return "antenna_task"
    if state.cable:
        return "laser_task"
    if state.neigung and state.temparatur:
        return "cable_task"
    return "intro"


def emit_subtitle(seq_id):
    """Emittiert eine Subtitle-Sequenz und setzt den Cooldown-Timer."""
    sequence = SUBTITLES[seq_id]
    # Berechne wann die Sequenz endet (letzter Subtitle-Zeitpunkt)
    max_time = max(s['time'] for s in sequence) if sequence else 0
    state.last_subtitle_end_time = time.time() + (max_time / 1000.0)
    socketio.emit('play_subtitle_sequence', {'sequence': sequence, 'id': seq_id})
