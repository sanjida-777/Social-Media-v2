// Socket.IO client integration for real-time features

let socket;
let socketConnected = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// Initialize Socket.IO connection
function initializeSocket() {
  if (socketConnected) return;
  
  // Create socket connection
  socket = io.connect(window.location.origin, {
    reconnection: true,
    reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
    timeout: 10000
  });
  
  // Socket connection event handlers
  socket.on('connect', handleSocketConnect);
  socket.on('disconnect', handleSocketDisconnect);
  socket.on('connect_error', handleSocketConnectError);
  socket.on('error', handleSocketError);
  
  // Message-related events
  socket.on('new_message', handleNewMessage);
  socket.on('message_deleted', handleMessageDeleted);
  socket.on('messages_read', handleMessagesRead);
  
  // Notification-related events
  socket.on('new_notification', handleNewNotification);
  
  // Chat events
  socket.on('chat_updated', handleChatUpdated);
  socket.on('member_added', handleMemberAdded);
  socket.on('member_removed', handleMemberRemoved);
}

// Handle successful socket connection
function handleSocketConnect() {
  console.log('Socket.IO connected');
  socketConnected = true;
  reconnectAttempts = 0;
  
  // Join rooms based on current page
  if (window.location.pathname.includes('/chat/')) {
    const chatId = window.location.pathname.split('/chat/')[1];
    joinChatRoom(chatId);
  }
  
  // Join user's notification room
  joinUserRoom();
  
  // Show connection status
  updateConnectionStatus(true);
}

// Handle socket disconnection
function handleSocketDisconnect() {
  console.log('Socket.IO disconnected');
  socketConnected = false;
  
  // Show disconnection status
  updateConnectionStatus(false);
}

// Handle socket connection error
function handleSocketConnectError(error) {
  console.error('Socket.IO connection error:', error);
  socketConnected = false;
  reconnectAttempts++;
  
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    showToast('Unable to establish real-time connection. Some features may be unavailable.', 'warning');
  }
  
  // Show connection error status
  updateConnectionStatus(false);
}

// Handle socket error
function handleSocketError(error) {
  console.error('Socket.IO error:', error);
}

// Join a chat room
function joinChatRoom(chatId) {
  if (!socketConnected) return;
  
  socket.emit('join_chat', { chat_id: chatId }, function(data) {
    if (data && data.error) {
      console.error('Error joining chat room:', data.error);
    } else {
      console.log('Joined chat room:', chatId);
    }
  });
}

// Leave a chat room
function leaveChatRoom(chatId) {
  if (!socketConnected) return;
  
  socket.emit('leave_chat', { chat_id: chatId }, function(data) {
    if (data && data.error) {
      console.error('Error leaving chat room:', data.error);
    } else {
      console.log('Left chat room:', chatId);
    }
  });
}

// Join user's personal notification room
function joinUserRoom() {
  if (!socketConnected) return;
  
  // We don't need to explicitly join user room as it's handled by the server
  // when the user connects with authenticated session
  
  // Request notifications
  socket.emit('get_notifications', {}, function(data) {
    if (data && data.success) {
      // Update notification UI with the latest notifications
      updateNotificationsUI(data.notifications, data.unread_count);
    }
  });
}

// Send a chat message
function sendChatMessage(chatId, content, messageType = 'text') {
  if (!socketConnected) {
    showToast('Unable to send message. Please check your connection.', 'warning');
    return Promise.reject(new Error('Socket not connected'));
  }
  
  return new Promise((resolve, reject) => {
    socket.emit('send_message', {
      chat_id: chatId,
      content: content,
      message_type: messageType
    }, function(response) {
      if (response.error) {
        reject(new Error(response.error));
      } else {
        resolve(response.message);
      }
    });
  });
}

// Delete a chat message
function deleteChatMessage(messageId) {
  if (!socketConnected) {
    showToast('Unable to delete message. Please check your connection.', 'warning');
    return Promise.reject(new Error('Socket not connected'));
  }
  
  return new Promise((resolve, reject) => {
    socket.emit('delete_message', {
      message_id: messageId
    }, function(response) {
      if (response.error) {
        reject(new Error(response.error));
      } else {
        resolve(response);
      }
    });
  });
}

