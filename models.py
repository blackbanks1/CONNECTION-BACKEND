from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(80))
    profile_picture = db.Column(db.String(255))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    deliveries = db.relationship('Delivery', backref='user', lazy=True, cascade='all, delete-orphan')
    feedbacks = db.relationship('Feedback', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set the user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'profile_picture': self.profile_picture,
            'bio': self.bio,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active
        }


class Delivery(db.Model):
    __tablename__ = 'deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    delivery_type = db.Column(db.String(50), nullable=False)  # e.g., 'standard', 'express', 'overnight'
    origin_address = db.Column(db.String(255), nullable=False)
    destination_address = db.Column(db.String(255), nullable=False)
    package_description = db.Column(db.Text)
    package_weight = db.Column(db.Float)  # in kg
    package_dimensions = db.Column(db.String(50))  # format: LxWxH in cm
    status = db.Column(db.String(50), default='pending')  # pending, in_transit, delivered, cancelled
    tracking_number = db.Column(db.String(100), unique=True)
    estimated_delivery = db.Column(db.DateTime)
    actual_delivery = db.Column(db.DateTime)
    cost = db.Column(db.Float, nullable=False)
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    feedbacks = db.relationship('Feedback', backref='delivery', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert delivery object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'delivery_type': self.delivery_type,
            'origin_address': self.origin_address,
            'destination_address': self.destination_address,
            'package_description': self.package_description,
            'package_weight': self.package_weight,
            'package_dimensions': self.package_dimensions,
            'status': self.status,
            'tracking_number': self.tracking_number,
            'estimated_delivery': self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            'actual_delivery': self.actual_delivery.isoformat() if self.actual_delivery else None,
            'cost': self.cost,
            'special_instructions': self.special_instructions,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class JoinToken(db.Model):
    __tablename__ = 'join_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime)
    
    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    def is_expired(self):
        """Check if the token has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if the token is still valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()
    
    def to_dict(self):
        """Convert token object to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'is_used': self.is_used,
            'used_at': self.used_at.isoformat() if self.used_at else None
        }


class Feedback(db.Model):
    __tablename__ = 'feedbacks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    delivery_experience = db.Column(db.String(50))  # e.g., 'excellent', 'good', 'average', 'poor'
    would_recommend = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert feedback object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'delivery_id': self.delivery_id,
            'rating': self.rating,
            'comment': self.comment,
            'delivery_experience': self.delivery_experience,
            'would_recommend': self.would_recommend,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    role = db.Column(db.String(50), default='admin')  # e.g., 'admin', 'moderator', 'support'
    permissions = db.Column(db.JSON, default=dict)  # Store permissions as JSON
    phone = db.Column(db.String(20))
    profile_picture = db.Column(db.String(255))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash and set the admin password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        """Check if admin has a specific permission"""
        if not self.permissions:
            return False
        return self.permissions.get(permission, False)
    
    def grant_permission(self, permission):
        """Grant a permission to the admin"""
        if not self.permissions:
            self.permissions = {}
        self.permissions[permission] = True
    
    def revoke_permission(self, permission):
        """Revoke a permission from the admin"""
        if self.permissions and permission in self.permissions:
            self.permissions[permission] = False
    
    def to_dict(self):
        """Convert admin object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'permissions': self.permissions,
            'phone': self.phone,
            'profile_picture': self.profile_picture,
            'bio': self.bio,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
