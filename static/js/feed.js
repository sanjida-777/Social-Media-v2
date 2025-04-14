// Feed related functionality

// Initialize feed module with namespace
const feedModule = (function() {
  // Private variables
  let currentPage = 1;
  let isLoading = false;
  let hasMorePosts = true;
  let postsContainer;
  let loadingIndicator;
  let postTemplate;
  
  // Initialize feed
  function init() {
    postsContainer = document.getElementById('posts-container');
    loadingIndicator = document.getElementById('loading-indicator');
    postTemplate = document.getElementById('post-template');
    
    if (!postsContainer) return;
    
    // Load initial posts
    loadPosts();
    
    // Set up infinite scroll
    window.addEventListener('scroll', debounce(handleScroll, 300));
    
    // Set up post interaction handlers
    setupPostInteractions();
    
    // Check for new posts periodically (every 30 seconds)
    setInterval(checkForNewPosts, 30000);
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
  
  // Load initial posts
  function loadPosts() {
    isLoading = true;
    showLoading();
    
    fetchAPI('/api/feed')
      .then(data => {
        hideLoading();
        renderPosts(data.posts);
        
        // Update pagination info
        currentPage = data.pagination.current_page;
        hasMorePosts = currentPage < data.pagination.total_pages;
        
        // Show empty state if no posts
        if (data.posts.length === 0) {
          showEmptyState();
        }
        
        isLoading = false;
      })
      .catch(error => {
        console.error('Error loading posts:', error);
        hideLoading();
        showLoadingError();
        isLoading = false;
      });
  }
  
  // Load more posts (next page)
  function loadMorePosts() {
    if (isLoading || !hasMorePosts) return;
    
    isLoading = true;
    showLoading();
    
    fetchAPI(`/api/feed?page=${currentPage + 1}`)
      .then(data => {
        hideLoading();
        renderPosts(data.posts, true); // append = true
        
        // Update pagination info
        currentPage = data.pagination.current_page;
        hasMorePosts = currentPage < data.pagination.total_pages;
        
        isLoading = false;
      })
      .catch(error => {
        console.error('Error loading more posts:', error);
        hideLoading();
        isLoading = false;
      });
  }
  
  // Check for new posts
  function checkForNewPosts() {
    // Only check if we're on the first page and not already loading
    if (currentPage !== 1 || isLoading) return;
    
    fetchAPI('/api/feed?page=1&check_new=true')
      .then(data => {
        if (data.has_new_posts) {
          showNewPostsNotification(data.new_posts_count);
        }
      })
      .catch(error => {
        console.error('Error checking for new posts:', error);
      });
  }
  
  // Show notification for new posts
  function showNewPostsNotification(count) {
    let notify = document.getElementById('new-posts-notification');
    
    if (!notify) {
      notify = document.createElement('div');
      notify.id = 'new-posts-notification';
      notify.className = 'new-posts-notification alert alert-primary text-center';
      notify.innerHTML = `<span>${count} new post${count !== 1 ? 's' : ''}</span>`;
      notify.style.cursor = 'pointer';
      notify.addEventListener('click', refreshFeed);
      
      // Insert at the top of the feed
      postsContainer.insertAdjacentElement('beforebegin', notify);
    } else {
      notify.innerHTML = `<span>${count} new post${count !== 1 ? 's' : ''}</span>`;
      notify.style.display = 'block';
    }
  }
  
  // Refresh the feed (reload first page)
  function refreshFeed() {
    // Hide new posts notification
    const notify = document.getElementById('new-posts-notification');
    if (notify) {
      notify.style.display = 'none';
    }
    
    // Reset state
    currentPage = 1;
    hasMorePosts = true;
    
    // Clear existing posts
    postsContainer.innerHTML = '';
    
    // Load first page
    loadPosts();
  }
  
  // Render posts to the feed
  function renderPosts(posts, append = false) {
    if (!append) {
      postsContainer.innerHTML = '';
    }
    
    posts.forEach(post => {
      const postElement = createPostElement(post);
      postsContainer.appendChild(postElement);
    });
    
    // Initialize lazy loading for new images
    lazyLoadImages();
  }
  
  // Create a post element from template
  function createPostElement(post) {
    const postEl = document.createElement('div');
    postEl.className = 'post card mb-3';
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
        <a href="/profile/${post.author}" class="me-3">
          <img src="${post.profile_pic || '/static/img/default-avatar.png'}" alt="${post.author}" 
            class="rounded-circle" width="40" height="40">
        </a>
        <div>
          <a href="/profile/${post.author}" class="fw-bold text-decoration-none">${post.author}</a>
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
        
        <div class="comments-container mt-3" id="comments-${post.id}" style="display: none;">
          <div class="comments-list mb-2"></div>
          <div class="comment-form">
            <form class="d-flex" data-post-id="${post.id}">
              <input type="text" class="form-control form-control-sm me-2" placeholder="Write a comment...">
              <button type="submit" class="btn btn-primary btn-sm">Send</button>
            </form>
          </div>
        </div>
      </div>
    `;
    
    return postEl;
  }
  
  // Setup post interaction handlers
  function setupPostInteractions() {
    // Use event delegation for post interactions
    document.addEventListener('click', function(e) {
      // Like button
      if (e.target.closest('[data-action="like"]')) {
        const btn = e.target.closest('[data-action="like"]');
        const postId = btn.dataset.postId;
        handleLikeAction(btn, postId);
      }
      
      // Comment button
      if (e.target.closest('[data-action="comment"]')) {
        const btn = e.target.closest('[data-action="comment"]');
        const postId = btn.dataset.postId;
        toggleComments(postId);
      }
      
      // Share button
      if (e.target.closest('[data-action="share"]')) {
        const btn = e.target.closest('[data-action="share"]');
        const postId = btn.dataset.postId;
        handleShareAction(postId);
      }
      
      // Delete post
      if (e.target.closest('[data-action="delete-post"]')) {
        const link = e.target.closest('[data-action="delete-post"]');
        const postEl = link.closest('.post');
        const postId = postEl.dataset.postId;
        
        e.preventDefault();
        if (confirm('Are you sure you want to delete this post?')) {
          deletePost(postId);
        }
      }
      
      // Report post
      if (e.target.closest('[data-action="report-post"]')) {
        const link = e.target.closest('[data-action="report-post"]');
        const postEl = link.closest('.post');
        const postId = postEl.dataset.postId;
        
        e.preventDefault();
        reportPost(postId);
      }
    });
    
    // Use event delegation for comment form submissions
    document.addEventListener('submit', function(e) {
      const form = e.target.closest('.comment-form form');
      if (form) {
        e.preventDefault();
        const postId = form.dataset.postId;
        const input = form.querySelector('input');
        const comment = input.value.trim();
        
        if (comment) {
          submitComment(postId, comment, form);
        }
      }
    });
  }
  
  // Handle like/unlike action
  function handleLikeAction(btn, postId) {
    fetch(`/api/post/${postId}/like`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        const iconEl = btn.querySelector('i');
        const countEl = btn.querySelector('.like-count');
        
        // Update like button state
        if (data.action === 'liked') {
          btn.classList.add('active', 'text-danger');
          iconEl.classList.remove('bi-heart');
          iconEl.classList.add('bi-heart-fill');
        } else {
          btn.classList.remove('active', 'text-danger');
          iconEl.classList.remove('bi-heart-fill');
          iconEl.classList.add('bi-heart');
        }
        
        // Update like count
        countEl.textContent = formatCount(data.likes);
      }
    })
    .catch(error => {
      console.error('Error liking post:', error);
      showToast('Error liking post. Please try again.', 'danger');
    });
  }
  
  // Toggle comments section
  function toggleComments(postId) {
    const commentsContainer = document.getElementById(`comments-${postId}`);
    
    if (commentsContainer.style.display === 'none') {
      // Show comments
      commentsContainer.style.display = 'block';
      
      // Load comments if not already loaded
      if (commentsContainer.querySelector('.comments-list').children.length === 0) {
        loadComments(postId);
      }
    } else {
      // Hide comments
      commentsContainer.style.display = 'none';
    }
  }
  
  // Load comments for a post
  function loadComments(postId) {
    const commentsContainer = document.getElementById(`comments-${postId}`);
    const commentsList = commentsContainer.querySelector('.comments-list');
    
    // Show loading
    commentsList.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div></div>';
    
    fetch(`/api/post/${postId}/comments`)
      .then(response => response.json())
      .then(data => {
        if (data.comments.length === 0) {
          commentsList.innerHTML = '<div class="text-center text-muted">No comments yet</div>';
        } else {
          commentsList.innerHTML = '';
          data.comments.forEach(comment => {
            const commentEl = createCommentElement(comment);
            commentsList.appendChild(commentEl);
          });
        }
      })
      .catch(error => {
        console.error('Error loading comments:', error);
        commentsList.innerHTML = '<div class="text-center text-danger">Error loading comments</div>';
      });
  }
  
  // Create a comment element
  function createCommentElement(comment) {
    const commentEl = document.createElement('div');
    commentEl.className = 'comment d-flex mb-2';
    commentEl.dataset.commentId = comment.id;
    
    commentEl.innerHTML = `
      <a href="/profile/${comment.author}" class="me-2">
        <img src="${comment.profile_pic || '/static/img/default-avatar.png'}" alt="${comment.author}" 
          class="rounded-circle" width="32" height="32">
      </a>
      <div class="comment-content">
        <div class="comment-bubble p-2 rounded bg-light">
          <div class="comment-header">
            <a href="/profile/${comment.author}" class="fw-bold text-decoration-none">${comment.author}</a>
          </div>
          <div class="comment-text">${comment.content}</div>
        </div>
        <div class="comment-actions mt-1">
          <small class="text-muted">${timeAgo(comment.created_at)}</small>
          <button class="btn btn-sm btn-link p-0 ms-2 comment-like-btn" data-action="like-comment" data-comment-id="${comment.id}">
            Like${comment.like_count > 0 ? ` · ${formatCount(comment.like_count)}` : ''}
          </button>
          ${comment.user_id === getCurrentUserId() ? 
            `<button class="btn btn-sm btn-link p-0 ms-2 text-danger" data-action="delete-comment" data-comment-id="${comment.id}">
              Delete
            </button>` : ''
          }
        </div>
      </div>
    `;
    
    return commentEl;
  }
  
  // Submit a new comment
  function submitComment(postId, comment, form) {
    fetch(`/api/post/${postId}/comment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content: comment })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Clear input
        form.querySelector('input').value = '';
        
        // Add new comment to UI
        const commentsList = document.querySelector(`#comments-${postId} .comments-list`);
        const commentEl = createCommentElement(data.comment);
        
        // Clear "no comments" message if present
        if (commentsList.innerHTML.includes('No comments yet')) {
          commentsList.innerHTML = '';
        }
        
        commentsList.appendChild(commentEl);
        
        // Update comment count
        const btn = document.querySelector(`[data-action="comment"][data-post-id="${postId}"]`);
        const countEl = btn.querySelector('.comment-count');
        const currentCount = parseInt(countEl.textContent.replace(/\D/g, ''), 10) || 0;
        countEl.textContent = formatCount(currentCount + 1);
      }
    })
    .catch(error => {
      console.error('Error submitting comment:', error);
      showToast('Error submitting comment. Please try again.', 'danger');
    });
  }
  
  // Handle share action
  function handleShareAction(postId) {
    const shareUrl = `${window.location.origin}/post/${postId}`;
    
    if (navigator.share) {
      navigator.share({
        title: 'Check out this post',
        url: shareUrl
      }).catch(error => {
        console.error('Error sharing:', error);
        copyToClipboard(shareUrl);
      });
    } else {
      copyToClipboard(shareUrl);
    }
  }
  
  // Copy URL to clipboard
  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Link copied to clipboard!', 'success');
    }).catch(error => {
      console.error('Error copying to clipboard:', error);
      showToast('Error copying link. Please try again.', 'danger');
    });
  }
  
  // Delete a post
  function deletePost(postId) {
    fetch(`/api/post/${postId}/delete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Remove post from UI
        const postEl = document.querySelector(`.post[data-post-id="${postId}"]`);
        if (postEl) {
          postEl.remove();
        }
        
        showToast('Post deleted successfully', 'success');
      } else {
        showToast(data.error || 'Error deleting post', 'danger');
      }
    })
    .catch(error => {
      console.error('Error deleting post:', error);
      showToast('Error deleting post. Please try again.', 'danger');
    });
  }
  
  // Report a post
  function reportPost(postId) {
    showToast('Post reported. Thank you for helping keep our community safe.', 'success');
  }
  
  // Show loading indicator
  function showLoading() {
    if (loadingIndicator) {
      loadingIndicator.style.display = 'block';
    }
  }
  
  // Hide loading indicator
  function hideLoading() {
    if (loadingIndicator) {
      loadingIndicator.style.display = 'none';
    }
  }
  
  // Show empty state when no posts
  function showEmptyState() {
    const emptyState = document.createElement('div');
    emptyState.className = 'text-center p-5';
    emptyState.innerHTML = `
      <div class="display-1 text-muted">
        <i class="bi bi-newspaper"></i>
      </div>
      <h3 class="mt-3">No posts yet</h3>
      <p class="text-muted">Follow more people or create your first post!</p>
      <a href="/post/create" class="btn btn-primary mt-3">
        <i class="bi bi-plus-circle me-2"></i>Create Post
      </a>
    `;
    
    postsContainer.appendChild(emptyState);
  }
  
  // Show loading error
  function showLoadingError() {
    const errorEl = document.createElement('div');
    errorEl.className = 'alert alert-danger';
    errorEl.innerHTML = `
      <p><i class="bi bi-exclamation-triangle me-2"></i>Error loading posts</p>
      <button class="btn btn-outline-danger btn-sm mt-2" onclick="feedModule.loadPosts()">
        Try Again
      </button>
    `;
    
    postsContainer.appendChild(errorEl);
  }
  
  // Create a new post
  function createPost(formData) {
    return fetch('/post/create', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Error creating post');
      }
      return response.json();
    });
  }
  
  // Initialize module when document is ready
  document.addEventListener('DOMContentLoaded', init);
  
  // Public methods
  return {
    loadPosts,
    loadMorePosts,
    refreshFeed,
    createPost
  };
})();

// Make feed module available globally
window.feedModule = feedModule;
