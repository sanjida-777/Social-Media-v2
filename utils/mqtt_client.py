import os
import json
import time
import logging
import threading
import queue
from typing import Dict, List, Optional, Callable

# Set up logger
logger = logging.getLogger(__name__)

# Rate limiting configuration
MAX_REQUESTS_PER_SECOND = 1  # Maximum 1 request per second
rate_limit_dict = {}
rate_limit_lock = threading.Lock()

# Message queues for rate limiting
message_queues = {}
queue_processors = {}

class MqttClient:
    """
    MQTT Client for real-time messaging
    
    Uses rate limiting to prevent flooding:
    - Each client can send at most 1 message per second
    - Messages exceeding this limit are queued and sent when the rate limit allows
    """
    
    def __init__(self, client_id: str, broker_address: str = "mqtt.eclipseprojects.io", port: int = 1883):
        """
        Initialize MQTT client with a unique ID
        
        Args:
            client_id: Unique identifier for this client
            broker_address: MQTT broker address
            port: MQTT broker port
        """
        self.client_id = client_id
        self.broker_address = broker_address
        self.port = port
        self.connected = False
        self.client = None
        self.topics_subscribed = set()
        self.callbacks = {}  # Message callbacks by topic
        
        # Rate limiting
        self.last_sent = 0
        
        # Import here to avoid global dependency
        try:
            import paho.mqtt.client as mqtt
            self.mqtt = mqtt
            self.client = mqtt.Client(client_id=client_id)
            self._setup_client()
        except ImportError:
            logger.error("paho-mqtt not installed. Please install it with: pip install paho-mqtt")
            self.mqtt = None
    
    def _setup_client(self):
        """Set up MQTT client callbacks"""
        if not self.client:
            return
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.connected = True
                logger.info(f"Connected to MQTT broker with client ID: {self.client_id}")
                # Re-subscribe to topics if reconnecting
                for topic in self.topics_subscribed:
                    self.client.subscribe(topic)
            else:
                logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
        
        def on_disconnect(client, userdata, rc):
            self.connected = False
            if rc != 0:
                logger.warning(f"Unexpected disconnection from MQTT broker, return code: {rc}")
            else:
                logger.info("Disconnected from MQTT broker")
        
        def on_message(client, userdata, msg):
            topic = msg.topic
            try:
                payload = json.loads(msg.payload.decode())
                if topic in self.callbacks:
                    for callback in self.callbacks[topic]:
                        callback(payload)
            except json.JSONDecodeError:
                logger.warning(f"Received non-JSON message on topic: {topic}")
            except Exception as e:
                logger.error(f"Error processing MQTT message: {str(e)}")
        
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message
    
    def connect(self) -> bool:
        """
        Connect to the MQTT broker
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.client:
            logger.error("MQTT client not initialized")
            return False
        
        try:
            self.client.connect(self.broker_address, self.port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {str(e)}")
            return False
    
    def disconnect(self):
        """
        Disconnect from the MQTT broker
        """
        if self.client and self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
    
    def _check_rate_limit(self) -> bool:
        """
        Check if the client has exceeded the rate limit
        
        Returns:
            bool: True if client can send, False if rate limited
        """
        current_time = time.time()
        with rate_limit_lock:
            if self.client_id not in rate_limit_dict:
                rate_limit_dict[self.client_id] = current_time
                return True
            
            last_sent = rate_limit_dict.get(self.client_id, 0)
            if current_time - last_sent >= 1.0 / MAX_REQUESTS_PER_SECOND:
                rate_limit_dict[self.client_id] = current_time
                return True
            return False
    
    def _ensure_queue_processor(self):
        """
        Ensure a queue processor exists for this client
        """
        if self.client_id not in queue_processors:
            # Create a message queue if it doesn't exist
            if self.client_id not in message_queues:
                message_queues[self.client_id] = queue.Queue()
            
            # Start a queue processor thread
            def process_queue():
                while True:
                    try:
                        # Get message from queue with timeout to allow thread to terminate
                        topic, payload = message_queues[self.client_id].get(timeout=1)
                        
                        # Wait until we can send (rate limiting)
                        while not self._check_rate_limit():
                            time.sleep(0.1)
                        
                        # Send message
                        if self.client and self.connected:
                            self.client.publish(topic, json.dumps(payload))
                            logger.debug(f"Sent queued message to topic: {topic}")
                        
                        # Mark as done
                        message_queues[self.client_id].task_done()
                    except queue.Empty:
                        # No messages, check if thread should exit
                        if not self.connected:
                            break
                    except Exception as e:
                        logger.error(f"Error in queue processor: {str(e)}")
            
            # Create and start the thread
            thread = threading.Thread(target=process_queue, daemon=True)
            thread.start()
            queue_processors[self.client_id] = thread
    
    def publish(self, topic: str, payload: dict) -> bool:
        """
        Publish a message to a topic with rate limiting
        
        If rate limited, message is queued to be sent later
        
        Args:
            topic: MQTT topic
            payload: Message payload (will be converted to JSON)
            
        Returns:
            bool: True if message was sent or queued successfully
        """
        if not self.client:
            logger.error("MQTT client not initialized")
            return False
        
        if not self.connected:
            logger.warning("Not connected to MQTT broker, trying to connect...")
            self.connect()
        
        # Check rate limit
        if self._check_rate_limit():
            # Within rate limit, send immediately
            try:
                self.client.publish(topic, json.dumps(payload))
                logger.debug(f"Published message to topic: {topic}")
                return True
            except Exception as e:
                logger.error(f"Error publishing MQTT message: {str(e)}")
                return False
        else:
            # Rate limited, queue the message
            logger.debug(f"Rate limited, queueing message for topic: {topic}")
            self._ensure_queue_processor()
            message_queues[self.client_id].put((topic, payload))
            return True
    
    def subscribe(self, topic: str, callback: Callable[[dict], None]) -> bool:
        """
        Subscribe to a topic
        
        Args:
            topic: MQTT topic to subscribe to
            callback: Function to call when a message is received
            
        Returns:
            bool: True if subscription successful
        """
        if not self.client:
            logger.error("MQTT client not initialized")
            return False
        
        if not self.connected:
            logger.warning("Not connected to MQTT broker, trying to connect...")
            self.connect()
        
        try:
            self.client.subscribe(topic)
            self.topics_subscribed.add(topic)
            
            # Add callback
            if topic not in self.callbacks:
                self.callbacks[topic] = []
            self.callbacks[topic].append(callback)
            
            logger.info(f"Subscribed to topic: {topic}")
            return True
        except Exception as e:
            logger.error(f"Error subscribing to MQTT topic: {str(e)}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from a topic
        
        Args:
            topic: MQTT topic to unsubscribe from
            
        Returns:
            bool: True if unsubscription successful
        """
        if not self.client or not self.connected:
            return False
        
        try:
            self.client.unsubscribe(topic)
            self.topics_subscribed.discard(topic)
            if topic in self.callbacks:
                del self.callbacks[topic]
            logger.info(f"Unsubscribed from topic: {topic}")
            return True
        except Exception as e:
            logger.error(f"Error unsubscribing from MQTT topic: {str(e)}")
            return False

# Singleton instance for app-wide use
_mqtt_client_instance = None

def get_mqtt_client(client_id: Optional[str] = None) -> MqttClient:
    """
    Get a singleton MQTT client instance
    
    Args:
        client_id: Optional client ID, defaults to a random UUID
        
    Returns:
        MqttClient: The MQTT client instance
    """
    global _mqtt_client_instance
    
    if _mqtt_client_instance is None:
        # Generate default client ID if none provided
        if client_id is None:
            import uuid
            client_id = f"socialconnect_{uuid.uuid4().hex[:8]}"
        
        # Create instance
        _mqtt_client_instance = MqttClient(client_id)
        
        # Connect automatically
        _mqtt_client_instance.connect()
    
    return _mqtt_client_instance