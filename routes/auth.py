import json
import os
from flask import Blueprint, request, jsonify, session, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
import secrets
from utils.email_sender import send_verification_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'All fields required'}), 400

    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long'}), 400

    if User.query.filter((User.email == email) | (User.username == username)).first():
        return jsonify({'error': 'Email or username already taken'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    user.verification_token = secrets.token_urlsafe(32)
    user.is_verified = False
    db.session.add(user)
    db.session.commit()
    
    _ensure_memory_dir(user)
    
    verify_url = request.host_url.rstrip("/") + url_for('auth.verify', token=user.verification_token)
    send_verification_email(user.email, verify_url)
    
    return jsonify({'ok': True, 'user': user.username, 'msg': 'Please check your email to verify your account.'})


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

@auth_bp.route('/auth/verify/<token>', methods=['GET'])
def verify(token):
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        return "Invalid or expired verification token.", 400
        
    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    return redirect(url_for('auth_page'))


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
