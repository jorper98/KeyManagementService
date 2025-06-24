#!/usr/bin/env python3
"""
Enhanced API Key Management Service with Web Authentication
Features: User management, role-based access, web interface support
"""

import os
import json
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import jwt
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for web frontend

# Configuration
DATABASE = 'keystore.db'
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
JWT_EXPIRY_HOURS = 24

# Initialize encryption
cipher = Fernet(ENCRYPTION_KEY)

def get_db():
    """Get database connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error):
    """Close database connection."""
    db = g.get('db')
    if db is not None:
        db.close()

@app.teardown_appcontext
def close_db_context(error):
    close_db(error)

def init_db():
    """Initialize the database with required tables."""
    with sqlite3.connect(DATABASE) as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT UNIQUE NOT NULL,
                encrypted_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                owner_id INTEGER,
                description TEXT,
                FOREIGN KEY (owner_id) REFERENCES users (id)
            );
            
            CREATE TABLE IF NOT EXISTS access_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                key_name TEXT,
                action TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        
        # Create default admin user (password: admin123)
        admin_hash = generate_password_hash('admin123')
        conn.execute('''
            INSERT OR IGNORE INTO users (username, password_hash, role) 
            VALUES (?, ?, ?)
        ''', ('admin', admin_hash, 'admin'))
        
        # Create default regular user (password: user123)
        user_hash = generate_password_hash('user123')
        conn.execute('''
            INSERT OR IGNORE INTO users (username, password_hash, role) 
            VALUES (?, ?, ?)
        ''', ('user', user_hash, 'user'))
        
        conn.commit()

def generate_jwt_token(user_id, username, role):
    """Generate JWT token for user authentication."""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_jwt_token(token):
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator to require authentication for endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        g.current_user = payload
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def log_access(action, key_name=None, success=True):
    """Log user access to the database."""
    db = get_db()
    user = g.get('current_user', {})
    
    db.execute('''
        INSERT INTO access_log (user_id, user_name, key_name, action, ip_address, user_agent, success)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user.get('user_id'),
        user.get('username'),
        key_name,
        action,
        request.remote_addr,
        request.headers.get('User-Agent', ''),
        success
    ))
    db.commit()

# Authentication endpoints
@app.route('/auth/login', methods=['POST'])
def login():
    """User login endpoint."""
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400
    
    username = data['username']
    password = data['password']
    
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ? AND is_active = 1',
        (username,)
    ).fetchone()
    
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Update last login
    db.execute(
        'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
        (user['id'],)
    )
    db.commit()
    
    # Generate JWT token
    token = generate_jwt_token(user['id'], user['username'], user['role'])
    
    return jsonify({
        'token': token,
        'user': user['username'],
        'role': user['role']
    })

@app.route('/auth/logout', methods=['POST'])
@require_auth
def logout():
    """User logout endpoint."""
    log_access('logout')
    return jsonify({'message': 'Logged out successfully'})

# API Key management endpoints
@app.route('/keys', methods=['GET'])
@require_auth
def get_keys():
    """Get all API keys (users see only their keys, admins see all)."""
    db = get_db()
    
    if g.current_user['role'] == 'admin':
        # Admins can see all keys
        keys = db.execute('''
            SELECT k.*, u.username as created_by_username
            FROM api_keys k
            LEFT JOIN users u ON k.owner_id = u.id
            ORDER BY k.created_at DESC
        ''').fetchall()
    else:
        # Regular users see only their keys
        keys = db.execute('''
            SELECT k.*, u.username as created_by_username
            FROM api_keys k
            LEFT JOIN users u ON k.owner_id = u.id
            WHERE k.owner_id = ?
            ORDER BY k.created_at DESC
        ''', (g.current_user['user_id'],)).fetchall()
    
    keys_list = []
    for key in keys:
        keys_list.append({
            'key_name': key['key_name'],
            'description': key['description'],
            'created_at': key['created_at'],
            'updated_at': key['updated_at'],
            'created_by': key['created_by_username'] or key['created_by']
        })
    
    log_access('list_keys')
    return jsonify({'keys': keys_list})

@app.route('/keys/<key_name>', methods=['GET'])
@require_auth
def get_key(key_name):
    """Get a specific API key with its value."""
    db = get_db()
    
    # Check if user can access this key
    if g.current_user['role'] == 'admin':
        key = db.execute(
            'SELECT * FROM api_keys WHERE key_name = ?',
            (key_name,)
        ).fetchone()
    else:
        key = db.execute(
            'SELECT * FROM api_keys WHERE key_name = ? AND owner_id = ?',
            (key_name, g.current_user['user_id'])
        ).fetchone()
    
    if not key:
        return jsonify({'error': 'Key not found'}), 404
    
    # Decrypt the API key
    try:
        decrypted_key = cipher.decrypt(key['encrypted_value'].encode()).decode()
    except Exception as e:
        return jsonify({'error': 'Failed to decrypt key'}), 500
    
    log_access('view_key', key_name)
    return jsonify({
        'key_name': key['key_name'],
        'api_key': decrypted_key,
        'description': key['description'],
        'created_at': key['created_at'],
        'updated_at': key['updated_at']
    })

@app.route('/keys', methods=['POST'])
@require_auth
def add_key():
    """Add a new API key."""
    data = request.get_json()
    
    if not data or 'key_name' not in data or 'api_key' not in data:
        return jsonify({'error': 'Key name and API key are required'}), 400
    
    key_name = data['key_name']
    api_key = data['api_key']
    description = data.get('description', '')
    
    # Validate key name
    if not key_name.strip():
        return jsonify({'error': 'Key name cannot be empty'}), 400
    
    # Encrypt the API key
    try:
        encrypted_key = cipher.encrypt(api_key.encode()).decode()
    except Exception as e:
        return jsonify({'error': 'Failed to encrypt key'}), 500
    
    db = get_db()
    
    try:
        db.execute('''
            INSERT INTO api_keys (key_name, encrypted_value, description, created_by, owner_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (key_name, encrypted_key, description, g.current_user['username'], g.current_user['user_id']))
        db.commit()
        
        log_access('add_key', key_name)
        return jsonify({'message': 'API key added successfully'}), 201
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Key name already exists'}), 409

@app.route('/keys/<key_name>', methods=['PUT'])
@require_auth
def update_key(key_name):
    """Update an existing API key."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    db = get_db()
    
    # Check if user can modify this key
    if g.current_user['role'] == 'admin':
        key = db.execute(
            'SELECT * FROM api_keys WHERE key_name = ?',
            (key_name,)
        ).fetchone()
    else:
        key = db.execute(
            'SELECT * FROM api_keys WHERE key_name = ? AND owner_id = ?',
            (key_name, g.current_user['user_id'])
        ).fetchone()
    
    if not key:
        return jsonify({'error': 'Key not found'}), 404
    
    # Update fields
    update_fields = []
    params = []
    
    if 'api_key' in data:
        try:
            encrypted_key = cipher.encrypt(data['api_key'].encode()).decode()
            update_fields.append('encrypted_value = ?')
            params.append(encrypted_key)
        except Exception as e:
            return jsonify({'error': 'Failed to encrypt key'}), 500
    
    if 'description' in data:
        update_fields.append('description = ?')
        params.append(data['description'])
    
    if update_fields:
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(key_name)
        
        query = f"UPDATE api_keys SET {', '.join(update_fields)} WHERE key_name = ?"
        db.execute(query, params)
        db.commit()
    
    log_access('update_key', key_name)
    return jsonify({'message': 'API key updated successfully'})

