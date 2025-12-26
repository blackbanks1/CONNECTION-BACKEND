import logging
from flask import jsonify, current_app, request  # ADDED: request import
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from models import db

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
            "message": "Duplicate or invalid data. Please check your input.",
            "details": str(e.orig) if hasattr(e, 'orig') else str(e)
        }), 400

    @app.errorhandler(OperationalError)
    def handle_operational_error(e):
        logger.exception("OperationalError: %s", e)
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "OperationalError",
            "message": "Database connection failed or unavailable. Please try again.",
            "details": str(e.orig) if hasattr(e, 'orig') else str(e)
        }), 503

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(e):
        db.session.rollback()
        logger.exception("SQLAlchemyError: %s", e)
        return jsonify({
            "success": False,
            "error": "SQLAlchemyError",
            "message": "An unexpected database error occurred.",
            "details": str(e.orig) if hasattr(e, 'orig') else str(e)
        }), 500

    # Additional error handlers for common issues
    @app.errorhandler(404)
    def handle_not_found(e):
        logger.warning("404 Not Found: %s", request.path)
        return jsonify({
            "success": False,
            "error": "NotFound",
            "message": "The requested resource was not found."
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        logger.warning("405 Method Not Allowed: %s", request.method)
        return jsonify({
            "success": False,
            "error": "MethodNotAllowed",
            "message": "The HTTP method is not allowed for this endpoint."
        }), 405

    @app.errorhandler(413)
    def handle_payload_too_large(e):
        logger.warning("413 Payload Too Large")
        return jsonify({
            "success": False,
            "error": "PayloadTooLarge",
            "message": "The request payload is too large."
        }), 413

    @app.errorhandler(429)
    def handle_too_many_requests(e):
        logger.warning("429 Too Many Requests from %s", request.remote_addr)
        return jsonify({
            "success": False,
            "error": "TooManyRequests",
            "message": "Too many requests. Please try again later."
        }), 429

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """Catch-all for any unhandled exceptions."""
        db.session.rollback()
        logger.exception("Unhandled exception: %s", e)
        
        # Don't expose internal errors in production
        if current_app.config.get('DEBUG', False):
            message = f"{type(e).__name__}: {str(e)}"
        else:
            message = "An internal server error occurred."
        
        return jsonify({
            "success": False,
            "error": "InternalServerError",
            "message": message
        }), 500

    # Special handler for missing CSRF token (if using Flask-WTF)
    @app.errorhandler(400)
    def handle_bad_request(e):
        """Handle 400 errors, including CSRF token missing."""
        logger.warning("400 Bad Request: %s", str(e))
        
        # Check if it's a CSRF error
        description = str(e.description) if hasattr(e, 'description') else str(e)
        if 'CSRF' in description or 'csrf' in description.lower():
            return jsonify({
                "success": False,
                "error": "CSRFTokenMissing",
                "message": "CSRF token is missing or invalid."
            }), 400
        
        return jsonify({
            "success": False,
            "error": "BadRequest",
            "message": "Bad request. Please check your input."
        }), 400