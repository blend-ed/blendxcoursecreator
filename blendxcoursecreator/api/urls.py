"""
URL configuration for course creator API.
"""
from django.urls import path
from blendxcoursecreator.api.views import (
    AttachmentView,
    AttachmentDetailView,
    AttachmentBulkDeleteView,
    CourseCreatorView,
    AICourseListView,
    AICourseDetailView,
    CourseCreatorTaskStatusView,
)

app_name = 'blendxcoursecreator_api'

urlpatterns = [
    # Course Creator endpoints
    path('course-creator/', CourseCreatorView.as_view(), name='course_creator'),
    path('task-status/<str:course>/', CourseCreatorTaskStatusView.as_view(), name='task_status'),
    
    # AI list courses
    path('ai-courses/', AICourseListView.as_view(), name='ai_courses_list'),
    path('ai-courses/<int:course_id>/', AICourseDetailView.as_view(), name='ai_course_detail'),
    
    # Attachment endpoints
    path('attachments/', AttachmentView.as_view(), name='attachments'),
    path('attachments/<int:pk>/', AttachmentDetailView.as_view(), name='attachment_detail'),
    path('attachments/bulk-delete/', AttachmentBulkDeleteView.as_view(), name='attachments_bulk_delete'),
]
