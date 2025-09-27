from path import Path as path

import os

APP_ROOT = path(__file__).abspath().dirname().dirname()
REPO_ROOT = APP_ROOT.dirname() 


def plugin_settings(settings):
    """
    Injects local settings into django settings
    """
    # Add the template directory for this package to
    # to the search path for Mako.