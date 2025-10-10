"""
Database models for blendxcoursecreator.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
import json

User = get_user_model()

class Attachment(TimeStampedModel):
    """
    Model to store attachment metadata for AI course creation.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blendx_attachments',
        help_text=_("User who uploaded the attachment")
    )
    filename = models.CharField(
        max_length=255,
        help_text=_("Original filename")
    )
    file_path = models.CharField(
        max_length=500,
        help_text=_("Path to the stored file")
    )
    file_size = models.BigIntegerField(
        help_text=_("File size in bytes")
    )
    file_type = models.CharField(
        max_length=150,
        help_text=_("File MIME type")
    )
    file_extension = models.CharField(
        max_length=10,
        help_text=_("File extension")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Optional description of the attachment")
    )
    org = models.CharField(
        max_length=100,
        default='AI',
        help_text=_("Organization name")
    )
    
    class Meta:
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user', 'created']),
            models.Index(fields=['file_type']),
            models.Index(fields=['org']),
        ]
    
    def __str__(self):
        return f"Attachment: {self.filename} ({self.user.username})"
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_supported_format(self):
        """Check if file format is supported for AI processing"""
        supported_extensions = [
            'pdf', 'docx', 'doc', 'txt', 'md', 'rtf',
            'pptx', 'ppt', 'xlsx', 'xls', 'csv'
        ]
        return self.file_extension.lower() in supported_extensions
