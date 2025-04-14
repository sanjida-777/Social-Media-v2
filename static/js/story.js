// Story related functionality

// Initialize story module with namespace
const storyModule = (function() {
  // Private variables
  let storyContainer;
  let storyProgressBar;
  let storyItemsContainer;
  let storyUsers = [];
  let currentUserIndex = 0;
  let currentStoryIndex = 0;
  let storyTimeout;
  let storyDuration = 5000; // 5 seconds per story
  let isPlaying = false;
  let storyModal;
  let storyCarousel;
  
  // Initialize stories
  function init() {
    // Initialize story carousel on feed page
    initStoryCarousel();
    
    // Initialize story viewer modal
    initStoryViewer();
    
    // Initialize create story functionality
    initCreateStory();
  }
  
  // Initialize story carousel on feed page
  function initStoryCarousel() {
    const storyCarousel = document.getElementById('story-carousel');
    if (!storyCarousel) return;
    
    // Load stories for the carousel
    loadStories();
    
    // Handle story item click
    storyCarousel.addEventListener('click', function(e) {
      const storyItem = e.target.closest('.story-item');
      if (storyItem) {
        const userIndex = parseInt(storyItem.dataset.userIndex, 10);
        const storyIndex = parseInt(storyItem.dataset.storyIndex, 10) || 0;
        
        openStoryViewer(userIndex, storyIndex);
      }
    });
  }
  
  // Initialize story viewer modal
  function initStoryViewer() {
    storyModal = document.getElementById('story-modal');
    if (!storyModal) return;
    
    storyContainer = storyModal.querySelector('.story-container');
    storyProgressBar = storyModal.querySelector('.story-progress-bar');
    storyItemsContainer = storyModal.querySelector('.story-content');
    
    // Handle modal events
    storyModal.addEventListener('hidden.bs.modal', function() {
      pauseStory();
      stopStoryTimeout();
    });
    
    // Handle navigation buttons
    storyModal.querySelector('.story-prev').addEventListener('click', function() {
      navigateStory('prev');
    });
    
    storyModal.querySelector('.story-next').addEventListener('click', function() {
      navigateStory('next');
    });
    
    // Handle video events
    storyModal.addEventListener('click', function(e) {
      const video = storyModal.querySelector('video');
      if (video && e.target === video) {
        if (video.paused) {
          video.play();
          resumeStory();
        } else {
          video.pause();
          pauseStory();
        }
      }
    });
    
    // Handle touch/click navigation zones
    const leftZone = storyModal.querySelector('.story-nav-zone-left');
    const rightZone = storyModal.querySelector('.story-nav-zone-right');
    
    leftZone.addEventListener('click', function(e) {
      if (e.target === leftZone) {
        navigateStory('prev');
      }
    });
    
    rightZone.addEventListener('click', function(e) {
      if (e.target === rightZone) {
        navigateStory('next');
      }
    });
    
    // Close button
    storyModal.querySelector('.story-close').addEventListener('click', function() {
      const bsModal = bootstrap.Modal.getInstance(storyModal);
      bsModal.hide();
    });
  }
  
  // Initialize create story functionality
  function initCreateStory() {
    const createStoryForm = document.getElementById('create-story-form');
    if (!createStoryForm) return;
    
    // Handle story type selection
    const storyTypeRadios = createStoryForm.querySelectorAll('input[name="story_type"]');
    const storyContentSections = createStoryForm.querySelectorAll('.story-content-section');
    
    storyTypeRadios.forEach(radio => {
      radio.addEventListener('change', function() {
        storyContentSections.forEach(section => {
          section.style.display = 'none';
        });
        
        const selectedType = this.value;
        const targetSection = createStoryForm.querySelector(`.story-content-section[data-type="${selectedType}"]`);
        if (targetSection) {
          targetSection.style.display = 'block';
        }
      });
    });
    
    // Handle photo preview
    const photoInput = createStoryForm.querySelector('input[name="photo"]');
    const photoPreview = createStoryForm.querySelector('.photo-preview');
    
    if (photoInput && photoPreview) {
      photoInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
          const reader = new FileReader();
          
          reader.onload = function(e) {
            photoPreview.innerHTML = `<img src="${e.target.result}" class="img-fluid rounded" alt="Photo preview">`;
            photoPreview.style.display = 'block';
          };
          
          reader.readAsDataURL(this.files[0]);
        }
      });
    }
    
    // Handle video preview and duration check
    const videoInput = createStoryForm.querySelector('input[name="video"]');
    const videoPreview = createStoryForm.querySelector('.video-preview');
    const videoDurationError = createStoryForm.querySelector('.video-duration-error');
    
    if (videoInput && videoPreview) {
      videoInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
          const file = this.files[0];
          const videoURL = URL.createObjectURL(file);
          
          // Create video element to check duration
          const video = document.createElement('video');
          video.muted = true;
          
          video.onloadedmetadata = function() {
            URL.revokeObjectURL(videoURL);
            
            const duration = video.duration;
            
            if (duration > 60) {
              // Video too long
              videoPreview.innerHTML = '';
              videoPreview.style.display = 'none';
              videoDurationError.style.display = 'block';
              videoInput.value = ''; // Clear input
            } else {
              // Video acceptable
              videoDurationError.style.display = 'none';
              videoPreview.innerHTML = `
                <video src="${videoURL}" controls class="img-fluid rounded"></video>
                <p class="text-muted mt-1">Duration: ${Math.round(duration)} seconds</p>
              `;
              videoPreview.style.display = 'block';
            }
          };
          
          video.src = videoURL;
        }
      });
    }
    
    // Form submission
    createStoryForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const storyType = createStoryForm.querySelector('input[name="story_type"]:checked').value;
      
      // Validate based on story type
      let isValid = true;
      
      if (storyType === 'text') {
        const textContent = createStoryForm.querySelector('textarea[name="content"]').value.trim();
        if (!textContent) {
          showToast('Please enter text for your story', 'danger');
          isValid = false;
        }
      } else if (storyType === 'photo') {
        const photoFile = createStoryForm.querySelector('input[name="photo"]').files[0];
        if (!photoFile) {
          showToast('Please select a photo for your story', 'danger');
          isValid = false;
        }
      } else if (storyType === 'video') {
        const videoFile = createStoryForm.querySelector('input[name="video"]').files[0];
        if (!videoFile) {
          showToast('Please select a video for your story', 'danger');
          isValid = false;
        }
      }
      
      if (isValid) {
        // Show loading state
        const submitBtn = createStoryForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating...';
        
        // Submit form
        const formData = new FormData(createStoryForm);
        
        fetch('/story/create', {
          method: 'POST',
          body: formData
        })
        .then(response => {
          if (!response.ok) {
            throw new Error('Error creating story');
          }
          return response.json();
        })
        .then(data => {
          if (data.success) {
            window.location.href = '/stories';
          } else {
            showToast(data.error || 'Error creating story', 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
          }
        })
        .catch(error => {
          console.error('Error creating story:', error);
          showToast('Error creating story. Please try again.', 'danger');
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalText;
        });
      }
    });
  }
  
  // Load stories for the carousel
  function loadStories() {
    const storyCarousel = document.getElementById('story-carousel');
    if (!storyCarousel) return;
    
    // Show loading state
    storyCarousel.innerHTML = `
      <div class="d-flex justify-content-center py-3">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    `;
    
    fetch('/api/stories')
      .then(response => response.json())
      .then(data => {
        storyUsers = data.story_users;
        
        if (storyUsers.length === 0) {
          storyCarousel.innerHTML = `
            <div class="text-center py-3">
              <p class="text-muted">No stories available</p>
              <a href="/story/create" class="btn btn-sm btn-primary mt-2">
                <i class="bi bi-plus-circle me-1"></i> Create Story
              </a>
            </div>
          `;
          return;
        }
        
        // Render story items
        storyCarousel.innerHTML = `
          <div class="story-items d-flex overflow-auto py-2">
            <!-- Create Story Button -->
            <div class="story-item create-story me-2">
              <a href="/story/create" class="text-decoration-none">
                <div class="story-create-avatar">
                  <div class="story-avatar">
                    <i class="bi bi-plus-circle-fill"></i>
                  </div>
                </div>
                <p class="story-username text-center text-truncate mt-1">Create</p>
              </a>
            </div>
            
            <!-- Story Items -->
            ${renderStoryItems(storyUsers)}
          </div>
        `;
      })
      .catch(error => {
        console.error('Error loading stories:', error);
        storyCarousel.innerHTML = `
          <div class="alert alert-danger m-3">
            Error loading stories. Please try again.
          </div>
        `;
      });
  }
  
  // Render story items for carousel
  function renderStoryItems(storyUsers) {
    return storyUsers.map((user, index) => {
      const hasUnviewed = user.stories.some(story => !story.viewed);
      
      return `
        <div class="story-item me-2" data-user-index="${index}" data-story-index="0">
          <div class="story-avatar-wrapper ${hasUnviewed ? 'unviewed' : 'viewed'}">
            <div class="story-avatar">
              <img src="${user.user.profile_pic || '/static/img/default-avatar.png'}" alt="${user.user.username}">
            </div>
          </div>
          <p class="story-username text-center text-truncate mt-1">${user.user.username}</p>
        </div>
      `;
    }).join('');
  }
  
  // Open story viewer modal
  function openStoryViewer(userIndex, storyIndex) {
    if (!storyUsers[userIndex]) return;
    
    currentUserIndex = userIndex;
    currentStoryIndex = storyIndex;
    
    // Initialize modal if not already
    if (!bootstrap.Modal.getInstance(storyModal)) {
      new bootstrap.Modal(storyModal).show();
    } else {
      bootstrap.Modal.getInstance(storyModal).show();
    }
    
    // Load and display story
    loadStory(userIndex, storyIndex);
  }
  
  // Load and display story content
  function loadStory(userIndex, storyIndex) {
    const user = storyUsers[userIndex];
    if (!user || !user.stories[storyIndex]) return;
    
    const story = user.stories[storyIndex];
    
    // Set user info
    storyModal.querySelector('.story-user-avatar').src = user.user.profile_pic || '/static/img/default-avatar.png';
    storyModal.querySelector('.story-username').textContent = user.user.username;
    storyModal.querySelector('.story-time').textContent = timeAgo(story.created_at);
    
    // Clear previous content
    storyItemsContainer.innerHTML = '';
    
    // Create and show content based on story type
    if (story.story_type === 'text') {
      // Text story
      storyItemsContainer.innerHTML = `
        <div class="story-text-content d-flex align-items-center justify-content-center">
          <div class="text-center p-4">
            <p class="h4">${story.content}</p>
          </div>
        </div>
      `;
    } else if (story.story_type === 'photo') {
      // Photo story
      storyItemsContainer.innerHTML = `
        <div class="story-image-content">
          <img src="${story.media_url}" alt="Story" class="img-fluid">
          ${story.content ? `<div class="story-caption p-3">${story.content}</div>` : ''}
        </div>
      `;
    } else if (story.story_type === 'video') {
      // Video story
      storyItemsContainer.innerHTML = `
        <div class="story-video-content">
          <video src="${story.media_url}" playsinline autoplay muted class="img-fluid"></video>
          ${story.content ? `<div class="story-caption p-3">${story.content}</div>` : ''}
        </div>
      `;
      
      const video = storyItemsContainer.querySelector('video');
      
      // Set story duration to video duration
      video.onloadedmetadata = function() {
        storyDuration = video.duration * 1000;
        startStoryProgress();
      };
      
      // Ensure video plays
      video.play().catch(error => {
        console.error('Error playing video:', error);
        // Fallback to default duration
        startStoryProgress();
      });
    }
    
    // Reset and start progress bar
    if (story.story_type !== 'video') {
      storyDuration = 5000; // Reset to default
      startStoryProgress();
    }
    
    // Mark story as viewed
    if (!story.viewed) {
      markStoryAsViewed(story.id);
    }
    
    // Update progress segments
    updateProgressSegments();
  }
  
  // Start story progress bar
  function startStoryProgress() {
    // Reset progress bar
    stopStoryTimeout();
    isPlaying = true;
    
    const progressElement = storyProgressBar.querySelector('.progress-bar');
    progressElement.style.width = '0%';
    progressElement.style.transition = 'none';
    
    // Force reflow
    void progressElement.offsetWidth;
    
    // Start animation
    progressElement.style.transition = `width ${storyDuration}ms linear`;
    progressElement.style.width = '100%';
    
    // Set timeout for next story
    storyTimeout = setTimeout(() => {
      navigateStory('next');
    }, storyDuration);
  }
  
  // Stop story timeout
  function stopStoryTimeout() {
    clearTimeout(storyTimeout);
    const progressElement = storyProgressBar.querySelector('.progress-bar');
    progressElement.style.transition = 'none';
  }
  
  // Pause story progress
  function pauseStory() {
    if (!isPlaying) return;
    
    isPlaying = false;
    clearTimeout(storyTimeout);
    
    const progressElement = storyProgressBar.querySelector('.progress-bar');
    const width = progressElement.offsetWidth;
    const totalWidth = progressElement.parentNode.offsetWidth;
    const progressPercentage = (width / totalWidth) * 100;
    
    progressElement.style.transition = 'none';
    progressElement.style.width = `${progressPercentage}%`;
  }
  
  // Resume story progress
  function resumeStory() {
    if (isPlaying) return;
    
    isPlaying = true;
    
    const progressElement = storyProgressBar.querySelector('.progress-bar');
    const width = progressElement.offsetWidth;
    const totalWidth = progressElement.parentNode.offsetWidth;
    const progressPercentage = (width / totalWidth) * 100;
    
    const remainingTime = (1 - (progressPercentage / 100)) * storyDuration;
    
    progressElement.style.transition = `width ${remainingTime}ms linear`;
    progressElement.style.width = '100%';
    
    storyTimeout = setTimeout(() => {
      navigateStory('next');
    }, remainingTime);
  }
  
  // Update progress segments
  function updateProgressSegments() {
    const user = storyUsers[currentUserIndex];
    if (!user) return;
    
    const storiesCount = user.stories.length;
    
    // Create progress segments
    let progressHtml = '';
    
    for (let i = 0; i < storiesCount; i++) {
      const activeClass = i === currentStoryIndex ? 'active' : '';
      const viewedClass = i < currentStoryIndex || user.stories[i].viewed ? 'viewed' : '';
      
      progressHtml += `<div class="progress story-progress-segment ${activeClass} ${viewedClass}">
        <div class="progress-bar"></div>
      </div>`;
    }
    
    storyProgressBar.innerHTML = progressHtml;
  }
  
  // Navigate to next/previous story
  function navigateStory(direction) {
    stopStoryTimeout();
    
    const user = storyUsers[currentUserIndex];
    if (!user) return;
    
    if (direction === 'next') {
      // Move to next story or next user
      if (currentStoryIndex < user.stories.length - 1) {
        // Next story for current user
        currentStoryIndex++;
        loadStory(currentUserIndex, currentStoryIndex);
      } else {
        // Move to next user
        if (currentUserIndex < storyUsers.length - 1) {
          currentUserIndex++;
          currentStoryIndex = 0;
          loadStory(currentUserIndex, currentStoryIndex);
        } else {
          // End of all stories, close modal
          const bsModal = bootstrap.Modal.getInstance(storyModal);
          bsModal.hide();
        }
      }
    } else {
      // Move to previous story or previous user
      if (currentStoryIndex > 0) {
        // Previous story for current user
        currentStoryIndex--;
        loadStory(currentUserIndex, currentStoryIndex);
      } else {
        // Move to previous user
        if (currentUserIndex > 0) {
          currentUserIndex--;
          const prevUser = storyUsers[currentUserIndex];
          currentStoryIndex = prevUser.stories.length - 1;
          loadStory(currentUserIndex, currentStoryIndex);
        }
        // If already at first user's first story, do nothing
      }
    }
  }
  
  // Mark story as viewed
  function markStoryAsViewed(storyId) {
    fetch(`/api/story/${storyId}/view`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update local state
        const story = storyUsers[currentUserIndex].stories[currentStoryIndex];
        story.viewed = true;
        
        // Update story item in carousel
        const storyItem = document.querySelector(`.story-item[data-user-index="${currentUserIndex}"]`);
        if (storyItem) {
          // Check if all stories for this user are viewed
          const allViewed = storyUsers[currentUserIndex].stories.every(s => s.viewed);
          if (allViewed) {
            const avatarWrapper = storyItem.querySelector('.story-avatar-wrapper');
            if (avatarWrapper) {
              avatarWrapper.classList.remove('unviewed');
              avatarWrapper.classList.add('viewed');
            }
          }
        }
      }
    })
    .catch(error => {
      console.error('Error marking story as viewed:', error);
    });
  }
  
  // Initialize module when document is ready
  document.addEventListener('DOMContentLoaded', init);
  
  // Public methods
  return {
    loadStories,
    openStoryViewer
  };
})();

// Make story module available globally
window.storyModule = storyModule;
