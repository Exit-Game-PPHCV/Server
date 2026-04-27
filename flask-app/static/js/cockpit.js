document.addEventListener('DOMContentLoaded', () => {
    const aiInner = document.querySelector('.ai-inner');
    const tempValue = document.getElementById('temp-value');
    const altValue = document.getElementById('alt-value');
    const speedValue = document.getElementById('speed-value');

    // UI Elements
    const autopilotIndicator = document.getElementById('autopilot-indicator');
    const radioDisplay = document.querySelector('.radio-display');

    let currentRoll = 0;
    let currentPitch = 0;
    let richtigefrequenz = "121.950";
    let standardfrequenz = "121.500";
    let currentAlt = 32000;
    let currentSpeed = 450;
    let lastTime = Date.now();

    const socket = io();

    function updateAI(pitch, roll) {
        const clampedPitch = Math.max(-45, Math.min(45, roll));

        const pitchOffset = clampedPitch * 1.5;
        aiInner.style.transform = `rotate(${pitch}deg) translateY(${pitchOffset}px)`;
    }

    socket.on('cockpit_gyro', (data) => {
        currentPitch = data.pitch || 0;
        currentRoll = data.roll || 0;
        updateAI(currentPitch, currentRoll);
    });

    // Listen for MQTT Data
    socket.on('mqtt_update', (msg) => {
        const payload = msg.data;
        if (payload && payload.temperature !== undefined) {
            tempValue.textContent = payload.temperature.toFixed(1);
        }
    });

    // Helper to update autopilot UI
    function setAutopilotUI(status) {
        if (status) {
            autopilotIndicator.textContent = "ON";
            autopilotIndicator.classList.add('active');
        } else {
            autopilotIndicator.textContent = "OFF";
            autopilotIndicator.classList.remove('active');
        }
    }

    // Helper to update radio UI
    function setRadioUI(isCorrect) {
        if (radioDisplay) {
            radioDisplay.textContent = isCorrect ? richtigefrequenz : standardfrequenz;
            if (isCorrect) {
                radioDisplay.style.color = '#00ffcc';
                radioDisplay.style.textShadow = '0 0 10px #00ffcc';
            } else {
                radioDisplay.style.color = '';
                radioDisplay.style.textShadow = '';
            }
        }
    }

    // Listen for Initial State on Connect
    socket.on('initial_state', (data) => {
        // Sync Autopilot
        setAutopilotUI(data.autopilot);

        // Sync Radio Frequency
        setRadioUI(data.frequenz);

        // Sync Game Task Status
        if (data.cable_task_complete) {
            const gameContainer = document.querySelector('.game-container');
            if (gameContainer) {
                gameContainer.style.borderColor = '#00ff44';
                gameContainer.style.boxShadow = '0 0 15px #00ff44';
            }
        }

        // Sync Sensor Data (look for temperature in any received topic)
        if (data.sensors) {
            for (const topic in data.sensors) {
                const payload = data.sensors[topic];
                if (payload && payload.temperature !== undefined) {
                    tempValue.textContent = payload.temperature.toFixed(1);
                }
            }
        }
    });

    // Listen for Autopilot Updates
    socket.on('autopilot_update', (data) => {
        setAutopilotUI(data.status);
    });

    // Listen for Frequency Updates
    socket.on('frequenz_update', (data) => {
        setRadioUI(data.frequenz);
    });

    // Listen for Task Completion
    socket.on('task_update', (data) => {
        if (data.task === 'wires' && data.status === 'complete') {
            const gameContainer = document.querySelector('.game-container');
            gameContainer.style.borderColor = '#00ff44';
            gameContainer.style.boxShadow = '0 0 15px #00ff44';
        }
    });

    function simulateMovement() {
        const now = Date.now();
        const deltaTime = (now - lastTime) / 1000; // in seconds
        lastTime = now;

        if (currentSpeed > 150) currentSpeed -= 1 * deltaTime;
        if (currentAlt > 15000) currentAlt -= 80 * deltaTime;

        // Add a slight jitter/wobble to simulate turbulence during crash
        const jitterAlt = Math.sin(now * 0.01) * 20;
        const jitterSpeed = Math.cos(now * 0.05) * 2;

        speedValue.textContent = Math.round(currentSpeed + jitterSpeed);
        altValue.textContent = Math.round(currentAlt + jitterAlt);
    }

    // Initial call
    setInterval(simulateMovement, 50);
});