// Mark messages as read
function markMessagesRead(chatId) {
  if (!socketConnected) return;
  
  socket.emit('read_messages', {
    chat_id: chatId
  }, function(response) {
    if (response.error) {
      console.error('Error marking messages as read:', response.error);
    }
  });
}

// Handle new incoming message
function handleNewMessage(message) {
  console.log('New message received:', message);
  
  // Check if we're in the chat view for this message
  if (window.location.pathname.includes(`/chat/${message.chat_id}`)) {
    // Add message to UI
    appendMessageToUI(message);
    
    // Mark as read if visible
    if (document.visibilityState === 'visible') {
      markMessagesRead(message.chat_id);
    }
  } else {
    // Show notification if not in chat view
    showMessageNotification(message);
  }
  
  // Update chat list if visible
  updateChatListUI(message.chat_id, message);
}

// Handle message deleted event
function handleMessageDeleted(message) {
  console.log('Message deleted:', message);
  
  // Check if we're in the chat view for this message
  if (window.location.pathname.includes(`/chat/${message.chat_id}`)) {
    // Update message in UI
    updateDeletedMessageUI(message);
  }
}

// Handle messages read event
function handleMessagesRead(data) {
  console.log('Messages read by:', data);
  
  // Check if we're in the chat view for this chat
  if (window.location.pathname.includes(`/chat/${data.chat_id}`)) {
    // Update read receipts in UI
    updateReadReceiptsUI(data);
  }
}

// Handle new notification event
function handleNewNotification(notification) {
  console.log('New notification received:', notification);
  
  // Add notification to UI
  addNotificationToUI(notification);
  
  // Update unread count
  updateNotificationCounter();
  
  // Show notification toast unless it's a message notification and we're in that chat
  if (notification.notification_type === 'message' && 
      window.location.pathname.includes(`/chat/${notification.reference_id}`)) {
    // Don't show toast for messages in current chat
    return;
  }
  
  // Show notification toast
  showNotificationToast(notification);
}

// Handle chat updated event
function handleChatUpdated(chat) {
  console.log('Chat updated:', chat);
  
  // Update chat in chat list UI
  updateChatInList(chat);
  
  // Update chat details if on that chat page
  if (window.location.pathname.includes(`/chat/${chat.id}`)) {
    updateChatDetailsUI(chat);
  }
}

// Handle member added to chat event
function handleMemberAdded(data) {
  console.log('Member added to chat:', data);
  
  // Update member list if on chat details page
  if (window.location.pathname.includes(`/chat/${data.chat_id}`)) {
    addMemberToUI(data.member);
  }
}

// Handle member removed from chat event
function handleMemberRemoved(data) {
  console.log('Member removed from chat:', data);
  
  // Update member list if on chat details page
  if (window.location.pathname.includes(`/chat/${data.chat_id}`)) {
    removeMemberFromUI(data.user_id);
  }
}

// Show a notification toast
function showNotificationToast(notification) {
  let title = 'Notification';
  let icon = 'info-circle';
  
  switch (notification.notification_type) {
    case 'like':
      title = 'New Like';
      icon = 'heart';
      break;
    case 'comment':
      title = 'New Comment';
      icon = 'chat';
      break;
    case 'friend_request':
      title = 'Friend Request';
      icon = 'user-plus';
      break;
    case 'friend_accepted':
      title = 'Friend Request Accepted';
      icon = 'user-check';
      break;
    case 'follow':
      title = 'New Follower';
      icon = 'user-plus';
      break;
    case 'message':
      title = 'New Message';
      icon = 'envelope';
      break;
    case 'chat_invite':
      title = 'Chat Invitation';
      icon = 'users';
      break;
  }
  
  const toast = `
    <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="toast-header">
        <i class="bi bi-${icon} me-2"></i>
        <strong class="me-auto">${title}</strong>
        <small>${timeAgo(notification.created_at)}</small>
        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${notification.content}
      </div>
    </div>
  `;
  
  // Add to toast container
  const toastContainer = document.getElementById('toast-container');
  if (toastContainer) {
    toastContainer.insertAdjacentHTML('beforeend', toast);
    const toastElement = toastContainer.lastElementChild;
    const bsToast = new bootstrap.Toast(toastElement);
    bsToast.show();
  }
}

