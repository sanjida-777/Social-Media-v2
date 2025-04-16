import logging
import os
from datetime import datetime, timezone
from flask import jsonify, request, g, current_app
from werkzeug.utils import secure_filename
from database import db
from models import User, Post, Friend, Follower, Comment, Like, PostMedia
from routes.api import api_bp
from routes.auth_old import login_required
from utils.multi_upload import save_multi_uploads

# Set up logger
logger = logging.getLogger(__name__)

@api_bp.route('/feed', methods=['GET'])
def get_feed():
    """Get feed data for the current user"""
    try:
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get page parameter for pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Get IDs of friends and people the user follows
        friend_ids = [f.friend_id for f in Friend.query.filter_by(user_id=g.user.id, status='accepted').all()]
        friend_ids += [f.user_id for f in Friend.query.filter_by(friend_id=g.user.id, status='accepted').all()]
        following_ids = [f.user_id for f in Follower.query.filter_by(follower_id=g.user.id).all()]

        # Combine IDs and add the user's own ID
        feed_user_ids = list(set(friend_ids + following_ids + [g.user.id]))

        # Get posts from these users
        posts_query = Post.query.filter(Post.user_id.in_(feed_user_ids))

        # Get total count for pagination
        total_posts = posts_query.count()

        # Get posts for the current page
        posts = posts_query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Format posts
        formatted_posts = []
        for post in posts.items:
            # Get post author
            author = User.query.get(post.user_id)

            # Get post media
            media = PostMedia.query.filter_by(post_id=post.id).all()
            media_urls = [m.media_url for m in media]

            # Get like count
            like_count = Like.query.filter_by(post_id=post.id).count()

            # Check if current user liked the post
            liked_by_user = False
            if g.user:
                liked_by_user = Like.query.filter_by(
                    post_id=post.id,
                    user_id=g.user.id
                ).first() is not None

            # Get comment count
            comment_count = Comment.query.filter_by(post_id=post.id).count()

            formatted_posts.append({
                'id': post.id,
                'user_id': post.user_id,
                'author': author.username,
                'profile_pic': author.profile_pic,
                'content': post.content,
                'created_at': post.created_at.isoformat(),
                'like_count': like_count,
                'comment_count': comment_count,
                'liked_by_user': liked_by_user,
                'media': media_urls
            })

        # Return response
        return jsonify({
            'success': True,
            'posts': formatted_posts,
            'pagination': {
                'current_page': posts.page,
                'total_pages': posts.pages,
                'total_items': posts.total,
                'per_page': posts.per_page
            }
        })

    except Exception as e:
        logger.error(f"Error getting feed data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting feed data'
        }), 500

@api_bp.route('/posts', methods=['POST'])
@login_required
def create_post():
    """Create a new post"""
    try:
        # Check if user is authenticated
        if not g.user:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401

        # Get post content from form data or JSON
        content = ''
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            content = data.get('content', '')
        else:
            content = request.form.get('content', '')

        # Create new post
        post = Post(
            user_id=g.user.id,
            content=content,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(post)
        db.session.flush()  # Get post ID without committing

        # Handle media uploads if any
        media_urls = []
        if 'media' in request.files:
            files = request.files.getlist('media')
            for file in files:
                if file and file.filename:
                    # Upload to external services
                    urls = save_multi_uploads(file)
                    if urls:
                        # Use the first successful URL
                        media_url = urls[0]
                        media_urls.append(media_url)

                        # Create post media entry
                        media = PostMedia(
                            post_id=post.id,
                            media_type='image',
                            media_url=media_url
                        )
                        db.session.add(media)

        # Commit changes
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Post created successfully',
            'post_id': post.id,
            'media_urls': media_urls
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating post: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating post: {str(e)}'
        }), 500

