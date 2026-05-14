document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    
    const currentAltEl = document.getElementById('current-alt');
    const targetAltEl = document.getElementById('target-alt');
    const warningMsg = document.getElementById('warning-msg');
    const subtitleDisplay = document.getElementById('subtitle-display');
    const canvas = document.getElementById('flightCanvas');
    const ctx = canvas.getContext('2d');

    // Audio and Subtitles
    let currentAudio = null;
    let subtitleTimeouts = [];

    // Resize canvas to match display size
    function resizeCanvas() {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
    }
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // Game config
    const GAME_DURATION_SEC = 120;
    const START_ALT = 8000;
    
    // Physics & Controls
    const PITCH_FACTOR = 20; 
    
    let planeAltitude = START_ALT;
    let targetAltitude = START_ALT;
    let currentPitch = 0; // Negative = nose down, Positive = nose up
    let displayedPitch = 0; // For smooth visual rotation
    
    let isGameRunning = false;
    let startTime = performance.now();
    let lastTime = performance.now();
    let warningActive = false;

    const startScreen = document.getElementById('landing-start-screen');
    const startBtn = document.getElementById('landing-start-btn');

    if (startBtn) {
        startBtn.addEventListener('click', () => {
            if (startScreen) {
                startScreen.style.opacity = '0';
                setTimeout(() => {
                    startScreen.style.display = 'none';
                }, 500);
            }
            
            // Audio erlauben und Server mitteilen, dass wir bereit sind
            socket.emit('landing_ready');
            
            // Spiel starten
            startTime = performance.now();
            lastTime = performance.now();
            isGameRunning = true;
            requestAnimationFrame(gameLoop);
        });
    }

    // Listen for gyro data
    socket.on('cockpit_gyro', (data) => {
        if (!isGameRunning) return;
        currentPitch = data.pitch || 0;
    });

    function showWarning() {
        if (warningActive) return;
        warningActive = true;
        warningMsg.classList.add('active');
        setTimeout(() => {
            warningMsg.classList.remove('active');
            warningActive = false;
        }, 1000);
    }

    // Subtitle sequence handling
    socket.on('play_subtitle_sequence', (data) => {
        subtitleTimeouts.forEach(clearTimeout);
        subtitleTimeouts = [];
        
        if (currentAudio) {
            currentAudio.pause();
            currentAudio.currentTime = 0;
        }

        subtitleDisplay.classList.add('active');
        
        // Play Audio file
        if (data.id) {
            currentAudio = new Audio(`/static/audio/${data.id}.mp3`);
            currentAudio.play().catch(e => console.log("Audio play failed or file missing:", e));
        }
        
        data.sequence.forEach((sub) => {
            let t = setTimeout(() => {
                subtitleDisplay.textContent = sub.text;
                if (sub.text === "") {
                    subtitleDisplay.classList.remove('active');
                }
            }, sub.time);
            subtitleTimeouts.push(t);
        });
    });

    // Helper: Calculate ideal altitude at a given time (in seconds)
    function getIdealAltitude(t) {
        if (t >= GAME_DURATION_SEC) return 0;
        
        // GRACE PERIOD: Bleibe für die ersten 25 Sekunden (während der Funkspruch läuft) auf 8000m
        if (t <= 25) return START_ALT;
        
        const activeDuration = GAME_DURATION_SEC - 25;
        const activeT = t - 25;
        const progress = activeT / activeDuration; // 0 to 1
        const remaining = 1 - progress;
        return START_ALT * (remaining * remaining);
    }

    // Drawing helpers
    function drawPath() {
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(150, 200, 255, 0.5)'; // less neon, muted blue
        ctx.lineWidth = 3;
        
        // Draw the path from x=10% to x=90% of screen
        const startX = canvas.width * 0.1;
        const endX = canvas.width * 0.9;
        const rangeX = endX - startX;

        // Draw points
        const steps = 100;
        for (let i = 0; i <= steps; i++) {
            const t = (i / steps) * GAME_DURATION_SEC;
            const alt = getIdealAltitude(t);
            
            const x = startX + (i / steps) * rangeX;
            // Map altitude 8000->0 to Y 10%->90%
            const yPct = 0.1 + 0.8 * (1 - (alt / START_ALT));
            const y = yPct * canvas.height;

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Draw Tolerance Tunnel
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(150, 200, 255, 0.15)'; // less neon
        ctx.lineWidth = 25; // narrower tunnel visually
        for (let i = 0; i <= steps; i++) {
            const t = (i / steps) * GAME_DURATION_SEC;
            const alt = getIdealAltitude(t);
            const x = startX + (i / steps) * rangeX;
            const yPct = 0.1 + 0.8 * (1 - (alt / START_ALT));
            const y = yPct * canvas.height;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }

    function drawPlane(x, y, pitch) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(-pitch * Math.PI / 180);

        // Plane Body (Fuselage)
        ctx.fillStyle = '#cccccc';
        ctx.beginPath();
        ctx.ellipse(0, 0, 26, 7, 0, 0, Math.PI * 2);
        ctx.fill();

        // Cockpit window
        ctx.fillStyle = '#445566'; 
        ctx.beginPath();
        ctx.moveTo(14, -5);
        ctx.lineTo(20, -4);
        ctx.lineTo(23, -1);
        ctx.lineTo(14, -1);
        ctx.fill();

        // Tail fin
        ctx.fillStyle = '#cccccc';
        ctx.beginPath();
        ctx.moveTo(-12, -4);
        ctx.lineTo(-20, -18);
        ctx.lineTo(-24, -18);
        ctx.lineTo(-24, -4);
        ctx.fill();

        // Main Wing
        ctx.fillStyle = '#999999';
        ctx.beginPath();
        ctx.moveTo(2, 2);
        ctx.lineTo(-6, 16);
        ctx.lineTo(-14, 16);
        ctx.lineTo(-4, 2);
        ctx.fill();

        // Engine Pod
        ctx.fillStyle = '#666666';
        ctx.beginPath();
        ctx.ellipse(-6, 8, 6, 3, 0, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    }

    function gameLoop(timestamp) {
        if (!isGameRunning) return;
        
        const dt = (timestamp - lastTime) / 1000;
        lastTime = timestamp;

        const timeElapsed = (timestamp - startTime) / 1000;
        
        // 1. Update Target
        targetAltitude = getIdealAltitude(timeElapsed);
        
        if (timeElapsed >= GAME_DURATION_SEC) {
            targetAltitude = 0;
            isGameRunning = false;
            winGame();
        }

        // 2. Update Plane Physics
        // Negative pitch = nose down = positive descent rate
        const playerDescentRate = (-currentPitch * PITCH_FACTOR);
        planeAltitude -= playerDescentRate * dt;

        // 3. Collision / Boundaries
        const altDifference = planeAltitude - targetAltitude; // positive = above path
        
        // Tolerance shrinks over time: from 600m to 100m (much narrower)
        const progress = timeElapsed / GAME_DURATION_SEC;
        const currentTolerance = 600 - (500 * progress);

        if (Math.abs(altDifference) > currentTolerance) {
            if (!warningActive) {
                // Penalty: Push the plane further away instead of resetting it to target!
                // Reduziert auf 250m. 800m war größer als die Toleranz, was zu einem 
                // unausweichlichen "Death Spiral" geführt hat (permanente Strafen).
                if (altDifference > 0) {
                    planeAltitude += 250;
                } else {
                    planeAltitude -= 250;
                }
                showWarning();
            }
        }

        // 4. Draw Frame
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Grid (optional, you can draw a custom grid here if you want)

        drawPath();

        // Calculate Plane X and Y on canvas
        const startX = canvas.width * 0.1;
        const endX = canvas.width * 0.9;
        const currentX = startX + progress * (endX - startX);

        // Map altitude: 8000 -> 10% height, 0 -> 90% height
        const planeAltProgress = 1 - (planeAltitude / START_ALT);
        let planeYPct = 0.1 + 0.8 * planeAltProgress;
        planeYPct = Math.max(0.05, Math.min(0.95, planeYPct));
        const planeY = planeYPct * canvas.height;

        // Smooth out the pitch visual rotation using lerp
        displayedPitch += (currentPitch - displayedPitch) * 10 * dt;

        drawPlane(currentX, planeY, displayedPitch);

        // 5. Update HUD
        currentAltEl.textContent = Math.round(planeAltitude);
        targetAltEl.textContent = Math.round(targetAltitude);

        if (isGameRunning) {
            requestAnimationFrame(gameLoop);
        }
    }

    function winGame() {
        const overlay = document.createElement('div');
        overlay.className = 'win-overlay active';
        overlay.textContent = 'TOUCHDOWN';
        document.body.appendChild(overlay);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawPath();
        drawPlane(canvas.width * 0.9, canvas.height * 0.9, 0); // Landed

        // Tell the server we won so it plays the success sequence
        socket.emit('landing_complete');
    }

    // requestAnimationFrame wird nun erst beim Klick auf den Start-Button aufgerufen
    // requestAnimationFrame(gameLoop);
});
