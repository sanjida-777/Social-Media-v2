import logging
import time
from datetime import datetime
from flask import g, request, jsonify
from urllib.parse import quote_plus

from routes.auth_old import login_required
from routes.chat import chat_bp
from models import ChatMember
from utils.mqtt_client import get_mqtt_client

# Set up logger
logger = logging.getLogger(__name__)

# Initialize MQTT client for the module
mqtt_client = None

def get_chat_mqtt_client():
    """Get or create the MQTT client for chat"""
    global mqtt_client
    if mqtt_client is None:
        mqtt_client = get_mqtt_client('socialconnect_chat')
    return mqtt_client

def get_chat_topic(chat_id):
    """Get the MQTT topic for a chat"""
    return f"socialconnect/chat/{chat_id}"

@chat_bp.route('/api/mqtt/connect', methods=['POST'])
@login_required
def handle_connect():
    """Connect to MQTT broker"""
    client = get_chat_mqtt_client()

    # Connection handled internally in get_mqtt_client
    if client.connected:
        return jsonify({'success': True})
    else:
        success = client.connect()
        return jsonify({'success': success})

@chat_bp.route('/api/mqtt/disconnect', methods=['POST'])
@login_required
def handle_disconnect():
    """Disconnect from MQTT broker"""
    client = get_chat_mqtt_client()
    client.disconnect()
    return jsonify({'success': True})

@chat_bp.route('/api/mqtt/join', methods=['POST'])
@login_required
def handle_join_chat(chat_id=None):
    """Join a chat's MQTT topic"""
    data = request.json
    if not data and not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400

    chat_id = chat_id or data.get('chat_id')
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400

    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id
    ).first()

    if not member:
        return jsonify({'error': 'Not a member of this chat'}), 403

    # Subscribe to chat topic
    client = get_chat_mqtt_client()
    topic = get_chat_topic(chat_id)

    def on_message(payload):
        """Handle incoming MQTT messages (for testing)"""
        logger.debug(f"Received MQTT message on topic {topic}: {payload}")

    success = client.subscribe(topic, on_message)

    # Update presence status
    presence_payload = {
        'type': 'presence',
        'action': 'join',
        'user_id': g.user.id,
        'username': g.user.username,
        'timestamp': datetime.utcnow().isoformat()
    }
    client.publish(topic, presence_payload)

    return jsonify({'success': success})

@chat_bp.route('/api/mqtt/leave', methods=['POST'])
@login_required
def handle_leave_chat(chat_id=None):
    """Leave a chat's MQTT topic"""
    data = request.json
    if not data and not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400

    chat_id = chat_id or data.get('chat_id')
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400

    # Unsubscribe from chat topic
    client = get_chat_mqtt_client()
    topic = get_chat_topic(chat_id)

    # Update presence status before unsubscribing
    presence_payload = {
        'type': 'presence',
        'action': 'leave',
        'user_id': g.user.id,
        'username': g.user.username,
        'timestamp': datetime.utcnow().isoformat()
    }
    client.publish(topic, presence_payload)

    success = client.unsubscribe(topic)

    return jsonify({'success': success})
