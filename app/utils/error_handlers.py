# app/error_handlers.py
"""
Centralized Flask error handlers.
Keeps routes.py files clean and guarantees consistent JSON/HTML responses.
"""
from flask import render_template, jsonify, request, current_app
from app.utils.logging import get_logger
from app.utils.exceptions import OshkeloshError, AuthorizationError

log = get_logger(__name__)

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify(error="not_found"), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        log.exception("Unhandled exception")  # full traceback
        if request.accept_mimetypes.accept_json:
            return jsonify(error="internal_server_error"), 500
        return render_template("errors/500.html"), 500

    # Handle your custom exceptions
    @app.errorhandler(OshkeloshError)
    def handle_oshkelosh_error(error: OshkeloshError):
        log.warning("OshkeloshError: %s | payload=%s", error, error.payload)
        response = {"error": error.message, "details": error.payload}
        return jsonify(response), error.status_code

    # Special case — you already had this in __init__.py
    @app.errorhandler(AuthorizationError)
    def handle_auth_error(error):
        from flask import flash, redirect, url_for
        from app import models

        admins = models.User.get(role="ADMIN")
        for admin in admins:
            # TODO: send internal alert / create message
            pass

        flash("Unauthorized action detected — you have been logged out.", "warning")
        return redirect(url_for("user.logout"))

    log.info("Error handlers registered")

