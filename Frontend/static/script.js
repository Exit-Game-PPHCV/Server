// DOM Elemente
const displayMessage = document.getElementById('display-message');
const codeInput = document.getElementById('code-input');
const submitBtn = document.getElementById('submit-btn');
const hintBtn = document.getElementById('hint-btn');
const timerDisplay = document.getElementById('timer');

// Visueller Timer (Reine Anzeige, ohne Game-Over-Logik)
let timeLeft = 3600; // 60 Minuten Startwert in Sekunden

function startVisualTimer() {
    setInterval(() => {
        if (timeLeft <= 0) return;
        
        timeLeft--;
        let minutes = Math.floor(timeLeft / 60);
        let seconds = timeLeft % 60;
        
        // Formatierung auf MM:SS
        timerDisplay.innerText = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
}

// Platzhalter-Funktion für die Code-Eingabe
function handleInput() {
    const userCode = codeInput.value.trim().toUpperCase();
    
    if (userCode === "") return;
    
    // Optisches Feedback für das UI
    displayMessage.innerHTML = `> VERARBEITE EINGABE: ${userCode}...<br>> WARTE AUF SERVER-ANTWORT...`;
    
    // Feld leeren
    codeInput.value = '';
}

// Platzhalter-Funktion für den Hilfe-Knopf
function showDummyHint() {
    displayMessage.innerHTML = `> EINGEHENDE TRANSMISSION...<br>> DATEN WERDEN GELADEN...`;
}

// Event Listener verknüpfen
submitBtn.addEventListener('click', handleInput);
hintBtn.addEventListener('click', showDummyHint);

// Erlaubt das Bestätigen mit der Enter-Taste im Eingabefeld
codeInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        handleInput();
    }
});

// UI beim Laden der Seite initialisieren
startVisualTimer();