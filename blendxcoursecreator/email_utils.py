"""
Email utility functions for blendxcoursecreator.
"""
import logging
from typing import Dict, Optional, List
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from edx_ace import ace
from edx_ace.recipient import Recipient
from openedx.core.lib.celery.task_utils import emulate_http_request

from blendxcoursecreator.message_types import (
    CourseCreationSuccess,
    CourseCreationFailure,
    CourseCreationProgress,
    CourseStructureGenerated,
)

log = logging.getLogger(__name__)
User = get_user_model()


def get_platform_settings():
    """
    Get platform-specific settings for email templates.
    """
    return {
        'platform_name': getattr(settings, 'PLATFORM_NAME', 'BlendX'),
        'reply_to_email': getattr(settings, 'REPLY_TO_EMAIL', 'contact@blend-ed.com'),
        'homepage_url': getattr(settings, 'LMS_ROOT_URL', ''),
        'dashboard_url': f"{getattr(settings, 'LMS_ROOT_URL', '')}/dashboard",
    }


def send_course_creation_success_email(
    user_email: str,
    course_key: str,
    course_name: str,
    user_id: Optional[int] = None,
    language: Optional[str] = None,
    org_name: Optional[str] = None
) -> bool:
    """
    Send email notification when course creation is successful.
    
    Args:
        user_email: Recipient's email address
        course_key: Generated course key
        course_name: Name of the created course
        user_id: LMS user ID (optional)
        language: Language for the email (optional)
        org_name: Organization name (optional)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        platform_settings = get_platform_settings()
        
        param_dict = {
            'user_id': user_id or 0,
            'email_address': user_email,
            'full_name': _('Course Creator'),
            'message_type': 'course_creation_success',
            'course_key': course_key,
            'course_name': course_name,
            'course_url': f"{platform_settings['homepage_url']}/courses/{course_key}/course/",
            'platform_name': platform_settings['platform_name'],
            'reply_to_email': platform_settings['reply_to_email'],
            'dashboard_url': platform_settings['dashboard_url'],
            'homepage_url': platform_settings['homepage_url'],
        }
        
        return _send_email(user_email, param_dict, language, org_name, user_id)
        
    except Exception as e:
        log.error(f"Error sending course creation success email to {user_email}: {str(e)}")
        return False


def send_course_creation_failure_email(
    user_email: str,
    course_topic: str,
    error_message: str,
    user_id: Optional[int] = None,
    language: Optional[str] = None,
    org_name: Optional[str] = None
) -> bool:
    """
    Send email notification when course creation fails.
    
    Args:
        user_email: Recipient's email address
        course_topic: Topic of the course that failed
        error_message: Error message explaining the failure
        user_id: LMS user ID (optional)
        language: Language for the email (optional)
        org_name: Organization name (optional)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        platform_settings = get_platform_settings()
        
        param_dict = {
            'user_id': user_id or 0,
            'email_address': user_email,
            'full_name': _('Course Creator'),
            'message_type': 'course_creation_failure',
            'course_topic': course_topic,
            'error_message': error_message,
            'platform_name': platform_settings['platform_name'],
            'reply_to_email': platform_settings['reply_to_email'],
            'dashboard_url': platform_settings['dashboard_url'],
            'homepage_url': platform_settings['homepage_url'],
        }
        
        return _send_email(user_email, param_dict, language, org_name, user_id)
        
    except Exception as e:
        log.error(f"Error sending course creation failure email to {user_email}: {str(e)}")
        return False


