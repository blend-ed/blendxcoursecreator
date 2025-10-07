import logging

log = logging.getLogger(__name__)

def import_course_from_path(user_id, course_key_string, file_path, language='en'):
    """
    Import a course from a local file path using Open edX storage and async task.
    """
    import os as _os
    from django.core.files import File as _DjangoFile
    from cms.djangoapps.contentstore.storage import course_import_export_storage as _storage
    from cms.djangoapps.contentstore.tasks import import_olx as _import_olx

    filename = _os.path.basename(file_path)
    try:
        with open(file_path, 'rb') as local_file:
            django_file = _DjangoFile(local_file)
            storage_path = _storage.save('olx_import/' + filename, django_file)

        async_result = _import_olx.delay(
            user_id,
            course_key_string,
            storage_path,
            filename,
            language,
        )
        return async_result.task_id
    except Exception:
        log.exception(f'Course import {course_key_string}: Error in import')
        raise
