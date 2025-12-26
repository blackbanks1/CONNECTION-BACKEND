from datetime import datetime, timedelta
import secrets
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Utility function for UUID generation
def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    
    # Public identifier for URLs/APIs (use this instead of id in URLs)
    public_id = db.Column(db.String(36), unique=True, default=generate_uuid, nullable=False)
    
    # Authentication fields
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Optional
    
    # Phone - MUST BE NORMALIZED FORMAT (250788123456)
    phone = db.Column(db.String(12), unique=True, nullable=False, index=True)
    
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="driver")
    
    # Personal info (optional)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(80), default="Rwanda")
    profile_picture = db.Column(db.String(255))
    bio = db.Column(db.Text)

    # Status and timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Driver-specific fields (from driver_routes.py requirements)
    last_session_at = db.Column(db.DateTime, nullable=True)
    total_sessions = db.Column(db.Integer, default=0)
    trial_end_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    # As driver
    deliveries_as_driver = db.relationship(
        'Delivery',
        foreign_keys='Delivery.driver_id',
        back_populates='driver',
        lazy='dynamic'
    )
    
    # As receiver (by phone match, not foreign key)
    deliveries_as_receiver = db.relationship(
        'Delivery',
        foreign_keys='Delivery.receiver_phone',
        primaryjoin='User.phone==Delivery.receiver_phone',
        viewonly=True,
        lazy='dynamic'
    )
    
    feedbacks = db.relationship('Feedback', backref='user', lazy=True, cascade='all, delete-orphan')
    payouts = db.relationship('Payout', foreign_keys='Payout.driver_id', backref='driver_user', lazy='dynamic')

    # ---------------------------
    # Password helpers
    # ---------------------------
    def set_password(self, password):
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()

    # ---------------------------
    # Serialization
    # ---------------------------
    def to_dict(self):
        return {
            'public_id': self.public_id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'country': self.country,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'last_session_at': self.last_session_at.isoformat() if self.last_session_at else None,
            'total_sessions': self.total_sessions,
        }
    
    def __repr__(self):
        return f'<User {self.username} ({self.phone})>'


