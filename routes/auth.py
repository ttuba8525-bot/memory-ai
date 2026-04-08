import json
import os
from flask import Blueprint, request, jsonify, session, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'All fields required'}), 400

    if User.query.filter((User.email == email) | (User.username == username)).first():
        return jsonify({'error': 'Email or username already taken'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)
    _ensure_memory_dir(user)
    return jsonify({'ok': True, 'user': user.username})


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    login_user(user, remember=True)
    return jsonify({'ok': True, 'user': user.username})


@auth_bp.route('/auth/guest', methods=['POST'])
def guest():
    import uuid
    uid = str(uuid.uuid4())[:8]
    user = User(username=f'guest_{uid}', email=f'{uid}@guest.local', is_guest=True)
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=False)
    _ensure_memory_dir(user)
    return jsonify({'ok': True, 'user': user.username})


@auth_bp.route('/auth/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth_page'))


@auth_bp.route('/auth/me')
def me():
    if current_user.is_authenticated:
        return jsonify({
            'user': current_user.username,
            'email': current_user.email,
            'persona': current_user.persona,
            'is_guest': current_user.is_guest,
            'created_at': current_user.created_at.isoformat()
        })
    return jsonify({'user': None}), 401


def _ensure_memory_dir(user):
    os.makedirs('memory', exist_ok=True)
