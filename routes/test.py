import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from app import save_photo, app
from models import FileUpload, db

# Create Blueprint
test_bp = Blueprint('test', __name__)

class UploadTestForm(FlaskForm):
    """Simple form for upload testing"""
    pass

@test_bp.route('/upload-test', methods=['GET', 'POST'])
def upload_test():
    """Test page for multi-site image uploads"""
    form = UploadTestForm()
    uploaded_urls = []
    primary_url = None
    error = None
    
    if request.method == 'POST' and 'photo' in request.files:
        photo = request.files['photo']
        
        # Check if photo is valid
        if photo.filename == '':
            error = "No file selected"
        else:
            try:
                # Try to upload the photo using our multi-site upload system
                url = save_photo(photo)
                
                if url:
                    # Get the FileUpload record to get all URLs
                    file_upload = FileUpload.query.filter_by(primary_url=url).first()
                    
                    if file_upload:
                        # Get all URLs
                        uploaded_urls = file_upload.get_all_urls()
                        primary_url = url
                    else:
                        # Just use the primary URL
                        uploaded_urls = [url]
                        primary_url = url
                else:
                    error = "Upload failed. The file may be invalid or all upload services may be down."
            except Exception as e:
                app.logger.error(f"Upload test error: {e}")
                error = f"An error occurred: {str(e)}"
    
    return render_template('upload_test.html', 
                           form=form, 
                           uploaded_urls=uploaded_urls, 
                           primary_url=primary_url, 
                           error=error)