class Delivery(db.Model):
    __tablename__ = 'deliveries'

    id = db.Column(db.Integer, primary_key=True)
    
    # Public identifier for sharing (used in track.html URLs)
    delivery_id = db.Column(db.String(36), unique=True, default=generate_uuid, nullable=False, index=True)
    
    # Driver (who created the delivery)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Receiver - identified by PHONE NUMBER (not foreign key)
    receiver_phone = db.Column(db.String(12), nullable=False, index=True)  # 250788123456 format
    receiver_name = db.Column(db.String(128), nullable=True)
    
    # Location info (optional at creation)
    start_lat = db.Column(db.Float, nullable=True)
    start_lng = db.Column(db.Float, nullable=True)
    end_lat = db.Column(db.Float, nullable=True)
    end_lng = db.Column(db.Float, nullable=True)
    
    # Address info (optional)
    pickup_address = db.Column(db.String(512), nullable=True)
    delivery_address = db.Column(db.String(512), nullable=True)
    
    # Delivery details
    delivery_type = db.Column(db.String(50), default="standard")
    package_description = db.Column(db.Text)
    package_weight = db.Column(db.Float)
    special_instructions = db.Column(db.Text)
    
    # Status tracking (matches frontend expectations)
    status = db.Column(db.String(20), default='pending', index=True)
    # pending, active, in_progress, completed, cancelled, failed
    
    # Socket.IO room for real-time updates
    socket_room = db.Column(db.String(100), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    
    # Metrics
    estimated_distance_km = db.Column(db.Float, nullable=True)
    estimated_duration_min = db.Column(db.Integer, nullable=True)
    actual_distance_km = db.Column(db.Float, nullable=True)
    actual_duration_min = db.Column(db.Integer, nullable=True)
    cost = db.Column(db.Float, nullable=True)
    
    # Feedback
    rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    feedback = db.Column(db.Text, nullable=True)
    
    # Relationships
    driver = db.relationship('User', foreign_keys=[driver_id], back_populates='deliveries_as_driver')
    
    # Location history
    locations = db.relationship('DeliveryLocation', backref='delivery', lazy='dynamic', cascade='all, delete-orphan')
    
    # Transactions (optional)
    transactions = db.relationship('Transaction', backref='delivery_transaction', lazy='dynamic', cascade='all, delete-orphan')
    
    # ---------------------------
    # Status management
    # ---------------------------
    def start_delivery(self):
        """Mark delivery as started."""
        self.status = 'active'
        self.started_at = datetime.utcnow()
    
    def complete_delivery(self):
        """Mark delivery as completed."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
    
    def cancel_delivery(self, reason=None):
        """Cancel delivery."""
        self.status = 'cancelled'
        self.cancelled_at = datetime.utcnow()
        if reason:
            self.special_instructions = f"Cancelled: {reason}"
    
    def is_active(self):
        """Check if delivery is currently active."""
        return self.status in ['active', 'in_progress']
    
    # ---------------------------
    # Serialization
    # ---------------------------
    def to_dict(self):
        return {
            'delivery_id': self.delivery_id,
            'driver_id': self.driver_id,
            'receiver_phone': self.receiver_phone,
            'receiver_name': self.receiver_name,
            'status': self.status,
            'socket_room': self.socket_room,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'estimated_distance_km': self.estimated_distance_km,
            'estimated_duration_min': self.estimated_duration_min,
            'actual_distance_km': self.actual_distance_km,
            'actual_duration_min': self.actual_duration_min,
            'cost': self.cost,
            'tracking_link': f"/track/{self.delivery_id}"  # For frontend
        }
    
    def __repr__(self):
        return f'<Delivery {self.delivery_id} ({self.status})>'


class DeliveryLocation(db.Model):
    """Historical location tracking for deliveries."""
    __tablename__ = 'delivery_locations'
    
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=False, index=True)
    
    # Who this location is for
    role = db.Column(db.String(10), nullable=False)  # 'driver' or 'receiver'
    
    # Location data
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    accuracy = db.Column(db.Float, nullable=True)
    speed = db.Column(db.Float, nullable=True)
    heading = db.Column(db.Float, nullable=True)
    
    # Timestamp
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self):
        return {
            'role': self.role,
            'lat': self.lat,
            'lng': self.lng,
            'speed': self.speed,
            'timestamp': self.timestamp.isoformat()
        }


# REMOVED JoinToken - We're using delivery_id directly for tracking
# class JoinToken(db.Model): ...  # DELETE THIS


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
    public_id = db.Column(db.String(36), unique=True, default=generate_uuid, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    role = db.Column(db.String(50), default='admin')
    permissions = db.Column(db.JSON, default=lambda: {})
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
            'public_id': self.public_id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'phone': self.phone,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'service_fee', 'commission', 'surcharge'
    status = db.Column(db.String(50), default='pending')  # 'pending', 'completed', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    period = db.Column(db.String(50))  # 'weekly', 'monthly'
    scheduled_date = db.Column(db.DateTime, nullable=False)
    completed_date = db.Column(db.DateTime)

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


# Optional: Route cache for optimization
class RouteCache(db.Model):
    """Cache for route calculations to avoid redundant API calls."""
    __tablename__ = 'route_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Route endpoints (rounded for caching)
    start_lat = db.Column(db.Float, nullable=False)
    start_lng = db.Column(db.Float, nullable=False)
    end_lat = db.Column(db.Float, nullable=False)
    end_lng = db.Column(db.Float, nullable=False)
    
    # Cache key
    cache_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Route data
    polyline = db.Column(db.Text, nullable=False)  # JSON array
    distance_km = db.Column(db.Float, nullable=False)
    duration_min = db.Column(db.Integer, nullable=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    access_count = db.Column(db.Integer, default=0)
    
    @staticmethod
    def generate_cache_key(start_lat, start_lng, end_lat, end_lng, precision=4):
        """Generate cache key from coordinates."""
        rounded = (
            round(start_lat, precision),
            round(start_lng, precision),
            round(end_lat, precision),
            round(end_lng, precision)
        )
        return f"{rounded[0]},{rounded[1]}|{rounded[2]},{rounded[3]}"
    
    def update_access(self):
        """Update access statistics."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1