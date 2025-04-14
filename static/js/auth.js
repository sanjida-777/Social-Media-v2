/**
 * Authentication functionality for the social media platform
 * Supports both Firebase and local fallback authentication
 */

// Track authentication state
let currentUser = null;
let authInitialized = false;

// DOM elements
const authContainer = document.getElementById('auth-container');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const logoutButton = document.getElementById('logout-button');
const authMessage = document.getElementById('auth-message');
const userProfileSection = document.getElementById('user-profile');

/**
 * Initialize Firebase Auth UI
 * Uses Firebase UI for a nicer authentication experience
 */
function setupFirebaseAuthUI() {
  try {
    // Check if Firebase is available and initialized
    if (typeof firebase === 'undefined') {
      console.error('Firebase SDK not loaded');
      setupLocalAuth();
      return;
    }

    if (!isFirebaseInitialized()) {
      console.warn('Firebase not initialized, using local auth');
      setupLocalAuth();
      return;
    }

    // Initialize Firebase UI if available
    if (typeof firebaseui !== 'undefined') {
      const ui = new firebaseui.auth.AuthUI(firebase.auth());
      ui.start('#firebaseui-auth-container', {
        signInOptions: [
          firebase.auth.EmailAuthProvider.PROVIDER_ID,
          firebase.auth.GoogleAuthProvider.PROVIDER_ID
        ],
        signInSuccessUrl: '/',
        tosUrl: '/terms',
        privacyPolicyUrl: '/privacy'
      });

      // Listen for auth state changes
      firebase.auth().onAuthStateChanged(handleAuthStateChange);
      authInitialized = true;
    } else {
      console.warn('Firebase UI not loaded, using basic auth');
      setupBasicFirebaseAuth();
    }
  } catch (error) {
    console.error('Error setting up Firebase Auth UI:', error);
    setupLocalAuth();
  }
}

/**
 * Setup basic Firebase auth without UI library
 */
function setupBasicFirebaseAuth() {
  // Listen for auth state changes
  firebase.auth().onAuthStateChanged(handleAuthStateChange);

  // Set up login form
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = loginForm.querySelector('[name="email"]').value;
      const password = loginForm.querySelector('[name="password"]').value;

      try {
        showAuthMessage('Logging in...', 'info');
        await login(email, password);
      } catch (error) {
        showAuthMessage(`Login failed: ${error.message}`, 'error');
      }
    });
  }

  // Set up register form
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = registerForm.querySelector('[name="email"]').value;
      const username = registerForm.querySelector('[name="username"]').value;
      const password = registerForm.querySelector('[name="password"]').value;
      const confirmPassword = registerForm.querySelector('[name="password-confirm"]').value;

      if (password !== confirmPassword) {
        showAuthMessage('Passwords do not match', 'error');
        return;
      }

      try {
        showAuthMessage('Creating account...', 'info');
        await register(email, password, username);
      } catch (error) {
        showAuthMessage(`Registration failed: ${error.message}`, 'error');
      }
    });
  }

  // Set up logout button
  if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
      try {
        await logout();
        location.href = '/login';
      } catch (error) {
        showAuthMessage(`Logout failed: ${error.message}`, 'error');
      }
    });
  }

  authInitialized = true;
}

/**
 * Setup local authentication (no Firebase)
 */
function setupLocalAuth() {
  // Check if we're already logged in (server-side session)
  fetch('/auth/api/me')
    .then(response => response.json())
    .then(data => {
      if (data.authenticated) {
        handleAuthStateChange({
          email: data.email,
          displayName: data.username,
          uid: data.id
        });
      }
    })
    .catch(error => {
      console.error('Error checking auth status:', error);
    });

  // Set up login form
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = loginForm.querySelector('[name="email"]').value;
      const password = loginForm.querySelector('[name="password"]').value;

      try {
        showAuthMessage('Logging in...', 'info');
        await login(email, password);
        showAuthMessage('Login successful! Redirecting...', 'success');

        // Add a small delay to show the success message before redirecting
        setTimeout(() => {
          window.location.href = '/';
        }, 1000);
      } catch (error) {
        showAuthMessage(`Login failed: ${error.message}`, 'error');
      }
    });
  }

  // Set up register form
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = registerForm.querySelector('[name="email"]').value;
      const username = registerForm.querySelector('[name="username"]').value;
      const password = registerForm.querySelector('[name="password"]').value;
      const confirmPassword = registerForm.querySelector('[name="password-confirm"]').value;

      if (password !== confirmPassword) {
        showAuthMessage('Passwords do not match', 'error');
        return;
      }

      try {
        showAuthMessage('Creating account...', 'info');
        await register(email, password, username);
        showAuthMessage('Account created! You can now log in.', 'success');

        // Redirect to login page or automatically log in
        setTimeout(() => {
          location.href = '/login';
        }, 2000);
      } catch (error) {
        showAuthMessage(`Registration failed: ${error.message}`, 'error');
      }
    });
  }

  // Set up logout button
  if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
      try {
        await fetch('/auth/api/logout', { method: 'POST' });
        location.href = '/login';
      } catch (error) {
        showAuthMessage(`Logout failed: ${error.message}`, 'error');
      }
    });
  }

  authInitialized = true;
}

