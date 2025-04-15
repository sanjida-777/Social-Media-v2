import logging
from flask import jsonify, request, g
from models import User, Friend, Follower, Story, StoryView
from datetime import datetime, timedelta
from routes.api import api_bp

# Set up logger
logger = logging.getLogger(__name__)

@api_bp.route('/stories', methods=['GET'])
def get_stories():
    """Get stories for the current user"""
    try:
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get IDs of friends and people the user follows
        friend_ids = [f.friend_id for f in Friend.query.filter_by(user_id=g.user.id, status='accepted').all()]
        friend_ids += [f.user_id for f in Friend.query.filter_by(friend_id=g.user.id, status='accepted').all()]
        following_ids = [f.user_id for f in Follower.query.filter_by(follower_id=g.user.id).all()]

        # Combine IDs and add the user's own ID
        story_user_ids = list(set(friend_ids + following_ids + [g.user.id]))

        # Get active stories from these users (not expired)
        now = datetime.utcnow()
        active_stories = Story.query.filter(
            Story.user_id.in_(story_user_ids),
            Story.expires_at > now
        ).order_by(Story.created_at.desc()).all()

        # Group stories by user
        stories_by_user = {}
        for story in active_stories:
            if story.user_id not in stories_by_user:
                stories_by_user[story.user_id] = {
                    'user': User.query.get(story.user_id).serialize(),
                    'stories': []
                }

            # Check if user has viewed this story
            viewed = StoryView.query.filter_by(story_id=story.id, user_id=g.user.id).first() is not None

            story_data = {
                'id': story.id,
                'user_id': story.user_id,
                'story_type': story.story_type,
                'content': story.content,
                'media_url': story.media_url,
                'created_at': story.created_at.isoformat(),
                'expires_at': story.expires_at.isoformat(),
                'viewed': viewed
            }

            stories_by_user[story.user_id]['stories'].append(story_data)

        # Convert to list for JSON response
        result = list(stories_by_user.values())

        # Sort by whether user has viewed all stories
        result.sort(key=lambda x: all(s['viewed'] for s in x['stories']))

        return jsonify({
            'success': True,
            'story_users': result
        })

    except Exception as e:
        logger.error(f"Error getting stories: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting stories'
        }), 500
