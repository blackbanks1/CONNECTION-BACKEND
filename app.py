# app.py - FIXED VERSION

from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import timedelta
import logging

# Initialize FIRST
db = SQLAlchemy()
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///connection.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
    
    # Initialize with app
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='gevent')
    CORS(app)
    
    # Register blueprints (FIXED NAMES)
    from driver_auth import driver_auth
    from driver_routes import driver_bp
    from receiver_routes import receiver_bp
    from admin_routes import admin_bp
    
    app.register_blueprint(driver_auth, url_prefix='/auth')
    app.register_blueprint(driver_bp, url_prefix='/driver')
    app.register_blueprint(receiver_bp, url_prefix='/track')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Import and register socket events
    from routes.socket_events import register_socket_events
    register_socket_events(socketio, db)
    
    # Import models (must be after db init)
    from models import User, Delivery, DeliveryLocation, Feedback, Admin, Transaction, Payout, RouteCache
    
    # Error handlers (FIXED FUNCTION NAME)
    from db_error_handlers import register_db_error_handlers
    register_db_error_handlers(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
        logging.info("Database tables created")
    
    # Routes
    @app.route('/')
    def index():
        return jsonify({'message': 'Connection API', 'status': 'running'})
    
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'Connection Delivery Tracking',
            'version': '1.0.0'
        })
    
    return app

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)