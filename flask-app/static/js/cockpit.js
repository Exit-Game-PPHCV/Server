document.addEventListener('DOMContentLoaded', () => {
    const aiInner = document.querySelector('.ai-inner');
    const tempStatus = document.getElementById('temp-status');
    const altValue = document.getElementById('alt-value');
    const speedValue = document.getElementById('speed-value');

    // UI Elements
    const autopilotIndicator = document.getElementById('autopilot-indicator');
    const radioDisplay = document.querySelector('.radio-display');
    const tipDisplay = document.getElementById('tip-display');
    const radioPanel = document.getElementById('radio-panel');

    let currentRoll = 0;
    let currentPitch = 0;
    let richtigefrequenz = "121.950";
    let standardfrequenz = "121.500";
    let currentAlt = 32000;
    let currentSpeed = 450;
    let lastTime = Date.now();
    
    let isCableSolved = false;
    let isGyroSolved = false;
    let isAnnouncing = false;
    let isAlarmActive = false;
    let subtitleTimeouts = [];
    let currentAudio = null;
    let alarmAudio = null;

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
        // Temperature parsing is no longer needed here since we use pure status updates
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

        // Sync Temperature Alarm
        setAlarmUI(data.temperature_alarm_active || false);

        // Sync Game Task Status
        if (data.cable_task_complete) {
            isCableSolved = true;
            const gameContainer = document.querySelector('.game-container');
            if (gameContainer) {
                gameContainer.style.borderColor = '#00ff44';
                gameContainer.style.boxShadow = '0 0 15px #00ff44';
            }
        }
        
        isGyroSolved = data.gyro_task_complete || false;
        
        updateUIState();

        // Sync Sensor Data (temperature parsing removed)
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
            isCableSolved = true;
            const gameContainer = document.querySelector('.game-container');
            gameContainer.style.borderColor = '#00ff44';
            gameContainer.style.boxShadow = '0 0 15px #00ff44';
            document.body.classList.remove('restricted-mode');
        }
    });

    // --- Temperature Alarm ---
    function setAlarmUI(active) {
        isAlarmActive = active;
        if (active) {
            document.body.classList.add('temp-alarm-active');
            if (tempStatus) tempStatus.textContent = "CRITICAL";
            // Start alarm sound loop (placeholder: static/audio/temperature_alarm.mp3)
            if (!alarmAudio) {
                alarmAudio = new Audio('/static/audio/temperature_alarm.mp3');
                alarmAudio.loop = true;
                alarmAudio.volume = 0.6;
            }
            alarmAudio.play().catch(e => console.log('Alarm audio failed:', e));
        } else {
            document.body.classList.remove('temp-alarm-active');
            if (tempStatus) {
                tempStatus.textContent = "OK";
                tempStatus.style.color = "#4caf50";
            }
            if (alarmAudio) {
                alarmAudio.pause();
                alarmAudio.currentTime = 0;
            }
        }
    }

    socket.on('temperature_alarm', (data) => {
        setAlarmUI(data.active);
    });

    // --- Neigung Challenge ---
    const neigungOverlay = document.getElementById('neigung-overlay');
    const neigungArrow = document.getElementById('neigung-arrow');
    const neigungBar = document.getElementById('neigung-bar');
    let neigungAudio = null;
    const ARROW_MAP = { up: '↑', down: '↓', left: '←', right: '→' };

    socket.on('neigung_challenge', (data) => {
        neigungArrow.textContent = ARROW_MAP[data.direction] || '?';
        neigungBar.style.width = '0%';
        neigungOverlay.classList.add('active');
        // Light alarm sound (placeholder: static/audio/neigung_alarm.mp3)
        if (!neigungAudio) {
            neigungAudio = new Audio('/static/audio/neigung_alarm.mp3');
            neigungAudio.loop = true;
            neigungAudio.volume = 0.3;
        }
        neigungAudio.play().catch(e => console.log('Neigung audio failed:', e));
    });

    socket.on('neigung_progress', (data) => {
        neigungBar.style.width = (data.progress * 100) + '%';
    });

    socket.on('neigung_challenge_complete', () => {
        neigungOverlay.classList.remove('active');
        neigungBar.style.width = '0%';
        if (neigungAudio) {
            neigungAudio.pause();
            neigungAudio.currentTime = 0;
        }
    });

    function updateUIState() {
        if (isGyroSolved) {
            document.body.classList.remove('restricted-mode');
        } else {
            document.body.classList.add('restricted-mode');
        }
        
        if (isAnnouncing) {
            document.body.classList.add('announcing');
        } else {
            document.body.classList.remove('announcing');
        }
    }

    // Subtitle sequence handling
    socket.on('play_subtitle_sequence', (data) => {
        subtitleTimeouts.forEach(clearTimeout);
        subtitleTimeouts = [];
        
        if (currentAudio) {
            currentAudio.pause();
            currentAudio.currentTime = 0;
        }

        isAnnouncing = true;
        updateUIState();

        tipDisplay.classList.add('subtitle-active');
        
        // Play Audio file
        if (data.id) {
            currentAudio = new Audio(`/static/audio/${data.id}.mp3`);
            currentAudio.play().catch(e => console.log("Audio play failed or file missing:", e));
        }
        
        data.sequence.forEach((sub) => {
            let t = setTimeout(() => {
                tipDisplay.textContent = sub.text;
                if (sub.text === "") {
                    // Sequence ended
                    isAnnouncing = false;
                    updateUIState();
                    tipDisplay.classList.remove('subtitle-active');
                    tipDisplay.textContent = "SYSTEM ONLINE: AWAITING DATA...";
                }
            }, sub.time);
            subtitleTimeouts.push(t);
        });
    });

    if (radioPanel) {
        radioPanel.addEventListener('click', () => {
            if (!isAnnouncing) {
                socket.emit('repeat_transmission');
            }
        });
    }

    socket.on('start_landing_sequence', () => {
        window.location.href = '/landing';
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
