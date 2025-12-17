"""
Admin Authentication Module

This module handles admin user authentication including:
- Admin registration
- Admin login
- Admin logout
- Token generation and validation
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import re

# Initialize Blueprint
admin_auth_bp = Blueprint('admin_auth', __name__, url_prefix='/api/admin/auth')


class AdminAuthService:
    """Service class for admin authentication operations"""
    
    # In a real application, this would use a database
    # For now, we'll use an in-memory store (replace with actual database)
    admins = {}
    
    @staticmethod
    def is_valid_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def is_valid_password(password):
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not any(char.isupper() for char in password):
            return False, "Password must contain at least one uppercase letter"
        if not any(char.isdigit() for char in password):
            return False, "Password must contain at least one digit"
        return True, "Password is valid"
    
    @classmethod
    def register_admin(cls, email, password, username):
        """
        Register a new admin user
        
        Args:
            email (str): Admin email address
            password (str): Admin password
            username (str): Admin username
            
        Returns:
            dict: Response with status and message
        """
        # Validate input
        if not email or not password or not username:
            return {
                'success': False,
                'message': 'Email, password, and username are required'
            }, 400
        
        # Check email format
        if not cls.is_valid_email(email):
            return {
                'success': False,
                'message': 'Invalid email format'
            }, 400
        
        # Validate password strength
        is_valid, message = cls.is_valid_password(password)
        if not is_valid:
            return {
                'success': False,
                'message': message
            }, 400
        
        # Check if email already exists
        if email in cls.admins:
            return {
                'success': False,
                'message': 'Email already registered'
            }, 409
        
        # Hash password and store admin
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        cls.admins[email] = {
            'username': username,
            'password': hashed_password,
            'email': email,
            'created_at': str(__import__('datetime').datetime.utcnow())
        }
        
        return {
            'success': True,
            'message': 'Admin registered successfully',
            'data': {
                'email': email,
                'username': username
            }
        }, 201
    
    @classmethod
    def login_admin(cls, email, password):
        """
        Authenticate admin and generate access token
        
        Args:
            email (str): Admin email address
            password (str): Admin password
            
        Returns:
            dict: Response with access token or error message
        """
        # Validate input
        if not email or not password:
            return {
                'success': False,
                'message': 'Email and password are required'
            }, 400
        
        # Check if admin exists
        if email not in cls.admins:
            return {
                'success': False,
                'message': 'Invalid email or password'
            }, 401
        
        admin = cls.admins[email]
        
        # Verify password
        if not check_password_hash(admin['password'], password):
            return {
                'success': False,
                'message': 'Invalid email or password'
            }, 401
        
        # Generate access token (expires in 24 hours)
        access_token = create_access_token(
            identity=email,
            expires_delta=timedelta(hours=24)
        )
        
        return {
            'success': True,
            'message': 'Login successful',
            'data': {
                'access_token': access_token,
                'email': email,
                'username': admin['username'],
                'token_type': 'Bearer'
            }
        }, 200
    
    @classmethod
    def logout_admin(cls, email):
        """
        Logout admin (token invalidation happens on client side)
        
        Args:
            email (str): Admin email address
            
        Returns:
            dict: Logout confirmation message
        """
        return {
            'success': True,
            'message': 'Logout successful'
        }, 200


# Routes

@admin_auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new admin user
    
    Expected JSON payload:
    {
        "email": "admin@example.com",
        "password": "SecurePass123",
        "username": "admin_user"
    }
    
    Returns:
        JSON response with registration status
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body must be JSON'
            }), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        username = data.get('username', '').strip()
        
        response, status_code = AdminAuthService.register_admin(email, password, username)
        return jsonify(response), status_code
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration',
            'error': str(e)
        }), 500


@admin_auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login admin user and return access token
    
    Expected JSON payload:
    {
        "email": "admin@example.com",
        "password": "SecurePass123"
    }
    
    Returns:
        JSON response with access token
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body must be JSON'
            }), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        response, status_code = AdminAuthService.login_admin(email, password)
        return jsonify(response), status_code
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred during login',
            'error': str(e)
        }), 500


@admin_auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout admin user
    
    Requires: Valid JWT token in Authorization header
    
    Returns:
        JSON response confirming logout
    """
    try:
        current_admin = get_jwt_identity()
        response, status_code = AdminAuthService.logout_admin(current_admin)
        return jsonify(response), status_code
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred during logout',
            'error': str(e)
        }), 500


@admin_auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """
    Verify if the provided JWT token is valid
    
    Requires: Valid JWT token in Authorization header
    
    Returns:
        JSON response with admin identity
    """
    try:
        current_admin = get_jwt_identity()
        return jsonify({
            'success': True,
            'message': 'Token is valid',
            'data': {
                'email': current_admin
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Token verification failed',
            'error': str(e)
        }), 401
