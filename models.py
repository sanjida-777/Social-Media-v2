from datetime import datetime
import json
from flask_login import UserMixin
from sqlalchemy import event, func
from app import db

class FileUpload(db.Model):
    """
    Tracks files uploaded to multiple hosting services
    """
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    primary_url = db.Column(db.String(500), nullable=False)
    fallback_urls = db.Column(db.Text)  # JSON list of backup URLs
    media_type = db.Column(db.String(20), nullable=False)  # 'image' or 'video'
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_check = db.Column(db.DateTime, default=datetime.utcnow)
    is_available = db.Column(db.Boolean, default=True)

    def get_all_urls(self):
        """
        Returns a list of all URLs for this file
        """
        urls = [self.primary_url]
        if self.fallback_urls:
            try:
                fallback = json.loads(self.fallback_urls)
                if isinstance(fallback, list):
                    urls.extend(fallback)
            except:
                pass
        return urls

    def get_best_url(self):
        """
        Returns the best available URL for this file
        """
        from utils.multi_upload import get_first_working_url
        urls = self.get_all_urls()
        return get_first_working_url(urls) or self.primary_url

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True, default=None)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))  # For local auth backup if needed
    bio = db.Column(db.String(500))
    profile_pic = db.Column(db.String(200), default='/static/images/default-avatar.svg')
    cover_pic = db.Column(db.String(200), default='/static/images/default-cover.svg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_online = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # User's posts
    posts = db.relationship('Post', backref='author', lazy='dynamic')

    # User's stories
    stories = db.relationship('Story', backref='author', lazy='dynamic')

    # Friendship-related fields defined in Friend model relationships

    # User's notification settings
    notification_settings = db.Column(db.String(500), default=json.dumps({
        'post_likes': True,
        'comments': True,
        'friend_requests': True,
        'messages': True,
        'story_views': True
    }))

    def __repr__(self):
        return f'<User {self.username}>'

    def serialize(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'bio': self.bio,
            'profile_pic': self.profile_pic,
            'cover_pic': self.cover_pic,
            'last_online': self.last_online.isoformat() if self.last_online else None,
            'created_at': self.created_at.isoformat()
        }

class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined
    relationship_score = db.Column(db.Float, default=0.0)  # Calculated score based on interactions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('friend_requests_sent', lazy='dynamic'))
    friend = db.relationship('User', foreign_keys=[friend_id], backref=db.backref('friend_requests_received', lazy='dynamic'))

    # Add unique constraint to prevent duplicate friendships
    __table_args__ = (db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),)

    def __repr__(self):
        return f'<Friend {self.user_id} -> {self.friend_id} ({self.status})>'

