import logging
from flask import render_template, g
from routes.main import main_bp

# Set up logger
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    """Home page"""
    logger.debug("Rendering home page")
    return render_template('feed/index.html')
