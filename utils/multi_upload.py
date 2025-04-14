import os
import time
import logging
import random
import requests
from werkzeug.utils import secure_filename
from datetime import datetime
import json

# Set up logger
logger = logging.getLogger(__name__)

# Keep track of last upload time for each service to implement rate limiting
last_upload_time = {
    'imgur': 0,
    'catbox': 0,
    'gofile': 0,
    'pixhost': 0,
    '0x0': 0
}

# Minimum time between uploads for each service (in seconds)
MIN_TIME_BETWEEN_UPLOADS = 1  # 1 second to enforce rate limit (max 1 per second)

# Track service availability
service_status = {
    'imgur': True,
    'catbox': True,
    'gofile': True,
    'pixhost': True,
    '0x0': True
}

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def _rate_limit(service):
    """
    Implement rate limiting for each service
    Returns True if we should proceed with the upload, False if we should skip
    """
    current_time = time.time()
    if current_time - last_upload_time.get(service, 0) < MIN_TIME_BETWEEN_UPLOADS:
        return False
    
    last_upload_time[service] = current_time
    return True

def _mark_service_down(service):
    """Mark a service as unavailable"""
    service_status[service] = False
    logger.warning(f"Service {service} marked as unavailable")

def _mark_service_up(service):
    """Mark a service as available"""
    service_status[service] = True
    logger.info(f"Service {service} is available again")

def _get_available_services():
    """Get a list of currently available services"""
    return [service for service, status in service_status.items() if status]

