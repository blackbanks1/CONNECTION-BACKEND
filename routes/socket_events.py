"""
Socket.IO event handlers for real-time communication
"""

import uuid
from datetime import datetime
from flask_socketio import emit, join_room, leave_room
from utils import normalize_phone
from flask import session, request

def register_socket_events(socketio, db):
    """Register all Socket.IO event handlers"""
    
    from models import DeliverySession, DeliveryLocation
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f"Client connected: {request.sid}")
        emit('connection_success', {'message': 'Connected to server'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"Client disconnected: {request.sid}")
    
    @socketio.on('join_delivery')
    def handle_join_delivery(data):
        """Join a delivery room"""
        try:
            delivery_id = data.get('delivery_id')
            user_type = data.get('user_type')  # 'driver' or 'receiver'
            phone = data.get('phone')
            
            if not delivery_id:
                emit('error', {'message': 'Delivery ID required'})
                return
            
            # Join the room
            room = f"delivery_{delivery_id}"
            join_room(room)
            print(f"{user_type} {phone} joined room: {room}")
            
            # Store session info
            session['delivery_room'] = room
            session['user_type'] = user_type
            session['phone'] = phone
            
            emit('joined_room', {
                'room': room,
                'user_type': user_type,
                'delivery_id': delivery_id
            })
            
            # Notify others in the room
            emit('user_joined', {
                'user_type': user_type,
                'phone': phone,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room, include_self=False)
            
        except Exception as e:
            emit('error', {'message': f'Failed to join delivery: {str(e)}'})
    
    @socketio.on('driver_location_update')
    def handle_driver_location(data):
        """Update driver location and broadcast to receiver"""
        try:
            delivery_id = data.get('delivery_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            accuracy = data.get('accuracy')
            phone = data.get('phone')
            
            if not all([delivery_id, latitude, longitude, phone]):
                emit('error', {'message': 'Missing required location data'})
                return
            
            # Store location in database
            with db.session.begin():
                delivery_session = DeliverySession.query.filter_by(
                    delivery_id=delivery_id
                ).first()
                
                if delivery_session:
                    # Update session with latest location
                    delivery_session.driver_latitude = latitude
                    delivery_session.driver_longitude = longitude
                    
                    # Create location history entry
                    location = DeliveryLocation(
                        id=str(uuid.uuid4()),
                        delivery_id=delivery_id,
                        latitude=latitude,
                        longitude=longitude,
                        accuracy=accuracy,
                        user_type='driver'
                    )
                    db.session.add(location)
            
            # Broadcast to room
            room = f"delivery_{delivery_id}"
            emit('driver_location_updated', {
                'latitude': latitude,
                'longitude': longitude,
                'accuracy': accuracy,
                'phone': phone,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room, include_self=False)
            
            print(f"Driver location updated for delivery {delivery_id}")
            
        except Exception as e:
            emit('error', {'message': f'Location update failed: {str(e)}'})
    
    @socketio.on('receiver_location_update')
    def handle_receiver_location(data):
        """Update receiver location and broadcast to driver"""
        try:
            delivery_id = data.get('delivery_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            phone = data.get('phone')
            
            if not all([delivery_id, latitude, longitude, phone]):
                emit('error', {'message': 'Missing required location data'})
                return
            
            # Store location in database
            with db.session.begin():
                delivery_session = DeliverySession.query.filter_by(
                    delivery_id=delivery_id
                ).first()
                
                if delivery_session:
                    # Update session
                    delivery_session.receiver_latitude = latitude
                    delivery_session.receiver_longitude = longitude
                    delivery_session.receiver_shared_location = True
                    
                    # Create location history entry
                    location = DeliveryLocation(
                        id=str(uuid.uuid4()),
                        delivery_id=delivery_id,
                        latitude=latitude,
                        longitude=longitude,
                        user_type='receiver'
                    )
                    db.session.add(location)
            
            # Broadcast to room
            room = f"delivery_{delivery_id}"
            emit('receiver_location_updated', {
                'latitude': latitude,
                'longitude': longitude,
                'phone': phone,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room, include_self=False)
            
            print(f"Receiver location updated for delivery {delivery_id}")
            
        except Exception as e:
            emit('error', {'message': f'Receiver location update failed: {str(e)}'})
    
    @socketio.on('delivery_status_update')
    def handle_status_update(data):
        """Update delivery status"""
        try:
            delivery_id = data.get('delivery_id')
            status = data.get('status')
            phone = data.get('phone')
            
            if not all([delivery_id, status, phone]):
                emit('error', {'message': 'Missing required data'})
                return
            
            with db.session.begin():
                delivery_session = DeliverySession.query.filter_by(
                    delivery_id=delivery_id
                ).first()
                
                if delivery_session:
                    delivery_session.status = status
                    if status == 'completed':
                        delivery_session.completed_at = datetime.utcnow()
            
            # Broadcast status change
            room = f"delivery_{delivery_id}"
            emit('delivery_status_changed', {
                'status': status,
                'phone': phone,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room)
            
            print(f"Delivery {delivery_id} status updated to {status}")
            
        except Exception as e:
            emit('error', {'message': f'Status update failed: {str(e)}'})
    
    @socketio.on('leave_delivery')
    def handle_leave_delivery(data):
        """Leave a delivery room"""
        try:
            delivery_id = data.get('delivery_id')
            user_type = data.get('user_type')
            phone = data.get('phone')
            
            if delivery_id:
                room = f"delivery_{delivery_id}"
                leave_room(room)
                
                emit('user_left', {
                    'user_type': user_type,
                    'phone': phone,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=room)
                
                print(f"{user_type} {phone} left room: {room}")
        
        except Exception as e:
            print(f"Error leaving room: {str(e)}")