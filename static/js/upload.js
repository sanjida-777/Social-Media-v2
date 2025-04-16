/**
 * Image Upload Module
 * Handles uploading images to external services
 */

const UploadModule = (function() {
    // Private variables
    let availableServices = [];
    let isInitialized = false;
    
    // Initialize the module
    function init() {
        if (isInitialized) return;
        
        // Fetch available services
        fetchAvailableServices();
        
        // Add event listeners for file inputs with data-upload attribute
        document.addEventListener('change', function(e) {
            const target = e.target;
            if (target.type === 'file' && target.hasAttribute('data-upload')) {
                const uploadType = target.getAttribute('data-upload') || 'image';
                const targetInput = target.getAttribute('data-target');
                const previewElement = target.getAttribute('data-preview');
                
                if (uploadType === 'image' && target.files && target.files.length > 0) {
                    handleImageUpload(target.files[0], targetInput, previewElement);
                }
            }
        });
        
        isInitialized = true;
    }
    
    // Fetch available upload services
    function fetchAvailableServices() {
        fetch('/api/uploads/services')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.services) {
                    availableServices = data.services;
                    console.log('Available upload services:', availableServices);
                }
            })
            .catch(error => {
                console.error('Error fetching upload services:', error);
            });
    }
    
    // Handle image upload
    function handleImageUpload(file, targetInput, previewElement) {
        // Check file type
        if (!file.type.match('image.*')) {
            notify.error('Please select an image file');
            return;
        }
        
        // Check file size (max 5MB)
        const maxSize = 5 * 1024 * 1024; // 5MB
        if (file.size > maxSize) {
            notify.error('Image size exceeds 5MB limit');
            return;
        }
        
        // Create FormData
        const formData = new FormData();
        formData.append('file', file);
        
        // Show loading indicator
        notify.info('Uploading image...', 'Please wait');
        
        // If preview element exists, show preview
        if (previewElement) {
            const preview = document.querySelector(previewElement);
            if (preview) {
                // Create object URL for preview
                const objectUrl = URL.createObjectURL(file);
                
                // If preview is an img element
                if (preview.tagName === 'IMG') {
                    preview.src = objectUrl;
                    preview.style.display = 'block';
                } 
                // If preview is a div or other element
                else {
                    preview.style.backgroundImage = `url(${objectUrl})`;
                    preview.style.display = 'block';
                }
            }
        }
        
        // Upload the image
        fetch('/api/uploads/image', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.url) {
                // If target input exists, set the value
                if (targetInput) {
                    const input = document.querySelector(targetInput);
                    if (input) {
                        input.value = data.url;
                        
                        // Trigger change event
                        const event = new Event('change', { bubbles: true });
                        input.dispatchEvent(event);
                    }
                }
                
                notify.success('Image uploaded successfully', 'Success');
                
                // Return the URL
                return data.url;
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        })
        .catch(error => {
            console.error('Error uploading image:', error);
            notify.error('Error uploading image: ' + error.message);
        });
    }
    
    // Upload an image programmatically
    function uploadImage(file, options = {}) {
        return new Promise((resolve, reject) => {
            // Check file type
            if (!file.type.match('image.*')) {
                reject(new Error('Please select an image file'));
                return;
            }
            
            // Check file size (max 5MB)
            const maxSize = 5 * 1024 * 1024; // 5MB
            if (file.size > maxSize) {
                reject(new Error('Image size exceeds 5MB limit'));
                return;
            }
            
            // Create FormData
            const formData = new FormData();
            formData.append('file', file);
            
            // Add service if specified
            if (options.service && availableServices.includes(options.service)) {
                formData.append('service', options.service);
            }
            
            // Show loading indicator if not silent
            if (!options.silent) {
                notify.info('Uploading image...', 'Please wait');
            }
            
            // Upload the image
            fetch('/api/uploads/image', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.url) {
                    // Show success notification if not silent
                    if (!options.silent) {
                        notify.success('Image uploaded successfully', 'Success');
                    }
                    
                    // Resolve with the result
                    resolve(data);
                } else {
                    throw new Error(data.error || 'Upload failed');
                }
            })
            .catch(error => {
                console.error('Error uploading image:', error);
                
                // Show error notification if not silent
                if (!options.silent) {
                    notify.error('Error uploading image: ' + error.message);
                }
                
                // Reject with the error
                reject(error);
            });
        });
    }
    
    // Create a file input for image upload
    function createImageUploader(options = {}) {
        const {
            targetInput,
            previewElement,
            multiple = false,
            accept = 'image/*',
            className = '',
            buttonText = 'Upload Image',
            buttonClass = 'btn btn-primary',
            iconClass = 'bi bi-upload'
        } = options;
        
        // Create the file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = accept;
        fileInput.multiple = multiple;
        fileInput.className = 'd-none';
        fileInput.setAttribute('data-upload', 'image');
        
        if (targetInput) {
            fileInput.setAttribute('data-target', targetInput);
        }
        
        if (previewElement) {
            fileInput.setAttribute('data-preview', previewElement);
        }
        
        // Create the button
        const button = document.createElement('button');
        button.type = 'button';
        button.className = buttonClass;
        button.innerHTML = `<i class="${iconClass} me-2"></i>${buttonText}`;
        
        // Add click event to the button
        button.addEventListener('click', function() {
            fileInput.click();
        });
        
        // Create the container
        const container = document.createElement('div');
        container.className = `image-uploader ${className}`;
        container.appendChild(fileInput);
        container.appendChild(button);
        
        return container;
    }
    
    // Public methods
    return {
        init,
        uploadImage,
        createImageUploader,
        getAvailableServices: () => [...availableServices]
    };
})();

// Initialize on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    UploadModule.init();
    
    // Make it globally available
    window.UploadModule = UploadModule;
});
