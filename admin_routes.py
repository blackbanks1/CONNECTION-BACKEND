from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime, timedelta
import logging

from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    create_access_token
)
from werkzeug.security import check_password_hash

from models import db, User, Delivery, Feedback, Transaction, Payout, Admin
# Initialize the admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Configure logging
logger = logging.getLogger(__name__)

# ==================== Authentication Middleware ====================

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        identity = get_jwt_identity()
        admin = Admin.query.filter_by(email=identity).first()
        if not admin:
            return jsonify({"error": "unauthorized"}), 403
        return f(*args, **kwargs)
    return decorated_function


def validate_admin_credentials(username, password):
    """
    Validate admin credentials against the database.
    """
    admin = Admin.query.filter_by(username=username).first()
    if admin and check_password_hash(admin.password_hash, password):
        return admin
    return None


# ==================== Admin Authentication Routes ====================

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    """
    Admin login endpoint

    Expected JSON:
    {
        "username": "admin_username",
        "password": "admin_password"
    }

    Returns:
    {
        "success": boolean,
        "message": string,
        "admin_id": string (if successful),
        "token": string (if successful)
    }
    """
    try:
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password are required'
            }), 400

        admin = validate_admin_credentials(username, password)
        if admin:
            token = create_access_token(identity=admin.email)
            logger.info(f"Admin login successful for user: {username}")
            return jsonify({
                'success': True,
                'message': 'Admin login successful',
                'admin_id': admin.id,
                'token': token
            }), 200
        else:
            logger.warning(f"Failed admin login attempt for user: {username}")
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401

    except Exception as e:
        logger.exception("Error in admin login")
        return jsonify({
            'success': False,
            'message': 'An error occurred during login'
        }), 500
# -------------------- Logout --------------------
@admin_bp.route('/logout', methods=['POST'])
@jwt_required()
def admin_logout():
    """
    Admin logout endpoint.
    With JWT, logout usually means client deletes the token.
    If you use token blacklisting, mark it revoked here.
    """
    try:
        identity = get_jwt_identity()
        logger.info(f"Admin logout successful for {identity}")
        return jsonify({
            'success': True,
            'message': 'Admin logout successful'
        }), 200
    except Exception as e:
        logger.exception("Error in admin logout")
        return jsonify({
            'success': False,
            'message': 'An error occurred during logout'
        }), 500


# -------------------- Verify --------------------
@admin_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_admin():
    """
    Verify current admin session.
    """
    try:
        identity = get_jwt_identity()
        return jsonify({
            'success': True,
            'admin_id': identity,
            'authenticated': True
        }), 200
    except Exception as e:
        logger.exception("Error verifying admin")
        return jsonify({
            'success': False,
            'message': 'An error occurred during verification'
        }), 500


# -------------------- Dashboard --------------------
@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """
    Get admin dashboard overview with key metrics.
    """
    try:
        total_users = User.query.count()
        total_deliveries = Delivery.query.count()
        pending_deliveries = Delivery.query.filter_by(status='pending').count()
        completed_deliveries = Delivery.query.filter_by(status='completed').count()
        active_drivers = User.query.filter_by(active=True).count()
        average_rating = db.session.query(db.func.avg(Feedback.value)).scalar() or 0.0

        from datetime import datetime
        now = datetime.utcnow()
        total_revenue = db.session.query(db.func.sum(Delivery.price)).scalar() or 0.0
        revenue_this_month = db.session.query(
            db.func.sum(Delivery.price)
        ).filter(
            db.extract('year', Delivery.created_at) == now.year,
            db.extract('month', Delivery.created_at) == now.month
        ).scalar() or 0.0

        dashboard_data = {
            "total_users": total_users,
            "total_deliveries": total_deliveries,
            "pending_deliveries": pending_deliveries,
            "completed_deliveries": completed_deliveries,
            "total_revenue": float(total_revenue),
            "revenue_this_month": float(revenue_this_month),
            "active_drivers": active_drivers,
            "average_rating": float(average_rating)
        }

        logger.info("Dashboard data retrieved successfully")
        return jsonify({'success': True, 'data': dashboard_data}), 200

    except Exception as e:
        logger.exception("Error retrieving dashboard data")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving dashboard data'
        }), 500
    

