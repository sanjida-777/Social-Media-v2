import logging
from flask import redirect, url_for
from routes.main import main_bp

# Set up logger
logger = logging.getLogger(__name__)

@main_bp.route('/messages')
def messages_redirect():
    """Redirect to messages inbox"""
    logger.debug("Redirecting to messages inbox")
    return redirect(url_for('auth.messages_inbox'))
