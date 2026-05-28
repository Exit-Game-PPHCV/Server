# Testanleitung (Flight Simulator Exit Game)

Dieses Dokument beschreibt, wie das Exit Game für ein schnelles Durchspielen und Testen zu Hause aufgesetzt wird. Dabei wird die originale Infrastruktur (Docker, Traefik, HTTPS) genutzt, auch wenn die physischen Sensoren und der Raspberry Pi nicht vorhanden sind.

---

## 1. Lokales Testing mit Docker Compose (Ohne Hardware)

Das gesamte System kann lokal auf einem Laptop/PC hochgefahren werden. Die fehlende Hardware wird dabei über den Browser simuliert.

**Voraussetzungen:** 
- Docker und Docker Compose sind auf dem ausführenden PC installiert.
- Das Repository ist lokal heruntergeladen.

### Schritt 1: Lokale IP-Adresse konfigurieren
Damit die Geräte untereinander kommunizieren können, muss der DNS-Server auf den lokalen PC gelenkt werden.
1. Die lokale (WLAN-) IP-Adresse des Laptops herausfinden (unter Windows: `ipconfig` -> IPv4-Adresse).
2. Die Datei `dnsmasq/dnsmasq.conf` in einem Texteditor öffnen.
3. Die IP-Adresse in der Datei durch die zuvor ermittelte IP-Adresse ersetzen:
   ```text
   address=/exit.game/LOKALE.IP.ADRESSE.HIER
   ```

### Schritt 2: Docker Container starten
Starten der gesamten Server-Architektur:
1. Ein Terminal im Projektordner (`Exit Game`) öffnen.
2. Folgenden Befehl ausführen:
   ```bash
   docker compose up -d --build
   ```
*Hinweis:* Wenn kein Zigbee-Dongle am PC eingesteckt ist, wird der Container `zigbee2mqtt` in einer Schleife abstürzen. **Das ist bei der lokalen Simulation normal und kann ignoriert werden.** Alle anderen Container (Flask, Traefik, Mosquitto, dnsmasq) laufen problemlos weiter.

### Schritt 3: DNS-Server am PC / Smartphone einrichten (Optional)
Damit die Domain `flask.exit.game` auf den PC weiterleitet, kann den Endgeräten mitgeteilt werden, dass sie den lokalen DNS-Container nutzen sollen. **Dieser Schritt ist nicht zwingend notwendig.** Das Spiel kann auch direkt über die IP-Adresse des Laptops aufgerufen werden.

*Falls die Domain genutzt werden soll:*
- **Am PC & Smartphone:** In den WLAN-Einstellungen der aktiven Verbindung den DNS-Server manuell auf die IP-Adresse des Laptops ändern (die gleiche IP aus Schritt 1).
- *(Alternative nur für den PC)*: Den Eintrag `127.0.0.1 flask.exit.game` in der Windows `hosts`-Datei (`C:\Windows\System32\drivers\etc\hosts`) ergänzen.

### Schritt 4: Spielen und Hardware simulieren
Da keine echten Hardware-Sensoren verbunden sind, müssen die Rätsel simuliert werden:

1. **Dashboard öffnen:** Entweder `https://flask.exit.game/` (falls Schritt 3 durchgeführt wurde) oder einfach direkt `http://LOKALE-IP:5000/` am Laptop aufrufen. 
2. **Events simulieren:** In einem neuen Browser-Tab `/test` aufrufen (also z.B. `http://LOKALE-IP:5000/test`). Hier kann auf die entsprechenden Buttons (z.B. "Temperaturalarm auslösen" oder "Poti gelöst") geklickt werden, wenn ein Rätsel laut Dashboard gefordert ist. Dies simuliert die MQTT-Events, die sonst von der Hardware kommen.
3. **Flugzeug-Steuerung (Gyro):** Die Route `/gyro` auf dem **Smartphone** öffnen (welches sich im selben WLAN befinden muss). 
   *Hinweis:* Ohne die DNS-Einrichtung (und das damit verbundene Traefik-HTTPS) blockieren mobile Browser oft das Gyroskop. Für einfache Tests kann das Flugzeug auch am Desktop-PC gesteuert werden, indem die Neigung über die Browser-Entwicklertools simuliert wird.

---

## 2. Übersicht der Routen (Endpoints)

Die Flask-App stellt folgende Hauptrouten zur Verfügung:
- `/` – Das Cockpit-Dashboard (Hauptansicht für den Laptop). Hier laufen die Story und die visuellen Rätsel ab.
- `/gyro` – Die Gyroskop-Steuerung (für das Smartphone). Erfasst Neigungsdaten und sendet sie an den Server.
- `/game` – Das Kabel-Minispiel (wird als Iframe in das Dashboard geladen).
- `/test` – Ein versteckter Endpunkt, um Hardware-Events manuell über den Browser auszulösen (Ersatz für die fehlenden ESP32-Sensoren).
