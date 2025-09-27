def plugin_settings(settings):
    """
    Injects development settings into django settings
    """
    settings.LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s %(levelname)s %(process)d [%(name)s] %(filename)s:%(lineno)d - %(message)s',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
        },
        'loggers': {
            '': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
            'blendxcoursecreator': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'tracking': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    } 