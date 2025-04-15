// Profile related functionality

// Initialize profile module with namespace
const profileModule = (function() {
  // Private variables
  let postsContainer;
  let userInfoContainer;
  let photosContainer;
  let friendsContainer;
  let currentPage = 1;
  let isLoading = false;
  let hasMorePosts = true;
  let profileUsername;

  // Initialize profile
  function init() {
    postsContainer = document.getElementById('profile-posts');
    userInfoContainer = document.getElementById('user-info');
    photosContainer = document.getElementById('photos-container');
    friendsContainer = document.getElementById('friends-container');

    // Get profile username from URL
    const pathParts = window.location.pathname.split('/');
    if ((pathParts[1] === 'profile' || pathParts[1] === 'auth' && pathParts[2] === 'profile') && pathParts[pathParts.length-1]) {
      profileUsername = pathParts[pathParts.length-1];
    }

    if (postsContainer && profileUsername) {
      // Load profile data
      loadProfileData(profileUsername);

      // Set up infinite scroll
      window.addEventListener('scroll', debounce(handleScroll, 300));
    }

    // Set up friendship buttons
    setupFriendshipButtons();

    // Set up profile edit form if present
    setupProfileEditForm();

    // Set up change picture functionality
    setupProfilePicture();
  }

  // Handle scroll events for infinite loading
  function handleScroll() {
    if (isLoading || !hasMorePosts) return;

    // Check if we're near the bottom of the page
    const scrollPosition = window.innerHeight + window.pageYOffset;
    const pageHeight = document.documentElement.scrollHeight;

    if (scrollPosition >= pageHeight - 500) {
      loadMorePosts();
    }
  }

  // Load profile data
  function loadProfileData(username, page = 1) {
    if (!username) return;

    isLoading = true;

    // Show loading state
    if (page === 1) {
      postsContainer.innerHTML = `
        <div class="text-center p-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading profile...</span>
          </div>
        </div>
      `;
    } else {
      // Show loading indicator at the bottom for more posts
      postsContainer.insertAdjacentHTML('beforeend', `
        <div class="text-center p-3 loading-more">
          <div class="spinner-border spinner-border-sm text-primary" role="status">
            <span class="visually-hidden">Loading more posts...</span>
          </div>
        </div>
      `);
    }

    fetch(`/api/profile/${username}?page=${page}`)
      .then(response => response.json())
      .then(data => {
        isLoading = false;

        // Remove loading indicators
        if (page === 1) {
          postsContainer.innerHTML = '';
        } else {
          const loadingMore = postsContainer.querySelector('.loading-more');
          if (loadingMore) loadingMore.remove();
        }

        // Update user info if first page
        if (page === 1) {
          if (userInfoContainer) {
            renderUserInfo(data);
          }

          // Render photos and friends
          if (photosContainer) {
            renderPhotos(data.posts);
          }

          if (friendsContainer) {
            renderFriends(data.friends || []);
          }
        }

        // Render posts
        if (data.posts.length === 0 && page === 1) {
          showEmptyPostsState();
        } else {
          renderProfilePosts(data.posts, page > 1);
        }

        // Update pagination info
        currentPage = data.pagination.current_page;
        hasMorePosts = currentPage < data.pagination.total_pages;
      })
      .catch(error => {
        console.error('Error loading profile data:', error);
        isLoading = false;

        // Remove loading indicators
        if (page === 1) {
          postsContainer.innerHTML = `
            <div class="alert alert-danger">
              Error loading profile. <a href="#" onclick="profileModule.loadProfileData('${username}'); return false;">Try again</a>
            </div>
          `;
        } else {
          const loadingMore = postsContainer.querySelector('.loading-more');
          if (loadingMore) loadingMore.remove();
        }
      });
  }

  // Load more posts
  function loadMorePosts() {
    if (isLoading || !hasMorePosts || !profileUsername) return;

    loadProfileData(profileUsername, currentPage + 1);
  }

  // Render user info
  function renderUserInfo(data) {
    if (!userInfoContainer) return;

    const user = data.user;
    const friendshipStatus = data.friendship_status;
    const isFollowing = data.is_following;

    // Update cover photo if present
    const coverEl = document.querySelector('.profile-cover');
    if (coverEl && user.cover_pic) {
      coverEl.style.backgroundImage = `url('${user.cover_pic}')`;
    }

    // Update profile picture
    const profilePicEl = document.querySelector('.profile-picture img');
    if (profilePicEl) {
      profilePicEl.src = user.profile_pic || '/static/img/default-avatar.png';
      profilePicEl.alt = user.username;
    }

    // Update user info
    userInfoContainer.innerHTML = `
      <h3 class="mb-0">${user.username}</h3>
      ${user.bio ? `<p class="text-muted mb-3">${user.bio}</p>` : '<p class="text-muted mb-3">No bio yet</p>'}

      <div class="profile-stats d-flex mb-3">
        <div class="stat me-4">
          <strong>${data.friend_count}</strong> Friends
        </div>
        <div class="stat me-4">
          <strong>${data.follower_count}</strong> Followers
        </div>
        <div class="stat">
          <strong>${data.following_count}</strong> Following
        </div>
      </div>

      <div class="profile-actions">
        ${renderProfileActions(user, friendshipStatus, isFollowing)}
      </div>
    `;

    // Update page title
    document.title = `${user.username} - Profile`;
  }

  // Render profile action buttons
  function renderProfileActions(user, friendshipStatus, isFollowing) {
    const currentUserId = getCurrentUserId();

    // If not logged in, show login button
    if (!currentUserId) {
      return `
        <a href="/auth/login" class="btn btn-primary me-2">
          <i class="bi bi-box-arrow-in-right me-1"></i> Login to Interact
        </a>
      `;
    }

    // If this is the current user's profile
    if (user.id == currentUserId) {
      return `
        <a href="/auth/settings" class="btn btn-outline-primary me-2">
          <i class="bi bi-pencil me-1"></i> Edit Profile
        </a>
        <a href="/auth/settings" class="btn btn-outline-secondary">
          <i class="bi bi-gear me-1"></i> Settings
        </a>
      `;
    }

    // Actions for other users
    let friendButton = '';

    if (friendshipStatus === 'accepted') {
      friendButton = `
        <button class="btn btn-outline-primary me-2" data-action="unfriend" data-username="${user.username}">
          <i class="bi bi-person-check me-1"></i> Friends
        </button>
      `;
    } else if (friendshipStatus === 'pending') {
      // If we sent the request
      friendButton = `
        <button class="btn btn-outline-secondary me-2" data-action="cancel-request" data-username="${user.username}">
          <i class="bi bi-person-dash me-1"></i> Cancel Request
        </button>
      `;
    } else if (friendshipStatus === 'received') {
      // If we received the request
      friendButton = `
        <button class="btn btn-primary me-2" data-action="accept-request" data-username="${user.username}">
          <i class="bi bi-person-plus me-1"></i> Accept Request
        </button>
        <button class="btn btn-outline-danger me-2" data-action="decline-request" data-username="${user.username}">
          <i class="bi bi-person-x me-1"></i> Decline
        </button>
      `;
    } else {
      // No friendship yet
      friendButton = `
        <button class="btn btn-primary me-2" data-action="add-friend" data-username="${user.username}">
          <i class="bi bi-person-plus me-1"></i> Add Friend
        </button>
      `;
    }

    // Follow button
    const followButton = isFollowing ?
      `<button class="btn btn-outline-primary me-2" data-action="unfollow" data-username="${user.username}">
        <i class="bi bi-person-dash me-1"></i> Unfollow
      </button>` :
      `<button class="btn btn-outline-primary me-2" data-action="follow" data-username="${user.username}">
        <i class="bi bi-person-plus me-1"></i> Follow
      </button>`;

    // Message button
    const messageButton = `
      <a href="#" class="btn btn-outline-secondary me-2" data-action="message" data-user-id="${user.id}">
        <i class="bi bi-chat-dots me-1"></i> Message
      </a>
    `;

    return `
      ${friendButton}
      ${followButton}
      ${messageButton}
    `;
  }

  // Show empty posts state
  function showEmptyPostsState() {
    postsContainer.innerHTML = `
      <div class="text-center p-5">
        <div class="display-1 text-muted">
          <i class="bi bi-newspaper"></i>
        </div>
        <h3 class="mt-3">No posts yet</h3>
        <p class="text-muted">This user hasn't shared any posts</p>
      </div>
    `;
  }

  // Render profile posts
  function renderProfilePosts(posts, append = false) {
    if (!postsContainer) return;

    if (!append) {
      postsContainer.innerHTML = '';
    }

    posts.forEach(post => {
      const postEl = createPostElement(post);
      postsContainer.appendChild(postEl);
    });

    // Initialize lazy loading for images
    lazyLoadImages();
  }

  // Create a post element
  function createPostElement(post) {
    const postEl = document.createElement('div');
    postEl.className = 'card post mb-3';
    postEl.dataset.postId = post.id;

    // Format date
    const postDate = timeAgo(post.created_at);

    // Create media HTML if post has media
    let mediaHTML = '';
    if (post.media && post.media.length > 0) {
      if (post.media.length === 1) {
        // Single image
        mediaHTML = `
          <div class="post-media">
            <img class="img-fluid rounded" data-src="${post.media[0].media_url}" alt="Post image">
          </div>
        `;
      } else {
        // Multiple images - carousel
        const indicators = post.media.map((_, index) =>
          `<button type="button" data-bs-target="#carousel-${post.id}" data-bs-slide-to="${index}"
          ${index === 0 ? 'class="active" aria-current="true"' : ''} aria-label="Slide ${index + 1}"></button>`
        ).join('');

        const slides = post.media.map((media, index) => `
          <div class="carousel-item ${index === 0 ? 'active' : ''}">
            <img class="d-block w-100" data-src="${media.media_url}" alt="Post image ${index + 1}">
          </div>
        `).join('');

        mediaHTML = `
          <div class="post-media">
            <div id="carousel-${post.id}" class="carousel slide" data-bs-ride="false">
              <div class="carousel-indicators">
                ${indicators}
              </div>
              <div class="carousel-inner rounded">
                ${slides}
              </div>
              <button class="carousel-control-prev" type="button" data-bs-target="#carousel-${post.id}" data-bs-slide="prev">
                <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                <span class="visually-hidden">Previous</span>
              </button>
              <button class="carousel-control-next" type="button" data-bs-target="#carousel-${post.id}" data-bs-slide="next">
                <span class="carousel-control-next-icon" aria-hidden="true"></span>
                <span class="visually-hidden">Next</span>
              </button>
            </div>
          </div>
        `;
      }
    }

    postEl.innerHTML = `
      <div class="card-header d-flex align-items-center">
        <img src="${post.profile_pic || '/static/img/default-avatar.png'}" alt="${post.author}"
          class="rounded-circle me-3" width="40" height="40">
        <div>
          <div class="fw-bold">${post.author}</div>
          <div class="text-muted small">${postDate}</div>
        </div>
        <div class="dropdown ms-auto">
          <button class="btn btn-sm" type="button" data-bs-toggle="dropdown" aria-expanded="false">
            <i class="bi bi-three-dots-vertical"></i>
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
            <li><a class="dropdown-item" href="/post/${post.id}">View Post</a></li>
            ${post.user_id === getCurrentUserId() ?
              `<li><a class="dropdown-item text-danger" href="#" data-action="delete-post">Delete Post</a></li>` :
              `<li><a class="dropdown-item" href="#" data-action="report-post">Report Post</a></li>`
            }
          </ul>
        </div>
      </div>
      <div class="card-body">
        <p class="card-text">${post.content}</p>
        ${mediaHTML}
      </div>
      <div class="card-footer">
        <div class="d-flex post-actions">
          <button class="btn btn-sm post-like-btn ${post.liked_by_user ? 'active text-danger' : ''}"
            data-action="like" data-post-id="${post.id}">
            <i class="bi ${post.liked_by_user ? 'bi-heart-fill' : 'bi-heart'}"></i>
            <span class="like-count">${formatCount(post.like_count || 0)}</span>
          </button>
          <button class="btn btn-sm post-comment-btn ms-2" data-action="comment" data-post-id="${post.id}">
            <i class="bi bi-chat"></i>
            <span class="comment-count">${formatCount(post.comment_count || 0)}</span>
          </button>
          <button class="btn btn-sm ms-2" data-action="share" data-post-id="${post.id}">
            <i class="bi bi-share"></i>
          </button>
        </div>
      </div>
    `;

    return postEl;
  }

  // Set up friendship buttons
  function setupFriendshipButtons() {
    // Use event delegation for friend buttons
    document.addEventListener('click', function(e) {
      // Add friend
      if (e.target.closest('[data-action="add-friend"]')) {
        const btn = e.target.closest('[data-action="add-friend"]');
        const username = btn.dataset.username;
        addFriend(username, btn);
      }

      // Unfriend
      if (e.target.closest('[data-action="unfriend"]')) {
        const btn = e.target.closest('[data-action="unfriend"]');
        const username = btn.dataset.username;
        unfriend(username, btn);
      }

      // Cancel request
      if (e.target.closest('[data-action="cancel-request"]')) {
        const btn = e.target.closest('[data-action="cancel-request"]');
        const username = btn.dataset.username;
        cancelRequest(username, btn);
      }

      // Accept request
      if (e.target.closest('[data-action="accept-request"]')) {
        const btn = e.target.closest('[data-action="accept-request"]');
        const username = btn.dataset.username;
        acceptRequest(username, btn);
      }

      // Decline request
      if (e.target.closest('[data-action="decline-request"]')) {
        const btn = e.target.closest('[data-action="decline-request"]');
        const username = btn.dataset.username;
        declineRequest(username, btn);
      }

      // Follow
      if (e.target.closest('[data-action="follow"]')) {
        const btn = e.target.closest('[data-action="follow"]');
        const username = btn.dataset.username;
        followUser(username, btn);
      }

      // Unfollow
      if (e.target.closest('[data-action="unfollow"]')) {
        const btn = e.target.closest('[data-action="unfollow"]');
        const username = btn.dataset.username;
        unfollowUser(username, btn);
      }

      // Message
      if (e.target.closest('[data-action="message"]')) {
        const btn = e.target.closest('[data-action="message"]');
        const userId = btn.dataset.userId;
        e.preventDefault();
        startChat(userId);
      }
    });
  }

  // Add friend
  function addFriend(username, button) {
    setButtonLoading(button);

    fetch(`/api/friend_request/${username}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update button to show pending
        button.outerHTML = `
          <button class="btn btn-outline-secondary me-2" data-action="cancel-request" data-username="${username}">
            <i class="bi bi-person-dash me-1"></i> Cancel Request
          </button>
        `;

        // Show success message
        showToast('Friend request sent', 'success');
      } else {
        showToast(data.error || 'Error sending friend request', 'danger');
        resetButtonLoading(button, 'Add Friend', 'bi-person-plus');
      }
    })
    .catch(error => {
      console.error('Error sending friend request:', error);
      showToast('Error sending friend request. Please try again.', 'danger');
      resetButtonLoading(button, 'Add Friend', 'bi-person-plus');
    });
  }

  // Unfriend user
  function unfriend(username, button) {
    if (!confirm('Are you sure you want to remove this friend?')) {
      return;
    }

    setButtonLoading(button);

    fetch(`/api/friend/${username}/remove`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update button to add friend
        button.outerHTML = `
          <button class="btn btn-primary me-2" data-action="add-friend" data-username="${username}">
            <i class="bi bi-person-plus me-1"></i> Add Friend
          </button>
        `;

        // Show success message
        showToast('Friend removed', 'success');
      } else {
        showToast(data.error || 'Error removing friend', 'danger');
        resetButtonLoading(button, 'Friends', 'bi-person-check');
      }
    })
    .catch(error => {
      console.error('Error removing friend:', error);
      showToast('Error removing friend. Please try again.', 'danger');
      resetButtonLoading(button, 'Friends', 'bi-person-check');
    });
  }

  // Cancel friend request
  function cancelRequest(username, button) {
    setButtonLoading(button);

    fetch(`/api/friend_request/${username}/cancel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update button to add friend
        button.outerHTML = `
          <button class="btn btn-primary me-2" data-action="add-friend" data-username="${username}">
            <i class="bi bi-person-plus me-1"></i> Add Friend
          </button>
        `;

        // Show success message
        showToast('Friend request cancelled', 'success');
      } else {
        showToast(data.error || 'Error cancelling request', 'danger');
        resetButtonLoading(button, 'Cancel Request', 'bi-person-dash');
      }
    })
    .catch(error => {
      console.error('Error cancelling request:', error);
      showToast('Error cancelling request. Please try again.', 'danger');
      resetButtonLoading(button, 'Cancel Request', 'bi-person-dash');
    });
  }

  // Accept friend request
  function acceptRequest(username, button) {
    setButtonLoading(button);

    fetch(`/api/friend_request/${username}/accept`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update UI - replace both buttons
        const buttonGroup = button.parentNode;
        const declineButton = buttonGroup.querySelector('[data-action="decline-request"]');

        if (declineButton) {
          declineButton.remove();
        }

        button.outerHTML = `
          <button class="btn btn-outline-primary me-2" data-action="unfriend" data-username="${username}">
            <i class="bi bi-person-check me-1"></i> Friends
          </button>
        `;

        // Show success message
        showToast('Friend request accepted', 'success');
      } else {
        showToast(data.error || 'Error accepting request', 'danger');
        resetButtonLoading(button, 'Accept Request', 'bi-person-plus');
      }
    })
    .catch(error => {
      console.error('Error accepting request:', error);
      showToast('Error accepting request. Please try again.', 'danger');
      resetButtonLoading(button, 'Accept Request', 'bi-person-plus');
    });
  }

  // Decline friend request
  function declineRequest(username, button) {
    setButtonLoading(button);

    fetch(`/api/friend_request/${username}/decline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update UI - replace both buttons
        const buttonGroup = button.parentNode;
        const acceptButton = buttonGroup.querySelector('[data-action="accept-request"]');

        if (acceptButton) {
          acceptButton.remove();
        }

        button.outerHTML = `
          <button class="btn btn-primary me-2" data-action="add-friend" data-username="${username}">
            <i class="bi bi-person-plus me-1"></i> Add Friend
          </button>
        `;

        // Show success message
        showToast('Friend request declined', 'success');
      } else {
        showToast(data.error || 'Error declining request', 'danger');
        resetButtonLoading(button, 'Decline', 'bi-person-x');
      }
    })
    .catch(error => {
      console.error('Error declining request:', error);
      showToast('Error declining request. Please try again.', 'danger');
      resetButtonLoading(button, 'Decline', 'bi-person-x');
    });
  }

  // Follow user
  function followUser(username, button) {
    setButtonLoading(button);

    fetch(`/api/follow/${username}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update button to unfollow
        button.outerHTML = `
          <button class="btn btn-outline-primary me-2" data-action="unfollow" data-username="${username}">
            <i class="bi bi-person-dash me-1"></i> Unfollow
          </button>
        `;

        // Update follower count
        updateFollowerCount(1);

        // Show success message
        showToast('You are now following ' + username, 'success');
      } else {
        showToast(data.error || 'Error following user', 'danger');
        resetButtonLoading(button, 'Follow', 'bi-person-plus');
      }
    })
    .catch(error => {
      console.error('Error following user:', error);
      showToast('Error following user. Please try again.', 'danger');
      resetButtonLoading(button, 'Follow', 'bi-person-plus');
    });
  }

  // Unfollow user
  function unfollowUser(username, button) {
    setButtonLoading(button);

    fetch(`/api/unfollow/${username}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update button to follow
        button.outerHTML = `
          <button class="btn btn-outline-primary me-2" data-action="follow" data-username="${username}">
            <i class="bi bi-person-plus me-1"></i> Follow
          </button>
        `;

        // Update follower count
        updateFollowerCount(-1);

        // Show success message
        showToast('You unfollowed ' + username, 'success');
      } else {
        showToast(data.error || 'Error unfollowing user', 'danger');
        resetButtonLoading(button, 'Unfollow', 'bi-person-dash');
      }
    })
    .catch(error => {
      console.error('Error unfollowing user:', error);
      showToast('Error unfollowing user. Please try again.', 'danger');
      resetButtonLoading(button, 'Unfollow', 'bi-person-dash');
    });
  }

  // Start a chat with user
  function startChat(userId) {
    // Check if the chat module exists
    if (typeof window.chatModule === 'undefined') {
      window.location.href = '/messages';
      return;
    }

    // Show loading toast
    showToast('Creating conversation...', 'info');

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
        // Redirect to chat
        window.location.href = `/chat/${data.chat.id}`;
      } else {
        showToast(data.error || 'Error creating chat', 'danger');
      }
    })
    .catch(error => {
      console.error('Error creating chat:', error);
      showToast('Error creating chat. Please try again.', 'danger');
    });
  }

  // Update follower count
  function updateFollowerCount(change) {
    const followerCountEl = document.querySelector('.profile-stats .stat:nth-child(2) strong');
    if (followerCountEl) {
      const currentCount = parseInt(followerCountEl.textContent, 10);
      followerCountEl.textContent = currentCount + change;
    }
  }

  // Render photos
  function renderPhotos(posts) {
    if (!photosContainer) return;

    // Clear loading spinner
    photosContainer.innerHTML = '';

    // Get posts with media
    const postsWithMedia = posts.filter(post => post.media && post.media.length > 0);

    if (postsWithMedia.length === 0) {
      photosContainer.innerHTML = '<p class="text-muted text-center">No photos yet</p>';
      return;
    }

    // Create photo grid
    const photoGrid = document.createElement('div');
    photoGrid.className = 'photo-grid';

    // Add up to 9 photos
    const maxPhotos = Math.min(9, postsWithMedia.length);
    for (let i = 0; i < maxPhotos; i++) {
      const post = postsWithMedia[i];
      const media = post.media[0]; // Just use the first media item

      const photoItem = document.createElement('div');
      photoItem.className = 'photo-item';
      photoItem.innerHTML = `
        <a href="/post/${post.id}">
          <img src="${media.media_url || '/static/img/placeholder.png'}" alt="Photo" class="img-fluid">
        </a>
      `;

      photoGrid.appendChild(photoItem);
    }

    photosContainer.appendChild(photoGrid);
  }

  // Render friends
  function renderFriends(friends) {
    if (!friendsContainer) return;

    // Clear loading spinner
    friendsContainer.innerHTML = '';

    if (friends.length === 0) {
      friendsContainer.innerHTML = '<p class="text-muted text-center">No friends yet</p>';
      return;
    }

    // Create friends grid
    const friendsGrid = document.createElement('div');
    friendsGrid.className = 'friends-grid';

    // Add up to 6 friends
    const maxFriends = Math.min(6, friends.length);
    for (let i = 0; i < maxFriends; i++) {
      const friend = friends[i];

      const friendItem = document.createElement('div');
      friendItem.className = 'friend-item';
      friendItem.innerHTML = `
        <a href="/auth/profile/${friend.username}" class="d-flex align-items-center">
          <img src="${friend.profile_pic || '/static/img/default-avatar.png'}" alt="${friend.username}" class="rounded-circle me-2" width="40" height="40">
          <div>
            <div class="fw-bold">${friend.username}</div>
          </div>
        </a>
      `;

      friendsGrid.appendChild(friendItem);
    }

    friendsContainer.appendChild(friendsGrid);
  }

  // Set button to loading state
  function setButtonLoading(button) {
    button.disabled = true;
    const originalText = button.innerHTML;
    button.setAttribute('data-original-text', originalText);
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
  }

  // Reset button from loading state
  function resetButtonLoading(button, text, icon) {
    button.disabled = false;
    const originalText = button.getAttribute('data-original-text');
    if (originalText) {
      button.innerHTML = originalText;
    } else {
      button.innerHTML = `<i class="bi ${icon} me-1"></i> ${text}`;
    }
  }

  // Set up profile edit form
  function setupProfileEditForm() {
    const profileForm = document.getElementById('profile-edit-form');
    if (!profileForm) return;

    profileForm.addEventListener('submit', function(e) {
      e.preventDefault();

      const formData = new FormData(profileForm);
      const submitBtn = profileForm.querySelector('button[type="submit"]');

      // Set loading state
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

      fetch('/profile/edit', {
        method: 'POST',
        body: formData
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Error updating profile');
        }
        return response.json();
      })
      .then(data => {
        if (data.success) {
          showToast('Profile updated successfully', 'success');

          // Redirect to profile
          window.location.href = `/profile/${data.user.username}`;
        } else {
          showToast(data.error || 'Error updating profile', 'danger');
          submitBtn.disabled = false;
          submitBtn.textContent = 'Save Changes';
        }
      })
      .catch(error => {
        console.error('Error updating profile:', error);
        showToast('Error updating profile. Please try again.', 'danger');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save Changes';
      });
    });
  }

  // Set up profile picture change
  function setupProfilePicture() {
    const profilePicInput = document.getElementById('profile-pic-input');
    const coverPicInput = document.getElementById('cover-pic-input');
    const profilePicBtn = document.getElementById('change-profile-pic-btn');
    const coverPicBtn = document.getElementById('change-cover-pic-btn');

    if (profilePicBtn && profilePicInput) {
      profilePicBtn.addEventListener('click', function() {
        profilePicInput.click();
      });

      profilePicInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
          const formData = new FormData();
          formData.append('profile_pic', this.files[0]);

          uploadProfilePicture(formData);
        }
      });
    }

    if (coverPicBtn && coverPicInput) {
      coverPicBtn.addEventListener('click', function() {
        coverPicInput.click();
      });

      coverPicInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
          const formData = new FormData();
          formData.append('cover_pic', this.files[0]);

          uploadCoverPicture(formData);
        }
      });
    }
  }

  // Upload profile picture
  function uploadProfilePicture(formData) {
    const profilePicContainer = document.querySelector('.profile-picture');
    if (!profilePicContainer) return;

    // Show loading state
    profilePicContainer.classList.add('uploading');
    profilePicContainer.insertAdjacentHTML('beforeend', `
      <div class="upload-overlay">
        <div class="spinner-border text-light" role="status">
          <span class="visually-hidden">Uploading...</span>
        </div>
      </div>
    `);

    fetch('/api/profile/upload_profile_pic', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      // Remove loading state
      profilePicContainer.classList.remove('uploading');
      const overlay = profilePicContainer.querySelector('.upload-overlay');
      if (overlay) overlay.remove();

      if (data.success) {
        // Update profile picture
        const profilePicEl = profilePicContainer.querySelector('img');
        if (profilePicEl) {
          profilePicEl.src = data.profile_pic;
        }

        // Show success message
        showToast('Profile picture updated', 'success');
      } else {
        showToast(data.error || 'Error updating profile picture', 'danger');
      }
    })
    .catch(error => {
      console.error('Error uploading profile picture:', error);

      // Remove loading state
      profilePicContainer.classList.remove('uploading');
      const overlay = profilePicContainer.querySelector('.upload-overlay');
      if (overlay) overlay.remove();

      showToast('Error uploading profile picture. Please try again.', 'danger');
    });
  }

  // Upload cover picture
  function uploadCoverPicture(formData) {
    const coverContainer = document.querySelector('.profile-cover');
    if (!coverContainer) return;

    // Show loading state
    coverContainer.classList.add('uploading');
    coverContainer.insertAdjacentHTML('beforeend', `
      <div class="upload-overlay">
        <div class="spinner-border text-light" role="status">
          <span class="visually-hidden">Uploading...</span>
        </div>
      </div>
    `);

    fetch('/api/profile/upload_cover_pic', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      // Remove loading state
      coverContainer.classList.remove('uploading');
      const overlay = coverContainer.querySelector('.upload-overlay');
      if (overlay) overlay.remove();

      if (data.success) {
        // Update cover picture
        coverContainer.style.backgroundImage = `url('${data.cover_pic}')`;

        // Show success message
        showToast('Cover picture updated', 'success');
      } else {
        showToast(data.error || 'Error updating cover picture', 'danger');
      }
    })
    .catch(error => {
      console.error('Error uploading cover picture:', error);

      // Remove loading state
      coverContainer.classList.remove('uploading');
      const overlay = coverContainer.querySelector('.upload-overlay');
      if (overlay) overlay.remove();

      showToast('Error uploading cover picture. Please try again.', 'danger');
    });
  }

  // Get current user ID
  function getCurrentUserId() {
    const userIdEl = document.getElementById('current-user-id');
    return userIdEl ? userIdEl.value : null;
  }

  // Lazy load images
  function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    images.forEach(img => {
      img.src = img.dataset.src;
      img.removeAttribute('data-src');
    });
  }

  // Initialize module when document is ready
  document.addEventListener('DOMContentLoaded', init);

  // Public methods
  return {
    loadProfileData,
    loadMorePosts
  };
})();

// Make profile module available globally
window.profileModule = profileModule;
