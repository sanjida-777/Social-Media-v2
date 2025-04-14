// Chat related functionality

// Initialize chat module with namespace
const chatModule = (function() {
  // Private variables
  let chatList;
  let chatMessages;
  let messageForm;
  let messageInput;
  let chatId;
  let lastMessageId;
  let isLoading = false;
  let hasMoreMessages = true;
  let currentPage = 1;
  let membersContainer;
  
  // Initialize chat
  function init() {
    // Get chat elements
    chatList = document.getElementById('chat-list');
    chatMessages = document.getElementById('chat-messages');
    messageForm = document.getElementById('message-form');
    messageInput = document.getElementById('message-input');
    membersContainer = document.getElementById('chat-members-container');
    
    // Get current chat ID from URL if on chat page
    const chatIdMatch = window.location.pathname.match(/\/chat\/(\d+)/);
    chatId = chatIdMatch ? chatIdMatch[1] : null;
    
    // Initialize chat list if present
    if (chatList) {
      loadChatList();
      
      // Set up new chat button
      const newChatBtn = document.getElementById('new-chat-btn');
      if (newChatBtn) {
        newChatBtn.addEventListener('click', showNewChatModal);
      }
    }
    
    // Initialize chat messages if present
    if (chatMessages && chatId) {
      loadChatMessages();
      
      // Join chat room via socket
      if (typeof socket !== 'undefined') {
        socket.emit('join_chat', { chat_id: chatId });
      }
      
      // Set up infinite scroll for messages
      chatMessages.addEventListener('scroll', handleMessagesScroll);
    }
    
    // Initialize message form if present
    if (messageForm && chatId) {
      messageForm.addEventListener('submit', sendMessage);
      
      // Auto-resize message input
      if (messageInput) {
        messageInput.addEventListener('input', () => {
          autoResizeTextarea(messageInput);
        });
        
        // Focus message input
        messageInput.focus();
      }
    }
    
    // Initialize members list if present
    if (membersContainer && chatId) {
      loadChatMembers();
    }
    
    // Initialize new chat modal events
    initNewChatModal();
    
    // Initialize group chat modal events
    initGroupChatModal();
  }
  
  // Load chat list
  function loadChatList() {
    if (!chatList) return;
    
    fetch('/api/chats')
      .then(response => response.json())
      .then(data => {
        renderChatList(data.chats);
      })
      .catch(error => {
        console.error('Error loading chat list:', error);
        chatList.innerHTML = `
          <div class="alert alert-danger">
            Error loading chats. <a href="#" onclick="chatModule.loadChatList(); return false;">Try again</a>
          </div>
        `;
      });
  }
  
  // Render chat list
  function renderChatList(chats) {
    if (!chatList) return;
    
    if (chats.length === 0) {
      chatList.innerHTML = `
        <div class="text-center p-4">
          <div class="display-1 text-muted">
            <i class="bi bi-chat-dots"></i>
          </div>
          <p class="mt-3">No conversations yet</p>
          <button class="btn btn-primary mt-2" id="start-chat-btn">Start a conversation</button>
        </div>
      `;
      
      // Set up start chat button
      const startChatBtn = document.getElementById('start-chat-btn');
      if (startChatBtn) {
        startChatBtn.addEventListener('click', showNewChatModal);
      }
      
      return;
    }
    
    chatList.innerHTML = '';
    
    chats.forEach(chat => {
      const chatItem = createChatListItem(chat);
      chatList.appendChild(chatItem);
    });
  }
  
  // Create a chat list item
  function createChatListItem(chat) {
    const chatItem = document.createElement('a');
    chatItem.className = `chat-item list-group-item list-group-item-action d-flex align-items-center ${chat.id === parseInt(chatId) ? 'active' : ''}`;
    chatItem.href = `/chat/${chat.id}`;
    
    const lastMessage = chat.last_message ? truncateText(chat.last_message.content, 30) : 'No messages yet';
    const lastMessageTime = chat.last_message ? timeAgo(chat.last_message.created_at) : '';
    
    chatItem.innerHTML = `
      <div class="chat-avatar me-3 position-relative">
        <img src="${chat.profile_pic || '/static/img/default-avatar.png'}" 
          alt="${chat.name}" class="rounded-circle" width="50" height="50">
        ${chat.is_group ? '<span class="position-absolute bottom-0 end-0 badge rounded-pill bg-primary"><i class="bi bi-people-fill"></i></span>' : ''}
      </div>
      <div class="chat-info flex-grow-1">
        <div class="d-flex justify-content-between align-items-center">
          <h6 class="mb-0">${chat.name}</h6>
          ${lastMessageTime ? `<small class="text-muted">${lastMessageTime}</small>` : ''}
        </div>
        <p class="text-muted mb-0 small">
          ${lastMessage}
        </p>
      </div>
      ${chat.unread_count > 0 ? 
        `<div class="chat-unread-badge badge bg-danger rounded-pill">${chat.unread_count}</div>` : 
        ''
      }
    `;
    
    return chatItem;
  }
  
  // Load chat messages
  function loadChatMessages(page = 1) {
    if (!chatMessages || !chatId) return;
    
    if (isLoading) return;
    isLoading = true;
    
    // Show loading indicator
    if (page === 1) {
      chatMessages.innerHTML = `
        <div class="text-center p-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading messages...</span>
          </div>
        </div>
      `;
    } else {
      // Add loading indicator at the top for pagination
      chatMessages.insertAdjacentHTML('afterbegin', `
        <div class="text-center p-2 loading-more-messages">
          <div class="spinner-border spinner-border-sm text-primary" role="status">
            <span class="visually-hidden">Loading more messages...</span>
          </div>
        </div>
      `);
    }
    
    fetch(`/api/chat/${chatId}/messages?page=${page}`)
      .then(response => response.json())
      .then(data => {
        isLoading = false;
        
        // Remove loading indicator
        if (page === 1) {
          chatMessages.innerHTML = '';
        } else {
          const loadingEl = chatMessages.querySelector('.loading-more-messages');
          if (loadingEl) loadingEl.remove();
        }
        
        if (data.messages.length === 0 && page === 1) {
          // No messages yet
          showEmptyChatState();
          return;
        }
        
        //  Store current scroll position and height
        const oldScrollHeight = chatMessages.scrollHeight;
        
        // Render messages
        renderChatMessages(data.messages, page > 1);
        
        // Update pagination state
        currentPage = data.pagination.current_page;
        hasMoreMessages = currentPage < data.pagination.total_pages;
        
        if (page === 1) {
          // Scroll to bottom for initial load
          scrollToBottom();
        } else {
          // Maintain scroll position when loading more
          const newScrollHeight = chatMessages.scrollHeight;
          const scrollDiff = newScrollHeight - oldScrollHeight;
          chatMessages.scrollTop = scrollDiff;
        }
        
        // Mark messages as read
        markMessagesAsRead();
      })
      .catch(error => {
        console.error('Error loading chat messages:', error);
        isLoading = false;
        
        // Remove loading indicator
        if (page === 1) {
          chatMessages.innerHTML = `
            <div class="alert alert-danger">
              Error loading messages. <a href="#" onclick="chatModule.loadChatMessages(); return false;">Try again</a>
            </div>
          `;
        } else {
          const loadingEl = chatMessages.querySelector('.loading-more-messages');
          if (loadingEl) loadingEl.remove();
        }
      });
  }
  
  // Show empty chat state
  function showEmptyChatState() {
    chatMessages.innerHTML = `
      <div class="text-center p-4">
        <div class="display-1 text-muted">
          <i class="bi bi-chat"></i>
        </div>
        <p class="mt-3">No messages yet</p>
        <p class="text-muted small">Send a message to start the conversation</p>
      </div>
    `;
  }
  
  // Render chat messages
  function renderChatMessages(messages, prepend = false) {
    const currentUserId = getCurrentUserId();
    
    if (prepend) {
      // Add messages to the top
      const fragment = document.createDocumentFragment();
      
      messages.forEach(message => {
        const messageEl = createMessageElement(message, currentUserId);
        fragment.appendChild(messageEl);
      });
      
      // Prepend to messages container
      chatMessages.insertBefore(fragment, chatMessages.firstChild);
    } else {
      // Clear and add all messages (for initial load)
      chatMessages.innerHTML = '';
      
      messages.forEach(message => {
        const messageEl = createMessageElement(message, currentUserId);
        chatMessages.appendChild(messageEl);
      });
      
      // Save ID of last message for pagination
      if (messages.length > 0) {
        lastMessageId = messages[messages.length - 1].id;
      }
    }
  }
  
  // Create a message element
  function createMessageElement(message, currentUserId) {
    const isOwn = message.user_id === currentUserId;
    const messageEl = document.createElement('div');
    
    messageEl.className = `message-item ${isOwn ? 'message-own' : 'message-other'}`;
    messageEl.dataset.messageId = message.id;
    
    let contentHTML = '';
    
    if (message.is_deleted) {
      contentHTML = `<div class="message-deleted text-muted"><i class="bi bi-trash me-1"></i> This message was deleted</div>`;
    } else if (message.message_type === 'text') {
      contentHTML = `<div class="message-content">${message.content}</div>`;
    } else if (message.message_type === 'image') {
      contentHTML = `
        <div class="message-media">
          <img src="${message.media_url}" alt="Image" class="img-fluid rounded">
          ${message.content ? `<div class="message-content mt-1">${message.content}</div>` : ''}
        </div>
      `;
    }
    
    messageEl.innerHTML = `
      <div class="message-bubble">
        ${!isOwn ? `
          <div class="message-avatar">
            <img src="${message.profile_pic || '/static/img/default-avatar.png'}" alt="${message.sender}" 
              class="rounded-circle" width="28" height="28">
          </div>
        ` : ''}
        <div class="message-inner">
          ${!isOwn ? `<div class="message-sender">${message.sender}</div>` : ''}
          ${contentHTML}
          <div class="message-meta">
            <small class="message-time text-muted">${formatTime(message.created_at)}</small>
            ${isOwn ? `
              <span class="message-status">
                ${message.read_by && message.read_by.length > 0 ? 
                  `<i class="bi bi-check2-all text-primary" title="Read"></i>` : 
                  `<i class="bi bi-check2" title="Sent"></i>`
                }
              </span>
            ` : ''}
          </div>
        </div>
        ${isOwn && !message.is_deleted ? `
          <div class="message-actions dropdown">
            <button class="btn btn-sm" data-bs-toggle="dropdown">
              <i class="bi bi-three-dots-vertical"></i>
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li><a class="dropdown-item" href="#" data-action="copy-message">Copy</a></li>
              <li><a class="dropdown-item text-danger" href="#" data-action="delete-message">Delete</a></li>
            </ul>
          </div>
        ` : ''}
      </div>
    `;
    
    // Add event listeners for message actions
    const copyBtn = messageEl.querySelector('[data-action="copy-message"]');
    if (copyBtn) {
      copyBtn.addEventListener('click', function(e) {
        e.preventDefault();
        copyMessageContent(message.content);
      });
    }
    
    const deleteBtn = messageEl.querySelector('[data-action="delete-message"]');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', function(e) {
        e.preventDefault();
        deleteMessage(message.id);
      });
    }
    
    return messageEl;
  }
  
  // Handle scroll events for messages
  function handleMessagesScroll() {
    // Load more messages when scrolling to top
    if (chatMessages.scrollTop === 0 && hasMoreMessages && !isLoading) {
      loadChatMessages(currentPage + 1);
    }
    
    // Mark messages as read when scrolling down
    if (chatMessages.scrollHeight - chatMessages.scrollTop <= chatMessages.clientHeight + 100) {
      markMessagesAsRead();
    }
  }
  
  // Send a new message
  function sendMessage(e) {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Clear input and reset height
    messageInput.value = '';
    autoResizeTextarea(messageInput);
    
    // Focus back on input
    messageInput.focus();
    
    // Send via socket
    if (typeof socket !== 'undefined' && socket.connected) {
      sendChatMessage(chatId, message)
        .then(sentMessage => {
          // Message sent successfully via socket
          appendMessage(sentMessage);
          scrollToBottom();
        })
        .catch(error => {
          console.error('Error sending message via socket:', error);
          // Fallback to AJAX
          sendMessageAjax(message);
        });
    } else {
      // Socket not available, use AJAX
      sendMessageAjax(message);
    }
  }
  
  // Send message via AJAX (fallback)
  function sendMessageAjax(message) {
    fetch(`/api/chat/${chatId}/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content: message })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        appendMessage(data.message);
        scrollToBottom();
      } else {
        showToast(data.error || 'Error sending message', 'danger');
      }
    })
    .catch(error => {
      console.error('Error sending message:', error);
      showToast('Error sending message. Please try again.', 'danger');
    });
  }
  
  // Append a message to the chat
  function appendMessage(message) {
    const currentUserId = getCurrentUserId();
    const messageEl = createMessageElement(message, currentUserId);
    
    chatMessages.appendChild(messageEl);
    
    // Update last message ID
    lastMessageId = message.id;
    
    // Scroll to bottom
    scrollToBottom();
    
    // Mark as read
    markMessagesAsRead();
  }
  
  // Update a deleted message in the UI
  function updateDeletedMessage(message) {
    const messageEl = document.querySelector(`.message-item[data-message-id="${message.id}"]`);
    if (!messageEl) return;
    
    const messageBubble = messageEl.querySelector('.message-bubble');
    const messageContent = messageEl.querySelector('.message-content, .message-media');
    const messageActions = messageEl.querySelector('.message-actions');
    
    if (messageContent) {
      messageContent.outerHTML = `<div class="message-deleted text-muted"><i class="bi bi-trash me-1"></i> This message was deleted</div>`;
    }
    
    if (messageActions) {
      messageActions.remove();
    }
  }
  
  // Scroll to bottom of messages
  function scrollToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }
  
  // Copy message content to clipboard
  function copyMessageContent(content) {
    navigator.clipboard.writeText(content).then(() => {
      showToast('Message copied to clipboard', 'success');
    }).catch(error => {
      console.error('Error copying to clipboard:', error);
      showToast('Error copying message', 'danger');
    });
  }
  
  // Delete a message
  function deleteMessage(messageId) {
    if (typeof socket !== 'undefined' && socket.connected) {
      deleteChatMessage(messageId)
        .then(result => {
          // Message deleted successfully via socket
          showToast('Message deleted', 'success');
        })
        .catch(error => {
          console.error('Error deleting message via socket:', error);
          showToast('Error deleting message', 'danger');
        });
    } else {
      // Socket not available, use AJAX
      fetch(`/api/chat/message/${messageId}/delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          updateDeletedMessage(data.message);
          showToast('Message deleted', 'success');
        } else {
          showToast(data.error || 'Error deleting message', 'danger');
        }
      })
      .catch(error => {
        console.error('Error deleting message:', error);
        showToast('Error deleting message. Please try again.', 'danger');
      });
    }
  }
  
  // Mark messages as read
  function markMessagesAsRead() {
    if (!chatId) return;
    
    if (typeof socket !== 'undefined' && socket.connected) {
      socket.emit('read_messages', { chat_id: chatId });
    } else {
      // Fallback to AJAX
      fetch(`/api/chat/${chatId}/read`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      }).catch(error => {
        console.error('Error marking messages as read:', error);
      });
    }
  }
  
  // Update read receipts in the UI
  function updateReadReceipts(data) {
    const messageEls = document.querySelectorAll('.message-own');
    
    messageEls.forEach(messageEl => {
      const statusEl = messageEl.querySelector('.message-status');
      if (statusEl) {
        statusEl.innerHTML = '<i class="bi bi-check2-all text-primary" title="Read"></i>';
      }
    });
  }
  
  // Initialize new chat modal
  function initNewChatModal() {
    const newChatModal = document.getElementById('new-chat-modal');
    if (!newChatModal) return;
    
    const searchInput = newChatModal.querySelector('#new-chat-search');
    const searchResults = newChatModal.querySelector('#new-chat-results');
    
    if (searchInput) {
      searchInput.addEventListener('input', debounce(function() {
        const query = this.value.trim();
        if (query.length < 2) {
          searchResults.innerHTML = '<p class="text-center text-muted">Type at least 2 characters to search</p>';
          return;
        }
        
        searchFriends(query, searchResults);
      }, 300));
    }
    
    // Handle click on search results
    if (searchResults) {
      searchResults.addEventListener('click', function(e) {
        const friendItem = e.target.closest('.friend-item');
        if (friendItem) {
          const userId = friendItem.dataset.userId;
          createDirectChat(userId);
        }
      });
    }
  }
  
  // Search friends for new chat
  function searchFriends(query, resultsContainer) {
    resultsContainer.innerHTML = `
      <div class="text-center p-2">
        <div class="spinner-border spinner-border-sm text-primary" role="status">
          <span class="visually-hidden">Searching...</span>
        </div>
      </div>
    `;
    
    fetch(`/api/friends?search=${encodeURIComponent(query)}`)
      .then(response => response.json())
      .then(data => {
        if (data.friends.length === 0) {
          resultsContainer.innerHTML = '<p class="text-center text-muted">No friends found</p>';
          return;
        }
        
        resultsContainer.innerHTML = '';
        
        data.friends.forEach(friend => {
          const friendItem = document.createElement('div');
          friendItem.className = 'friend-item d-flex align-items-center p-2 border-bottom';
          friendItem.dataset.userId = friend.user.id;
          
          friendItem.innerHTML = `
            <img src="${friend.user.profile_pic || '/static/img/default-avatar.png'}" 
              alt="${friend.user.username}" class="rounded-circle me-3" width="40" height="40">
            <div class="flex-grow-1">
              <h6 class="mb-0">${friend.user.username}</h6>
            </div>
            <button class="btn btn-sm btn-primary">
              <i class="bi bi-chat-dots-fill"></i>
            </button>
          `;
          
          resultsContainer.appendChild(friendItem);
        });
      })
      .catch(error => {
        console.error('Error searching friends:', error);
        resultsContainer.innerHTML = '<p class="text-center text-danger">Error searching friends</p>';
      });
  }
  
  // Create a direct chat
  function createDirectChat(userId) {
    const newChatModal = document.getElementById('new-chat-modal');
    const bsModal = bootstrap.Modal.getInstance(newChatModal);
    
    // Show loading state
    const modalBody = newChatModal.querySelector('.modal-body');
    modalBody.innerHTML = `
      <div class="text-center p-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Creating chat...</span>
        </div>
        <p class="mt-3">Creating conversation...</p>
      </div>
    `;
    
    fetch('/api/chat/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        is_group: false,
        member_ids: [userId]
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Close modal
        bsModal.hide();
        
        // Redirect to new chat
        window.location.href = `/chat/${data.chat.id}`;
      } else {
        showToast(data.error || 'Error creating chat', 'danger');
        bsModal.hide();
      }
    })
    .catch(error => {
      console.error('Error creating chat:', error);
      showToast('Error creating chat. Please try again.', 'danger');
      bsModal.hide();
    });
  }
  
  // Initialize group chat modal
  function initGroupChatModal() {
    const groupChatModal = document.getElementById('group-chat-modal');
    if (!groupChatModal) return;
    
    const searchInput = groupChatModal.querySelector('#group-chat-search');
    const searchResults = groupChatModal.querySelector('#group-chat-results');
    const selectedMembers = groupChatModal.querySelector('#selected-members');
    const createGroupBtn = groupChatModal.querySelector('#create-group-btn');
    const groupNameInput = groupChatModal.querySelector('#group-name');
    
    if (searchInput) {
      searchInput.addEventListener('input', debounce(function() {
        const query = this.value.trim();
        if (query.length < 2) {
          searchResults.innerHTML = '<p class="text-center text-muted">Type at least 2 characters to search</p>';
          return;
        }
        
        searchFriendsForGroup(query, searchResults, selectedMembers);
      }, 300));
    }
    
    // Handle click on search results
    if (searchResults) {
      searchResults.addEventListener('click', function(e) {
        const selectButton = e.target.closest('[data-action="select-friend"]');
        if (selectButton) {
          const friendItem = selectButton.closest('.friend-item');
          const userId = friendItem.dataset.userId;
          const username = friendItem.dataset.username;
          const profilePic = friendItem.dataset.profilePic;
          
          addSelectedMember(userId, username, profilePic, selectedMembers);
          updateCreateGroupButton(createGroupBtn, selectedMembers);
        }
      });
    }
    
    // Handle remove selected member
    if (selectedMembers) {
      selectedMembers.addEventListener('click', function(e) {
        const removeButton = e.target.closest('[data-action="remove-member"]');
        if (removeButton) {
          const memberItem = removeButton.closest('.selected-member');
          memberItem.remove();
          updateCreateGroupButton(createGroupBtn, selectedMembers);
        }
      });
    }
    
    // Handle group name input
    if (groupNameInput) {
      groupNameInput.addEventListener('input', function() {
        updateCreateGroupButton(createGroupBtn, selectedMembers);
      });
    }
    
    // Handle create group button
    if (createGroupBtn) {
      createGroupBtn.addEventListener('click', function() {
        createGroupChat(groupNameInput.value, selectedMembers);
      });
    }
  }
  
  // Search friends for group chat
  function searchFriendsForGroup(query, resultsContainer, selectedMembersContainer) {
    resultsContainer.innerHTML = `
      <div class="text-center p-2">
        <div class="spinner-border spinner-border-sm text-primary" role="status">
          <span class="visually-hidden">Searching...</span>
        </div>
      </div>
    `;
    
    fetch(`/api/friends?search=${encodeURIComponent(query)}`)
      .then(response => response.json())
      .then(data => {
        if (data.friends.length === 0) {
          resultsContainer.innerHTML = '<p class="text-center text-muted">No friends found</p>';
          return;
        }
        
        resultsContainer.innerHTML = '';
        
        // Get already selected member IDs
        const selectedIds = Array.from(selectedMembersContainer.querySelectorAll('.selected-member'))
          .map(item => item.dataset.userId);
        
        data.friends.forEach(friend => {
          // Skip already selected members
          if (selectedIds.includes(friend.user.id.toString())) return;
          
          const friendItem = document.createElement('div');
          friendItem.className = 'friend-item d-flex align-items-center p-2 border-bottom';
          friendItem.dataset.userId = friend.user.id;
          friendItem.dataset.username = friend.user.username;
          friendItem.dataset.profilePic = friend.user.profile_pic || '/static/img/default-avatar.png';
          
          friendItem.innerHTML = `
            <img src="${friend.user.profile_pic || '/static/img/default-avatar.png'}" 
              alt="${friend.user.username}" class="rounded-circle me-3" width="40" height="40">
            <div class="flex-grow-1">
              <h6 class="mb-0">${friend.user.username}</h6>
            </div>
            <button class="btn btn-sm btn-outline-primary" data-action="select-friend">
              <i class="bi bi-plus"></i>
            </button>
          `;
          
          resultsContainer.appendChild(friendItem);
        });
      })
      .catch(error => {
        console.error('Error searching friends:', error);
        resultsContainer.innerHTML = '<p class="text-center text-danger">Error searching friends</p>';
      });
  }
  
  // Add selected member to the list
  function addSelectedMember(userId, username, profilePic, container) {
    // Check if already selected
    if (container.querySelector(`.selected-member[data-user-id="${userId}"]`)) {
      return;
    }
    
    const memberItem = document.createElement('div');
    memberItem.className = 'selected-member badge bg-primary me-2 mb-2 p-2';
    memberItem.dataset.userId = userId;
    
    memberItem.innerHTML = `
      <img src="${profilePic}" alt="${username}" class="rounded-circle me-1" width="20" height="20">
      ${username}
      <button type="button" class="btn-close btn-close-white ms-1" data-action="remove-member" aria-label="Remove"></button>
    `;
    
    container.appendChild(memberItem);
  }
  
  // Update create group button state
  function updateCreateGroupButton(button, selectedMembersContainer) {
    const memberCount = selectedMembersContainer.querySelectorAll('.selected-member').length;
    const groupNameInput = document.getElementById('group-name');
    const groupName = groupNameInput ? groupNameInput.value.trim() : '';
    
    // Enable if name is provided and at least 2 members selected (3 total including creator)
    const isValid = groupName.length > 0 && memberCount >= 2;
    
    button.disabled = !isValid;
    
    // Update button text with member count
    button.innerHTML = isValid ? 
      `Create Group (${memberCount + 1} members)` : 
      `Create Group`;
  }
  
  // Create a group chat
  function createGroupChat(groupName, selectedMembersContainer) {
    const groupChatModal = document.getElementById('group-chat-modal');
    const bsModal = bootstrap.Modal.getInstance(groupChatModal);
    
    // Get selected member IDs
    const memberIds = Array.from(selectedMembersContainer.querySelectorAll('.selected-member'))
      .map(item => parseInt(item.dataset.userId, 10));
    
    if (memberIds.length < 2) {
      showToast('Please select at least 2 members for a group chat', 'warning');
      return;
    }
    
    if (!groupName) {
      showToast('Please enter a group name', 'warning');
      return;
    }
    
    // Show loading state
    const modalBody = groupChatModal.querySelector('.modal-body');
    modalBody.innerHTML = `
      <div class="text-center p-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Creating group...</span>
        </div>
        <p class="mt-3">Creating group chat...</p>
      </div>
    `;
    
    fetch('/api/chat/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        is_group: true,
        name: groupName,
        member_ids: memberIds
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Close modal
        bsModal.hide();
        
        // Redirect to new chat
        window.location.href = `/chat/${data.chat.id}`;
      } else {
        showToast(data.error || 'Error creating group chat', 'danger');
        bsModal.hide();
      }
    })
    .catch(error => {
      console.error('Error creating group chat:', error);
      showToast('Error creating group chat. Please try again.', 'danger');
      bsModal.hide();
    });
  }
  
  // Load chat members
  function loadChatMembers() {
    if (!membersContainer || !chatId) return;
    
    fetch(`/api/chat/${chatId}/members`)
      .then(response => response.json())
      .then(data => {
        renderChatMembers(data.members);
      })
      .catch(error => {
        console.error('Error loading chat members:', error);
        membersContainer.innerHTML = `
          <div class="alert alert-danger">
            Error loading members. <a href="#" onclick="chatModule.loadChatMembers(); return false;">Try again</a>
          </div>
        `;
      });
  }
  
  // Render chat members
  function renderChatMembers(members) {
    if (!membersContainer) return;
    
    membersContainer.innerHTML = '';
    
    if (members.length === 0) {
      membersContainer.innerHTML = '<p class="text-center text-muted">No members</p>';
      return;
    }
    
    const currentUserId = getCurrentUserId();
    const isAdmin = members.some(m => m.user_id == currentUserId && m.role === 'admin');
    
    members.forEach(member => {
      const memberItem = document.createElement('div');
      memberItem.className = 'member-item d-flex align-items-center p-2 border-bottom';
      memberItem.dataset.userId = member.user_id;
      
      memberItem.innerHTML = `
        <img src="${member.profile_pic || '/static/img/default-avatar.png'}" 
          alt="${member.username}" class="rounded-circle me-3" width="40" height="40">
        <div class="flex-grow-1">
          <h6 class="mb-0">
            ${member.username}
            ${member.role === 'admin' ? '<span class="badge bg-primary ms-2">Admin</span>' : ''}
          </h6>
          <small class="text-muted">Joined ${timeAgo(member.joined_at)}</small>
        </div>
        
        ${isAdmin && member.user_id != currentUserId ? `
          <div class="dropdown">
            <button class="btn btn-sm" type="button" data-bs-toggle="dropdown">
              <i class="bi bi-three-dots-vertical"></i>
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
              ${member.role !== 'admin' ? 
                `<li><a class="dropdown-item" href="#" data-action="make-admin" data-user-id="${member.user_id}">Make Admin</a></li>` : 
                ''
              }
              <li><a class="dropdown-item text-danger" href="#" data-action="remove-member" data-user-id="${member.user_id}">Remove</a></li>
            </ul>
          </div>
        ` : ''}
      `;
      
      // Add event listeners for member actions
      const makeAdminBtn = memberItem.querySelector('[data-action="make-admin"]');
      if (makeAdminBtn) {
        makeAdminBtn.addEventListener('click', function(e) {
          e.preventDefault();
          makeAdmin(member.user_id);
        });
      }
      
      const removeMemberBtn = memberItem.querySelector('[data-action="remove-member"]');
      if (removeMemberBtn) {
        removeMemberBtn.addEventListener('click', function(e) {
          e.preventDefault();
          removeMember(member.user_id);
        });
      }
      
      membersContainer.appendChild(memberItem);
    });
  }
  
  // Make a member an admin
  function makeAdmin(userId) {
    if (!chatId) return;
    
    fetch(`/api/chat/${chatId}/make_admin`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showToast('Member promoted to admin', 'success');
        loadChatMembers(); // Reload members
      } else {
        showToast(data.error || 'Error promoting member', 'danger');
      }
    })
    .catch(error => {
      console.error('Error promoting member:', error);
      showToast('Error promoting member. Please try again.', 'danger');
    });
  }
  
  // Remove a member from the chat
  function removeMember(userId) {
    if (!chatId) return;
    
    if (!confirm('Are you sure you want to remove this member?')) {
      return;
    }
    
    fetch(`/api/chat/${chatId}/remove_member`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showToast('Member removed', 'success');
        
        // Remove from UI
        const memberItem = membersContainer.querySelector(`.member-item[data-user-id="${userId}"]`);
        if (memberItem) {
          memberItem.remove();
        }
      } else {
        showToast(data.error || 'Error removing member', 'danger');
      }
    })
    .catch(error => {
      console.error('Error removing member:', error);
      showToast('Error removing member. Please try again.', 'danger');
    });
  }
  
  // Show modal to start a new chat
  function showNewChatModal() {
    const newChatModal = document.getElementById('new-chat-modal');
    if (!newChatModal) return;
    
    // Reset modal content
    const searchInput = newChatModal.querySelector('#new-chat-search');
    const searchResults = newChatModal.querySelector('#new-chat-results');
    
    if (searchInput) searchInput.value = '';
    if (searchResults) {
      searchResults.innerHTML = '<p class="text-center text-muted">Search for friends to start a chat</p>';
    }
    
    // Show modal
    const bsModal = new bootstrap.Modal(newChatModal);
    bsModal.show();
  }
  
  // Update chat list
  function updateChatList(chatId, message) {
    if (!chatList) return;
    
    // Find chat item if exists
    let chatItem = chatList.querySelector(`.chat-item[href="/chat/${chatId}"]`);
    
    if (chatItem) {
      // Update existing chat item
      const lastMessageEl = chatItem.querySelector('.chat-info p');
      const timeEl = chatItem.querySelector('.chat-info small');
      const unreadBadge = chatItem.querySelector('.chat-unread-badge');
      
      if (lastMessageEl) {
        lastMessageEl.textContent = truncateText(message.content, 30);
      }
      
      if (timeEl) {
        timeEl.textContent = timeAgo(message.created_at);
      }
      
      // Increment unread count if not the current chat
      if (chatId !== parseInt(window.location.pathname.split('/chat/')[1]) && message.user_id !== getCurrentUserId()) {
        if (unreadBadge) {
          const count = parseInt(unreadBadge.textContent) + 1;
          unreadBadge.textContent = count;
          unreadBadge.style.display = 'block';
        } else {
          // Create new badge
          const badge = document.createElement('div');
          badge.className = 'chat-unread-badge badge bg-danger rounded-pill';
          badge.textContent = '1';
          chatItem.appendChild(badge);
        }
      }
      
      // Move chat to top
      chatList.insertBefore(chatItem, chatList.firstChild);
    } else {
      // Chat not in list, refresh the entire list
      loadChatList();
    }
  }
  
  // Update a chat in the list
  function updateChatInList(chat) {
    if (!chatList) return;
    
    // Find chat item if exists
    let chatItem = chatList.querySelector(`.chat-item[href="/chat/${chat.id}"]`);
    
    if (chatItem) {
      // Update chat item
      const nameEl = chatItem.querySelector('.chat-info h6');
      if (nameEl) {
        nameEl.textContent = chat.name;
      }
      
      // Update last message if available
      if (chat.last_message) {
        const lastMessageEl = chatItem.querySelector('.chat-info p');
        const timeEl = chatItem.querySelector('.chat-info small');
        
        if (lastMessageEl) {
          lastMessageEl.textContent = truncateText(chat.last_message.content, 30);
        }
        
        if (timeEl) {
          timeEl.textContent = timeAgo(chat.last_message.created_at);
        }
      }
    }
  }
  
  // Update chat details
  function updateChatDetails(chat) {
    // Update chat name in header
    const chatNameEl = document.querySelector('.chat-header .chat-name');
    if (chatNameEl) {
      chatNameEl.textContent = chat.name;
    }
    
    // Update member count
    const memberCountEl = document.querySelector('.chat-header .member-count');
    if (memberCountEl && chat.members) {
      memberCountEl.textContent = `${chat.members.length} members`;
    }
  }
  
  // Add a member to the UI
  function addMember(member) {
    if (!membersContainer) return;
    
    // Check if member already exists
    const existingMember = membersContainer.querySelector(`.member-item[data-user-id="${member.user_id}"]`);
    if (existingMember) return;
    
    const currentUserId = getCurrentUserId();
    const isAdmin = membersContainer.querySelector(`.member-item[data-user-id="${currentUserId}"] .badge.bg-primary`) !== null;
    
    const memberItem = document.createElement('div');
    memberItem.className = 'member-item d-flex align-items-center p-2 border-bottom';
    memberItem.dataset.userId = member.user_id;
    
    memberItem.innerHTML = `
      <img src="${member.profile_pic || '/static/img/default-avatar.png'}" 
        alt="${member.username}" class="rounded-circle me-3" width="40" height="40">
      <div class="flex-grow-1">
        <h6 class="mb-0">
          ${member.username}
          ${member.role === 'admin' ? '<span class="badge bg-primary ms-2">Admin</span>' : ''}
        </h6>
        <small class="text-muted">Joined ${timeAgo(member.joined_at)}</small>
      </div>
      
      ${isAdmin && member.user_id != currentUserId ? `
        <div class="dropdown">
          <button class="btn btn-sm" type="button" data-bs-toggle="dropdown">
            <i class="bi bi-three-dots-vertical"></i>
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
            ${member.role !== 'admin' ? 
              `<li><a class="dropdown-item" href="#" data-action="make-admin" data-user-id="${member.user_id}">Make Admin</a></li>` : 
              ''
            }
            <li><a class="dropdown-item text-danger" href="#" data-action="remove-member" data-user-id="${member.user_id}">Remove</a></li>
          </ul>
        </div>
      ` : ''}
    `;
    
    // Add event listeners for member actions
    const makeAdminBtn = memberItem.querySelector('[data-action="make-admin"]');
    if (makeAdminBtn) {
      makeAdminBtn.addEventListener('click', function(e) {
        e.preventDefault();
        makeAdmin(member.user_id);
      });
    }
    
    const removeMemberBtn = memberItem.querySelector('[data-action="remove-member"]');
    if (removeMemberBtn) {
      removeMemberBtn.addEventListener('click', function(e) {
        e.preventDefault();
        removeMember(member.user_id);
      });
    }
    
    membersContainer.appendChild(memberItem);
    
    // Update member count
    const memberCountEl = document.querySelector('.chat-header .member-count');
    if (memberCountEl) {
      const count = membersContainer.querySelectorAll('.member-item').length;
      memberCountEl.textContent = `${count} members`;
    }
  }
  
  // Remove a member from the UI
  function removeMember(userId) {
    if (!membersContainer) return;
    
    const memberItem = membersContainer.querySelector(`.member-item[data-user-id="${userId}"]`);
    if (memberItem) {
      memberItem.remove();
      
      // Update member count
      const memberCountEl = document.querySelector('.chat-header .member-count');
      if (memberCountEl) {
        const count = membersContainer.querySelectorAll('.member-item').length;
        memberCountEl.textContent = `${count} members`;
      }
    }
  }
  
  // Get current user ID
  function getCurrentUserId() {
    const userIdEl = document.getElementById('current-user-id');
    return userIdEl ? userIdEl.value : null;
  }
  
  // Initialize module when document is ready
  document.addEventListener('DOMContentLoaded', init);
  
  // Public methods for socket.js to use
  return {
    appendMessage,
    updateDeletedMessage,
    updateReadReceipts,
    updateChatList,
    updateChatInList,
    updateChatDetails,
    addMember,
    removeMember,
    loadChatMessages,
    loadChatMembers,
    loadChatList
  };
})();

// Make chat module available globally
window.chatModule = chatModule;
