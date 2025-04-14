// Firebase configuration
// This will be populated from the server via the template system
// This is the correct approach - credentials should never be hardcoded in client-side JS
// The public Firebase config is injected by the server during template rendering
let firebaseConfig = window.firebaseConfig || {};

// Initialize Firebase once credentials are provided
let firebaseInitialized = false;
let auth = null;

// Function to check if firebase is initialized
function isFirebaseInitialized() {
  return firebaseInitialized;
}

// Initialize Firebase when credentials are provided
function initFirebase(config) {
  try {
    // If firebase is already initialized, return
    if (firebaseInitialized) {
      console.log('Firebase already initialized');
      return true;
    }
    
    // If no config provided, use default (empty)
    const finalConfig = config || firebaseConfig;
    
    // Check if config has valid API key
    if (!finalConfig.apiKey) {
      console.log('Firebase API key not provided, using development mode');
      return false;
    }
    
    // Initialize Firebase
    firebase.initializeApp(finalConfig);
    auth = firebase.auth();
    
    // Set initialization flag
    firebaseInitialized = true;
    console.log('Firebase initialized successfully');
    return true;
  } catch (error) {
    console.error('Error initializing Firebase:', error);
    return false;
  }
}

// Fallback for development mode
function devLogin(email, password) {
  return new Promise((resolve, reject) => {
    // Send login request to server for local auth
    fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        resolve({ user: { email } });
      } else {
        reject(new Error(data.message || 'Invalid credentials'));
      }
    })
    .catch(error => {
      reject(error);
    });
  });
}

// Fallback for development mode
function devRegister(email, password, username) {
  return new Promise((resolve, reject) => {
    // Send registration request to server for local auth
    fetch('/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password, username }),
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        resolve({ user: { email } });
      } else {
        reject(new Error(data.message || 'Registration failed'));
      }
    })
    .catch(error => {
      reject(error);
    });
  });
}

// Login function that works with both Firebase and development mode
function login(email, password) {
  if (isFirebaseInitialized()) {
    return auth.signInWithEmailAndPassword(email, password);
  } else {
    return devLogin(email, password);
  }
}

// Register function that works with both Firebase and development mode
function register(email, password, username) {
  if (isFirebaseInitialized()) {
    return auth.createUserWithEmailAndPassword(email, password)
      .then(userCredential => {
        // Send username to server
        return fetch('/api/auth/update-profile', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ uid: userCredential.user.uid, username }),
        }).then(() => userCredential);
      });
  } else {
    return devRegister(email, password, username);
  }
}

// Logout function that works with both Firebase and development mode
function logout() {
  if (isFirebaseInitialized()) {
    return auth.signOut();
  } else {
    return fetch('/api/auth/logout', {
      method: 'POST',
    }).then(() => true);
  }
}

// Try to initialize Firebase on page load with default config
document.addEventListener('DOMContentLoaded', () => {
  // Try to initialize firebase
  initFirebase();
});