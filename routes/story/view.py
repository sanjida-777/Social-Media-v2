import logging
from datetime import datetime, timezone
from flask import render_template, g, request, jsonify, abort
from routes.story import story_bp
from routes.auth_old import login_required
from models import Story, User, Friend, Follower

# Set up logger
logger = logging.getLogger(__name__)

@story_bp.route('/')
@login_required
def view_stories():
    """View all stories"""
    return render_template('story/index.html')

@story_bp.route('/<int:story_id>')
@login_required
def view_story(story_id):
    """View a specific story"""
    story = Story.query.get_or_404(story_id)
    
    # Check if story has expired
    if story.expires_at < datetime.now(timezone.utc):
        abort(404)
    
    # Check if user can view this story
    if story.user_id != g.user.id:
        # Check if user is friends with story author
        is_friend = Friend.query.filter(
            ((Friend.user_id == g.user.id) & (Friend.friend_id == story.user_id)) |
            ((Friend.user_id == story.user_id) & (Friend.friend_id == g.user.id))
        ).filter_by(status='accepted').first() is not None
        
        # Check if user follows story author
        is_following = Follower.query.filter_by(
            follower_id=g.user.id,
            user_id=story.user_id
        ).first() is not None
        
        if not (is_friend or is_following):
            abort(403)
    
    # Get story author
    author = User.query.get(story.user_id)
    
    return render_template('story/view.html', story=story, author=author)

@story_bp.route('/api/stories')
@login_required
def get_stories():
    """Get stories for the current user"""
    try:
        # Get IDs of friends and people the user follows
        friend_ids = [f.friend_id for f in Friend.query.filter_by(user_id=g.user.id, status='accepted').all()]
        friend_ids += [f.user_id for f in Friend.query.filter_by(friend_id=g.user.id, status='accepted').all()]
        following_ids = [f.user_id for f in Follower.query.filter_by(follower_id=g.user.id).all()]
        
        # Combine IDs and add the user's own ID
        story_user_ids = list(set(friend_ids + following_ids + [g.user.id]))
        
        # Get active stories from these users
        stories = Story.query.filter(
            Story.user_id.in_(story_user_ids),
            Story.expires_at > datetime.now(timezone.utc)
        ).order_by(Story.created_at.desc()).all()
        
        # Group stories by user
        stories_by_user = {}
        for story in stories:
            if story.user_id not in stories_by_user:
                # Get user info
                user = User.query.get(story.user_id)
                stories_by_user[story.user_id] = {
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'profile_pic': user.profile_pic
                    },
                    'stories': []
                }
            
            # Add story to user's stories
            stories_by_user[story.user_id]['stories'].append({
                'id': story.id,
                'content': story.content,
                'story_type': story.story_type,
                'media_url': story.media_url,
                'created_at': story.created_at.isoformat(),
                'expires_at': story.expires_at.isoformat()
            })
        
        # Convert to list for JSON response
        result = list(stories_by_user.values())
        
        return jsonify({
            'success': True,
            'stories': result
        })
    
    except Exception as e:
        logger.error(f"Error getting stories: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting stories: {str(e)}'
        }), 500
