from flask import Flask, render_template, redirect, url_for, send_from_directory
from flask_login import LoginManager, current_user
from models import db, User
from routes.chat import chat_bp
from routes.auth import auth_bp
import secrets
import os

app = Flask(__name__)
app.config['SECRET_KEY']           = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI']  = 'sqlite:///dejavu.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Init extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth_page'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Serve /assets/ folder
@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(os.path.join(app.root_path, 'assets'), filename)

# Register blueprints
app.register_blueprint(chat_bp)
app.register_blueprint(auth_bp)

# ── Page routes ─────────────────────────────────────────────────────────────

@app.route("/")
def splash():
    return render_template("splash.html")

@app.route("/auth")
def auth_page():
    return render_template("auth.html")

@app.route("/chat")
def chat():
    return render_template("index.html")

@app.route("/insights")
def insights():
    return render_template("insights.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/memory")
def memory_editor():
    return render_template("memory_editor.html")

@app.route("/legal")
def legal():
    return render_template("legal.html")

@app.route("/reminders")
def reminders():
    return render_template("reminders.html")

# ── DB init ───────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    os.makedirs('memory', exist_ok=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
