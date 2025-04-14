import os
import uuid
import json
import logging
from werkzeug.utils import secure_filename
from flask import current_app

# Set up logger
logger = logging.getLogger(__name__)

def save_photo(file):
    """
    Save a photo to the server or external services
    Returns the URL of the saved photo
    """
    if not file:
        return None

    # First try to upload to multiple services
    from utils.multi_upload import save_multi_uploads
    from database import db
    from models import FileUpload

    urls = save_multi_uploads(file)
    if urls:
        # Store in database
        upload = FileUpload(
            original_filename=secure_filename(file.filename),
            primary_url=urls[0],
            fallback_urls=json.dumps(urls[1:]) if len(urls) > 1 else None,
            media_type='image'
        )
        db.session.add(upload)
        db.session.commit()
        logger.info(f"File uploaded to external services: {upload.id} - {upload.original_filename}")
        return urls[0]

    # Fall back to local storage if external uploads fail
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER_PHOTOS"], unique_filename)
    file.save(file_path)
    local_url = os.path.join("uploads/photos", unique_filename)

    # Still track in the database even for local files
    upload = FileUpload(
        original_filename=filename,
        primary_url=local_url,
        media_type='image'
    )
    db.session.add(upload)
    db.session.commit()
    logger.info(f"File saved locally: {upload.id} - {unique_filename} (external uploads failed)")

    return local_url

def save_video(file):
    """
    Save a video to the server or external services
    Returns the URL of the saved video
    """
    if not file:
        return None

    # First try to upload to multiple services
    from utils.multi_upload import save_multi_uploads
    from database import db
    from models import FileUpload

    urls = save_multi_uploads(file)
    if urls:
        # Store in database
        upload = FileUpload(
            original_filename=secure_filename(file.filename),
            primary_url=urls[0],
            fallback_urls=json.dumps(urls[1:]) if len(urls) > 1 else None,
            media_type='video'
        )
        db.session.add(upload)
        db.session.commit()
        logger.info(f"Video uploaded to external services: {upload.id} - {upload.original_filename}")
        return urls[0]

    # Fall back to local storage if external uploads fail
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER_VIDEOS"], unique_filename)
    file.save(file_path)
    local_url = os.path.join("uploads/videos", unique_filename)

    # Still track in the database even for local files
    upload = FileUpload(
        original_filename=filename,
        primary_url=local_url,
        media_type='video'
    )
    db.session.add(upload)
    db.session.commit()
    logger.info(f"Video saved locally: {upload.id} - {unique_filename} (external uploads failed)")

    return local_url