# -------------------- Dashboard Summary --------------------
@admin_bp.route('/dashboard/summary', methods=['GET'])
@admin_required
def get_dashboard_summary():
    """
    Get detailed dashboard summary with analytics.

    Query parameters:
    - period: 'daily', 'weekly', 'monthly', 'yearly' (default: 'daily')
    """
    try:
        period = request.args.get('period', 'daily')

        from datetime import datetime, timedelta
        now = datetime.utcnow()

        # Calculate date range based on period
        if period == 'daily':
            start_date = now - timedelta(days=1)
        elif period == 'weekly':
            start_date = now - timedelta(weeks=1)
        elif period == 'monthly':
            start_date = now - timedelta(days=30)
        elif period == 'yearly':
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=1)

        # Example metrics (adjust to your schema)
        deliveries_in_period = Delivery.query.filter(Delivery.created_at >= start_date).count()
        completed_in_period = Delivery.query.filter(
            Delivery.created_at >= start_date,
            Delivery.status == 'completed'
        ).count()
        revenue_in_period = db.session.query(db.func.sum(Delivery.price)).filter(
            Delivery.created_at >= start_date
        ).scalar() or 0.0

        summary_data = {
            "period": period,
            "metrics": {
                "deliveries": deliveries_in_period,
                "completed_deliveries": completed_in_period,
                "revenue": float(revenue_in_period)
            },
            "trends": {
                # Placeholder for trend analytics (growth rates, charts, etc.)
            }
        }

        logger.info(f"Dashboard summary retrieved for period: {period}")
        return jsonify({'success': True, 'data': summary_data}), 200

    except Exception as e:
        logger.exception("Error retrieving dashboard summary")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving dashboard summary'
        }), 500


# -------------------- Deliveries Management --------------------
@admin_bp.route('/deliveries', methods=['GET'])
@admin_required
def get_deliveries():
    """
    Get all deliveries with filters.

    Query parameters:
    - status: 'pending', 'in_progress', 'completed', 'cancelled'
    - page: integer (default: 1)
    - limit: integer (default: 20)
    - sort_by: 'date', 'status', 'driver' (default: 'date')
    """
    try:
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        sort_by = request.args.get('sort_by', 'date')

        query = Delivery.query

        if status:
            query = query.filter_by(status=status)

        # Sorting
        if sort_by == 'status':
            query = query.order_by(Delivery.status.asc())
        elif sort_by == 'driver':
            query = query.order_by(Delivery.driver_id.asc())
        else:  # default sort by date
            query = query.order_by(Delivery.created_at.desc())

        # Pagination
        total = query.count()
        deliveries = query.offset((page - 1) * limit).limit(limit).all()

        deliveries_data = []
        for d in deliveries:
            deliveries_data.append({
                "delivery_id": d.id,
                "user_id": d.user_id,
                "driver_id": d.driver_id,
                "status": d.status,
                "pickup_location": d.pickup_location,
                "delivery_location": d.delivery_location,
                "created_at": d.created_at,
                "completed_at": d.completed_at,
                "amount": float(d.price) if d.price else 0.0
            })

        logger.info(f"Deliveries retrieved with filters - Status: {status}, Page: {page}")
        return jsonify({
            'success': True,
            'data': deliveries_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total
            }
        }), 200

    except Exception as e:
        logger.exception("Error retrieving deliveries")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving deliveries'
        }), 500
        
