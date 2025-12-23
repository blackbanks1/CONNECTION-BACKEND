from datetime import datetime, timedelta
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

    # FIX: Make email optional so signup can succeed without it
    email = db.Column(db.String(120), unique=True, nullable=True)

    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="receiver")
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

    # NEW: Track driver sessions and subscriptions
    last_session_at = db.Column(db.DateTime, nullable=True)
    total_sessions = db.Column(db.Integer, default=0)
    trial_end_date = db.Column(db.DateTime, nullable=True)  # optional trial period

    # Relationships
    deliveries_requested = db.relationship(
        'Delivery',
        foreign_keys='Delivery.user_id',
        back_populates='requester',
        lazy=True,
        cascade='all, delete-orphan'
    )
    deliveries_driven = db.relationship(
        'Delivery',
        foreign_keys='Delivery.driver_id',
        back_populates='driver',
        lazy=True,
        cascade='all, delete-orphan'
    )
    deliveries_received = db.relationship(
        'Delivery',
        foreign_keys='Delivery.receiver_id',
        back_populates='receiver',
        lazy=True,
        cascade='all, delete-orphan'
    )

    feedbacks = db.relationship('Feedback', backref='user', lazy=True, cascade='all, delete-orphan')

    # ---------------------------
    # Password helpers
    # ---------------------------
    def set_password(self, password):
        # FIX: Align with frontend rule (≥6 chars instead of ≥8)
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ---------------------------
    # Serialization
    # ---------------------------
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'last_session_at': self.last_session_at.isoformat() if self.last_session_at else None,
            'total_sessions': self.total_sessions,
            'trial_end_date': self.trial_end_date.isoformat() if self.trial_end_date else None
        }
class Delivery(db.Model):
    __tablename__ = 'deliveries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)   # requester
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))                 # driver
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'))               # receiver
    delivery_type = db.Column(db.String(50), nullable=False)
    origin_address = db.Column(db.String(255), nullable=False)
    destination_address = db.Column(db.String(255), nullable=False)
    package_description = db.Column(db.Text)
    package_weight = db.Column(db.Float)
    package_dimensions = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')
    tracking_number = db.Column(db.String(100), unique=True, default=lambda: secrets.token_hex(8))
    estimated_delivery = db.Column(db.DateTime)
    actual_delivery = db.Column(db.DateTime)
    cost = db.Column(db.Float, nullable=True)
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (explicit back_populates)
    requester = db.relationship('User', foreign_keys=[user_id], back_populates='deliveries_requested')
    driver = db.relationship('User', foreign_keys=[driver_id], back_populates='deliveries_driven')
    receiver = db.relationship('User', foreign_keys=[receiver_id], back_populates='deliveries_received')

    feedbacks = db.relationship('Feedback', backref='delivery', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'driver_id': self.driver_id,
            'receiver_id': self.receiver_id,
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class JoinToken(db.Model):
    __tablename__ = 'join_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(32)
    )
    email = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(
        db.DateTime,
        default=lambda: datetime.utcnow() + timedelta(hours=24)  # auto-expire in 24h
    )
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime)

    # -------------------- Helpers --------------------
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return self.expires_at and datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired()

    def mark_used(self):
        """Mark the token as used and set timestamp."""
        self.is_used = True
        self.used_at = datetime.utcnow()

    # -------------------- Serialization --------------------
    def to_dict(self) -> dict:
        """Serialize token details to dictionary."""
        return {
            'id': self.id,
            'token': self.token,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
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
    delivery_experience = db.Column(db.String(50))
    would_recommend = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_rating(self, value):
        if value < 1 or value > 5:
            raise ValueError("Rating must be between 1 and 5")
        self.rating = value
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'delivery_id': self.delivery_id,
            'rating': self.rating,
            'comment': self.comment,
            'delivery_experience': self.delivery_experience,
            'would_recommend': self.would_recommend,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    role = db.Column(db.String(50), default='admin')
    permissions = db.Column(db.JSON, default=lambda: {})  # FIXED
    phone = db.Column(db.String(20))
    profile_picture = db.Column(db.String(255))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        if not self.permissions:
            return False
        return self.permissions.get(permission, False)
    
    def grant_permission(self, permission):
        if not self.permissions:
            self.permissions = {}
        self.permissions[permission] = True
    
    def revoke_permission(self, permission):
        if self.permissions and permission in self.permissions:
            self.permissions[permission] = False
    
    def to_dict(self):
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # e.g., 'service_fee', 'commission', 'surcharge'
    status = db.Column(db.String(50), default='pending')  # 'pending', 'completed', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    delivery = db.relationship('Delivery', backref='transactions', lazy=True)

    def to_dict(self):
        return {
            'transaction_id': self.id,
            'delivery_id': self.delivery_id,
            'amount': self.amount,
            'type': self.type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Payout(db.Model):
    __tablename__ = 'payouts'

    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending')  # 'pending', 'completed', 'failed'
    period = db.Column(db.String(50))  # e.g., 'weekly', 'monthly'
    scheduled_date = db.Column(db.DateTime, nullable=False)
    completed_date = db.Column(db.DateTime)

    # Relationships
    driver = db.relationship('User', foreign_keys=[driver_id], backref='payouts')

    def to_dict(self):
        return {
            'payout_id': self.id,
            'driver_id': self.driver_id,
            'amount': self.amount,
            'status': self.status,
            'period': self.period,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None
        }