import logging
import json
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from openedx.core.lib.api.view_utils import view_auth_classes

from edx_api_doc_tools import schema
from drf_yasg import openapi
from blendxcoursecreator.models import Attachment
from blendxcoursecreator.api.serializers import (
    AttachmentSerializer,
    AttachmentUploadSerializer,
    AttachmentListSerializer,
)
from blendxcoursecreator.api.utils import (
    save_attachment_file,
    delete_attachment_file,
    get_file_info,
    get_attachment_url,
    validate_file_type,
    get_supported_file_types
)

log = logging.getLogger(__name__)

@view_auth_classes(is_authenticated=True)
class AttachmentView(APIView):
    """
    API endpoint for managing attachments (upload, list, get, delete).
    """
    permission_classes = [IsAuthenticated]
    
    @schema(
        body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "file": openapi.Schema(type=openapi.TYPE_FILE),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["file"]
        ),
        responses={
            201: openapi.Response(description="Attachment uploaded successfully"),
            400: openapi.Response(description="Invalid request"),
            500: openapi.Response(description="Server error"),
        }
    )
    @csrf_exempt
    def post(self, request):
        """Upload a new attachment"""
        try:
            serializer = AttachmentUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    data={"message": "Invalid data", "errors": serializer.errors, "status": "failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file_obj = serializer.validated_data['file']
            description = serializer.validated_data.get('description', '')
            
            # Validate file type
            if not validate_file_type(file_obj):
                supported_types = get_supported_file_types()
                return Response(
                    data={
                        "message": f"Unsupported file type. Supported formats: {', '.join(supported_types)}",
                        "status": "failed"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get file information
            file_info = get_file_info(file_obj)
            
            # Save file to storage
            file_path = save_attachment_file(
                file_obj=file_obj,
                org=getattr(request, 'org', 'AI'),
                user_id=request.user.id
            )
            
            # Create attachment record
            attachment = Attachment.objects.create(
                user=request.user,
                filename=file_info['filename'],
                file_path=file_path,
                file_size=file_info['file_size'],
                file_type=file_info['file_type'],
                file_extension=file_info['file_extension'],
                description=description,
                org=getattr(request, 'org', 'AI')
            )
            
            # Serialize response
            response_serializer = AttachmentSerializer(attachment)
            
            return Response(
                data={
                    "message": "Attachment uploaded successfully",
                    "status": "success",
                    "attachment": response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            log.error(f"Error uploading attachment: {e}")
            return Response(
                data={"message": str(e), "status": "failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @schema(
        responses={
            200: openapi.Response(description="List of attachments"),
            500: openapi.Response(description="Server error"),
        }
    )
    def get(self, request):
        """List user's attachments"""
        try:
            # Get query parameters
            file_type = request.query_params.get('file_type')
            org = getattr(request, 'org', 'AI')
            
            # Build queryset
            queryset = Attachment.objects.filter(user=request.user, org=org)
            
            if file_type:
                queryset = queryset.filter(file_type__icontains=file_type)
            
            # Serialize response
            serializer = AttachmentListSerializer(queryset, many=True)
            
            return Response(
                data={
                    "attachments": serializer.data,
                    "count": queryset.count(),
                    "status": "success"
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            log.error(f"Error listing attachments: {e}")
            return Response(
                data={"message": str(e), "status": "failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@view_auth_classes(is_authenticated=True)
class AttachmentDetailView(APIView):
    """
    API endpoint for individual attachment operations (get, update, delete).
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get attachment object or return 404"""
        try:
            return Attachment.objects.get(pk=pk, user=user)
        except Attachment.DoesNotExist:
            return None
    
    @schema(
        responses={
            200: openapi.Response(description="Attachment details"),
            404: openapi.Response(description="Attachment not found"),
            500: openapi.Response(description="Server error"),
        }
    )
    def get(self, request, pk):
        """Get attachment details"""
        try:
            attachment = self.get_object(pk, request.user)
            if not attachment:
                return Response(
                    data={"message": "Attachment not found", "status": "failed"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = AttachmentSerializer(attachment)
            
            # Add file URL to response
            response_data = serializer.data.copy()
            response_data['file_url'] = get_attachment_url(attachment.file_path)
            
            return Response(
                data={
                    "attachment": response_data,
                    "status": "success"
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            log.error(f"Error getting attachment {pk}: {e}")
            return Response(
                data={"message": str(e), "status": "failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @schema(
        body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response(description="Attachment updated successfully"),
            404: openapi.Response(description="Attachment not found"),
            400: openapi.Response(description="Invalid request"),
            500: openapi.Response(description="Server error"),
        }
    )
    def patch(self, request, pk):
        """Update attachment description"""
        try:
            attachment = self.get_object(pk, request.user)
            if not attachment:
                return Response(
                    data={"message": "Attachment not found", "status": "failed"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Update description
            description = request.data.get('description', '')
            attachment.description = description
            attachment.save()
            
            serializer = AttachmentSerializer(attachment)
            
            return Response(
                data={
                    "message": "Attachment updated successfully",
                    "attachment": serializer.data,
                    "status": "success"
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            log.error(f"Error updating attachment {pk}: {e}")
            return Response(
                data={"message": str(e), "status": "failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @schema(
        responses={
            200: openapi.Response(description="Attachment deleted successfully"),
            404: openapi.Response(description="Attachment not found"),
            500: openapi.Response(description="Server error"),
        }
    )
    def delete(self, request, pk):
        """Delete attachment"""
        try:
            attachment = self.get_object(pk, request.user)
            if not attachment:
                return Response(
                    data={"message": "Attachment not found", "status": "failed"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Delete file from storage
            file_deleted = delete_attachment_file(attachment.file_path)
            if not file_deleted:
                log.warning(f"Failed to delete file from storage: {attachment.file_path}")
            
            # Delete database record
            attachment.delete()
            
            return Response(
                data={
                    "message": "Attachment deleted successfully",
                    "status": "success"
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            log.error(f"Error deleting attachment {pk}: {e}")
            return Response(
                data={"message": str(e), "status": "failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@view_auth_classes(is_authenticated=True)
class AttachmentBulkDeleteView(APIView):
    """
    API endpoint for bulk deletion of attachments.
    """
    permission_classes = [IsAuthenticated]
    
    @schema(
        body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "attachment_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER)
                ),
            },
            required=["attachment_ids"]
        ),
        responses={
            200: openapi.Response(description="Attachments deleted successfully"),
            400: openapi.Response(description="Invalid request"),
            500: openapi.Response(description="Server error"),
        }
    )
    @csrf_exempt
    def post(self, request):
        """Bulk delete attachments"""
        try:
            attachment_ids = request.data.get('attachment_ids', [])
            
            if not attachment_ids:
                return Response(
                    data={"message": "No attachment IDs provided", "status": "failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user's attachments
            attachments = Attachment.objects.filter(
                id__in=attachment_ids,
                user=request.user
            )
            
            if not attachments.exists():
                return Response(
                    data={"message": "No attachments found", "status": "failed"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            deleted_count = 0
            failed_deletions = []
            
            for attachment in attachments:
                try:
                    # Delete file from storage
                    file_deleted = delete_attachment_file(attachment.file_path)
                    if not file_deleted:
                        log.warning(f"Failed to delete file from storage: {attachment.file_path}")
                    
                    # Delete database record
                    attachment.delete()
                    deleted_count += 1
                    
                except Exception as e:
                    log.error(f"Error deleting attachment {attachment.id}: {e}")
                    failed_deletions.append(attachment.id)
            
            response_data = {
                "message": f"Deleted {deleted_count} attachments",
                "deleted_count": deleted_count,
                "status": "success"
            }
            
            if failed_deletions:
                response_data["failed_deletions"] = failed_deletions
                response_data["message"] += f", {len(failed_deletions)} failed"
            
            return Response(data=response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            log.error(f"Error in bulk delete: {e}")
            return Response(
                data={"message": str(e), "status": "failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