# -------------------- Delivery Details --------------------
@admin_bp.route('/deliveries/<delivery_id>', methods=['GET'])
@admin_required
def get_delivery_details(delivery_id):
    """
    Get detailed information about a specific delivery.
    """
    try:
        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            return jsonify({
                'success': False,
                'message': 'Delivery not found'
            }), 404

        delivery_data = {
            "delivery_id": delivery.id,
            "user_id": delivery.user_id,
            "driver_id": delivery.driver_id,
            "status": delivery.status,
            "pickup_location": delivery.pickup_location or {},
            "delivery_location": delivery.delivery_location or {},
            "route": delivery.route or [],
            "created_at": delivery.created_at.isoformat() if delivery.created_at else None,
            "started_at": delivery.started_at.isoformat() if delivery.started_at else None,
            "completed_at": delivery.completed_at.isoformat() if delivery.completed_at else None,
            "amount": float(delivery.price) if delivery.price else 0.0,
            "distance": float(delivery.distance) if delivery.distance else 0.0,
            "duration": int(delivery.duration) if delivery.duration else 0,
            "notes": delivery.notes,
            "rating": float(delivery.rating) if delivery.rating else None,
            "feedback": delivery.feedback
        }

        logger.info(f"Delivery details retrieved for ID: {delivery_id}")
        return jsonify({'success': True, 'data': delivery_data}), 200

    except Exception as e:
        logger.exception("Error retrieving delivery details")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving delivery details'
        }), 500


