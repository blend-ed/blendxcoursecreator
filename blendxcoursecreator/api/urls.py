"""
URL configuration for course creator API.
"""
from django.urls import path
from blendxcoursecreator.api.views import (
    AttachmentView,
    AttachmentDetailView,
    AttachmentBulkDeleteView,
)

app_name = 'blendxcoursecreator_api'

urlpatterns = [
    # Attachment endpoints
    path('attachments/', AttachmentView.as_view(), name='attachments'),
    path('attachments/<int:pk>/', AttachmentDetailView.as_view(), name='attachment_detail'),
    path('attachments/bulk-delete/', AttachmentBulkDeleteView.as_view(), name='attachments_bulk_delete'),
]
