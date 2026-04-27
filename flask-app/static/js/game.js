const colors = ['#FF4136', '#0074D9', '#FFDC00', '#2ECC40'];
const gameBoard = document.getElementById('game-board');
const svgCanvas = document.getElementById('svg-canvas');
let activeLine = null;
let connections = 0;

// Initialisierung
function initGame() {
    const leftNodes = document.getElementById('left-nodes');
    const rightNodes = document.getElementById('right-nodes');
    const shuffledColors = [...colors].sort(() => Math.random() - 0.5);

    colors.forEach((color, i) => {
        const left = createNode(color, 'left');
        const right = createNode(shuffledColors[i], 'right');
        leftNodes.appendChild(left);
        rightNodes.appendChild(right);
    });
}

function createNode(color, side) {
    const div = document.createElement('div');
    div.className = `node ${side}-node`;
    div.style.backgroundColor = color;
    div.dataset.color = color;
    if (side === 'left') {
        div.onmousedown = (e) => startLine(e, color, div);
    }
    return div;
}

function getPos(el) {
    const rect = el.getBoundingClientRect();
    const board = gameBoard.getBoundingClientRect();
    return {
        x: rect.left - board.left + rect.width / 2,
        y: rect.top - board.top + rect.height / 2
    };
}

function startLine(e, color, node) {
    if (node.dataset.connected) return;
    const pos = getPos(node);
    activeLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
    activeLine.setAttribute('x1', pos.x);
    activeLine.setAttribute('y1', pos.y);
    activeLine.setAttribute('x2', pos.x);
    activeLine.setAttribute('y2', pos.y);
    activeLine.setAttribute('stroke', color);
    activeLine.setAttribute('stroke-width', '10');
    activeLine.dataset.color = color;
    svgCanvas.appendChild(activeLine);

    const move = (ev) => {
        const b = gameBoard.getBoundingClientRect();
        activeLine.setAttribute('x2', ev.clientX - b.left);
        activeLine.setAttribute('y2', ev.clientY - b.top);
    };

    const up = (ev) => {
        window.removeEventListener('mousemove', move);
        window.removeEventListener('mouseup', up);
        
        activeLine.style.display = 'none';
        const target = document.elementFromPoint(ev.clientX, ev.clientY);
        activeLine.style.display = 'block';

        if (target && target.classList.contains('right-node') && target.dataset.color === color) {
            const end = getPos(target);
            activeLine.setAttribute('x2', end.x);
            activeLine.setAttribute('y2', end.y);
            node.dataset.connected = true;
            target.dataset.connected = true;
            connections++;
            if (connections === colors.length) finishGame();
        } else {
            svgCanvas.removeChild(activeLine);
        }
        activeLine = null;
    };

    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
}

function finishGame() {
    // Server benachrichtigen
    fetch('/game-complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: 'wires', status: 'complete' })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            document.getElementById('win-message').style.display = 'block';
            console.log("Gesamt-Task erfolgreich abgeschlossen!");
        } else if (data.status === 'progress') {
            console.log(`Durchlauf ${data.count}/3 erfolgreich. Starte nächsten Durchlauf...`);
            // Board zurücksetzen für nächste Runde
            setTimeout(() => {
                svgCanvas.innerHTML = '';
                document.getElementById('left-nodes').innerHTML = '';
                document.getElementById('right-nodes').innerHTML = '';
                connections = 0;
                initGame();
            }, 500);
        }
    });
}
document.addEventListener('DOMContentLoaded', () => {
    if (gameBoard.dataset.done === 'true') {
        document.getElementById('win-message').style.display = 'block';
    } else {
        initGame();
    }
})