# -------------------- Update Delivery Status --------------------
@admin_bp.route('/deliveries/<delivery_id>/status', methods=['PUT'])
@admin_required
def update_delivery_status(delivery_id):
    """
    Update delivery status.
    """
    try:
        data = request.get_json() or {}
        new_status = data.get('status')
        notes = data.get('notes', '')

        if not new_status:
            return jsonify({
                'success': False,
                'message': 'Status is required'
            }), 400

        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            return jsonify({
                'success': False,
                'message': 'Delivery not found'
            }), 404

        delivery.status = new_status
        if notes:
            delivery.notes = notes
        delivery.updated_at = datetime.utcnow()

        db.session.commit()

        updated_delivery = {
            'delivery_id': delivery.id,
            'status': delivery.status,
            'notes': delivery.notes,
            'updated_at': delivery.updated_at.isoformat()
        }

        logger.info(f"Delivery {delivery_id} status updated to: {new_status}")
        return jsonify({
            'success': True,
            'message': f'Delivery status updated to {new_status}',
            'data': updated_delivery
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.exception("Error updating delivery status")
        return jsonify({
            'success': False,
            'message': 'An error occurred while updating delivery status'
        }), 500
    

# -------------------- Cancel Delivery --------------------
@admin_bp.route('/deliveries/<delivery_id>/cancel', methods=['POST'])
@admin_required
def cancel_delivery(delivery_id):
    """
    Cancel a specific delivery.
    """
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Cancelled by admin')
        refund = data.get('refund', True)

        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            return jsonify({
                'success': False,
                'message': 'Delivery not found'
            }), 404

        delivery.status = 'cancelled'
        delivery.notes = reason
        delivery.cancelled_at = datetime.utcnow()

        # Example refund logic (adjust to your schema)
        delivery.refund_processed = refund

        db.session.commit()

        cancelled_delivery = {
            'delivery_id': delivery.id,
            'status': delivery.status,
            'reason': delivery.notes,
            'refund_processed': delivery.refund_processed,
            'cancelled_at': delivery.cancelled_at.isoformat()
        }

        logger.info(f"Delivery {delivery_id} cancelled by admin. Refund: {refund}")
        return jsonify({
            'success': True,
            'message': 'Delivery cancelled successfully',
            'data': cancelled_delivery
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.exception("Error cancelling delivery")
        return jsonify({
            'success': False,
            'message': 'An error occurred while cancelling delivery'
        }), 500

# -------------------- Delivery Statistics --------------------
@admin_bp.route('/deliveries/stats', methods=['GET'])
@admin_required
def get_deliveries_stats():
    """
    Get delivery statistics.
    """
    try:
        period = request.args.get('period', 'monthly')

        from datetime import datetime, timedelta
        now = datetime.utcnow()

        # Calculate date range based on period
        if period == 'daily':
            start_date = now - timedelta(days=1)
        elif period == 'weekly':
            start_date = now - timedelta(weeks=1)
        elif period == 'yearly':
            start_date = now - timedelta(days=365)
        else:  # default monthly
            start_date = now - timedelta(days=30)

        query = Delivery.query.filter(Delivery.created_at >= start_date)

        total_deliveries = query.count()
        completed = query.filter_by(status='completed').count()
        pending = query.filter_by(status='pending').count()
        cancelled = query.filter_by(status='cancelled').count()

        average_rating = db.session.query(db.func.avg(Delivery.rating)).filter(
            Delivery.created_at >= start_date
        ).scalar() or 0.0

        total_distance = db.session.query(db.func.sum(Delivery.distance)).filter(
            Delivery.created_at >= start_date
        ).scalar() or 0.0

        average_duration = db.session.query(db.func.avg(Delivery.duration)).filter(
            Delivery.created_at >= start_date
        ).scalar() or 0

        stats = {
            "total_deliveries": total_deliveries,
            "completed": completed,
            "pending": pending,
            "cancelled": cancelled,
            "average_rating": float(average_rating),
            "total_distance": float(total_distance),
            "average_duration": int(average_duration)
        }

        logger.info(f"Delivery statistics retrieved for period: {period}")
        return jsonify({'success': True, 'data': stats}), 200

    except Exception as e:
        logger.exception("Error retrieving delivery statistics")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving delivery statistics'
        }), 500


# -------------------- Revenue Overview --------------------
@admin_bp.route('/revenue', methods=['GET'])
@admin_required
def get_revenue():
    """
    Get revenue overview.
    """
    try:
        period = request.args.get('period', 'monthly')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        from datetime import datetime, timedelta
        now = datetime.utcnow()

        if not start_date:
            if period == 'daily':
                start_date = (now - timedelta(days=1)).date()
            elif period == 'weekly':
                start_date = (now - timedelta(weeks=1)).date()
            elif period == 'yearly':
                start_date = (now - timedelta(days=365)).date()
            else:  # monthly
                start_date = (now - timedelta(days=30)).date()
        else:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_date = now.date()

        query = Delivery.query.filter(
            Delivery.created_at >= start_date,
            Delivery.created_at <= end_date
        )

        total_revenue = db.session.query(db.func.sum(Delivery.price)).scalar() or 0.0
        period_revenue = db.session.query(db.func.sum(Delivery.price)).filter(
            Delivery.created_at >= start_date,
            Delivery.created_at <= end_date
        ).scalar() or 0.0

        transaction_count = query.count()
        average_transaction = (period_revenue / transaction_count) if transaction_count else 0.0

        # Example growth calculation: compare with previous period
        prev_start = start_date - (end_date - start_date)
        prev_end = start_date
        prev_revenue = db.session.query(db.func.sum(Delivery.price)).filter(
            Delivery.created_at >= prev_start,
            Delivery.created_at < prev_end
        ).scalar() or 0.0

        growth_percentage = ((period_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 0.0

        revenue_data = {
            "total_revenue": float(total_revenue),
            "period_revenue": float(period_revenue),
            "transaction_count": transaction_count,
            "average_transaction": float(average_transaction),
            "growth_percentage": float(growth_percentage)
        }

        logger.info(f"Revenue data retrieved for period: {period}")
        return jsonify({'success': True, 'data': revenue_data}), 200

    except Exception as e:
        logger.exception("Error retrieving revenue data")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving revenue data'
        }), 500


# -------------------- Revenue Breakdown --------------------
@admin_bp.route('/revenue/breakdown', methods=['GET'])
@admin_required
def get_revenue_breakdown():
    """
    Get revenue breakdown by category.
    """
    try:
        period = request.args.get('period', 'monthly')
        category = request.args.get('category')

        from datetime import datetime, timedelta
        now = datetime.utcnow()

        if period == 'daily':
            start_date = now - timedelta(days=1)
        elif period == 'weekly':
            start_date = now - timedelta(weeks=1)
        elif period == 'yearly':
            start_date = now - timedelta(days=365)
        else:  # monthly
            start_date = now - timedelta(days=30)

        query = Delivery.query.filter(Delivery.created_at >= start_date)

        # Example breakdown fields (adjust to your schema)
        service_fees = db.session.query(db.func.sum(Delivery.service_fee)).filter(
            Delivery.created_at >= start_date
        ).scalar() or 0.0

        commission = db.session.query(db.func.sum(Delivery.commission)).filter(
            Delivery.created_at >= start_date
        ).scalar() or 0.0

        surcharges = db.session.query(db.func.sum(Delivery.surcharge)).filter(
            Delivery.created_at >= start_date
        ).scalar() or 0.0

        other = db.session.query(db.func.sum(Delivery.other_fee)).filter(
            Delivery.created_at >= start_date
        ).scalar() or 0.0

        total = service_fees + commission + surcharges + other

        breakdown_data = {
            "service_fees": float(service_fees),
            "commission": float(commission),
            "surcharges": float(surcharges),
            "other": float(other),
            "total": float(total)
        }

        logger.info(f"Revenue breakdown retrieved for period: {period}")
        return jsonify({'success': True, 'data': breakdown_data}), 200

    except Exception as e:
        logger.exception("Error retrieving revenue breakdown")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving revenue breakdown'
        }), 500
    
