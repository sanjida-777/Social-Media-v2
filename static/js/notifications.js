/**
 * Smart Notification System
 * Provides elegant, customizable notifications with different types and behaviors
 */

const NotificationSystem = (function() {
    // Private variables
    let container = null;
    let notificationCount = 0;
    let notificationQueue = [];
    let isProcessingQueue = false;
    const maxVisibleNotifications = 3;
    const defaultDuration = 5000; // 5 seconds
    
    // Notification types with their icons and colors
    const types = {
        success: {
            icon: 'bi-check-circle-fill',
            color: 'var(--bs-success)',
            bgColor: 'rgba(25, 135, 84, 0.1)'
        },
        error: {
            icon: 'bi-x-circle-fill',
            color: 'var(--bs-danger)',
            bgColor: 'rgba(220, 53, 69, 0.1)'
        },
        warning: {
            icon: 'bi-exclamation-triangle-fill',
            color: 'var(--bs-warning)',
            bgColor: 'rgba(255, 193, 7, 0.1)'
        },
        info: {
            icon: 'bi-info-circle-fill',
            color: 'var(--bs-info)',
            bgColor: 'rgba(13, 202, 240, 0.1)'
        },
        primary: {
            icon: 'bi-bell-fill',
            color: 'var(--bs-primary)',
            bgColor: 'rgba(13, 110, 253, 0.1)'
        }
    };
    
    // Initialize the notification container
    function init() {
        // Check if container already exists
        container = document.getElementById('notification-container');
        if (!container) {
            // Create container if it doesn't exist
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            document.body.appendChild(container);
        }
    }
    
    // Process the notification queue
    function processQueue() {
        if (isProcessingQueue || notificationQueue.length === 0) {
            return;
        }
        
        isProcessingQueue = true;
        
        // Count visible notifications
        const visibleCount = container.querySelectorAll('.notification:not(.notification-hiding)').length;
        
        // Process queue if we can show more notifications
        if (visibleCount < maxVisibleNotifications) {
            const notification = notificationQueue.shift();
            showNotification(notification);
        }
        
        isProcessingQueue = false;
        
        // Continue processing if there are more in the queue
        if (notificationQueue.length > 0) {
            setTimeout(processQueue, 300);
        }
    }
    
    // Show a notification
    function showNotification(options) {
        const { message, type = 'info', title = '', duration = defaultDuration, closable = true, progress = true } = options;
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.dataset.id = ++notificationCount;
        
        // Get type configuration
        const typeConfig = types[type] || types.info;
        
        // Set custom styles
        notification.style.borderLeftColor = typeConfig.color;
        notification.style.backgroundColor = typeConfig.bgColor;
        
        // Create notification content
        let titleHtml = title ? `<div class="notification-title">${title}</div>` : '';
        
        notification.innerHTML = `
            <div class="notification-icon">
                <i class="bi ${typeConfig.icon}" style="color: ${typeConfig.color}"></i>
            </div>
            <div class="notification-content">
                ${titleHtml}
                <div class="notification-message">${message}</div>
                ${progress ? '<div class="notification-progress"></div>' : ''}
            </div>
            ${closable ? '<button class="notification-close"><i class="bi bi-x"></i></button>' : ''}
        `;
        
        // Add to container
        container.appendChild(notification);
        
        // Add close button event listener
        if (closable) {
            const closeBtn = notification.querySelector('.notification-close');
            closeBtn.addEventListener('click', () => {
                hideNotification(notification);
            });
        }
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 10);
        
        // Set up progress bar animation
        if (progress && duration > 0) {
            const progressBar = notification.querySelector('.notification-progress');
            progressBar.style.transition = `width ${duration}ms linear`;
            
            // Start progress animation
            setTimeout(() => {
                progressBar.style.width = '0%';
            }, 10);
        }
        
        // Auto-hide after duration
        if (duration > 0) {
            setTimeout(() => {
                hideNotification(notification);
            }, duration);
        }
        
        // Add click event to the notification body (excluding close button)
        notification.addEventListener('click', (e) => {
            if (!e.target.closest('.notification-close')) {
                // Pause the progress bar on click
                const progressBar = notification.querySelector('.notification-progress');
                if (progressBar) {
                    progressBar.style.transition = 'none';
                }
            }
        });
        
        return notification;
    }
    
    // Hide a notification
    function hideNotification(notification) {
        if (notification.classList.contains('notification-hiding')) {
            return;
        }
        
        notification.classList.add('notification-hiding');
        
        // Remove after animation completes
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
                
                // Process queue after removing
                setTimeout(processQueue, 300);
            }
        }, 300);
    }
    
    // Clear all notifications
    function clearAll() {
        const notifications = container.querySelectorAll('.notification');
        notifications.forEach(notification => {
            hideNotification(notification);
        });
        
        // Clear the queue
        notificationQueue = [];
    }
    
    // Public methods
    return {
        init: function() {
            init();
            return this;
        },
        
        show: function(options) {
            if (typeof options === 'string') {
                options = { message: options };
            }
            
            // Initialize if not already done
            if (!container) {
                init();
            }
            
            // Add to queue
            notificationQueue.push(options);
            
            // Process queue
            processQueue();
            
            return notificationCount;
        },
        
        success: function(message, title = '', duration = defaultDuration) {
            return this.show({
                type: 'success',
                message,
                title,
                duration
            });
        },
        
        error: function(message, title = '', duration = defaultDuration) {
            return this.show({
                type: 'error',
                message,
                title,
                duration
            });
        },
        
        warning: function(message, title = '', duration = defaultDuration) {
            return this.show({
                type: 'warning',
                message,
                title,
                duration
            });
        },
        
        info: function(message, title = '', duration = defaultDuration) {
            return this.show({
                type: 'info',
                message,
                title,
                duration
            });
        },
        
        primary: function(message, title = '', duration = defaultDuration) {
            return this.show({
                type: 'primary',
                message,
                title,
                duration
            });
        },
        
        clear: function(id) {
            if (id) {
                const notification = container.querySelector(`.notification[data-id="${id}"]`);
                if (notification) {
                    hideNotification(notification);
                }
            } else {
                clearAll();
            }
            
            return this;
        }
    };
})();

