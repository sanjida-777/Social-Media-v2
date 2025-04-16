# Routes Directory Structure

This directory contains all the route handlers for the SocialConnect application, organized in a modular structure.

## Directory Structure

Each route category has its own directory with the following structure:

```
routes/
├── api/                # API endpoints
│   ├── __init__.py     # Blueprint initialization
│   ├── feed.py         # Feed API endpoints
│   ├── friends.py      # Friends API endpoints
│   ├── messages.py     # Messages API endpoints
│   ├── profile.py      # Profile API endpoints
│   ├── search.py       # Search API endpoints
│   ├── stories.py      # Stories API endpoints
│   └── user.py         # User API endpoints
│
├── auth/               # Authentication routes
│   ├── __init__.py     # Blueprint initialization
│   ├── friends.py      # Friend management routes
│   ├── login.py        # Login/logout routes
│   ├── messages.py     # Messaging routes
│   ├── profile.py      # Profile routes
│   ├── register.py     # Registration routes
│   └── settings.py     # User settings routes
│
├── chat/               # Chat routes
│   ├── __init__.py     # Blueprint initialization
│   ├── messages.py     # Chat message functionality
│   ├── groups.py       # Chat group management
│   └── realtime.py     # Real-time chat functionality
│
├── feed/               # Feed routes
│   ├── __init__.py     # Blueprint initialization
│   └── posts.py        # Feed posts routes
│
├── main/               # Main application routes
│   ├── __init__.py     # Blueprint initialization
│   ├── index.py        # Home page routes
│   └── messages.py     # Message overview routes
│
├── notifications/      # Notification routes
│   ├── __init__.py     # Blueprint initialization
│   └── api.py          # Notification API endpoints
│
├── profile/            # Profile routes
│   ├── __init__.py     # Blueprint initialization
│   ├── view.py         # Profile viewing routes
│   └── edit.py         # Profile editing routes
│
├── story/              # Story routes
│   ├── __init__.py     # Blueprint initialization
│   ├── create.py       # Story creation routes
│   └── view.py         # Story viewing routes
│
├── test/               # Test routes
│   ├── __init__.py     # Blueprint initialization
│   └── upload.py       # Test upload functionality
│
└── __init__.py         # Package initialization
```

## Blueprint Structure

Each route category has its own Blueprint with a specific URL prefix:

- `auth_bp`: `/auth` - Authentication routes
- `feed_bp`: `/feed` - Feed routes
- `main_bp`: `/` - Main application routes (no prefix)
- `story_bp`: `/story` - Story routes
- `notifications_bp`: `/notifications` - Notification routes
- `api_bp`: `/api` - API routes
- `profile_bp`: `/profile` - Profile routes
- `chat_bp`: `/chat` - Chat routes
- `test_bp`: `/test` - Test routes

## Route Organization Guidelines

1. **Modular Structure**: Each route category has its own directory
2. **Blueprint Initialization**: Each directory has an `__init__.py` file that initializes the blueprint
3. **Functionality Separation**: Routes are separated by functionality into different files
4. **Related Functionality**: Closely related functionality (like login/signup/logout) can be in the same file
5. **API Routes**: All API endpoints are under the `/api` prefix and organized by functionality

## Adding New Routes

To add a new route:

1. Create a new file in the appropriate directory
2. Import the blueprint from the directory's `__init__.py` file
3. Define your route using the blueprint's `route` decorator
4. Import your new file in `create_app.py` if it's not already imported

Example:

```python
# routes/profile/stats.py
from routes.profile import profile_bp

@profile_bp.route('/stats')
def profile_stats():
    """Show profile statistics"""
    return render_template('profile/stats.html')
```

Then in `create_app.py`:

```python
# Import the new route module
import routes.profile.stats
```
