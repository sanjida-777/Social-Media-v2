import logging
from flask import render_template, flash
from routes.test import test_bp

# Set up logger
logger = logging.getLogger(__name__)

@test_bp.route('/upload')
def upload_demo():
    """Demo page for the image upload functionality"""
    # Add some flash messages for demonstration
    flash('Welcome to the image upload demo!', 'info')
    flash('Images will be uploaded to external services like Imgur, Catbox, etc.', 'primary')
    
    return render_template('test/upload.html')