// Initialize on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    NotificationSystem.init();
    
    // Make it globally available
    window.notify = NotificationSystem;
});

// Dialog system for more complex interactions
const DialogSystem = (function() {
    // Private variables
    let dialogCounter = 0;
    let activeDialog = null;
    
    // Create a dialog
    function createDialog(options) {
        const {
            title = '',
            content = '',
            size = 'medium', // small, medium, large, fullscreen
            closable = true,
            buttons = [],
            onClose = null,
            customClass = ''
        } = options;
        
        // Create dialog ID
        const dialogId = `dialog-${++dialogCounter}`;
        
        // Create dialog element
        const dialog = document.createElement('div');
        dialog.className = `smart-dialog-overlay ${customClass}`;
        dialog.id = dialogId;
        
        // Determine size class
        let sizeClass = '';
        switch (size) {
            case 'small': sizeClass = 'dialog-sm'; break;
            case 'large': sizeClass = 'dialog-lg'; break;
            case 'fullscreen': sizeClass = 'dialog-fullscreen'; break;
            default: sizeClass = ''; // medium is default
        }
        
        // Create buttons HTML
        let buttonsHtml = '';
        if (buttons.length > 0) {
            buttonsHtml = '<div class="dialog-footer">';
            buttons.forEach(button => {
                const btnType = button.type || 'secondary';
                const btnClass = button.class || `btn-${btnType}`;
                const btnId = button.id || `btn-${btnType}-${dialogId}`;
                
                buttonsHtml += `
                    <button id="${btnId}" class="btn ${btnClass}" ${button.attributes || ''}>
                        ${button.icon ? `<i class="bi ${button.icon} me-1"></i>` : ''}
                        ${button.text}
                    </button>
                `;
            });
            buttonsHtml += '</div>';
        }
        
        // Set dialog content
        dialog.innerHTML = `
            <div class="smart-dialog ${sizeClass}">
                <div class="dialog-header">
                    <h5 class="dialog-title">${title}</h5>
                    ${closable ? '<button class="dialog-close" aria-label="Close"><i class="bi bi-x"></i></button>' : ''}
                </div>
                <div class="dialog-body">
                    ${content}
                </div>
                ${buttonsHtml}
            </div>
        `;
        
        // Add to document
        document.body.appendChild(dialog);
        
        // Add event listeners
        if (closable) {
            const closeBtn = dialog.querySelector('.dialog-close');
            closeBtn.addEventListener('click', () => {
                closeDialog(dialog);
                if (typeof onClose === 'function') {
                    onClose('close');
                }
            });
            
            // Close on overlay click if closable
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) {
                    closeDialog(dialog);
                    if (typeof onClose === 'function') {
                        onClose('overlay');
                    }
                }
            });
        }
        
        // Add button event listeners
        buttons.forEach(button => {
            const btnId = button.id || `btn-${button.type || 'secondary'}-${dialogId}`;
            const btnElement = dialog.querySelector(`#${btnId}`);
            
            if (btnElement && typeof button.onClick === 'function') {
                btnElement.addEventListener('click', (e) => {
                    const result = button.onClick(e);
                    
                    // Auto close if onClick returns true or undefined
                    if (result === true || result === undefined) {
                        closeDialog(dialog);
                    }
                });
            }
        });
        
        // Show dialog with animation
        setTimeout(() => {
            dialog.classList.add('active');
            activeDialog = dialog;
            
            // Add body class to prevent scrolling
            document.body.classList.add('dialog-open');
        }, 10);
        
        return dialog;
    }
    
    // Close a dialog
    function closeDialog(dialog) {
        dialog.classList.remove('active');
        
        // Remove after animation
        setTimeout(() => {
            if (dialog.parentNode) {
                dialog.parentNode.removeChild(dialog);
                
                // Remove body class if no active dialogs
                if (document.querySelectorAll('.smart-dialog-overlay.active').length === 0) {
                    document.body.classList.remove('dialog-open');
                }
                
                // Clear active dialog reference
                if (activeDialog === dialog) {
                    activeDialog = null;
                }
            }
        }, 300);
    }
    
    // Public methods
    return {
        open: function(options) {
            return createDialog(options);
        },
        
        close: function(dialog) {
            if (dialog) {
                closeDialog(dialog);
            } else if (activeDialog) {
                closeDialog(activeDialog);
            }
            return this;
        },
        
        alert: function(message, title = 'Alert', callback = null) {
            return this.open({
                title: title,
                content: `<p>${message}</p>`,
                size: 'small',
                buttons: [
                    {
                        text: 'OK',
                        type: 'primary',
                        onClick: function() {
                            if (typeof callback === 'function') {
                                callback();
                            }
                            return true;
                        }
                    }
                ]
            });
        },
        
        confirm: function(message, title = 'Confirm', onConfirm = null, onCancel = null) {
            return this.open({
                title: title,
                content: `<p>${message}</p>`,
                size: 'small',
                buttons: [
                    {
                        text: 'Cancel',
                        type: 'secondary',
                        onClick: function() {
                            if (typeof onCancel === 'function') {
                                onCancel();
                            }
                            return true;
                        }
                    },
                    {
                        text: 'Confirm',
                        type: 'primary',
                        onClick: function() {
                            if (typeof onConfirm === 'function') {
                                onConfirm();
                            }
                            return true;
                        }
                    }
                ]
            });
        },
        
        prompt: function(message, defaultValue = '', title = 'Prompt', onSubmit = null, onCancel = null) {
            const inputId = `prompt-input-${++dialogCounter}`;
            
            const dialog = this.open({
                title: title,
                content: `
                    <p>${message}</p>
                    <div class="form-group">
                        <input type="text" class="form-control" id="${inputId}" value="${defaultValue}">
                    </div>
                `,
                size: 'small',
                buttons: [
                    {
                        text: 'Cancel',
                        type: 'secondary',
                        onClick: function() {
                            if (typeof onCancel === 'function') {
                                onCancel();
                            }
                            return true;
                        }
                    },
                    {
                        text: 'OK',
                        type: 'primary',
                        onClick: function() {
                            const input = document.getElementById(inputId);
                            const value = input ? input.value : '';
                            
                            if (typeof onSubmit === 'function') {
                                onSubmit(value);
                            }
                            return true;
                        }
                    }
                ]
            });
            
            // Focus the input
            setTimeout(() => {
                const input = document.getElementById(inputId);
                if (input) {
                    input.focus();
                    input.select();
                }
            }, 300);
            
            return dialog;
        }
    };
})();

// Make dialog system globally available
document.addEventListener('DOMContentLoaded', function() {
    window.dialog = DialogSystem;
});