def send_course_structure_generated_email(
    user_email: str,
    course_topic: str,
    user_id: Optional[int] = None,
    language: Optional[str] = None,
    org_name: Optional[str] = None
) -> bool:
    """
    Send email notification when course structure is generated.
    
    Args:
        user_email: Recipient's email address
        course_topic: Topic of the course
        user_id: LMS user ID (optional)
        language: Language for the email (optional)
        org_name: Organization name (optional)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        platform_settings = get_platform_settings()
        
        param_dict = {
            'user_id': user_id or 0,
            'email_address': user_email,
            'full_name': _('Course Creator'),
            'message_type': 'course_structure_generated',
            'course_topic': course_topic,
            'platform_name': platform_settings['platform_name'],
            'reply_to_email': platform_settings['reply_to_email'],
            'dashboard_url': platform_settings['dashboard_url'],
            'homepage_url': platform_settings['homepage_url'],
        }
        
        return _send_email(user_email, param_dict, language, org_name, user_id)
        
    except Exception as e:
        log.error(f"Error sending course structure generated email to {user_email}: {str(e)}")
        return False


def send_course_creation_progress_email(
    user_email: str,
    course_topic: str,
    progress_message: str,
    user_id: Optional[int] = None,
    language: Optional[str] = None,
    org_name: Optional[str] = None
) -> bool:
    """
    Send email notification about course creation progress.
    
    Args:
        user_email: Recipient's email address
        course_topic: Topic of the course
        progress_message: Progress update message
        user_id: LMS user ID (optional)
        language: Language for the email (optional)
        org_name: Organization name (optional)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        platform_settings = get_platform_settings()
        
        param_dict = {
            'user_id': user_id or 0,
            'email_address': user_email,
            'full_name': _('Course Creator'),
            'message_type': 'course_creation_progress',
            'course_topic': course_topic,
            'progress_message': progress_message,
            'platform_name': platform_settings['platform_name'],
            'reply_to_email': platform_settings['reply_to_email'],
            'dashboard_url': platform_settings['dashboard_url'],
            'homepage_url': platform_settings['homepage_url'],
        }
        
        return _send_email(user_email, param_dict, language, org_name, user_id)
        
    except Exception as e:
        log.error(f"Error sending course creation progress email to {user_email}: {str(e)}")
        return False


def _send_email(
    user_email: str,
    param_dict: Dict,
    language: Optional[str] = None,
    org_name: Optional[str] = None,
    user_id: Optional[int] = None
) -> bool:
    """
    Internal function to send email using ACE framework.
    
    Args:
        user_email: Recipient's email address
        param_dict: Dictionary containing email parameters
        language: Language for the email (optional)
        org_name: Organization name (optional)
        user_id: LMS user ID (optional)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        message_type = param_dict['message_type']
        
        # Map message types to ACE email classes
        ace_emails_dict = {
            'course_creation_success': CourseCreationSuccess,
            'course_creation_failure': CourseCreationFailure,
            'course_creation_progress': CourseCreationProgress,
            'course_structure_generated': CourseStructureGenerated,
        }
        
        if message_type not in ace_emails_dict:
            log.error(f"Unknown message type: {message_type}")
            return False
        
        message_class = ace_emails_dict[message_type]
        lms_user_id = param_dict.get('user_id', 0)
        
        message = message_class().personalize(
            recipient=Recipient(lms_user_id=lms_user_id, email_address=user_email),
            language=language,
            user_context=param_dict,
        )
        
        log.debug(f"Sending email to {user_email} with params: {_masked_dict(param_dict)}")
        
        # Use blendxadmin user to send the email if user_id is not provided
        request_user = User.objects.get(username='blendxadmin')
        if user_id:
            try:
                request_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                log.warning(f"User with ID {user_id} not found, using blendxadmin")
        
        with emulate_http_request(site=Site.objects.get(id=settings.SITE_ID), user=request_user):
            ace.send(message)
        
        return True
        
    except Exception as e:
        log.error(f"Error sending email to {user_email}: {str(e)}")
        return False


def _masked_dict(param_dict: Dict) -> Dict:
    """
    Mask sensitive information in the parameter dictionary for logging.
    
    Args:
        param_dict: Dictionary to mask
    
    Returns:
        Dict: Masked dictionary
    """
    sensitive_keys = ['password', 'token', 'client_id', 'client_secret', 'Authorization', 'secret']
    masked_dict = param_dict.copy()
    
    for key in sensitive_keys:
        if key in masked_dict:
            masked_dict[key] = '***'
    
    return masked_dict
