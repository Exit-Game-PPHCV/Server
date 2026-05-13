import time


class GameState:
    def __init__(self):
        # Task-Flags
        self.keypad = False
        self.frequenz = False
        self.temparatur = False
        self.neigung = False
        self.cable = False
        self.laser = False
        self.autopilot = False
        self.temperature_alarm_active = False
        self.cable_count = 0

        # --- Neigung Challenge System ---
        self.neigung_challenge_active = False
        self.neigung_challenge_data = None   # {'axis': 'pitch'|'roll', 'target': int, 'direction': str}
        self.neigung_hold_start = None
        self.last_neigung_challenge_time = 0

        # Timing
        self.last_send_time = 0
        self.last_subtitle_end_time = 0      # Wann die letzte Subtitle-Sequenz endet

        # --- Inaktivitäts-Erkennung ---
        self.last_sensor_receive_time = time.time()

        # Spielende
        self.game_finished = False           # True nach erfolgreicher Landung

        # Sensordaten-Cache
        self.latest_sensor_data = {}


state = GameState()
