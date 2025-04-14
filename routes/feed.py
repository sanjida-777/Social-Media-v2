import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from sqlalchemy import desc, func

from database import db
from utils.upload import save_photo
from flask import current_app
from models import User, Post, PostMedia, PostLike, Comment, Story, Friend, Follower, Notification
from routes.auth import login_required
from utils.feed_algorithm import rank_posts

# Set up logger
logger = logging.getLogger(__name__)

# Create Blueprint
feed_bp = Blueprint('feed', __name__)

@feed_bp.route('/')
def index():
    if g.user:
        # Show feed for logged in users
        return render_template('feed.html')
    else:
        # Redirect to login for guests
        return redirect(url_for('auth.login'))

@feed_bp.route('/api/feed')
@login_required
def get_feed():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Get IDs of friends and people the user follows
    friend_ids = [f.friend_id for f in Friend.query.filter_by(user_id=g.user.id, status='accepted').all()]
    friend_ids += [f.user_id for f in Friend.query.filter_by(friend_id=g.user.id, status='accepted').all()]
    following_ids = [f.user_id for f in g.user.following.all()]

    # Combine IDs and add the user's own ID
    feed_user_ids = list(set(friend_ids + following_ids + [g.user.id]))

    # Get posts from these users
    base_query = Post.query.filter(Post.user_id.in_(feed_user_ids))

    # Get total count for pagination
    total_posts = base_query.count()

    # Get posts for the current page
    posts = base_query.order_by(Post.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    # Rank posts based on personalized algorithm (if enough posts)
    if len(posts) > 5:
        posts = rank_posts(posts, g.user.id)

    # Serialize posts
    serialized_posts = [post.serialize() for post in posts]

    # Add liked status for each post
    for post_data in serialized_posts:
        post_data['liked_by_user'] = PostLike.query.filter_by(post_id=post_data['id'], user_id=g.user.id).first() is not None

    return jsonify({
        'posts': serialized_posts,
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_posts': total_posts,
            'total_pages': (total_posts + per_page - 1) // per_page
        }
    })

@feed_bp.route('/post/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        if request.is_json:
            # Handle API post creation
            data = request.get_json()
            content = data.get('content', '').strip()

            if not content and 'media' not in request.files:
                return jsonify({'error': 'Post must contain text or media'}), 400

            # Create the post
            post = Post(user_id=g.user.id, content=content)
            db.session.add(post)
            db.session.flush()  # Get post ID without committing

            # Handle media files if any (this part would be handled differently in a real API)
            # For this example, media would be handled separately through file uploads

            db.session.commit()

            return jsonify({
                'success': True,
                'post': post.serialize()
            })
        else:
            # Handle form post creation
            content = request.form.get('content', '').strip()

            if not content and 'media' not in request.files:
                flash('Post must contain text or media', 'danger')
                return redirect(url_for('feed.create_post'))

            # Create the post
            post = Post(user_id=g.user.id, content=content)
            db.session.add(post)
            db.session.flush()  # Get post ID without committing

            # Handle media files if any
            media_files = request.files.getlist('media')
            for media_file in media_files:
                if media_file and media_file.filename:
                    media_path = save_photo(media_file)
                    if not media_path:
                        continue
                    media_url = url_for('static', filename=media_path)
                    post_media = PostMedia(
                        post_id=post.id,
                        media_type='image',
                        media_url=media_url
                    )
                    db.session.add(post_media)

            db.session.commit()

            flash('Post created successfully', 'success')
            return redirect(url_for('feed.index'))

    return render_template('create_post.html')

@feed_bp.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)

@feed_bp.route('/api/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)

    # Check if user already liked the post
    existing_like = PostLike.query.filter_by(post_id=post_id, user_id=g.user.id).first()

    if existing_like:
        # Unlike the post
        db.session.delete(existing_like)
        db.session.commit()
        return jsonify({'success': True, 'action': 'unliked', 'likes': post.likes.count()})
    else:
        # Like the post
        like = PostLike(post_id=post_id, user_id=g.user.id)
        db.session.add(like)
        db.session.commit()

        # Create notification for post owner (if not self)
        if post.user_id != g.user.id:
            notification = Notification(
                user_id=post.user_id,
                notification_type='like',
                sender_id=g.user.id,
                reference_id=post_id,
                content=f"{g.user.username} liked your post"
            )
            db.session.add(notification)
            db.session.commit()

        return jsonify({'success': True, 'action': 'liked', 'likes': post.likes.count()})

@feed_bp.route('/api/post/<int:post_id>/comment', methods=['POST'])
@login_required
def comment_post(post_id):
    post = Post.query.get_or_404(post_id)

    if request.is_json:
        data = request.get_json()
        content = data.get('content', '').strip()
    else:
        content = request.form.get('content', '').strip()

    if not content:
        return jsonify({'error': 'Comment cannot be empty'}), 400

    # Create the comment
    comment = Comment(
        post_id=post_id,
        user_id=g.user.id,
        content=content
    )
    db.session.add(comment)
    db.session.commit()

    # Create notification for post owner (if not self)
    if post.user_id != g.user.id:
        notification = Notification(
            user_id=post.user_id,
            notification_type='comment',
            sender_id=g.user.id,
            reference_id=post_id,
            content=f"{g.user.username} commented on your post"
        )
        db.session.add(notification)
        db.session.commit()

    return jsonify({
        'success': True,
        'comment': comment.serialize()
    })

@feed_bp.route('/api/post/<int:post_id>/comments')
def get_comments(post_id):
    post = Post.query.get_or_404(post_id)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Get comments for the post with pagination
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc())
    total_comments = comments.count()

    comments = comments.offset((page - 1) * per_page).limit(per_page).all()

    # Serialize comments
    serialized_comments = [comment.serialize() for comment in comments]

    return jsonify({
        'comments': serialized_comments,
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_comments': total_comments,
            'total_pages': (total_comments + per_page - 1) // per_page
        }
    })

@feed_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()

    if not query:
        return render_template('search.html', results=None, query=None)

    # Search for users
    users = User.query.filter(
        User.username.ilike(f'%{query}%') |
        User.bio.ilike(f'%{query}%')
    ).limit(20).all()

    # Search for posts
    posts = Post.query.filter(
        Post.content.ilike(f'%{query}%')
    ).order_by(Post.created_at.desc()).limit(20).all()

    return render_template('search.html', users=users, posts=posts, query=query)

@feed_bp.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'users': [], 'posts': []})

    # Search for users
    users = User.query.filter(
        User.username.ilike(f'%{query}%') |
        User.bio.ilike(f'%{query}%')
    ).limit(20).all()

    # Search for posts
    posts = Post.query.filter(
        Post.content.ilike(f'%{query}%')
    ).order_by(Post.created_at.desc()).limit(20).all()

    return jsonify({
        'users': [user.serialize() for user in users],
        'posts': [post.serialize() for post in posts]
    })

# The blueprint will be registered in app.py
