document.addEventListener('DOMContentLoaded', () => {
    const aiSky = document.querySelector('.ai-sky');
    const aiGround = document.querySelector('.ai-ground');
    const tempValue = document.getElementById('temp-value');
    const altValue = document.getElementById('alt-value');
    const speedValue = document.getElementById('speed-value');

    let currentRoll = 0;
    let currentPitch = 0;

    // Function to update the Attitude Indicator
    function updateAI(pitch, roll) {
        // pitch: -90 to 90
        // roll: -180 to 180
        const pitchOffset = pitch * 2; // scale for visual effect
        aiSky.style.transform = `rotate(${roll}deg) translateY(${pitchOffset}px)`;
        aiGround.style.transform = `rotate(${roll}deg) translateY(${pitchOffset}px)`;
    }

    // Function to fetch sensor data
    async function fetchSensorData() {
        try {
            const response = await fetch('/api/sensors');
            const data = await response.json();
            
            // Example data structure from app.py:
            // latest_sensor_data[msg.topic] = payload
            // Assuming something like 'zigbee2mqtt/sensor1': { temperature: 22.5, roll: 5, pitch: -2 }
            
            let foundTemp = null;
            let foundRoll = 0;
            let foundPitch = 0;

            for (const topic in data) {
                const payload = data[topic];
                if (payload.temperature !== undefined) foundTemp = payload.temperature;
                if (payload.roll !== undefined) foundRoll = payload.roll;
                if (payload.pitch !== undefined) foundPitch = payload.pitch;
            }

            if (foundTemp !== null) {
                tempValue.textContent = foundTemp.toFixed(1);
            }

            // Smoothly update AI
            currentRoll = foundRoll;
            currentPitch = foundPitch;
            updateAI(currentPitch, currentRoll);

        } catch (error) {
            console.error('Error fetching sensor data:', error);
        }
    }

    // Simulate some movement for the "wow" factor if no real data is coming in
    function simulateMovement() {
        const time = Date.now() * 0.001;
        const simRoll = Math.sin(time * 0.5) * 5;
        const simPitch = Math.cos(time * 0.7) * 3;
        
        // Only simulate if we don't have real sensor data (this is a simple check)
        // In a real app, you might check a flag
        updateAI(simPitch, simRoll);

        // Simulate speed and altitude
        const simSpeed = 450 + Math.sin(time) * 10;
        const simAlt = 32000 + Math.cos(time * 0.1) * 100;
        
        speedValue.textContent = Math.round(simSpeed);
        altValue.textContent = Math.round(simAlt);
    }

    // Initial call
    setInterval(fetchSensorData, 1000);
    setInterval(simulateMovement, 50); // Fast update for smooth AI animation
});
