import logging
from flask import Blueprint, render_template, g, redirect, url_for

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page"""
    # If user is not logged in, redirect to login
    if not g.user:
        return redirect(url_for('auth.login'))
    
    return render_template('index.html')