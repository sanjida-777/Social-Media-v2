"""
Shared SocketIO instance to avoid circular imports
"""
import logging
from flask_socketio import SocketIO

# Set up logger
logger = logging.getLogger(__name__)

# Create a shared SocketIO instance
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='threading',
    logger=True,
    engineio_logger=True,
    ping_timeout=20,
    ping_interval=10,
    max_http_buffer_size=1024 * 1024
)

logger.info("SocketIO instance created with threading mode")
