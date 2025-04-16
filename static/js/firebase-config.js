// Authentication configuration
// Using server-side authentication only - no Firebase on client side

// Function to check if firebase is initialized - always returns false
function isFirebaseInitialized() {
  return false;
}

// Fallback for development mode
function devLogin(email, password) {
  return new Promise((resolve, reject) => {
    console.log('Using local authentication for login');
    // Send login request to server for local auth
    fetch('/auth/api/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        console.log('Login successful:', data);
        resolve({
          user: {
            email: data.user.email,
            displayName: data.user.username,
            uid: data.user.id
          }
        });
      } else {
        console.error('Login failed:', data.message);
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
    console.log('Using local authentication for registration');
    // Send registration request to server for local auth
    fetch('/auth/api/register', {
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

// Login function - uses server-side authentication only
function login(email, password) {
  return devLogin(email, password);
}

// Register function - uses server-side authentication only
function register(email, password, username) {
  return devRegister(email, password, username);
}

// Logout function - uses server-side authentication only
function logout() {
  return fetch('/auth/api/logout', {
    method: 'POST',
  }).then(() => true);
}