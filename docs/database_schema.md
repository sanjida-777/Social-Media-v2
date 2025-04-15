# Database Schema

This document describes the database schema for the Social Media Application.

## Entity Relationship Diagram

```
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│     User      │       │     Post      │       │  PostMedia    │
├───────────────┤       ├───────────────┤       ├───────────────┤
│ id            │       │ id            │       │ id            │
│ username      │       │ user_id       │◄──────┤ post_id       │
│ email         │       │ content       │       │ media_type    │
│ password_hash │       │ created_at    │       │ media_url     │
│ bio           │       │ updated_at    │       │ created_at    │
│ profile_pic   │◄──────┤               │       │               │
│ cover_pic     │       └───────────────┘       └───────────────┘
│ created_at    │               ▲
│ last_online   │               │
└───────────────┘               │
        ▲                       │
        │                       │
        │                       │
┌───────┴───────┐       ┌───────┴───────┐       ┌───────────────┐
│    Friend     │       │   PostLike    │       │    Comment    │
├───────────────┤       ├───────────────┤       ├───────────────┤
│ id            │       │ id            │       │ id            │
│ user_id       │       │ post_id       │       │ post_id       │
│ friend_id     │       │ user_id       │       │ user_id       │
│ status        │       │ created_at    │       │ content       │
│ created_at    │       │               │       │ created_at    │
│ updated_at    │       └───────────────┘       │ updated_at    │
└───────────────┘                               └───────────────┘
        ▲                                               ▲
        │                                               │
        │                                               │
┌───────┴───────┐       ┌───────────────┐       ┌───────┴───────┐
│   Follower    │       │     Story     │       │  CommentLike  │
├───────────────┤       ├───────────────┤       ├───────────────┤
│ id            │       │ id            │       │ id            │
│ user_id       │       │ user_id       │       │ comment_id    │
│ follower_id   │       │ content       │       │ user_id       │
│ created_at    │       │ media_url     │       │ created_at    │
│               │       │ created_at    │       │               │
│               │       │ expires_at    │       │               │
└───────────────┘       └───────────────┘       └───────────────┘
```

## Tables

### User

Stores user account information.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| firebase_uid  | String       | Firebase user ID (optional)               |
| username      | String       | Unique username                           |
| email         | String       | Unique email address                      |
| password_hash | String       | Hashed password                           |
| bio           | String       | User biography                            |
| profile_pic   | String       | URL to profile picture                    |
| cover_pic     | String       | URL to cover picture                      |
| created_at    | DateTime     | Account creation timestamp                |
| last_online   | DateTime     | Last activity timestamp                   |
| is_active     | Boolean      | Account status                            |

### Post

Stores user posts.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| user_id       | Integer      | Foreign key to User                       |
| content       | Text         | Post text content                         |
| created_at    | DateTime     | Post creation timestamp                   |
| updated_at    | DateTime     | Post update timestamp                     |

### PostMedia

Stores media associated with posts.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| post_id       | Integer      | Foreign key to Post                       |
| media_type    | String       | Type of media (image, video)              |
| media_url     | String       | URL to media file                         |
| created_at    | DateTime     | Creation timestamp                        |

### PostLike

Stores post likes.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| post_id       | Integer      | Foreign key to Post                       |
| user_id       | Integer      | Foreign key to User                       |
| created_at    | DateTime     | Like timestamp                            |

### Comment

Stores comments on posts.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| post_id       | Integer      | Foreign key to Post                       |
| user_id       | Integer      | Foreign key to User                       |
| content       | Text         | Comment text                              |
| created_at    | DateTime     | Comment creation timestamp                |
| updated_at    | DateTime     | Comment update timestamp                  |

### CommentLike

Stores likes on comments.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| comment_id    | Integer      | Foreign key to Comment                    |
| user_id       | Integer      | Foreign key to User                       |
| created_at    | DateTime     | Like timestamp                            |

### Friend

Stores friendship relationships.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| user_id       | Integer      | Foreign key to User (requester)           |
| friend_id     | Integer      | Foreign key to User (recipient)           |
| status        | String       | Status (pending, accepted, declined)      |
| created_at    | DateTime     | Request timestamp                         |
| updated_at    | DateTime     | Status update timestamp                   |

### Follower

Stores follower relationships.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| user_id       | Integer      | Foreign key to User (being followed)      |
| follower_id   | Integer      | Foreign key to User (follower)            |
| created_at    | DateTime     | Follow timestamp                          |

### Story

Stores user stories.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| user_id       | Integer      | Foreign key to User                       |
| content       | Text         | Story text content                        |
| media_url     | String       | URL to media file                         |
| created_at    | DateTime     | Story creation timestamp                  |
| expires_at    | DateTime     | Story expiration timestamp                |

### Notification

Stores user notifications.

| Column        | Type         | Description                               |
|---------------|--------------|-------------------------------------------|
| id            | Integer      | Primary key                               |
| user_id       | Integer      | Foreign key to User (recipient)           |
| sender_id     | Integer      | Foreign key to User (sender)              |
| type          | String       | Notification type                         |
| content       | Text         | Notification content                      |
| is_read       | Boolean      | Read status                               |
| created_at    | DateTime     | Notification timestamp                    |

### UserInteraction

Tracks user interactions for relationship strength algorithm.

| Column           | Type         | Description                               |
|------------------|--------------|-------------------------------------------|
| id               | Integer      | Primary key                               |
| user_id          | Integer      | Foreign key to User (actor)               |
| target_id        | Integer      | Foreign key to User (target)              |
| interaction_type | String       | Type of interaction                       |
| interaction_count| Integer      | Number of interactions                    |
| last_interaction | DateTime     | Last interaction timestamp                |

## Indexes

- `users_username_idx`: Index on `User.username` for username lookups
- `users_email_idx`: Index on `User.email` for email lookups
- `posts_user_id_idx`: Index on `Post.user_id` for user's posts lookups
- `posts_created_at_idx`: Index on `Post.created_at` for timeline sorting
- `friends_user_id_idx`: Index on `Friend.user_id` for friend lookups
- `friends_friend_id_idx`: Index on `Friend.friend_id` for friend lookups
- `followers_user_id_idx`: Index on `Follower.user_id` for follower lookups
- `followers_follower_id_idx`: Index on `Follower.follower_id` for following lookups

## Constraints

- Unique constraint on `User.username`
- Unique constraint on `User.email`
- Unique constraint on `Friend.user_id` and `Friend.friend_id` to prevent duplicate friendships
- Unique constraint on `Follower.user_id` and `Follower.follower_id` to prevent duplicate follows
- Unique constraint on `PostLike.post_id` and `PostLike.user_id` to prevent duplicate likes
- Unique constraint on `CommentLike.comment_id` and `CommentLike.user_id` to prevent duplicate likes

## Relationships

- One-to-many: User to Posts
- One-to-many: User to Stories
- One-to-many: Post to PostMedia
- One-to-many: Post to Comments
- One-to-many: Post to PostLikes
- One-to-many: Comment to CommentLikes
- Many-to-many: User to User (via Friend)
- Many-to-many: User to User (via Follower)
