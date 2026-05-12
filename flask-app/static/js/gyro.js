const socket = io();

const pitchEl = document.getElementById('pitch');
const rollEl = document.getElementById('roll');
const infoEl = document.getElementById('info');
const valuesEl = document.getElementById('values');
let isRunning = false;

let lastEmitTime = 0;

function handleOrientation(event) {
    const now = Date.now();
    if (now - lastEmitTime < 100) return;
    lastEmitTime = now;

    let pitch = Math.round(event.beta || 0);
    let roll = Math.round(event.gamma || 0);

    pitchEl.textContent = pitch;
    rollEl.textContent = roll;

    socket.emit('sensor_data', {
        pitch: roll,
        roll: pitch
    });
}

function startSensor() {
    if (isRunning) return;

    // Versuche Vollbild und Landscape-Lock (funktioniert auf vielen mobilen Browsern)
    try {
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().then(() => {
                if (screen.orientation && screen.orientation.lock) {
                    screen.orientation.lock('landscape').catch(console.warn);
                }
            }).catch(console.warn);
        }
    } catch (e) {
        console.warn("Fullscreen/Orientation API nicht verfügbar", e);
    }
    
    if (typeof DeviceOrientationEvent.requestPermission === 'function') {
        DeviceOrientationEvent.requestPermission()
            .then(permissionState => {
                if (permissionState === 'granted') {
                    window.addEventListener('deviceorientation', handleOrientation);
                    showValues();
                } else {
                    infoEl.textContent = "Zugriff verweigert.";
                }
            })
            .catch(console.error);
    } else {
        window.addEventListener('deviceorientation', handleOrientation);
        showValues();
    }
}

function showValues() {
    isRunning = true;
    infoEl.style.display = 'none';
    valuesEl.style.display = 'flex';
}

document.body.addEventListener('click', startSensor);