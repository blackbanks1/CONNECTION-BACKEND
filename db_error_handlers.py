import logging
from flask import jsonify
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from app import db   # adjust import to your app structure

logger = logging.getLogger(__name__)

def register_db_error_handlers(app):
    """
    Register global error handlers for database errors.
    Call this inside create_app() after initializing Flask and SQLAlchemy.
    """

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e):
        db.session.rollback()
        logger.exception("IntegrityError: %s", e)
        return jsonify({
            "success": False,
            "error": "IntegrityError",
            "message": "Duplicate or invalid data. Please check your input."
        }), 400

    @app.errorhandler(OperationalError)
    def handle_operational_error(e):
        logger.exception("OperationalError: %s", e)
        return jsonify({
            "success": False,
            "error": "OperationalError",
            "message": "Database connection failed or unavailable."
        }), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(e):
        db.session.rollback()
        logger.exception("SQLAlchemyError: %s", e)
        return jsonify({
            "success": False,
            "error": "SQLAlchemyError",
            "message": "An unexpected database error occurred."
        }), 500