@app.route('/keys/<key_name>', methods=['DELETE'])
@require_auth
def delete_key(key_name):
    """Delete an API key."""
    db = get_db()
    
    # Check if user can delete this key
    if g.current_user['role'] == 'admin':
        key = db.execute(
            'SELECT * FROM api_keys WHERE key_name = ?',
            (key_name,)
        ).fetchone()
    else:
        key = db.execute(
            'SELECT * FROM api_keys WHERE key_name = ? AND owner_id = ?',
            (key_name, g.current_user['user_id'])
        ).fetchone()
    
    if not key:
        return jsonify({'error': 'Key not found'}), 404
    
    db.execute('DELETE FROM api_keys WHERE key_name = ?', (key_name,))
    db.commit()
    
    log_access('delete_key', key_name)
    return jsonify({'message': 'API key deleted successfully'})

# Logging endpoints
@app.route('/logs', methods=['GET'])
@require_auth
def get_logs():
    """Get access logs."""
    db = get_db()
    
    # Build query based on user role
    if g.current_user['role'] == 'admin':
        # Admins can see all logs
        logs = db.execute('''
            SELECT * FROM access_log 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''').fetchall()
    else:
        # Regular users see only their logs
        logs = db.execute('''
            SELECT * FROM access_log 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''', (g.current_user['user_id'],)).fetchall()
    
    logs_list = []
    for log in logs:
        logs_list.append({
            'timestamp': log['timestamp'],
            'user_name': log['user_name'],
            'key_name': log['key_name'],
            'action': log['action'],
            'ip_address': log['ip_address'],
            'success': bool(log['success'])
        })
    
    return jsonify({'logs': logs_list})

