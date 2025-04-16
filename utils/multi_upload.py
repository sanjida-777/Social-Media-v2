import os
import json
import time
import logging
import threading
import requests
from werkzeug.utils import secure_filename
from typing import List, Dict, Optional, Tuple

# Set up logger
logger = logging.getLogger(__name__)

# Rate limiting configuration
MAX_REQUESTS_PER_SECOND = 1  # 1 request per second per service
upload_timestamps = {}
rate_limit_lock = threading.Lock()

# Image hosting services configuration
UPLOAD_SERVICES = {
    "imgur": {
        "enabled": True,
        "upload_url": "https://api.imgur.com/3/image",
        "headers": {
            "Authorization": f"Client-ID {os.environ.get('IMGUR_CLIENT_ID', '')}"
        },
        "field_name": "image",
        "response_url_path": ["data", "link"]
    },
    "catbox": {
        "enabled": True,
        "upload_url": "https://catbox.moe/user/api.php",
        "form_data": {
            "reqtype": "fileupload",
            "userhash": ""  # Anonymous upload
        },
        "field_name": "fileToUpload",
        "response_url_path": []  # Direct response is the URL
    },
    "imgbb": {
        "enabled": True,
        "upload_url": "https://api.imgbb.com/1/upload",
        "form_data": {
            "key": os.environ.get('IMGBB_API_KEY', '')
        },
        "field_name": "image",
        "response_url_path": ["data", "url"]
    }
}

def check_rate_limit(service_name: str) -> bool:
    """
    Check if a service has been rate limited

    Args:
        service_name: Name of the service to check

    Returns:
        bool: True if requests can be made, False if rate limited
    """
    current_time = time.time()
    with rate_limit_lock:
        if service_name not in upload_timestamps:
            upload_timestamps[service_name] = current_time
            return True

        elapsed = current_time - upload_timestamps[service_name]
        if elapsed >= 1.0 / MAX_REQUESTS_PER_SECOND:
            upload_timestamps[service_name] = current_time
            return True

        logger.debug(f"Rate limited for service: {service_name}, need to wait {1.0 / MAX_REQUESTS_PER_SECOND - elapsed:.2f}s")
        return False

def wait_for_rate_limit(service_name: str) -> None:
    """
    Wait until a service is no longer rate limited

    Args:
        service_name: Name of the service to wait for
    """
    while not check_rate_limit(service_name):
        time.sleep(0.1)

def upload_to_service(file, service_name: str, service_config: Dict) -> Optional[str]:
    """
    Upload a file to a specific service with rate limiting

    Args:
        file: File object to upload
        service_name: Name of the service
        service_config: Service configuration

    Returns:
        Optional[str]: URL of the uploaded file if successful, None otherwise
    """
    # Check if service is enabled
    if not service_config.get("enabled", False):
        logger.debug(f"Service {service_name} is disabled, skipping")
        return None

    # Wait for rate limit
    wait_for_rate_limit(service_name)

    try:
        # Reset file pointer
        file.seek(0)

        # Prepare upload
        upload_url = service_config["upload_url"]
        field_name = service_config["field_name"]

        # Prepare request arguments
        kwargs = {
            "files": {
                field_name: (
                    secure_filename(file.filename),
                    file,
                    file.content_type if hasattr(file, 'content_type') else None
                )
            },
            "timeout": 30
        }

        # Add headers if specified
        if "headers" in service_config:
            kwargs["headers"] = service_config["headers"]

        # Add form data if specified
        if "form_data" in service_config:
            kwargs["data"] = service_config["form_data"]

        # Make request
        logger.info(f"Uploading to {service_name}...")
        response = requests.post(upload_url, **kwargs)

        # Check response
        if response.status_code not in (200, 201):
            logger.warning(f"Upload to {service_name} failed with status code {response.status_code}: {response.text}")
            return None

        # Extract URL from response
        if service_name in ("0x0", "catbox"):
            # These services return the URL directly as text
            url = response.text.strip()
        else:
            # Other services return JSON
            response_data = response.json()
            url = response_data
            for key in service_config["response_url_path"]:
                url = url[key]

        logger.info(f"Successfully uploaded to {service_name}: {url}")
        return url

    except Exception as e:
        logger.error(f"Error uploading to {service_name}: {str(e)}")
        return None

def save_multi_uploads(file) -> List[str]:
    """
    Save a file to multiple hosting services for redundancy

    Args:
        file: File object to upload

    Returns:
        List[str]: List of URLs where the file was uploaded
    """
    urls = []
    errors = []

    # Try each service in sequence
    for service_name, service_config in UPLOAD_SERVICES.items():
        try:
            url = upload_to_service(file, service_name, service_config)
            if url:
                urls.append(url)
                logger.info(f"Successfully uploaded to {service_name}: {url}")
            else:
                errors.append(f"{service_name}: Failed to upload")
        except Exception as e:
            logger.error(f"Error with {service_name}: {str(e)}")
            errors.append(f"{service_name}: {str(e)}")

    if not urls and errors:
        logger.error(f"All uploads failed: {', '.join(errors)}")

    return urls

def get_first_working_url(urls: List[str]) -> Optional[str]:
    """
    Check a list of URLs and return the first one that is accessible

    Args:
        urls: List of URLs to check

    Returns:
        Optional[str]: The first working URL, or None if none work
    """
    for url in urls:
        try:
            response = requests.head(url, timeout=5)
            if response.status_code < 400:
                return url
        except Exception:
            continue

    return None if not urls else urls[0]  # Fall back to first URL if all checks fail