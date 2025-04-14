// Firebase configuration for the application
// Placeholder configuration - replace with your Firebase project configuration
const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY || "your-api-key",
  authDomain: process.env.FIREBASE_AUTH_DOMAIN || "your-auth-domain",
  projectId: process.env.FIREBASE_PROJECT_ID || "your-project-id",
  storageBucket: process.env.FIREBASE_STORAGE_BUCKET || "your-storage-bucket",
  messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID || "your-messaging-sender-id",
  appId: process.env.FIREBASE_APP_ID || "your-app-id"
};

// Initialize Firebase
let firebaseInitialized = false;

function initializeFirebase() {
  if (firebaseInitialized) return;
  
  try {
    firebase.initializeApp(firebaseConfig);
    firebaseInitialized = true;
    console.log("Firebase initialized successfully");
  } catch (error) {
    console.error("Error initializing Firebase:", error);
  }
}

// Initialize Firebase Authentication
function initializeAuth() {
  initializeFirebase();
  return firebase.auth();
}

// Set up UI for Firebase auth
function setupFirebaseAuthUI() {
  initializeFirebase();
  
  // Firebase UI config
  const uiConfig = {
    signInOptions: [
      firebase.auth.EmailAuthProvider.PROVIDER_ID,
      firebase.auth.GoogleAuthProvider.PROVIDER_ID,
    ],
    signInFlow: 'popup',
    callbacks: {
      signInSuccessWithAuthResult: function(authResult, redirectUrl) {
        // User successfully signed in
        const user = authResult.user;
        // Get ID token
        user.getIdToken().then(token => {
          // Send token to backend
          sendTokenToBackend(token);
        });
        return false; // Don't redirect, we'll handle it in the callback
      }
    }
  };
  
  // Initialize the FirebaseUI Auth instance
  if (document.getElementById('firebaseui-auth-container')) {
    const ui = new firebaseui.auth.AuthUI(firebase.auth());
    ui.start('#firebaseui-auth-container', uiConfig);
  }
}

// Send token to backend
function sendTokenToBackend(token) {
  const endpoint = window.location.pathname.includes('register') ? '/register' : '/login';
  
  fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token }),
  })
  .then(response => response.json())
  .then(data => {
    if (data.success && data.redirect) {
      window.location.href = data.redirect;
    } else {
      console.error('Authentication failed:', data.error);
      showAlert('danger', 'Authentication failed: ' + (data.error || 'Unknown error'));
    }
  })
  .catch(error => {
    console.error('Error sending token to backend:', error);
    showAlert('danger', 'Error during authentication. Please try again.');
  });
}

// Check if user is already authenticated on page load
function checkAuthState() {
  initializeAuth().onAuthStateChanged(user => {
    if (user) {
      user.getIdToken().then(token => {
        // Check with backend if session is valid
        fetch('/auth/check')
          .then(response => response.json())
          .then(data => {
            if (!data.authenticated) {
              // Session is not valid, send token to backend
              sendTokenToBackend(token);
            }
          })
          .catch(error => {
            console.error('Error checking auth state:', error);
          });
      });
    }
  });
}

// Sign out function
function signOut() {
  initializeAuth().signOut().then(() => {
    // Sign-out successful, redirect to server logout to clear session
    window.location.href = '/logout';
  }).catch((error) => {
    console.error('Error signing out:', error);
  });
}

// Show alert message
function showAlert(type, message) {
  const alertContainer = document.getElementById('alert-container');
  if (!alertContainer) return;
  
  const alertDiv = document.createElement('div');
  alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
  alertDiv.role = 'alert';
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  
  alertContainer.appendChild(alertDiv);
  
  // Auto dismiss after 5 seconds
  setTimeout(() => {
    alertDiv.classList.remove('show');
    setTimeout(() => alertDiv.remove(), 150);
  }, 5000);
}