# -------------------- Revenue Transactions --------------------
@admin_bp.route('/revenue/transactions', methods=['GET'])
@admin_required
def get_revenue_transactions():
    """
    Get detailed revenue transactions.
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        status = request.args.get('status')
        sort_by = request.args.get('sort_by', 'date')

        query = Transaction.query  # assuming you have a Transaction model

        if status:
            query = query.filter_by(status=status)

        # Sorting
        if sort_by == 'amount':
            query = query.order_by(Transaction.amount.desc())
        else:  # default sort by date
            query = query.order_by(Transaction.created_at.desc())

        total = query.count()
        transactions = query.offset((page - 1) * limit).limit(limit).all()

        transactions_data = []
        for t in transactions:
            transactions_data.append({
                "transaction_id": t.id,
                "delivery_id": t.delivery_id,
                "amount": float(t.amount),
                "type": t.type,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None
            })

        logger.info(f"Revenue transactions retrieved - Page: {page}, Status: {status}")
        return jsonify({
            'success': True,
            'data': transactions_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total
            }
        }), 200

    except Exception as e:
        logger.exception("Error retrieving revenue transactions")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving revenue transactions'
        }), 500


# -------------------- Revenue Analytics --------------------
@admin_bp.route('/revenue/analytics', methods=['GET'])
@admin_required
def get_revenue_analytics():
    """
    Get detailed revenue analytics and insights.
    """
    try:
        period = request.args.get('period', 'monthly')

        from datetime import datetime, timedelta
        now = datetime.utcnow()

        # Calculate date range based on period
        if period == 'daily':
            start_date = now - timedelta(days=1)
        elif period == 'weekly':
            start_date = now - timedelta(weeks=1)
        elif period == 'yearly':
            start_date = now - timedelta(days=365)
        else:  # monthly
            start_date = now - timedelta(days=30)

        query = Delivery.query.filter(Delivery.created_at >= start_date)

        total_revenue = db.session.query(db.func.sum(Delivery.price)).filter(
            Delivery.created_at >= start_date
        ).scalar() or 0.0

        # Average daily revenue
        days = (now - start_date).days or 1
        average_daily_revenue = total_revenue / days

        # Peak day (highest revenue day in period)
        peak_day = db.session.query(
            db.func.date(Delivery.created_at),
            db.func.sum(Delivery.price).label("day_revenue")
        ).filter(
            Delivery.created_at >= start_date
        ).group_by(
            db.func.date(Delivery.created_at)
        ).order_by(
            db.desc("day_revenue")
        ).first()

        peak_day_data = {
            "date": peak_day[0].isoformat() if peak_day else None,
            "revenue": float(peak_day[1]) if peak_day else 0.0
        }

        # Trends (example: revenue per week/day)
        trends = []
        trend_rows = db.session.query(
            db.func.date(Delivery.created_at),
            db.func.sum(Delivery.price)
        ).filter(
            Delivery.created_at >= start_date
        ).group_by(
            db.func.date(Delivery.created_at)
        ).all()
        for row in trend_rows:
            trends.append({"date": row[0].isoformat(), "revenue": float(row[1])})

        # Top routes (example: most frequent pickup->delivery pairs)
        top_routes = db.session.query(
            Delivery.pickup_location,
            Delivery.delivery_location,
            db.func.count(Delivery.id).label("count")
        ).filter(
            Delivery.created_at >= start_date
        ).group_by(
            Delivery.pickup_location, Delivery.delivery_location
        ).order_by(
            db.desc("count")
        ).limit(5).all()
        top_routes_data = [
            {"pickup": r[0], "delivery": r[1], "count": r[2]} for r in top_routes
        ]

        # Top drivers (by revenue)
        top_drivers = db.session.query(
            Delivery.driver_id,
            db.func.sum(Delivery.price).label("driver_revenue")
        ).filter(
            Delivery.created_at >= start_date
        ).group_by(
            Delivery.driver_id
        ).order_by(
            db.desc("driver_revenue")
        ).limit(5).all()
        top_drivers_data = [
            {"driver_id": d[0], "revenue": float(d[1])} for d in top_drivers
        ]

        analytics_data = {
            "total_revenue": float(total_revenue),
            "average_daily_revenue": float(average_daily_revenue),
            "peak_day": peak_day_data,
            "trends": trends,
            "top_routes": top_routes_data,
            "top_drivers": top_drivers_data
        }

        logger.info(f"Revenue analytics retrieved for period: {period}")
        return jsonify({'success': True, 'data': analytics_data}), 200

    except Exception as e:
        logger.exception("Error retrieving revenue analytics")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving revenue analytics'
        }), 500

# -------------------- Driver Payout Information --------------------
@admin_bp.route('/revenue/payout', methods=['GET'])
@admin_required
def get_payout_info():
    """
    Get driver payout information.
    """
    try:
        driver_id = request.args.get('driver_id')
        status = request.args.get('status')

        query = Payout.query  # assuming you have a Payout model

        if driver_id:
            query = query.filter_by(driver_id=driver_id)
        if status:
            query = query.filter_by(status=status)

        payouts = query.order_by(Payout.scheduled_date.desc()).all()

        payout_data = []
        for p in payouts:
            payout_data.append({
                "payout_id": p.id,
                "driver_id": p.driver_id,
                "amount": float(p.amount),
                "status": p.status,
                "period": p.period,
                "scheduled_date": p.scheduled_date.isoformat() if p.scheduled_date else None,
                "completed_date": p.completed_date.isoformat() if p.completed_date else None
            })

        logger.info(f"Payout information retrieved for driver: {driver_id}")
        return jsonify({'success': True, 'data': payout_data}), 200

    except Exception as e:
        logger.exception("Error retrieving payout information")
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving payout information'
        }), 500


# -------------------- Health Check --------------------
@admin_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint (no authentication required).
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# -------------------- Error Handlers --------------------
@admin_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    logger.error(f"Bad request: {str(error)}")
    return jsonify({'success': False, 'message': 'Bad request'}), 400


@admin_bp.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors"""
    logger.error(f"Unauthorized access attempt: {str(error)}")
    return jsonify({'success': False, 'message': 'Unauthorized'}), 401


@admin_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    logger.error(f"Resource not found: {str(error)}")
    return jsonify({'success': False, 'message': 'Resource not found'}), 404


@admin_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'success': False, 'message': 'Internal server error'}), 500