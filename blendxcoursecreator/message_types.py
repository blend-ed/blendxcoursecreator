"""
Message types for blendxcoursecreator email notifications.
"""
from openedx.core.djangoapps.ace_common.message import BaseMessageType


class CourseCreationSuccess(BaseMessageType):
    """
    A message for notifying users when their AI course creation is successful.
    """
    APP_LABEL = 'blendxcoursecreator'
    Name = 'course_creation_success'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options['transactional'] = True


class CourseCreationFailure(BaseMessageType):
    """
    A message for notifying users when their AI course creation fails.
    """
    APP_LABEL = 'blendxcoursecreator'
    Name = 'course_creation_failure'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options['transactional'] = True


class CourseCreationProgress(BaseMessageType):
    """
    A message for notifying users about course creation progress.
    """
    APP_LABEL = 'blendxcoursecreator'
    Name = 'course_creation_progress'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options['transactional'] = True


class CourseStructureGenerated(BaseMessageType):
    """
    A message for notifying users when course structure is generated.
    """
    APP_LABEL = 'blendxcoursecreator'
    Name = 'course_structure_generated'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options['transactional'] = True


