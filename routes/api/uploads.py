import os
import logging
import json
from flask import request, jsonify, g, current_app
from werkzeug.utils import secure_filename
from routes.api import api_bp
from utils.image_upload import upload_image, get_active_services
from config import get_config, get_allowed_image_extensions

# Set up logger
logger = logging.getLogger(__name__)

@api_bp.route('/uploads/image', methods=['POST'])
def upload_image_api():
    """
    API endpoint for uploading images to external services
    
    Request:
        - file: The image file to upload
        - service: (optional) The service to use for upload
        
    Response:
        {
            'success': bool,
            'url': str,
            'service': str,
            'error': str (if success is False)
        }
    """
    # Check if user is authenticated
    if not g.user:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No file provided'
        }), 400
    
    file = request.files['file']
    
    # Check if file is empty
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    # Check file extension
    allowed_extensions = get_allowed_image_extensions()
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext[1:] not in allowed_extensions:
        return jsonify({
            'success': False,
            'error': f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
        }), 400
    
    # Get service from request (optional)
    service = request.form.get('service')
    
    try:
        # Upload the image
        result = upload_image(file, filename, service)
        
        # Log the result
        if result['success']:
            logger.info(f"Image uploaded successfully to {result['service']}: {result['url']}")
        else:
            logger.error(f"Image upload failed: {result.get('error')}")
        
        return jsonify(result)
    
    except Exception as e:
        logger.exception(f"Error uploading image: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error uploading image: {str(e)}'
        }), 500

@api_bp.route('/uploads/services', methods=['GET'])
def get_upload_services():
    """
    Get available image upload services
    
    Response:
        {
            'success': bool,
            'services': list of active services
        }
    """
    try:
        services = get_active_services()
        return jsonify({
            'success': True,
            'services': services
        })
    except Exception as e:
        logger.exception(f"Error getting upload services: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error getting upload services: {str(e)}'
        }), 500
