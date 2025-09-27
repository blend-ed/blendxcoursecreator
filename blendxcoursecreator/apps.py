"""
blendxcoursecreator Django application initialization.
"""

from django.apps import AppConfig

from openedx.core.djangoapps.plugins.constants import (
    PluginURLs,
    PluginSettings,
    ProjectType,
    SettingsType,
)

class BlendxcoursecreatorConfig(AppConfig):
    """
    Configuration for the blendxcoursecreator Django application.
    """

    name = 'blendxcoursecreator'

    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.CMS: {
                PluginURLs.NAMESPACE: name,
                PluginURLs.REGEX: "^blendxcoursecreator",
                PluginURLs.RELATIVE_PATH: "urls",
            }
        },
        PluginSettings.CONFIG: {
            ProjectType.CMS: {
                SettingsType.PRODUCTION: {PluginSettings.RELATIVE_PATH: "settings.production"},
                SettingsType.COMMON: {PluginSettings.RELATIVE_PATH: "settings.common"},
                SettingsType.DEVSTACK: {PluginSettings.RELATIVE_PATH: "settings.development"},
            }
        },
    }