# User management endpoints (Admin only)
@app.route('/users', methods=['GET'])
@require_auth
@require_admin
def get_users():
    """Get all users (admin only)."""
    db = get_db()
    users = db.execute('''
        SELECT id, username, role, created_at, last_login, is_active
        FROM users
        ORDER BY created_at DESC
    ''').fetchall()
    
    users_list = []
    for user in users:
        users_list.append({
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'created_at': user['created_at'],
            'last_login': user['last_login'],
            'is_active': bool(user['is_active'])
        })
    
    log_access('list_users')
    return jsonify({'users': users_list})

@app.route('/users', methods=['POST'])
@require_auth
@require_admin
def add_user():
    """Add a new user (admin only)."""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400
    
    username = data['username']
    password = data['password']
    role = data.get('role', 'user')
    
    # Validate inputs
    if not username.strip():
        return jsonify({'error': 'Username cannot be empty'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if role not in ['user', 'admin']:
        return jsonify({'error': 'Role must be either "user" or "admin"'}), 400
    
    # Hash password
    password_hash = generate_password_hash(password)
    
    db = get_db()
    
    try:
        db.execute('''
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
        ''', (username, password_hash, role))
        db.commit()
        
        log_access('add_user', username)
        return jsonify({'message': 'User added successfully'}), 201
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 409

@app.route('/users/<int:user_id>', methods=['PUT'])
@require_auth
@require_admin
def update_user(user_id):
    """Update a user (admin only)."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    db = get_db()
    
    # Check if user exists
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update fields
    update_fields = []
    params = []
    
    if 'password' in data:
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        password_hash = generate_password_hash(data['password'])
        update_fields.append('password_hash = ?')
        params.append(password_hash)
    
    if 'role' in data:
        if data['role'] not in ['user', 'admin']:
            return jsonify({'error': 'Role must be either "user" or "admin"'}), 400
        update_fields.append('role = ?')
        params.append(data['role'])
    
    if 'is_active' in data:
        update_fields.append('is_active = ?')
        params.append(bool(data['is_active']))
    
    if update_fields:
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        db.execute(query, params)
        db.commit()
    
    log_access('update_user', user['username'])
    return jsonify({'message': 'User updated successfully'})

@app.route('/users/<int:user_id>', methods=['DELETE'])
@require_auth
@require_admin
def delete_user(user_id):
    """Delete a user (admin only)."""
    db = get_db()
    
    # Check if user exists
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Prevent admin from deleting themselves
    if user_id == g.current_user['user_id']:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    # Delete user's API keys first
    db.execute('DELETE FROM api_keys WHERE owner_id = ?', (user_id,))
    
    # Delete user
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    
    log_access('delete_user', user['username'])
    return jsonify({'message': 'User deleted successfully'})

# Static file serving for frontend
@app.route('/')
def serve_frontend():
    """Serve the frontend HTML file."""
    return send_from_directory('.', 'keystore_web_frontend.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('.', filename)

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'API Key Management Service'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Initializing API Key Management Service...")
    
    # Initialize database
    init_db()
    print("Database initialized successfully")
    
    # Print default credentials
    print("\n" + "="*50)
    print("DEFAULT LOGIN CREDENTIALS:")
    print("Admin - Username: admin, Password: admin123")
    print("User  - Username: user,  Password: user123")
    print("="*50 + "\n")
    
    print(f"Encryption key: {ENCRYPTION_KEY.decode() if isinstance(ENCRYPTION_KEY, bytes) else ENCRYPTION_KEY}")
    print(f"JWT Secret: {SECRET_KEY}")
    
    # Run the application
    print("Starting server on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)