from flask import Flask, render_template
from routes.chat import chat_bp

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(chat_bp)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
