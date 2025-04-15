import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from werkzeug.utils import secure_filename

from database import db
from utils.upload import save_photo, save_video
from models import User, Story, StoryView
from routes.auth_old import login_required

# Set up logger
logger = logging.getLogger(__name__)

# Create Blueprint
story_bp = Blueprint('story', __name__)

@story_bp.route('/stories')
@login_required
def stories():
    return render_template('story.html')

@story_bp.route('/api/stories')
@login_required
def get_stories():
    # Get IDs of friends and people the user follows
    from models import Friend, Follower

    friend_ids = [f.friend_id for f in Friend.query.filter_by(user_id=g.user.id, status='accepted').all()]
    friend_ids += [f.user_id for f in Friend.query.filter_by(friend_id=g.user.id, status='accepted').all()]
    following_ids = [f.user_id for f in g.user.following.all()]

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

        story_data = story.serialize()
        story_data['viewed'] = viewed

        stories_by_user[story.user_id]['stories'].append(story_data)

    # Convert to list for JSON response
    result = list(stories_by_user.values())

    # Sort by whether user has viewed all stories
    result.sort(key=lambda x: all(s['viewed'] for s in x['stories']))

    return jsonify({
        'story_users': result
    })

@story_bp.route('/story/create', methods=['GET', 'POST'])
@login_required
def create_story():
    if request.method == 'POST':
        story_type = request.form.get('story_type')
        content = request.form.get('content', '').strip()

        # Set expiry time (24 hours from now)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        if story_type == 'text':
            if not content:
                flash('Text story cannot be empty', 'danger')
                return redirect(url_for('story.create_story'))

            # Create text story
            story = Story(
                user_id=g.user.id,
                story_type='text',
                content=content,
                expires_at=expires_at
            )
            db.session.add(story)

        elif story_type == 'photo':
            if 'photo' not in request.files:
                flash('No photo selected', 'danger')
                return redirect(url_for('story.create_story'))

            photo = request.files['photo']

            if photo.filename == '':
                flash('No photo selected', 'danger')
                return redirect(url_for('story.create_story'))

            # Save the photo
            media_path = save_photo(photo)
            if not media_path:
                flash('Invalid file type', 'danger')
                return redirect(url_for('story.create_story'))
            media_url = url_for('static', filename=media_path)

            # Create photo story
            story = Story(
                user_id=g.user.id,
                story_type='photo',
                content=content,  # Caption
                media_url=media_url,
                expires_at=expires_at
            )
            db.session.add(story)

        elif story_type == 'video':
            if 'video' not in request.files:
                flash('No video selected', 'danger')
                return redirect(url_for('story.create_story'))

            video = request.files['video']

            if video.filename == '':
                flash('No video selected', 'danger')
                return redirect(url_for('story.create_story'))

            # Save the video
            media_path = save_video(video)
            if not media_path:
                flash('Invalid file type', 'danger')
                return redirect(url_for('story.create_story'))
            media_url = url_for('static', filename=media_path)

            # Create video story
            story = Story(
                user_id=g.user.id,
                story_type='video',
                content=content,  # Caption
                media_url=media_url,
                expires_at=expires_at
            )
            db.session.add(story)

        else:
            flash('Invalid story type', 'danger')
            return redirect(url_for('story.create_story'))

        db.session.commit()

        flash('Story created successfully', 'success')
        return redirect(url_for('story.stories'))

    return render_template('create_story.html')

@story_bp.route('/api/story/<int:story_id>/view', methods=['POST'])
@login_required
def view_story(story_id):
    story = Story.query.get_or_404(story_id)

    # Check if user has already viewed this story
    existing_view = StoryView.query.filter_by(story_id=story_id, user_id=g.user.id).first()

    if not existing_view:
        # Create view record
        view = StoryView(story_id=story_id, user_id=g.user.id)
        db.session.add(view)
        db.session.commit()

    return jsonify({'success': True})

# Blueprint is registered in create_app.py
