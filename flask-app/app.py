from flask import Flask, render_template, request, jsonify
app = Flask(__name__)

@app.route("/")
def helloWorld():
    return render_template("index.html")
@app.route("/game")
def game():
    return render_template("game.html")
@app.route('/game-complete', methods=['POST'])
def game_complete():
    data = request.get_json()
    print(f"Erfolg: Task {data.get('task')} abgeschlossen.")
    return jsonify({"status": "success", "received": data}), 200