"""
Utility functions for blendxcoursecreator API.
"""
import os
import uuid
import mimetypes
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import logging

log = logging.getLogger(__name__)


def get_attachment_storage():
    """
    Get the storage backend for attachments.
    """
    return default_storage


def save_attachment_file(file_obj, org="AI", user_id=None):
    """
    Save uploaded file to storage and return the file path.
    
    Args:
        file_obj: Django UploadedFile object
        org: Organization name
        user_id: User ID for organizing files
        
    Returns:
        str: Path to the saved file
    """
    try:
        # Generate unique filename
        file_extension = file_obj.name.split('.')[-1].lower()
        unique_filename = f"att_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Create directory path: attachments/{org}/{user_id}/
        if user_id:
            directory_path = f"attachments/{org}/{user_id}/"
        else:
            directory_path = f"attachments/{org}/"
        
        # Ensure directory exists
        storage = get_attachment_storage()
        if not storage.exists(directory_path):
            # Create directory by saving an empty file and then deleting it
            temp_path = os.path.join(directory_path, '.keep')
            storage.save(temp_path, ContentFile(''))
            storage.delete(temp_path)
        
        # Save file
        file_path = os.path.join(directory_path, unique_filename)
        saved_path = storage.save(file_path, file_obj)
        
        log.info(f"File saved successfully: {saved_path}")
        return saved_path
        
    except Exception as e:
        log.error(f"Error saving attachment file: {e}")
        raise


def delete_attachment_file(file_path):
    """
    Delete attachment file from storage.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        storage = get_attachment_storage()
        if storage.exists(file_path):
            storage.delete(file_path)
            log.info(f"File deleted successfully: {file_path}")
            return True
        else:
            log.warning(f"File not found for deletion: {file_path}")
            return False
    except Exception as e:
        log.error(f"Error deleting attachment file {file_path}: {e}")
        return False


def get_file_info(file_obj):
    """
    Extract file information from uploaded file.
    
    Args:
        file_obj: Django UploadedFile object
        
    Returns:
        dict: File information
    """
    filename = file_obj.name
    file_size = file_obj.size
    file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        # Fallback MIME types for common extensions
        mime_type_map = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'rtf': 'application/rtf',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'ppt': 'application/vnd.ms-powerpoint',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xls': 'application/vnd.ms-excel',
            'csv': 'text/csv',
        }
        mime_type = mime_type_map.get(file_extension, 'application/octet-stream')
    
    return {
        'filename': filename,
        'file_size': file_size,
        'file_extension': file_extension,
        'file_type': mime_type
    }


def get_attachment_url(file_path):
    """
    Get the URL for accessing an attachment file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: URL to access the file
    """
    try:
        storage = get_attachment_storage()
        if hasattr(storage, 'url'):
            return storage.url(file_path)
        else:
            # For local storage, construct URL manually
            if hasattr(settings, 'MEDIA_URL'):
                return f"{settings.MEDIA_URL}{file_path}"
            return f"/media/{file_path}"
    except Exception as e:
        log.error(f"Error getting attachment URL for {file_path}: {e}")
        return None


def validate_file_type(file_obj):
    """
    Validate if the file type is supported for AI processing.
    
    Args:
        file_obj: Django UploadedFile object
        
    Returns:
        bool: True if supported, False otherwise
    """
    supported_extensions = [
        'pdf', 'docx', 'doc', 'txt', 'md', 'rtf',
        'pptx', 'ppt', 'xlsx', 'xls', 'csv'
    ]
    
    filename = file_obj.name
    file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
    
    return file_extension in supported_extensions


def get_supported_file_types():
    """
    Get list of supported file types for AI processing.
    
    Returns:
        list: List of supported file extensions
    """
    return [
        'pdf', 'docx', 'doc', 'txt', 'md', 'rtf',
        'pptx', 'ppt', 'xlsx', 'xls', 'csv'
    ]
