# Social Media Application

A modern social media web application built with Flask, featuring user authentication, profiles, posts, friend connections, and real-time messaging.

## Features

- **User Authentication**: Secure registration and login with email verification
- **User Profiles**: Customizable profiles with profile pictures and cover photos
- **News Feed**: View posts from friends and followed users
- **Friend System**: Send, accept, and manage friend requests
- **Follow System**: Follow users to see their content without being friends
- **Real-time Messaging**: Chat with friends using WebSockets
- **Notifications**: Get notified of important activities
- **Mobile-Responsive Design**: Works on all device sizes

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Real-time Communication**: Flask-SocketIO
- **Authentication**: Custom auth system with Firebase integration

## Getting Started

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/social-media-app.git
   cd social-media-app
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```
   python init_db.py
   ```

6. Run the application:
   ```
   python app.py
   ```

7. Access the application at http://localhost:5000

## Project Structure

```
social-media-app/
├── app.py                  # Application entry point
├── create_app.py           # Flask application factory
├── config.json             # Application configuration
├── database.py             # Database connection and models
├── models.py               # Database models
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in repo)
├── static/                 # Static files (CSS, JS, images)
├── templates/              # HTML templates
├── routes/                 # Route handlers
│   ├── auth.py             # Authentication routes
│   ├── feed.py             # Feed and post routes
│   ├── profile.py          # User profile routes
│   └── ...
└── utils/                  # Utility functions
    ├── filters.py          # Custom Jinja2 filters
    ├── firebase.py         # Firebase integration
    └── ...
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Bootstrap for the responsive UI components
- Flask and its extensions for the powerful backend framework
- All contributors who have helped improve this project
