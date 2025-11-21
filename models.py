from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import secrets
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def gen_uuid():
    return str(uuid.uuid4())


# ============================================================
# JOIN TOKEN  (Receiver gets this via WhatsApp/SMS)
# ============================================================
class JoinToken(db.Model):
    __tablename__ = "join_tokens"

    token = db.Column(db.String(32), primary_key=True)
    delivery_id = db.Column(db.String(36), db.ForeignKey("deliveries.id"), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def generate(delivery_id, hours=24):
        token_string = secrets.token_hex(16)

        token = JoinToken(
            token=token_string,
            delivery_id=delivery_id,
            expires_at=datetime.utcnow() + timedelta(hours=hours)
        )

        db.session.add(token)
        db.session.commit()
        return token

    @property
    def is_valid(self):
        return (
            self.used_at is None and
            datetime.utcnow() <= self.expires_at
        )


# ============================================================
# DELIVERY (Core session between driver & receiver)
# ============================================================
class Delivery(db.Model):
    __tablename__ = "deliveries"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    driver_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)

    # Receiver does NOT have an account
    receiver_phone = db.Column(db.String(32), nullable=False)

    status = db.Column(db.String(32), default="active", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    feedbacks = db.relationship("Feedback", back_populates="delivery", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Delivery {self.id}>"


# ============================================================
# USER / DRIVER
# ============================================================
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    phone = db.Column(db.String(32), nullable=False, index=True)
    role = db.Column(db.String(32), default="driver")   # MVP only supports drivers

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # DAILY PASS
    daily_pass_expires = db.Column(db.DateTime, nullable=True)
    trial_end_date = db.Column(db.DateTime, nullable=True)

    # -------------------------
    # Password helpers
    # -------------------------
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    # -------------------------
    # Daily pass logic
    # -------------------------
    def has_active_pass(self):
        if not self.daily_pass_expires:
            return False
        return datetime.utcnow() <= self.daily_pass_expires

    def activate_daily_pass(self, hours=24):
        self.daily_pass_expires = datetime.utcnow() + timedelta(hours=hours)
        db.session.add(self)
        db.session.commit()
        # -------------------------
    # Trial logic
    # -------------------------
    def start_trial(self):
        """Start a 7-day free trial for new users."""
        self.trial_end_date = datetime.utcnow() + timedelta(days=7)

    def trial_active(self):
        """Returns True if user is still within free trial."""
        return self.trial_end_date and datetime.utcnow() < self.trial_end_date

    def trial_days_left(self):
        """Returns remaining days in the trial."""
        if not self.trial_end_date:
            return 0
        remaining = self.trial_end_date - datetime.utcnow()
        return max(remaining.days, 0)
    

    def __repr__(self):
        return f"<User {self.username}>"
    



# ============================================================
# FEEDBACK
# ============================================================
class Feedback(db.Model):
    __tablename__ = "feedbacks"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    delivery_id = db.Column(db.String(36), db.ForeignKey("deliveries.id"), nullable=False, index=True)

    receiver_id = db.Column(db.String(64), nullable=True)  # receiver has no account, but kept for future use

    feedback = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    delivery = db.relationship("Delivery", back_populates="feedbacks")

    def __repr__(self):
        return f"<Feedback {self.id}>"