@api_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific post by ID"""
    try:
        post = Post.query.get(post_id)
        if not post:
            return jsonify({
                'success': False,
                'message': 'Post not found'
            }), 404

        # Get post author
        author = User.query.get(post.user_id)

        # Get post media
        media = PostMedia.query.filter_by(post_id=post.id).all()
        media_urls = [m.media_url for m in media]

        # Get like count
        like_count = Like.query.filter_by(post_id=post.id).count()

        # Check if current user liked the post
        liked_by_user = False
        if g.user:
            liked_by_user = Like.query.filter_by(
                post_id=post.id,
                user_id=g.user.id
            ).first() is not None

        # Get comment count
        comment_count = Comment.query.filter_by(post_id=post.id).count()

        # Format post
        formatted_post = {
            'id': post.id,
            'user_id': post.user_id,
            'author': author.username,
            'profile_pic': author.profile_pic,
            'content': post.content,
            'created_at': post.created_at.isoformat(),
            'like_count': like_count,
            'comment_count': comment_count,
            'liked_by_user': liked_by_user,
            'media': media_urls
        }

        return jsonify({
            'success': True,
            'post': formatted_post
        })

    except Exception as e:
        logger.error(f"Error getting post: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting post: {str(e)}'
        }), 500

@api_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    """Delete a post"""
    try:
        post = Post.query.get(post_id)
        if not post:
            return jsonify({
                'success': False,
                'message': 'Post not found'
            }), 404

        # Check if user is the post author
        if post.user_id != g.user.id:
            return jsonify({
                'success': False,
                'message': 'You can only delete your own posts'
            }), 403

        # Delete post media
        PostMedia.query.filter_by(post_id=post.id).delete()

        # Delete post likes
        Like.query.filter_by(post_id=post.id).delete()

        # Delete post comments
        Comment.query.filter_by(post_id=post.id).delete()

        # Delete post
        db.session.delete(post)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Post deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting post: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting post: {str(e)}'
        }), 500

@api_bp.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    """Get comments for a post"""
    try:
        post = Post.query.get(post_id)
        if not post:
            return jsonify({
                'success': False,
                'message': 'Post not found'
            }), 404

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Get comments with pagination
        comments_query = Comment.query.filter_by(post_id=post_id)
        comments = comments_query.order_by(Comment.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Format comments
        formatted_comments = []
        for comment in comments.items:
            # Get comment author
            author = User.query.get(comment.user_id)

            formatted_comments.append({
                'id': comment.id,
                'post_id': comment.post_id,
                'user_id': comment.user_id,
                'author': author.username,
                'profile_pic': author.profile_pic,
                'content': comment.content,
                'created_at': comment.created_at.isoformat()
            })

        # Return response
        return jsonify({
            'success': True,
            'comments': formatted_comments,
            'pagination': {
                'current_page': comments.page,
                'total_pages': comments.pages,
                'total_items': comments.total,
                'per_page': comments.per_page
            }
        })

    except Exception as e:
        logger.error(f"Error getting comments: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting comments: {str(e)}'
        }), 500

@api_bp.route('/posts/<int:post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    """Add a comment to a post"""
    try:
        # Check if user is authenticated
        if not g.user:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401

        # Check if post exists
        post = Post.query.get(post_id)
        if not post:
            return jsonify({
                'success': False,
                'message': 'Post not found'
            }), 404

        # Get comment content
        data = request.get_json()
        if not data or not data.get('content'):
            return jsonify({
                'success': False,
                'message': 'Comment content is required'
            }), 400

        content = data.get('content')

        # Create comment
        comment = Comment(
            post_id=post_id,
            user_id=g.user.id,
            content=content,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(comment)
        db.session.commit()

        # Get comment author
        author = User.query.get(comment.user_id)

        # Format comment
        formatted_comment = {
            'id': comment.id,
            'post_id': comment.post_id,
            'user_id': comment.user_id,
            'author': author.username,
            'profile_pic': author.profile_pic,
            'content': comment.content,
            'created_at': comment.created_at.isoformat()
        }

        return jsonify({
            'success': True,
            'message': 'Comment added successfully',
            'comment': formatted_comment
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding comment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error adding comment: {str(e)}'
        }), 500

@api_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    try:
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({
                'success': False,
                'message': 'Comment not found'
            }), 404

        # Check if user is the comment author or post author
        post = Post.query.get(comment.post_id)
        if comment.user_id != g.user.id and post.user_id != g.user.id:
            return jsonify({
                'success': False,
                'message': 'You can only delete your own comments or comments on your posts'
            }), 403

        # Delete comment
        db.session.delete(comment)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Comment deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting comment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting comment: {str(e)}'
        }), 500

@api_bp.route('/posts/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    """Like a post"""
    try:
        # Check if user is authenticated
        if not g.user:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401

        # Check if post exists
        post = Post.query.get(post_id)
        if not post:
            return jsonify({
                'success': False,
                'message': 'Post not found'
            }), 404

        # Check if user already liked the post
        existing_like = Like.query.filter_by(
            post_id=post_id,
            user_id=g.user.id
        ).first()

        if existing_like:
            return jsonify({
                'success': False,
                'message': 'You already liked this post'
            }), 400

        # Create like
        like = Like(
            post_id=post_id,
            user_id=g.user.id,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(like)
        db.session.commit()

        # Get updated like count
        like_count = Like.query.filter_by(post_id=post_id).count()

        return jsonify({
            'success': True,
            'message': 'Post liked successfully',
            'like_count': like_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error liking post: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error liking post: {str(e)}'
        }), 500

@api_bp.route('/posts/<int:post_id>/unlike', methods=['POST'])
@login_required
def unlike_post(post_id):
    """Unlike a post"""
    try:
        # Check if user is authenticated
        if not g.user:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401

        # Check if post exists
        post = Post.query.get(post_id)
        if not post:
            return jsonify({
                'success': False,
                'message': 'Post not found'
            }), 404

        # Check if user liked the post
        existing_like = Like.query.filter_by(
            post_id=post_id,
            user_id=g.user.id
        ).first()

        if not existing_like:
            return jsonify({
                'success': False,
                'message': 'You have not liked this post'
            }), 400

        # Delete like
        db.session.delete(existing_like)
        db.session.commit()

        # Get updated like count
        like_count = Like.query.filter_by(post_id=post_id).count()

        return jsonify({
            'success': True,
            'message': 'Post unliked successfully',
            'like_count': like_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unliking post: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error unliking post: {str(e)}'
        }), 500
