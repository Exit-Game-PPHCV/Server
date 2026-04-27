const socket = io();

const pitchEl = document.getElementById('pitch');
const rollEl = document.getElementById('roll');
const infoEl = document.getElementById('info');
const valuesEl = document.getElementById('values');
let isRunning = false;

function handleOrientation(event) {
    let pitch = Math.round(event.beta || 0);
    let roll = Math.round(event.gamma || 0);

    pitchEl.textContent = pitch;
    rollEl.textContent = roll;

    socket.emit('sensor_data', {
        pitch: pitch,
        roll: roll
    });
}

function startSensor() {
    if (isRunning) return;

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