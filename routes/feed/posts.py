import logging
from flask import render_template, g, request, redirect, url_for, flash
from routes.feed import feed_bp
from routes.auth_old import login_required
from models import Post, User, Like, Comment, PostMedia

# Set up logger
logger = logging.getLogger(__name__)

@feed_bp.route('/')
@login_required
def index():
    """Feed index page"""
    return render_template('feed/index.html')

@feed_bp.route('/post/<int:post_id>')
@login_required
def view_post(post_id):
    """View a single post"""
    post = Post.query.get_or_404(post_id)
    
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
    
    # Get comments
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.created_at.desc()).all()
    
    # Format comments
    formatted_comments = []
    for comment in comments:
        # Get comment author
        comment_author = User.query.get(comment.user_id)
        
        formatted_comments.append({
            'id': comment.id,
            'author': comment_author,
            'content': comment.content,
            'created_at': comment.created_at
        })
    
    return render_template(
        'feed/post.html',
        post=post,
        author=author,
        media_urls=media_urls,
        like_count=like_count,
        liked_by_user=liked_by_user,
        comments=formatted_comments
    )
