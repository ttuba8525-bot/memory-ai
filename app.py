from flask import Flask, render_template, redirect, url_for, send_from_directory
from flask_login import LoginManager, current_user
from models import db, User
from routes.chat import chat_bp
from routes.auth import auth_bp
import secrets
import os

app = Flask(__name__)
app.config['SECRET_KEY']              = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dejavu.db'
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

from flask_login import login_required

@app.route("/")
def splash():
    return render_template("splash.html")

@app.route("/auth")
def auth_page():
    return render_template("auth.html")

@app.route("/chat")
@login_required
def chat():
    return render_template("index.html")

@app.route("/insights")
@login_required
def insights():
    return render_template("insights.html")

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

@app.route("/memory")
@login_required
def memory_editor():
    return render_template("memory_editor.html")

@app.route("/legal")
def legal():
    return render_template("legal.html")

@app.route("/reminders")
@login_required
def reminders():
    return render_template("reminders.html")

# ── DB + directories init ─────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    os.makedirs('memory', exist_ok=True)

# ── Background scheduler (decay + consolidation) ──────────────────────────────

def _run_decay_all():
    """Apply memory decay to all user memory files."""
    try:
        from memory.store import MemoryStore
        from memory.decay import process_decay
        mem_dir = os.path.join(os.path.dirname(__file__), 'memory')
        for fname in os.listdir(mem_dir):
            if fname.startswith('user_') and fname.endswith('.json'):
                path = os.path.join(mem_dir, fname)
                store = MemoryStore(path)
                process_decay(store)
        print("[Scheduler] Decay cycle complete.")
    except Exception as e:
        print(f"[Scheduler] Decay failed: {e}")

def _run_consolidation_all():
    """Run consolidation agent on all user memory files."""
    try:
        from memory.store import MemoryStore
        from agents.consolidation_agent import run_consolidation
        mem_dir = os.path.join(os.path.dirname(__file__), 'memory')
        for fname in os.listdir(mem_dir):
            if fname.startswith('user_') and fname.endswith('.json'):
                path = os.path.join(mem_dir, fname)
                store = MemoryStore(path)
                run_consolidation(store)
        print("[Scheduler] Consolidation cycle complete.")
    except Exception as e:
        print(f"[Scheduler] Consolidation failed: {e}")

def _run_reminders_all():
    """Check all users for pending reminders and send emails."""
    try:
        from models import User
        from utils.email_sender import send_reminder_email
        from datetime import datetime
        import json
        
        with app.app_context():
            users = User.query.all()
            now = datetime.utcnow()
            for user in users:
                if not user.email or user.is_guest:
                    continue
                
                reminders_path = user.reminders_path()
                if not os.path.exists(reminders_path):
                    continue
                    
                try:
                    with open(reminders_path, 'r') as f:
                        reminders = json.load(f)
                except Exception:
                    continue
                    
                changed = False
                for r in reminders:
                    if not r.get("done"):
                        try:
                            t_str = r["remind_at"].replace("Z", "+00:00").replace("+00:00", "").split(".")[0]
                            t = datetime.fromisoformat(t_str)
                            if t <= now:
                                # Send the email!
                                if send_reminder_email(user.email, r["text"]):
                                    r["done"] = True
                                    changed = True
                        except Exception as ex:
                            print(f"[Scheduler] Error parsing reminder date: {ex}")
                            
                if changed:
                    with open(reminders_path, 'w') as f:
                        json.dump(reminders, f, indent=2)
                    
        # print("[Scheduler] Reminder check cycle complete.")
    except Exception as e:
        print(f"[Scheduler] Reminder check failed: {e}")

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(daemon=True)
    # Decay: every day at 02:00
    scheduler.add_job(_run_decay_all,        'cron', hour=2,  minute=0,  id='decay')
    # Consolidation: every day at 03:00
    scheduler.add_job(_run_consolidation_all, 'cron', hour=3,  minute=0,  id='consolidation')
    # Reminders: every minute
    scheduler.add_job(_run_reminders_all, 'interval', minutes=1, id='reminders')
    scheduler.start()
    print("[Scheduler] Memory decay, consolidation & reminders jobs scheduled.")
except Exception as e:
    print(f"[Scheduler] Could not start: {e}")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