def upload_to_imgur(file):
    """Upload image to Imgur"""
    if not _rate_limit('imgur'):
        logger.debug("Rate limiting Imgur upload")
        return None
    
    # Get Imgur client ID from environment
    client_id = os.environ.get('IMGUR_CLIENT_ID')
    if not client_id:
        logger.warning("IMGUR_CLIENT_ID not found in environment variables")
        return None
    
    try:
        headers = {'Authorization': f'Client-ID {client_id}'}
        files = {'image': (file.filename, file.read(), file.content_type)}
        file.seek(0)  # Reset file pointer for potential reuse
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    'https://api.imgur.com/3/image',
                    headers=headers,
                    files=files
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        _mark_service_up('imgur')
                        return data['data']['link']
                
                if response.status_code == 429:  # Rate limited
                    logger.warning("Imgur rate limit reached, waiting longer")
                    time.sleep(RETRY_DELAY * 2)  # Wait longer for rate limits
                    continue
                    
                logger.error(f"Imgur upload failed: {response.text}")
                break
                
            except Exception as e:
                logger.error(f"Imgur upload attempt {attempt+1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        
        _mark_service_down('imgur')
        return None
        
    except Exception as e:
        logger.error(f"Imgur upload failed: {e}")
        _mark_service_down('imgur')
        return None

def upload_to_catbox(file):
    """Upload image to Catbox.moe"""
    if not _rate_limit('catbox'):
        logger.debug("Rate limiting Catbox upload")
        return None
    
    try:
        files = {
            'reqtype': (None, 'fileupload'),
            'fileToUpload': (file.filename, file.read(), file.content_type)
        }
        file.seek(0)  # Reset file pointer for potential reuse
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    'https://catbox.moe/user/api.php',
                    files=files
                )
                
                if response.status_code == 200 and response.text.startswith('https://'):
                    _mark_service_up('catbox')
                    return response.text
                
                logger.error(f"Catbox upload failed: {response.text}")
                break
                
            except Exception as e:
                logger.error(f"Catbox upload attempt {attempt+1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        
        _mark_service_down('catbox')
        return None
        
    except Exception as e:
        logger.error(f"Catbox upload failed: {e}")
        _mark_service_down('catbox')
        return None

def upload_to_gofile(file):
    """Upload image to GoFile.io"""
    if not _rate_limit('gofile'):
        logger.debug("Rate limiting GoFile upload")
        return None
    
    try:
        # First get the best server
        for attempt in range(MAX_RETRIES):
            try:
                server_response = requests.get('https://api.gofile.io/getServer')
                if server_response.status_code == 200:
                    data = server_response.json()
                    if data.get('status') == 'ok':
                        server = data['data']['server']
                        break
                logger.error(f"GoFile get server failed: {server_response.text}")
                time.sleep(RETRY_DELAY)
            except Exception as e:
                logger.error(f"GoFile get server attempt {attempt+1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    _mark_service_down('gofile')
                    return None
        
        # Now upload to the server
        files = {'file': (file.filename, file.read(), file.content_type)}
        file.seek(0)  # Reset file pointer for potential reuse
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    f'https://{server}.gofile.io/uploadFile',
                    files=files
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'ok':
                        _mark_service_up('gofile')
                        return data['data']['downloadPage']
                
                logger.error(f"GoFile upload failed: {response.text}")
                break
                
            except Exception as e:
                logger.error(f"GoFile upload attempt {attempt+1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        
        _mark_service_down('gofile')
        return None
        
    except Exception as e:
        logger.error(f"GoFile upload failed: {e}")
        _mark_service_down('gofile')
        return None

def upload_to_pixhost(file):
    """Upload image to Pixhost.to"""
    if not _rate_limit('pixhost'):
        logger.debug("Rate limiting Pixhost upload")
        return None
    
    try:
        files = {
            'img': (file.filename, file.read(), file.content_type)
        }
        data = {
            'content_type': 0,  # 0 for family friendly content
            'max_th_size': 300  # Max thumbnail size
        }
        file.seek(0)  # Reset file pointer for potential reuse
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    'https://api.pixhost.to/images',
                    files=files,
                    data=data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    _mark_service_up('pixhost')
                    return data.get('show_url')
                
                logger.error(f"Pixhost upload failed: {response.text}")
                break
                
            except Exception as e:
                logger.error(f"Pixhost upload attempt {attempt+1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        
        _mark_service_down('pixhost')
        return None
        
    except Exception as e:
        logger.error(f"Pixhost upload failed: {e}")
        _mark_service_down('pixhost')
        return None

def upload_to_0x0(file):
    """Upload image to 0x0.st"""
    if not _rate_limit('0x0'):
        logger.debug("Rate limiting 0x0.st upload")
        return None
    
    try:
        files = {'file': (file.filename, file.read(), file.content_type)}
        file.seek(0)  # Reset file pointer for potential reuse
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    'https://0x0.st',
                    files=files
                )
                
                if response.status_code == 200 and response.text.startswith('https://'):
                    _mark_service_up('0x0')
                    return response.text.strip()
                
                logger.error(f"0x0.st upload failed: {response.text}")
                break
                
            except Exception as e:
                logger.error(f"0x0.st upload attempt {attempt+1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        
        _mark_service_down('0x0')
        return None
        
    except Exception as e:
        logger.error(f"0x0.st upload failed: {e}")
        _mark_service_down('0x0')
        return None

def upload_to_multiple_services(file):
    """
    Upload an image to multiple services for redundancy
    Returns a list of successful upload URLs
    """
    # Use a copy because it might change during execution
    available_services = _get_available_services()
    
    if not available_services:
        logger.error("No image hosting services are available")
        return []
    
    # Randomize the order to distribute load
    random.shuffle(available_services)
    
    # Store successful upload URLs
    upload_urls = []
    
    # Try to upload to each service
    for service in available_services:
        if service == 'imgur':
            url = upload_to_imgur(file)
        elif service == 'catbox':
            url = upload_to_catbox(file)
        elif service == 'gofile':
            url = upload_to_gofile(file)
        elif service == 'pixhost':
            url = upload_to_pixhost(file)
        elif service == '0x0':
            url = upload_to_0x0(file)
        else:
            url = None
        
        if url:
            upload_urls.append(url)
            
            # If we have at least 2 successful uploads, we can stop
            if len(upload_urls) >= 2:
                break
    
    return upload_urls

def save_multi_uploads(file):
    """
    Save an uploaded file to multiple services and return the URLs
    Also tracks the URLs in a local JSON file for reference
    """
    # Check if file is valid
    if not file or not file.filename:
        return []
    
    # Get the file extension
    _, ext = os.path.splitext(file.filename)
    ext = ext.lower()
    
    # Make sure it's an allowed file type
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
    if ext not in allowed_extensions:
        logger.warning(f"Invalid file extension: {ext}")
        return []
    
    # Upload to multiple services
    urls = upload_to_multiple_services(file)
    
    # Track the uploads in a local file for reference
    if urls:
        try:
            uploads_file = 'instance/uploads.json'
            uploads = {}
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(uploads_file), exist_ok=True)
            
            # Load existing data if the file exists
            if os.path.exists(uploads_file):
                with open(uploads_file, 'r') as f:
                    uploads = json.load(f)
            
            # Add new upload
            timestamp = datetime.now().isoformat()
            filename = secure_filename(file.filename)
            if 'files' not in uploads:
                uploads['files'] = []
            
            uploads['files'].append({
                'original_filename': filename,
                'timestamp': timestamp,
                'urls': urls
            })
            
            # Save the updated data
            with open(uploads_file, 'w') as f:
                json.dump(uploads, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error tracking upload: {e}")
    
    return urls

def get_first_working_url(urls):
    """
    Check which URLs are still working and return the first one that works
    """
    if not urls:
        return None
    
    for url in urls:
        try:
            response = requests.head(url, timeout=5)
            if response.status_code < 400:  # Any successful status code
                return url
        except:
            continue
    
    return None