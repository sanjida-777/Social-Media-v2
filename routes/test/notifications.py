import logging
from flask import render_template, flash
from routes.test import test_bp

# Set up logger
logger = logging.getLogger(__name__)

@test_bp.route('/notifications')
def notifications_demo():
    """Demo page for the notification system"""
    # Add some flash messages for demonstration
    flash('Welcome to the notification system demo!', 'info')
    flash('This is a success message', 'success')
    flash('This is a warning message', 'warning')
    flash('This is an error message', 'danger')
    
    return render_template('test/notifications.html')
