document.addEventListener('DOMContentLoaded', () => {
    const aiInner = document.querySelector('.ai-inner');
    const tempValue = document.getElementById('temp-value');
    const altValue = document.getElementById('alt-value');
    const speedValue = document.getElementById('speed-value');

    // UI Elements
    const potiSlider = document.getElementById('potentiometer');
    const potiValueDisplay = document.getElementById('poti-value');
    const pinButtons = document.querySelectorAll('.pin-btn');

    let currentRoll = 0;
    let currentPitch = 0;
    
    // Initial conditions for the crash scenario
    let currentAlt = 32000;
    let currentSpeed = 450;
    let lastTime = Date.now();

    // Connect to WebSocket
    const socket = io();

    // Function to update the Attitude Indicator
    function updateAI(pitch, roll) {
        // Explicitly clamp visual pitch to realistic limits to prevent over-rotation UI bugs
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
        // If a pinpad key is received via MQTT, light up the corresponding button
        if (payload && payload.key !== undefined) {
            const keyStr = payload.key.toString();
            pinButtons.forEach(btn => {
                if (btn.textContent === keyStr) {
                    btn.style.backgroundColor = '#4caf50';
                    setTimeout(() => btn.style.backgroundColor = '', 300);
                }
            });
        }
        // If a potentiometer value is received
        if (payload && payload.potentiometer !== undefined) {
            potiSlider.value = payload.potentiometer;
            potiValueDisplay.textContent = payload.potentiometer;
        }
    });

    // --- UI Interactions (Visual Only) ---

    // The webpage is purely visual now. User cannot change sliders/buttons to emit.
    potiSlider.disabled = true; 

    // Simulate the crash scenario (decreasing altitude and speed)
    function simulateMovement() {
        const now = Date.now();
        const deltaTime = (now - lastTime) / 1000; // in seconds
        lastTime = now;
        
        // Speed decreases by ~2 knots per second, Altitude by ~50 ft per second
        // They won't hit exactly 0 quickly, but will trend downwards.
        if (currentSpeed > 150) currentSpeed -= 2 * deltaTime;
        if (currentAlt > 1000) currentAlt -= 80 * deltaTime;
        
        // Add a slight jitter/wobble to simulate turbulence during crash
        const jitterAlt = Math.sin(now * 0.01) * 20;
        const jitterSpeed = Math.cos(now * 0.05) * 2;

        speedValue.textContent = Math.round(currentSpeed + jitterSpeed);
        altValue.textContent = Math.round(currentAlt + jitterAlt);
    }

    // Initial call
    setInterval(simulateMovement, 50); // Fast update for smooth animation
});
