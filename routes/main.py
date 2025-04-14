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
    
    # Get stories (most recent from friends and followed users)
    stories = []
    
    # Get posts for the feed (from friends and followed users)
    posts = []
    
    # Get friend suggestions
    friend_suggestions = []
    
    # Get trending tags
    trending_tags = []
    
    # Configuration values 
    from config import get_site_name
    site_name = get_site_name()
    
    return render_template(
        'main/index.html',
        site_name=site_name,
        stories=stories,
        posts=posts,
        friend_suggestions=friend_suggestions,
        trending_tags=trending_tags
    )