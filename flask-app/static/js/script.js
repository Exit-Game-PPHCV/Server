const div = document.createElement('div')
async function getProgress() {
    await fetch('/getProgress', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    })
}
const progress = getProgress();
div.innerHTML = progress;