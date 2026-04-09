from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)   # None for guests
    is_guest      = db.Column(db.Boolean, default=False)
    persona       = db.Column(db.String(40), default='friend')  # tutor/friend/coach/formal
    is_verified   = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return self.password_hash and check_password_hash(self.password_hash, password)

    def memory_path(self):
        return f"memory/user_{self.id}.json"

    def conflicts_path(self):
        return f"memory/conflicts_{self.id}.json"

    def reminders_path(self):
        return f"memory/reminders_{self.id}.json"

    def chats_path(self):
        return f"memory/chats_{self.id}.json"

    def __repr__(self):
        return f"<User {self.username}>"
