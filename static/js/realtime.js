// Real-time functionality using WebSockets

const realtimeModule = (function() {
  // Private variables
  let socket = null;
  let connected = false;
  let reconnectAttempts = 0;
  let maxReconnectAttempts = 5;
  let reconnectInterval = 3000; // 3 seconds
  let reconnectTimer = null;
  let handlers = {};

  // Initialize WebSocket connection
  function init() {
    // Check if WebSockets are supported
    if (!('WebSocket' in window)) {
      console.error('WebSockets are not supported in this browser');
      return;
    }

    // Get the WebSocket URL (ws:// or wss:// depending on the current protocol)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    connect(wsUrl);

    // Set up event listeners for page visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
  }

  // Connect to WebSocket server
  function connect(url) {
    try {
      socket = new WebSocket(url);

      socket.onopen = function() {
        console.log('WebSocket connection established');
        connected = true;
        reconnectAttempts = 0;

        // Send authentication message
        authenticate();
      };

      socket.onmessage = function(event) {
        handleMessage(event.data);
      };

      socket.onclose = function(event) {
        console.log('WebSocket connection closed', event.code, event.reason);
        connected = false;

        // Attempt to reconnect if not a clean close
        if (event.code !== 1000) {
          scheduleReconnect();
        }
      };

      socket.onerror = function(error) {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      scheduleReconnect();
    }
  }

  // Schedule reconnection attempt
  function scheduleReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
    }

    if (reconnectAttempts < maxReconnectAttempts) {
      reconnectAttempts++;
      console.log(`Scheduling reconnect attempt ${reconnectAttempts}/${maxReconnectAttempts} in ${reconnectInterval}ms`);
      
      reconnectTimer = setTimeout(() => {
        if (!connected) {
          console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`);
          init();
        }
      }, reconnectInterval);
    } else {
      console.error('Maximum reconnection attempts reached');
    }
  }

  // Handle page visibility changes
  function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
      // Page is now visible, reconnect if needed
      if (!connected) {
        reconnectAttempts = 0; // Reset reconnect attempts
        init();
      }
    }
  }

  // Handle online event
  function handleOnline() {
    console.log('Browser is online, reconnecting WebSocket...');
    if (!connected) {
      reconnectAttempts = 0; // Reset reconnect attempts
      init();
    }
  }

  // Handle offline event
  function handleOffline() {
    console.log('Browser is offline, WebSocket will reconnect when online');
  }

  // Send authentication message
  function authenticate() {
    if (!connected) return;

    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    
    send({
      type: 'auth',
      token: csrfToken
    });
  }

  // Send message to server
  function send(data) {
    if (!connected) {
      console.warn('Cannot send message: WebSocket not connected');
      return false;
    }

    try {
      socket.send(JSON.stringify(data));
      return true;
    } catch (error) {
      console.error('Error sending message:', error);
      return false;
    }
  }

  // Handle incoming message
  function handleMessage(data) {
    try {
      const message = JSON.parse(data);
      
      // Log message for debugging
      console.log('WebSocket message received:', message);

      // Call appropriate handler based on message type
      if (message.type && handlers[message.type]) {
        handlers[message.type](message);
      }

      // Dispatch event for other modules to listen for
      const event = new CustomEvent('realtime-message', { detail: message });
      document.dispatchEvent(event);
    } catch (error) {
      console.error('Error handling message:', error, data);
    }
  }

  // Register message handler
  function on(messageType, callback) {
    handlers[messageType] = callback;
  }

  // Initialize module when document is ready
  document.addEventListener('DOMContentLoaded', init);

  // Public methods
  return {
    send,
    on,
    isConnected: () => connected
  };
})();

// Make realtime module available globally
window.realtimeModule = realtimeModule;

// Add event listeners for real-time updates
document.addEventListener('realtime-message', function(e) {
  const message = e.detail;
  
  // Handle different message types
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
        document.querySelector('.feed-container')?.prepend(notification);
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
  }
});
