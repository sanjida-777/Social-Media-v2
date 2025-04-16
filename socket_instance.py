"""
Shared SocketIO instance to avoid circular imports
"""
from flask_socketio import SocketIO

# Create a shared SocketIO instance
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