class Follower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('followers', lazy='dynamic'))
    follower = db.relationship('User', foreign_keys=[follower_id], backref=db.backref('following', lazy='dynamic'))

    # Add unique constraint to prevent duplicate following
    __table_args__ = (db.UniqueConstraint('user_id', 'follower_id', name='unique_follower'),)

    def __repr__(self):
        return f'<Follower {self.follower_id} -> {self.user_id}>'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Media related to the post (handled via the PostMedia model)
    media = db.relationship('PostMedia', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    # Post engagement metrics
    likes = db.relationship('PostLike', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Post {self.id} by {self.user_id}>'

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'author': self.author.username,
            'profile_pic': self.author.profile_pic,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'media': [m.serialize() for m in self.media.all()],
            'like_count': self.likes.count(),
            'comment_count': self.comments.count()
        }

class PostMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # image, video
    media_url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PostMedia {self.id} - {self.media_type}>'

    def serialize(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'media_type': self.media_type,
            'media_url': self.media_url,
            'created_at': self.created_at.isoformat()
        }

class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationships
    user = db.relationship('User', backref=db.backref('post_likes', lazy='dynamic'))

    # Add unique constraint to prevent duplicate likes
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='unique_post_like'),)

    def __repr__(self):
        return f'<PostLike {self.user_id} -> {self.post_id}>'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define relationships
    user = db.relationship('User', backref=db.backref('comments', lazy='dynamic'))

    # Comment likes
    likes = db.relationship('CommentLike', backref='comment', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Comment {self.id} on {self.post_id} by {self.user_id}>'

    def serialize(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'user_id': self.user_id,
            'author': self.user.username,
            'profile_pic': self.user.profile_pic,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'like_count': self.likes.count()
        }

class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationships
    user = db.relationship('User', backref=db.backref('comment_likes', lazy='dynamic'))

    # Add unique constraint to prevent duplicate likes
    __table_args__ = (db.UniqueConstraint('comment_id', 'user_id', name='unique_comment_like'),)

    def __repr__(self):
        return f'<CommentLike {self.user_id} -> {self.comment_id}>'

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    story_type = db.Column(db.String(20), nullable=False)  # text, image, video
    content = db.Column(db.Text)  # For text stories or caption
    media_url = db.Column(db.String(255))  # For image or video stories
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # 24 hours after creation

    # Story views
    views = db.relationship('StoryView', backref='story', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Story {self.id} by {self.user_id} ({self.story_type})>'

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'author': self.author.username,
            'profile_pic': self.author.profile_pic,
            'story_type': self.story_type,
            'content': self.content,
            'media_url': self.media_url,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'view_count': self.views.count()
        }

class StoryView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationships
    user = db.relationship('User', backref=db.backref('story_views', lazy='dynamic'))

    # Add unique constraint to prevent duplicate views
    __table_args__ = (db.UniqueConstraint('story_id', 'user_id', name='unique_story_view'),)

    def __repr__(self):
        return f'<StoryView {self.user_id} -> {self.story_id}>'

class ChatGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_group = db.Column(db.Boolean, default=False)  # False for direct messages

    # Define relationships
    creator = db.relationship('User', backref=db.backref('created_chats', lazy='dynamic'))
    members = db.relationship('ChatMember', backref='chat_group', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('ChatMessage', backref='chat_group', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ChatGroup {self.id} - {self.name}>'

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_group': self.is_group,
            'members': [m.serialize() for m in self.members.all()],
            'last_message': self.messages.order_by(ChatMessage.created_at.desc()).first().serialize() if self.messages.count() > 0 else None
        }

class ChatMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat_group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # admin, member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_read = db.Column(db.DateTime)

    # Define relationships
    user = db.relationship('User', backref=db.backref('chat_memberships', lazy='dynamic'))

    # Add unique constraint to prevent duplicate memberships
    __table_args__ = (db.UniqueConstraint('chat_id', 'user_id', name='unique_chat_member'),)

    def __repr__(self):
        return f'<ChatMember {self.user_id} in {self.chat_id}>'

    def serialize(self):
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'user_id': self.user_id,
            'username': self.user.username,
            'profile_pic': self.user.profile_pic,
            'role': self.role,
            'joined_at': self.joined_at.isoformat(),
            'last_read': self.last_read.isoformat() if self.last_read else None
        }

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat_group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, image
    content = db.Column(db.Text)
    media_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    # Define relationships
    user = db.relationship('User', backref=db.backref('chat_messages', lazy='dynamic'))
    read_receipts = db.relationship('MessageReadReceipt', backref='message', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ChatMessage {self.id} in {self.chat_id} by {self.user_id}>'

    def serialize(self):
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'user_id': self.user_id,
            'sender': self.user.username,
            'profile_pic': self.user.profile_pic,
            'message_type': self.message_type,
            'content': self.content,
            'media_url': self.media_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_deleted': self.is_deleted,
            'read_by': [r.serialize() for r in self.read_receipts.all()]
        }

class MessageReadReceipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationships
    user = db.relationship('User', backref=db.backref('message_reads', lazy='dynamic'))

    # Add unique constraint to prevent duplicate read receipts
    __table_args__ = (db.UniqueConstraint('message_id', 'user_id', name='unique_message_read'),)

    def __repr__(self):
        return f'<MessageReadReceipt {self.message_id} read by {self.user_id}>'

    def serialize(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'user_id': self.user_id,
            'username': self.user.username,
            'read_at': self.read_at.isoformat()
        }

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # like, comment, friend_request, message
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reference_id = db.Column(db.Integer)  # ID of the related item (post, comment, etc.)
    content = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('notifications', lazy='dynamic'))
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_notifications', lazy='dynamic'))

    def __repr__(self):
        return f'<Notification {self.id} to {self.user_id} type {self.notification_type}>'

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'notification_type': self.notification_type,
            'sender_id': self.sender_id,
            'sender_name': self.sender.username if self.sender else None,
            'sender_profile_pic': self.sender.profile_pic if self.sender else None,
            'reference_id': self.reference_id,
            'content': self.content,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }

class UserInteraction(db.Model):
    """Tracks user interactions for the relationship strength algorithm"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interaction_type = db.Column(db.String(50), nullable=False)  # profile_visit, message, like, comment
    interaction_count = db.Column(db.Integer, default=1)
    last_interaction = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('interactions', lazy='dynamic'))
    target = db.relationship('User', foreign_keys=[target_id], backref=db.backref('received_interactions', lazy='dynamic'))

    # Add unique constraint to prevent duplicate interaction records
    __table_args__ = (db.UniqueConstraint('user_id', 'target_id', 'interaction_type', name='unique_interaction'),)

    def __repr__(self):
        return f'<UserInteraction {self.user_id} -> {self.target_id} ({self.interaction_type})>'

# Event listeners to update the friendship scores based on interactions
@event.listens_for(UserInteraction, 'after_insert')
@event.listens_for(UserInteraction, 'after_update')
def update_friendship_score(mapper, connection, target):
    from utils.friend_algorithm import calculate_relationship_score

    # Get the Friend record if it exists
    friendship = Friend.query.filter(
        (Friend.user_id == target.user_id) & (Friend.friend_id == target.target_id) |
        (Friend.user_id == target.target_id) & (Friend.friend_id == target.user_id)
    ).first()

    if friendship and friendship.status == 'accepted':
        # Calculate the new relationship score
        new_score = calculate_relationship_score(target.user_id, target.target_id)

        # Update the relationship score
        friendship.relationship_score = new_score
        db.session.commit()