def plugin_settings(settings):
    """
    Injects local settings into django settings
    """
    # Specifically configure blendxapi logger to show INFO
    settings.LOGGING['loggers']['blendxcoursecreator'] = {
        'handlers': ['console'],
        'level': 'INFO',
        'propagate': False,
    }

    settings.LOGGING['loggers'][''] = {
        'handlers': ['console'],
        'level': 'INFO',
        'propagate': True,
    }