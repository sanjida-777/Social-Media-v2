/**
 * Utility functions for the social media platform
 */

// Constants
const DEFAULT_AVATAR = '/static/images/default-avatar.png';
const DEFAULT_COVER = '/static/images/default-cover.jpg';

// Check if we're in a Node.js environment or browser
const isNode = typeof process !== 'undefined' &&
  process.versions != null &&
  process.versions.node != null;

// Environment object that works in both Node.js and browser
const env = {
  isDevelopment: !isNode && window.location.hostname === 'localhost',
  isProduction: !isNode && window.location.hostname !== 'localhost',
  get: function(key, defaultValue) {
    // In browser, try to get from localStorage first
    if (!isNode) {
      const value = localStorage.getItem(key);
      if (value) return value;
    }
    // Return default value as fallback
    return defaultValue;
  }
};

/**
 * Format date for display
 * @param {Date|string} date - Date object or ISO string
 * @param {boolean} includeTime - Whether to include time
 * @returns {string} - Formatted date string
 */
function formatDate(date, includeTime = false) {
  try {
    if (!date) return '';
    const d = typeof date === 'string' ? new Date(date) : date;

    // Check if date is valid
    if (isNaN(d.getTime())) return '';

    const options = {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    };

    if (includeTime) {
      options.hour = '2-digit';
      options.minute = '2-digit';
    }

    return d.toLocaleDateString(undefined, options);
  } catch (error) {
    console.error('Error formatting date:', error);
    return '';
  }
}

/**
 * Format relative time (e.g., "2 hours ago")
 * @param {Date|string} date - Date object or ISO string
 * @returns {string} - Relative time string
 */
function formatRelativeTime(date) {
  try {
    if (!date) return '';
    const d = typeof date === 'string' ? new Date(date) : date;

    // Check if date is valid
    if (isNaN(d.getTime())) return '';

    const now = new Date();
    const diffMs = now - d;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    const diffMonth = Math.floor(diffDay / 30);
    const diffYear = Math.floor(diffDay / 365);

    if (diffSec < 60) return 'just now';
    if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
    if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
    if (diffDay < 30) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
    if (diffMonth < 12) return `${diffMonth} month${diffMonth > 1 ? 's' : ''} ago`;
    return `${diffYear} year${diffYear > 1 ? 's' : ''} ago`;
  } catch (error) {
    console.error('Error formatting relative time:', error);
    return '';
  }
}

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} - Truncated text
 */
function truncateText(text, maxLength = 100) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

/**
 * Format a number (e.g., 1000 -> 1K)
 * @param {number} num - Number to format
 * @returns {string} - Formatted number
 */
function formatNumber(num) {
  if (num === undefined || num === null) return '0';

  if (num < 1000) return num.toString();
  if (num < 1000000) return (num / 1000).toFixed(1) + 'K';
  return (num / 1000000).toFixed(1) + 'M';
}

/**
 * Create a debounced function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} - Debounced function
 */
function debounce(func, wait = 300) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

/**
 * Get the file extension from a filename
 * @param {string} filename - Filename
 * @returns {string} - File extension
 */
function getFileExtension(filename) {
  if (!filename) return '';
  return filename.split('.').pop().toLowerCase();
}

/**
 * Check if a file is an image
 * @param {string} filename - Filename
 * @returns {boolean} - True if image
 */
function isImageFile(filename) {
  const ext = getFileExtension(filename);
  return ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext);
}

/**
 * Check if a file is a video
 * @param {string} filename - Filename
 * @returns {boolean} - True if video
 */
function isVideoFile(filename) {
  const ext = getFileExtension(filename);
  return ['mp4', 'webm', 'ogg'].includes(ext);
}

/**
 * Safely parse JSON
 * @param {string} json - JSON string
 * @param {*} defaultValue - Default value if parsing fails
 * @returns {*} - Parsed object or default value
 */
function safeJsonParse(json, defaultValue = {}) {
  try {
    if (!json) return defaultValue;
    return JSON.parse(json);
  } catch (error) {
    console.error('Error parsing JSON:', error);
    return defaultValue;
  }
}

/**
 * Fetch API wrapper with error handling
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise} - Promise with response data
 */
function fetchApi(url, options = {}) {
  // Default options
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json'
    },
    credentials: 'same-origin'
  };

  // Merge options
  const fetchOptions = { ...defaultOptions, ...options };

  // If data is provided and method is not GET, stringify body
  if (options.data && options.method !== 'GET') {
    fetchOptions.body = JSON.stringify(options.data);
    delete fetchOptions.data;
  }

  // If method is GET and data is provided, append as query string
  if (options.data && (!options.method || options.method === 'GET')) {
    const params = new URLSearchParams();
    Object.entries(options.data).forEach(([key, value]) => {
      params.append(key, value);
    });
    url = `${url}?${params.toString()}`;
    delete fetchOptions.data;
  }

  return fetch(url, fetchOptions)
    .then(response => {
      // Check if response is JSON
      const contentType = response.headers.get('content-type');
      const isJson = contentType && contentType.includes('application/json');

      // Handle error responses
      if (!response.ok) {
        return isJson ? response.json().then(data => {
          throw new Error(data.message || response.statusText);
        }) : Promise.reject(new Error(response.statusText));
      }

      // Parse JSON or return raw response
      return isJson ? response.json() : response;
    });
}

/**
 * Format time ago (alias for formatRelativeTime)
 * @param {Date|string} date - Date object or ISO string
 * @returns {string} - Relative time string
 */
function timeAgo(date) {
  return formatRelativeTime(date);
}

/**
 * Format count (alias for formatNumber)
 * @param {number} num - Number to format
 * @returns {string} - Formatted number
 */
function formatCount(num) {
  return formatNumber(num);
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, danger, warning, info)
 * @param {number} duration - Duration in ms
 */
function showToast(message, type = 'info', duration = 3000) {
  // Create toast container if it doesn't exist
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(toastContainer);
  }

  // Create toast element
  const toastId = 'toast-' + Date.now();
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-white bg-${type} border-0`;
  toast.id = toastId;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');

  // Create toast content
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        ${message}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  // Add toast to container
  toastContainer.appendChild(toast);

  // Initialize Bootstrap toast
  const bsToast = new bootstrap.Toast(toast, {
    autohide: true,
    delay: duration
  });

  // Show toast
  bsToast.show();

  // Remove toast after it's hidden
  toast.addEventListener('hidden.bs.toast', function() {
    toast.remove();
  });
}

// Export functions if in Node.js environment
if (isNode) {
  module.exports = {
    formatDate,
    formatRelativeTime,
    timeAgo,
    truncateText,
    formatNumber,
    formatCount,
    showToast,
    debounce,
    getFileExtension,
    isImageFile,
    isVideoFile,
    safeJsonParse,
    fetchApi,
    env
  };
}