// Show a message notification
function showMessageNotification(message) {
  if (message.user_id === getCurrentUserId()) return; // Don't notify for own messages
  
  const content = message.content || '(media content)';
  const toast = `
    <div class="toast chat-notification" role="alert" aria-live="assertive" aria-atomic="true" data-chat-id="${message.chat_id}">
      <div class="toast-header">
        <img src="${message.profile_pic || '/static/img/default-avatar.png'}" class="rounded me-2" width="20" height="20" alt="${message.sender}">
        <strong class="me-auto">${message.sender}</strong>
        <small>${timeAgo(message.created_at)}</small>
        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${truncateText(content, 50)}
      </div>
    </div>
  `;
  
  // Add to toast container
  const toastContainer = document.getElementById('toast-container');
  if (toastContainer) {
    toastContainer.insertAdjacentHTML('beforeend', toast);
    const toastElement = toastContainer.lastElementChild;
    
    // Add click handler to navigate to chat
    toastElement.addEventListener('click', function(e) {
      if (!e.target.closest('.btn-close')) {
        window.location.href = `/chat/${message.chat_id}`;
      }
    });
    
    const bsToast = new bootstrap.Toast(toastElement);
    bsToast.show();
  }
}

// Get current user ID
function getCurrentUserId() {
  const userElement = document.getElementById('current-user-id');
  return userElement ? userElement.value : null;
}

// Update connection status indicator
function updateConnectionStatus(connected) {
  const statusEl = document.getElementById('connection-status');
  
  if (!statusEl) return;
  
  if (connected) {
    statusEl.classList.remove('bg-danger');
    statusEl.classList.add('bg-success');
    statusEl.setAttribute('title', 'Connected');
  } else {
    statusEl.classList.remove('bg-success');
    statusEl.classList.add('bg-danger');
    statusEl.setAttribute('title', 'Disconnected');
  }
}

// Placeholder functions to be implemented in respective feature files
function appendMessageToUI(message) {
  // Implemented in chat.js
  if (typeof window.chatModule !== 'undefined' && window.chatModule.appendMessage) {
    window.chatModule.appendMessage(message);
  }
}

function updateDeletedMessageUI(message) {
  // Implemented in chat.js
  if (typeof window.chatModule !== 'undefined' && window.chatModule.updateDeletedMessage) {
    window.chatModule.updateDeletedMessage(message);
  }
}

function updateReadReceiptsUI(data) {
  // Implemented in chat.js
  if (typeof window.chatModule !== 'undefined' && window.chatModule.updateReadReceipts) {
    window.chatModule.updateReadReceipts(data);
  }
}

function addNotificationToUI(notification) {
  // Implemented in notifications.js
  if (typeof window.notificationsModule !== 'undefined' && window.notificationsModule.addNotification) {
    window.notificationsModule.addNotification(notification);
  }
}

function updateNotificationCounter() {
  // Implemented in notifications.js
  if (typeof window.notificationsModule !== 'undefined' && window.notificationsModule.updateCounter) {
    window.notificationsModule.updateCounter();
  }
}

function updateChatListUI(chatId, message) {
  // Implemented in chat.js
  if (typeof window.chatModule !== 'undefined' && window.chatModule.updateChatList) {
    window.chatModule.updateChatList(chatId, message);
  }
}

function updateChatInList(chat) {
  // Implemented in chat.js
  if (typeof window.chatModule !== 'undefined' && window.chatModule.updateChatInList) {
    window.chatModule.updateChatInList(chat);
  }
}

function updateChatDetailsUI(chat) {
  // Implemented in chat.js
  if (typeof window.chatModule !== 'undefined' && window.chatModule.updateChatDetails) {
    window.chatModule.updateChatDetails(chat);
  }
}

function addMemberToUI(member) {
  // Implemented in chat.js
  if (typeof window.chatModule !== 'undefined' && window.chatModule.addMember) {
    window.chatModule.addMember(member);
  }
}

function removeMemberFromUI(userId) {
  // Implemented in chat.js
  if (typeof window.chatModule !== 'undefined' && window.chatModule.removeMember) {
    window.chatModule.removeMember(userId);
  }
}

// Initialize socket when document is ready
document.addEventListener('DOMContentLoaded', function() {
  // Only initialize if user is logged in
  if (document.getElementById('current-user-id')) {
    initializeSocket();
  }
});
