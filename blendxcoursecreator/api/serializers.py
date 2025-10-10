"""
Serializers for blendxcoursecreator API.
"""
from rest_framework import serializers
from blendxcoursecreator.models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Attachment model.
    """
    file_size_mb = serializers.ReadOnlyField()
    is_supported_format = serializers.ReadOnlyField()
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Attachment
        fields = [
            'id',
            'filename',
            'file_path',
            'file_size',
            'file_size_mb',
            'file_type',
            'file_extension',
            'description',
            'org',
            'username',
            'is_supported_format',
            'created',
            'modified'
        ]
        read_only_fields = [
            'id',
            'file_path',
            'file_size',
            'file_type',
            'file_extension',
            'org',
            'username',
            'is_supported_format',
            'created',
            'modified'
        ]


class AttachmentUploadSerializer(serializers.Serializer):
    """
    Serializer for file upload requests.
    """
    file = serializers.FileField()
    description = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    
    def validate_file(self, value):
        """
        Validate uploaded file.
        """
        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 50MB.")
        
        # Check file extension
        supported_extensions = [
            'pdf', 'docx', 'doc', 'txt', 'md', 'rtf',
            'pptx', 'ppt', 'xlsx', 'xls', 'csv'
        ]
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in supported_extensions:
            raise serializers.ValidationError(
                f"Unsupported file type. Supported formats: {', '.join(supported_extensions)}"
            )
        
        return value


class AttachmentListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for attachment lists.
    """
    file_size_mb = serializers.ReadOnlyField()
    is_supported_format = serializers.ReadOnlyField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Attachment
        fields = [
            'id',
            'filename',
            'file_path',
            'file_size_mb',
            'file_type',
            'file_extension',
            'description',
            'is_supported_format',
            'file_url',
            'created'
        ]
    
    def get_file_url(self, obj):
        """Get the file URL for the attachment"""
        from blendxcoursecreator.api.utils import get_attachment_url
        return get_attachment_url(obj.file_path)
