// Auth related functionality

document.addEventListener('DOMContentLoaded', function() {
  // Initialize Firebase auth UI if we're on login or register page
  if (window.location.pathname.includes('login') || window.location.pathname.includes('register')) {
    setupFirebaseAuthUI();
  }
  
  // Check auth state on every page
  checkAuthState();
  
  // Handle traditional form login/register if present
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleTraditionalLogin);
  }
  
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', handleTraditionalRegister);
  }
  
  // Handle logout button
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function(e) {
      e.preventDefault();
      signOut();
    });
  }
});

// Handle traditional form login
function handleTraditionalLogin(e) {
  e.preventDefault();
  
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  
  if (!email || !password) {
    showAlert('danger', 'Please enter both email and password');
    return;
  }
  
  // Sign in with Firebase
  initializeAuth().signInWithEmailAndPassword(email, password)
    .then((userCredential) => {
      // Get token and send to backend
      userCredential.user.getIdToken().then(token => {
        sendTokenToBackend(token);
      });
    })
    .catch((error) => {
      console.error('Firebase login error:', error);
      showAlert('danger', 'Login failed: ' + error.message);
    });
}

// Handle traditional form registration
function handleTraditionalRegister(e) {
  e.preventDefault();
  
  const username = document.getElementById('username').value;
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirm-password').value;
  
  if (!username || !email || !password) {
    showAlert('danger', 'Please fill out all required fields');
    return;
  }
  
  if (password !== confirmPassword) {
    showAlert('danger', 'Passwords do not match');
    return;
  }
  
  // Create user with Firebase
  initializeAuth().createUserWithEmailAndPassword(email, password)
    .then((userCredential) => {
      // Update profile with username
      return userCredential.user.updateProfile({
        displayName: username
      }).then(() => userCredential);
    })
    .then((userCredential) => {
      // Get token and send to backend
      userCredential.user.getIdToken().then(token => {
        sendTokenToBackend(token);
      });
    })
    .catch((error) => {
      console.error('Firebase registration error:', error);
      showAlert('danger', 'Registration failed: ' + error.message);
    });
}

// Check if user is authenticated, update UI accordingly
function updateAuthUI() {
  const user = initializeAuth().currentUser;
  
  const authNav = document.getElementById('auth-nav');
  const userNav = document.getElementById('user-nav');
  
  if (!authNav || !userNav) return;
  
  if (user) {
    authNav.classList.add('d-none');
    userNav.classList.remove('d-none');
    
    // Update user profile elements
    const userDisplayName = document.getElementById('user-display-name');
    const userProfilePic = document.getElementById('user-profile-pic');
    
    if (userDisplayName) {
      userDisplayName.textContent = user.displayName || 'User';
    }
    
    if (userProfilePic && user.photoURL) {
      userProfilePic.src = user.photoURL;
      userProfilePic.alt = user.displayName || 'User';
    }
  } else {
    authNav.classList.remove('d-none');
    userNav.classList.add('d-none');
  }
}
