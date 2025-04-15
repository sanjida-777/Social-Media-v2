# API Reference

This document provides details about the API endpoints available in the Social Media Application.

## Authentication

### Register a new user

**Endpoint:** `/auth/api/register`

**Method:** `POST`

**Request Body:**
```json
{
  "username": "example_user",
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": 123,
  "message": "User registered successfully"
}
```

### Login

**Endpoint:** `/auth/api/login`

**Method:** `POST`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": 123,
  "username": "example_user",
  "token": "jwt_token_here"
}
```

## User Profiles

### Get user profile

**Endpoint:** `/api/profile/{username}`

**Method:** `GET`

**Response:**
```json
{
  "success": true,
  "user": {
    "id": 123,
    "username": "example_user",
    "profile_pic": "url_to_profile_pic",
    "bio": "User bio here",
    "created_at": "2023-01-01T00:00:00Z",
    "last_online": "2023-01-02T12:34:56Z"
  },
  "friendship_status": "none",
  "is_following": false,
  "friend_count": 42,
  "follower_count": 100,
  "following_count": 50
}
```

## Posts

### Create a post

**Endpoint:** `/feed/api/post`

**Method:** `POST`

**Request Body:**
```json
{
  "content": "This is my new post!",
  "media": ["url_to_media_1", "url_to_media_2"]
}
```

**Response:**
```json
{
  "success": true,
  "post_id": 456,
  "message": "Post created successfully"
}
```

### Get posts for feed

**Endpoint:** `/feed/api/posts`

**Method:** `GET`

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)

**Response:**
```json
{
  "success": true,
  "posts": [
    {
      "id": 456,
      "user_id": 123,
      "author": "example_user",
      "profile_pic": "url_to_profile_pic",
      "content": "This is my new post!",
      "created_at": "2023-01-03T10:11:12Z",
      "media": [
        {
          "id": 789,
          "media_type": "image",
          "media_url": "url_to_media"
        }
      ],
      "like_count": 15,
      "comment_count": 3
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 5,
    "total_items": 42,
    "per_page": 10
  }
}
```

## Friends

### Send friend request

**Endpoint:** `/profile/api/friend/{username}/request`

**Method:** `POST`

**Response:**
```json
{
  "success": true,
  "status": "pending",
  "message": "Friend request sent"
}
```

### Accept friend request

**Endpoint:** `/profile/api/friend/{username}/accept`

**Method:** `POST`

**Response:**
```json
{
  "success": true,
  "status": "accepted",
  "message": "Friend request accepted"
}
```

## Follow

### Follow a user

**Endpoint:** `/profile/api/follow/{username}`

**Method:** `POST`

**Response:**
```json
{
  "success": true,
  "message": "Now following user"
}
```

### Unfollow a user

**Endpoint:** `/profile/api/unfollow/{username}`

**Method:** `POST`

**Response:**
```json
{
  "success": true,
  "message": "Unfollowed user"
}
```

## Error Responses

All API endpoints return appropriate HTTP status codes and error messages in case of failure:

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

Common error status codes:
- `400`: Bad Request - Invalid input
- `401`: Unauthorized - Authentication required
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `500`: Internal Server Error - Server-side error
