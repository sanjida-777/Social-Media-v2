import logging
from datetime import datetime, timezone, timedelta
from flask import render_template, g, request, jsonify, redirect, url_for
from routes.story import story_bp
from routes.auth_old import login_required
from database import db
from models import Story, User
from utils.multi_upload import save_multi_uploads

# Set up logger
logger = logging.getLogger(__name__)

@story_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_story():
    """Create a new story"""
    if request.method == 'GET':
        return render_template('story/create.html')
    
    # Handle POST request
    try:
        # Get story content
        content = request.form.get('content', '')
        story_type = request.form.get('story_type', 'text')
        
        # Create story
        story = Story(
            user_id=g.user.id,
            content=content,
            story_type=story_type,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        
        # Handle media upload if any
        if 'media' in request.files and request.files['media'].filename:
            file = request.files['media']
            
            # Upload to external services
            urls = save_multi_uploads(file)
            if urls:
                # Use the first successful URL
                story.media_url = urls[0]
                story.story_type = 'image'
        
        db.session.add(story)
        db.session.commit()
        
        # Return JSON response for API requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Story created successfully',
                'story_id': story.id
            })
        
        # Redirect to stories page for regular requests
        return redirect(url_for('story.view_stories'))
    
    except Exception as e:
        logger.error(f"Error creating story: {str(e)}")
        db.session.rollback()
        
        # Return JSON response for API requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': f'Error creating story: {str(e)}'
            }), 500
        
        # Redirect to stories page with error for regular requests
        return redirect(url_for('story.view_stories'))
