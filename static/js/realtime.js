// Real-time functionality using Socket.IO

const realtimeModule = (function() {
  // Private variables
  let socket = null;
  let connected = false;
  let authenticated = false;
  let messageHandlers = {};
  let userId = null;
  let username = null;

  // Initialize Socket.IO connection
  function init() {
    try {
      console.log('Initializing Socket.IO connection...');
      
      // Get current user ID if available
      const userIdElement = document.getElementById('current-user-id');
      if (userIdElement) {
        userId = userIdElement.value;
        console.log('Current user ID:', userId);
      }

      // Initialize Socket.IO with proper configuration
      socket = io({
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        timeout: 20000
      });

      // Connection established
      socket.on('connect', function() {
        console.log('Socket.IO connected with ID:', socket.id);
        connected = true;
        
        // Listen for connection errors
        socket.on('connect_error', (error) => {
          console.error('Connection error:', error);
        });
        
        // Authenticate after connection
        if (userId) {
          authenticate();
        }
      });

      // Connection closed
      socket.on('disconnect', function(reason) {
        console.log('Socket.IO disconnected:', reason);
        connected = false;
        authenticated = false;
      });

      // Connection error
      socket.on('connect_error', function(error) {
        console.error('Socket.IO connection error:', error);
      });

      // Authentication response
      socket.on('auth_response', function(data) {
        console.log('Authentication response:', data);
        if (data.status === 'success') {
          authenticated = true;
          userId = data.user_id;
          username = data.username;
          console.log('Successfully authenticated as:', username);
        } else {
          console.error('Authentication failed:', data.message);
        }
      });

      // General message handler
      socket.on('message', function(data) {
        console.log('Received message:', data);
        handleMessage(data);
      });

      // User status updates
      socket.on('user_status', function(data) {
        console.log('User status update:', data);
        // Could update UI to show user online/offline status
      });

      // Connected confirmation
      socket.on('connected', function(data) {
        console.log('Connected confirmation:', data);
      });

      // Set up event listeners for page visibility and network changes
      document.addEventListener('visibilitychange', handleVisibilityChange);
      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);
    } catch (error) {
      console.error('Error initializing Socket.IO:', error);
    }
  }

  // Handle page visibility changes
  function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
      // Page is now visible, reconnect if needed
      if (!connected && socket) {
        console.log('Page visible, reconnecting...');
        socket.connect();
      }
    }
  }

  // Handle online event
  function handleOnline() {
    console.log('Browser is online, reconnecting Socket.IO...');
    if (!connected && socket) {
      socket.connect();
    }
  }

  // Handle offline event
  function handleOffline() {
    console.log('Browser is offline, Socket.IO will reconnect when online');
  }

  // Send authentication message
  function authenticate() {
    if (!connected || !socket) {
      console.warn('Cannot authenticate: Socket.IO not connected');
      return;
    }

    console.log('Sending authentication request...');
    socket.emit('auth', {});
  }

  // Send message to server
  function send(eventName, data) {
    if (!connected || !socket) {
      console.warn('Cannot send message: Socket.IO not connected');
      return false;
    }

    try {
      console.log(`Sending ${eventName} event:`, data);
      socket.emit(eventName, data);
      return true;
    } catch (error) {
      console.error('Error sending message:', error);
      return false;
    }
  }

  // Handle incoming message
  function handleMessage(data) {
    try {
      // Log message for debugging
      console.log('Message received:', data);

      // Call appropriate handler based on message type
      if (data && data.type && messageHandlers[data.type]) {
        messageHandlers[data.type](data);
      }

      // Dispatch event for other modules to listen for
      const event = new CustomEvent('realtime-message', { detail: data });
      document.dispatchEvent(event);
    } catch (error) {
      console.error('Error handling message:', error);
    }
  }

  // Register message handler
  function on(messageType, callback) {
    messageHandlers[messageType] = callback;
    console.log(`Registered handler for message type: ${messageType}`);
  }

  // Initialize module when document is ready
  document.addEventListener('DOMContentLoaded', function() {
    console.log('Document ready, initializing realtime module...');
    init();
  });

  // Public methods
  return {
    send: function(data) { 
      return send('message', data); 
    },
    on: on,
    isConnected: function() { 
      return connected; 
    },
    isAuthenticated: function() {
      return authenticated;
    },
    getSocket: function() {
      return socket;
    }
  };
})();

// Make realtime module available globally
window.realtimeModule = realtimeModule;

// Add event listeners for real-time updates
document.addEventListener('realtime-message', function(e) {
  const message = e.detail;
  console.log('Processing realtime message:', message);

  // Handle different message types
  if (!message || !message.type) {
    console.warn('Invalid message format:', message);
    return;
  }

  switch (message.type) {
    case 'new_post':
      // Show notification for new post
      if (window.feedModule) {
        const notification = document.createElement('div');
        notification.className = 'new-content-notification';
        notification.innerHTML = `
          <div class="alert alert-info alert-dismissible fade show" role="alert">
            <i class="bi bi-newspaper me-2"></i>
            New post from ${message.author}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
          </div>
        `;
        const feedContainer = document.querySelector('.feed-container');
        if (feedContainer) {
          feedContainer.prepend(notification);
        }
      }
      break;

    case 'new_comment':
      // Update comment count and show notification if viewing the post
      const postElement = document.querySelector(`.post[data-post-id="${message.post_id}"]`);
      if (postElement) {
        // Update comment count
        const commentCountEl = postElement.querySelector('.comment-count');
        if (commentCountEl) {
          const currentCount = parseInt(commentCountEl.textContent.replace(/\D/g, ''), 10) || 0;
          commentCountEl.textContent = formatCount(currentCount + 1);
        }

        // Show notification if comments are open
        const commentsContainer = document.getElementById(`comments-${message.post_id}`);
        if (commentsContainer && commentsContainer.style.display !== 'none') {
          // Reload comments
          if (window.feedModule) {
            window.feedModule.loadComments(message.post_id);
          }
        }
      }
      break;

    case 'new_like':
      // Update like count if viewing the post
      const likedPostElement = document.querySelector(`.post[data-post-id="${message.post_id}"]`);
      if (likedPostElement) {
        const likeCountEl = likedPostElement.querySelector('.like-count');
        if (likeCountEl) {
          likeCountEl.textContent = formatCount(message.like_count);
        }
      }
      break;
      
    default:
      console.log('Unhandled message type:', message.type);
  }
});
