"""
Image Upload Utility
Handles uploading images to various external services
"""
import os
import json
import logging
import requests
import random
import base64
from io import BytesIO
from PIL import Image
from config import get_config

# Set up logger
logger = logging.getLogger(__name__)

class ImageUploader:
    """
    Handles uploading images to various external services
    """
    def __init__(self):
        # Get available image services from config
        self.available_services = get_config('upload.image_services', [
            'imgur', 'catbox', 'gofile', 'pixhost', '0x0'
        ])
        
        # Get API keys from environment variables
        self.api_keys = {
            'imgur': os.getenv('IMGUR_CLIENT_ID'),
            'catbox': os.getenv('CATBOX_USER_HASH'),
            'gofile': os.getenv('GOFILE_API_KEY'),
            'pixhost': os.getenv('PIXHOST_API_KEY')
            # 0x0 doesn't require an API key
        }
        
        # Initialize service adapters
        self.adapters = {
            'imgur': self.upload_to_imgur,
            'catbox': self.upload_to_catbox,
            'gofile': self.upload_to_gofile,
            'pixhost': self.upload_to_pixhost,
            '0x0': self.upload_to_0x0
        }
        
        # Filter out services without API keys
        self.active_services = []
        for service in self.available_services:
            if service == '0x0' or self.api_keys.get(service):
                self.active_services.append(service)
        
        if not self.active_services:
            logger.warning("No active image upload services available. Check your API keys.")
    
    def upload(self, file_data, filename=None, service=None):
        """
        Upload an image to an external service
        
        Args:
            file_data: The image data (bytes or file-like object)
            filename: Optional filename
            service: Optional service name to use (otherwise random from active services)
            
        Returns:
            dict: {
                'success': bool,
                'url': str,
                'service': str,
                'error': str (if success is False)
            }
        """
        # If no active services, return error
        if not self.active_services:
            return {
                'success': False,
                'error': 'No active image upload services available',
                'service': None,
                'url': None
            }
        
        # If no service specified, pick a random one from active services
        if not service or service not in self.active_services:
            service = random.choice(self.active_services)
        
        # Get the appropriate adapter
        adapter = self.adapters.get(service)
        if not adapter:
            return {
                'success': False,
                'error': f'Service {service} not supported',
                'service': service,
                'url': None
            }
        
        try:
            # Call the adapter
            result = adapter(file_data, filename)
            result['service'] = service
            return result
        except Exception as e:
            logger.error(f"Error uploading to {service}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'service': service,
                'url': None
            }
    
    def upload_to_imgur(self, file_data, filename=None):
        """Upload image to Imgur"""
        if not self.api_keys.get('imgur'):
            return {'success': False, 'error': 'Imgur API key not configured'}
        
        # Convert file data to base64 if it's not already
        if hasattr(file_data, 'read'):
            # It's a file-like object
            file_data = file_data.read()
        
        # Encode as base64
        b64_image = base64.b64encode(file_data).decode('utf-8')
        
        headers = {
            'Authorization': f'Client-ID {self.api_keys["imgur"]}'
        }
        
        data = {
            'image': b64_image,
            'type': 'base64'
        }
        
        if filename:
            data['name'] = filename
        
        response = requests.post(
            'https://api.imgur.com/3/image',
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'url': result['data']['link']
            }
        else:
            return {
                'success': False,
                'error': f'Imgur upload failed: {response.text}'
            }
    
    def upload_to_catbox(self, file_data, filename=None):
        """Upload image to Catbox.moe"""
        if not self.api_keys.get('catbox'):
            return {'success': False, 'error': 'Catbox user hash not configured'}
        
        # Ensure we have a filename
        if not filename:
            filename = 'image.jpg'
        
        # Prepare the file for upload
        files = {
            'fileToUpload': (filename, file_data, 'image/jpeg')
        }
        
        data = {
            'reqtype': 'fileupload',
            'userhash': self.api_keys['catbox']
        }
        
        response = requests.post(
            'https://catbox.moe/user/api.php',
            files=files,
            data=data
        )
        
        if response.status_code == 200 and response.text.startswith('https://'):
            return {
                'success': True,
                'url': response.text.strip()
            }
        else:
            return {
                'success': False,
                'error': f'Catbox upload failed: {response.text}'
            }
    
    def upload_to_gofile(self, file_data, filename=None):
        """Upload image to GoFile.io"""
        # First, get a server
        server_response = requests.get('https://api.gofile.io/getServer')
        if server_response.status_code != 200:
            return {'success': False, 'error': 'Failed to get GoFile server'}
        
        server = server_response.json().get('data', {}).get('server')
        if not server:
            return {'success': False, 'error': 'No GoFile server available'}
        
        # Ensure we have a filename
        if not filename:
            filename = 'image.jpg'
        
        # Prepare the file for upload
        files = {
            'file': (filename, file_data, 'image/jpeg')
        }
        
        # Add API token if available
        data = {}
        if self.api_keys.get('gofile'):
            data['token'] = self.api_keys['gofile']
        
        # Upload the file
        upload_url = f'https://{server}.gofile.io/uploadFile'
        response = requests.post(upload_url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                return {
                    'success': True,
                    'url': result.get('data', {}).get('downloadPage', '')
                }
        
        return {
            'success': False,
            'error': f'GoFile upload failed: {response.text}'
        }
    
    def upload_to_pixhost(self, file_data, filename=None):
        """Upload image to Pixhost.to"""
        # Ensure we have a filename
        if not filename:
            filename = 'image.jpg'
        
        # Prepare the file for upload
        files = {
            'img': (filename, file_data, 'image/jpeg')
        }
        
        data = {
            'content_type': 0,  # 0 for family-friendly content
            'max_th_size': 300  # Thumbnail size
        }
        
        response = requests.post(
            'https://api.pixhost.to/images',
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'show_url' in result:
                return {
                    'success': True,
                    'url': result['show_url']
                }
        
        return {
            'success': False,
            'error': f'Pixhost upload failed: {response.text}'
        }
    
    def upload_to_0x0(self, file_data, filename=None):
        """Upload image to 0x0.st"""
        # Prepare the file for upload
        files = {
            'file': (filename or 'image.jpg', file_data, 'image/jpeg')
        }
        
        response = requests.post(
            'https://0x0.st',
            files=files
        )
        
        if response.status_code == 200 and response.text.startswith('https://'):
            return {
                'success': True,
                'url': response.text.strip()
            }
        else:
            return {
                'success': False,
                'error': f'0x0.st upload failed: {response.text}'
            }

# Create a singleton instance
uploader = ImageUploader()

def upload_image(file_data, filename=None, service=None):
    """
    Upload an image to an external service
    
    Args:
        file_data: The image data (bytes or file-like object)
        filename: Optional filename
        service: Optional service name to use (otherwise random from active services)
        
    Returns:
        dict: {
            'success': bool,
            'url': str,
            'service': str,
            'error': str (if success is False)
        }
    """
    return uploader.upload(file_data, filename, service)

def get_active_services():
    """Get list of active image upload services"""
    return uploader.active_services