/**
 * Handle authentication state changes
 * @param {Object} user - User object from Firebase or local auth
 */
function handleAuthStateChange(user) {
  currentUser = user;

  if (user) {
    console.log('User is signed in:', user.email);

    // Update UI for logged in user
    document.body.classList.add('user-logged-in');
    document.body.classList.remove('user-logged-out');

    // Update profile section if it exists
    if (userProfileSection) {
      updateUserProfile(user);
    }

    // Send the Firebase token to the backend to create a session
    if (typeof firebase !== 'undefined' && isFirebaseInitialized()) {
      firebase.auth().currentUser.getIdToken(true)
        .then(token => {
          return fetch('/api/auth/session', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token }),
          });
        })
        .then(response => response.json())
        .then(data => {
          console.log('Session created:', data);
        })
        .catch(error => {
          console.error('Error creating session:', error);
        });
    }
  } else {
    console.log('User is signed out');

    // Update UI for logged out user
    document.body.classList.remove('user-logged-in');
    document.body.classList.add('user-logged-out');

    // Redirect to login page if not already there
    const currentPath = window.location.pathname;
    if (currentPath !== '/login' && currentPath !== '/register') {
      location.href = '/login';
    }
  }
}

/**
 * Update user profile section
 * @param {Object} user - User object
 */
function updateUserProfile(user) {
  if (!userProfileSection) return;

  // Get user details from the server
  fetch(`/api/users/profile`)
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        console.error('Error fetching user profile:', data.error);
        return;
      }

      // Update profile picture
      const profilePic = userProfileSection.querySelector('.profile-pic');
      if (profilePic) {
        profilePic.src = data.profile_pic || '/static/images/default-avatar.png';
        profilePic.alt = data.username;
      }

      // Update username
      const usernameElement = userProfileSection.querySelector('.username');
      if (usernameElement) {
        usernameElement.textContent = data.username;
      }

      // Update bio
      const bioElement = userProfileSection.querySelector('.bio');
      if (bioElement) {
        bioElement.textContent = data.bio || 'No bio yet';
      }
    })
    .catch(error => {
      console.error('Error fetching user profile:', error);
    });
}

/**
 * Show authentication message
 * @param {string} message - Message to display
 * @param {string} type - Message type (success, error, info)
 */
function showAuthMessage(message, type = 'info') {
  if (!authMessage) {
    // Create a floating message if authMessage element doesn't exist
    const messageDiv = document.createElement('div');
    messageDiv.style.position = 'fixed';
    messageDiv.style.top = '20px';
    messageDiv.style.left = '50%';
    messageDiv.style.transform = 'translateX(-50%)';
    messageDiv.style.zIndex = '9999';
    messageDiv.style.padding = '15px 25px';
    messageDiv.style.borderRadius = '5px';
    messageDiv.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
    messageDiv.style.fontSize = '16px';
    messageDiv.style.fontWeight = 'bold';

    if (type === 'success') {
      messageDiv.style.backgroundColor = '#28a745';
      messageDiv.style.color = 'white';
    } else if (type === 'error') {
      messageDiv.style.backgroundColor = '#dc3545';
      messageDiv.style.color = 'white';
    } else {
      messageDiv.style.backgroundColor = '#17a2b8';
      messageDiv.style.color = 'white';
    }

    messageDiv.textContent = message;
    document.body.appendChild(messageDiv);

    // Remove after 5 seconds
    setTimeout(() => {
      document.body.removeChild(messageDiv);
    }, 5000);
    return;
  }

  authMessage.textContent = message;
  authMessage.className = `auth-message ${type}`;
  authMessage.style.display = 'block';

  // Hide message after 5 seconds
  setTimeout(() => {
    authMessage.style.display = 'none';
  }, 5000);
}

/**
 * Get current user
 * @returns {Object|null} - Current user or null if not logged in
 */
function getCurrentUser() {
  return currentUser;
}

/**
 * Check if user is logged in
 * @returns {boolean} - True if user is logged in
 */
function isLoggedIn() {
  return currentUser !== null;
}

// Initialize auth when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Check if Firebase is available
  if (typeof firebase !== 'undefined') {
    // Try to initialize Firebase first
    setTimeout(() => {
      if (isFirebaseInitialized()) {
        console.log('Using Firebase authentication');
        setupFirebaseAuthUI();
      } else {
        console.log('Firebase not initialized, using local authentication');
        setupLocalAuth();
      }
    }, 1000); // Wait for Firebase to initialize
  } else {
    console.log('Firebase not available, using local authentication');
    setupLocalAuth();
  }
});