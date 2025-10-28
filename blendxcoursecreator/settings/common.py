from path import Path as path

import os

APP_ROOT = path(__file__).abspath().dirname().dirname()
REPO_ROOT = APP_ROOT.dirname() 


def plugin_settings(settings):
    """
    Injects local settings into django settings
    """

    # Email Configuration
    settings.PLATFORM_NAME = os.environ.get('PLATFORM_NAME', 'BlendX')
    settings.REPLY_TO_EMAIL = os.environ.get('REPLY_TO_EMAIL', 'contact@blend-ed.com')
    
    # Email notification settings
    settings.ENABLE_COURSE_CREATION_EMAILS = os.environ.get('ENABLE_COURSE_CREATION_EMAILS', 'True').lower() == 'true'
    settings.EMAIL_NOTIFICATION_LANGUAGE = os.environ.get('EMAIL_NOTIFICATION_LANGUAGE', 'en')