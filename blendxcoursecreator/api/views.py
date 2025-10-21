import logging
import json
import requests
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
from blendxcoursecreator.email_utils import (
    send_course_creation_progress_email,
    send_course_creation_failure_email
)
from django.contrib.auth.models import User
log = logging.getLogger(__name__)
# Attachment Views
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
            
            file_url = get_attachment_url(file_path)
            
            # Create attachment record
            attachment = Attachment.objects.create(
                user=request.user,
                filename=file_info['filename'],
                file_path=file_url,
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


## Course Creator View
@view_auth_classes(is_authenticated=True)
class CourseCreatorView(APIView):
    """
    API endpoint for course creator.
    """
    permission_classes = [IsAuthenticated]
    
    @schema(
        body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "topic": openapi.Schema(type=openapi.TYPE_STRING),
                "instructions": openapi.Schema(type=openapi.TYPE_STRING),
                "course_structure": openapi.Schema(type=openapi.TYPE_OBJECT),
                "action": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["create_structure", "create_content", "update_structure"]
                ),
                "course_size": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["small", "medium", "large", "ai-generated"]
                ),
                "attachment_path": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING)
                ),
                "available_components": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING)
                ),
                "audience": openapi.Schema(type=openapi.TYPE_STRING),
                "target_language": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["en", "es", "fr", "de", "hi", "ml", "ar", "he", "fa", "ur"]
                ),
                "org": openapi.Schema(type=openapi.TYPE_STRING)
            },
            required=["action", "topic"]
        ),
        responses={
            200: openapi.Response(description="Success"),
            400: openapi.Response(description="Invalid request"),
            500: openapi.Response(description="Server error"),
        }
    )
    def post(self, request):
        """
        Forward course creation request to external AICC API.
        
        Supports three actions:
        - create_structure: Generate course structure
        - create_content: Generate course content
        - update_structure: Update existing course structure
        """
        try:
            API_KEY = settings.BLENDX_AICC_KEY
            API_URL = settings.BLENDX_AICC_APP_URL
            
            user_email = User.objects.get(id=request.user.id).email
            
            # Get request data
            request_data = request.data.copy()
            
            # Add user email to the request data
            request_data['user_email'] = user_email
            
            # Send progress email notification
            try:
                topic = request_data.get('topic', 'AI Course')
                send_course_creation_progress_email(
                    user_email=user_email,
                    course_topic=topic,
                    progress_message="Starting AI course creation process...",
                    user_id=request.user.id,
                    language=request_data.get('target_language', 'en'),
                    org_name=request_data.get('org', 'AI')
                )
                log.info(f"Sent course creation progress email to {user_email}")
            except Exception as email_error:
                log.error(f"Failed to send course creation progress email: {email_error}")
            
            # Prepare headers for external API
            headers = {
                'accept': 'application/json',
                'X-API-Key': API_KEY,
                'Content-Type': 'application/json'
            }
            
            # Make POST request to external API
            external_api_url = f"{API_URL}/api/v1/courses/create"
            
            log.info(f"Forwarding request to external API: {external_api_url}")
            log.info(f"Request data: {request_data}")
            response = requests.post(
                external_api_url,
                headers=headers,
                json=request_data,
                timeout=300  # 5 minutes timeout for AI operations
            )
            
            # Check if the response indicates success or failure
            if response.status_code >= 400:
                # Send failure email notification
                try:
                    topic = request_data.get('topic', 'AI Course')
                    error_message = response.json().get('error', 'Unknown error occurred') if response.content else 'Request failed'
                    send_course_creation_failure_email(
                        user_email=user_email,
                        course_topic=topic,
                        error_message=error_message,
                        user_id=request.user.id,
                        language=request_data.get('target_language', 'en'),
                        org_name=request_data.get('org', 'AI')
                    )
                    log.info(f"Sent course creation failure email to {user_email}")
                except Exception as email_error:
                    log.error(f"Failed to send course creation failure email: {email_error}")
            
            # Return the response from external API
            return Response(
                response.json() if response.content else {},
                status=response.status_code
            )
            
        except User.DoesNotExist:
            log.error(f"User with id {request.user.id} not found")
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except requests.exceptions.Timeout:
            log.error("External API request timed out")
            # Send failure email notification for timeout
            try:
                user_email = User.objects.get(id=request.user.id).email
                topic = request.data.get('topic', 'AI Course')
                send_course_creation_failure_email(
                    user_email=user_email,
                    course_topic=topic,
                    error_message="Request to external API timed out",
                    user_id=request.user.id,
                    language=request.data.get('target_language', 'en'),
                    org_name=request.data.get('org', 'AI')
                )
                log.info(f"Sent course creation failure email to {user_email}")
            except Exception as email_error:
                log.error(f"Failed to send course creation failure email: {email_error}")
            
            return Response(
                {"error": "Request to external API timed out"},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except requests.exceptions.RequestException as e:
            log.error(f"Error calling external API: {str(e)}")
            # Send failure email notification for request exception
            try:
                user_email = User.objects.get(id=request.user.id).email
                topic = request.data.get('topic', 'AI Course')
                send_course_creation_failure_email(
                    user_email=user_email,
                    course_topic=topic,
                    error_message=f"Failed to connect to external API: {str(e)}",
                    user_id=request.user.id,
                    language=request.data.get('target_language', 'en'),
                    org_name=request.data.get('org', 'AI')
                )
                log.info(f"Sent course creation failure email to {user_email}")
            except Exception as email_error:
                log.error(f"Failed to send course creation failure email: {email_error}")
            
            return Response(
                {"error": f"Failed to connect to external API: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            log.error(f"Unexpected error in CourseCreatorView: {str(e)}")
            # Send failure email notification for unexpected error
            try:
                user_email = User.objects.get(id=request.user.id).email
                topic = request.data.get('topic', 'AI Course')
                send_course_creation_failure_email(
                    user_email=user_email,
                    course_topic=topic,
                    error_message=f"Internal server error: {str(e)}",
                    user_id=request.user.id,
                    language=request.data.get('target_language', 'en'),
                    org_name=request.data.get('org', 'AI')
                )
                log.info(f"Sent course creation failure email to {user_email}")
            except Exception as email_error:
                log.error(f"Failed to send course creation failure email: {email_error}")
            
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

## AI Course List View
@view_auth_classes(is_authenticated=True)
class AICourseListView(APIView):
    """
    API endpoint for listing AI courses.
    """
    permission_classes = [IsAuthenticated]
    
    @schema(
        parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by status (pending, processing, success, failed)",
                type=openapi.TYPE_STRING,
                enum=['pending', 'processing', 'success', 'failed']
            ),
            openapi.Parameter(
                'action',
                openapi.IN_QUERY,
                description="Filter by action type (create_structure, create_content, update_structure)",
                type=openapi.TYPE_STRING,
                enum=['create_structure', 'create_content', 'update_structure']
            ),
            openapi.Parameter(
                'course_size',
                openapi.IN_QUERY,
                description="Filter by course size (small, medium, large, ai-generated)",
                type=openapi.TYPE_STRING,
                enum=['small', 'medium', 'large', 'ai-generated']
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Search in topic and instructions",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'ordering',
                openapi.IN_QUERY,
                description="Order by field (created_at, topic, status). Prefix with - for descending",
                type=openapi.TYPE_STRING,
                default='-created_at'
            )
        ],
        responses={
            200: openapi.Response(
                description="List of AI courses",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'courses': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                        'total': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            400: openapi.Response(description="Invalid request parameters"),
            500: openapi.Response(description="Server error"),
        }
    )
    def get(self, request):
        """
        List AI courses from external AICC API with server-side filtering.
        
        Query Parameters:
        - status: Filter by course status
        - action: Filter by action type
        - course_size: Filter by course size
        - search: Search in topic and instructions
        - ordering: Order by field, prefix with - for descending (default: -created_at)
        """
        try:
            API_KEY = settings.BLENDX_AICC_KEY
            API_URL = settings.BLENDX_AICC_APP_URL
            
            # Prepare headers for external API
            headers = {
                'accept': 'application/json',
                'X-API-Key': API_KEY,
            }
            
            # Fetch all courses from external API with limit=1000
            external_api_url = f"{API_URL}/api/v1/courses"
            params = {
                'limit': 1000,
                'offset': 0
            }
            
            log.info(f"Fetching all courses from external API: {external_api_url}")
            
            response = requests.get(
                external_api_url,
                headers=headers,
                params=params,
                timeout=60  # 1 minute timeout for listing
            )
            
            if response.status_code != 200:
                return Response(
                    response.json() if response.content else {},
                    status=response.status_code
                )
            
            # Parse response
            data = response.json()
            courses = data.get('courses', [])
            
            # Apply server-side filtering
            filtered_courses = courses
            
            # Filter by status
            status_filter = request.query_params.get('status')
            if status_filter:
                filtered_courses = [c for c in filtered_courses if c.get('status') == status_filter]
            
            # Filter by action
            action_filter = request.query_params.get('action')
            if action_filter:
                filtered_courses = [c for c in filtered_courses if c.get('action') == action_filter]
            
            # Filter by course_size
            course_size_filter = request.query_params.get('course_size')
            if course_size_filter:
                filtered_courses = [c for c in filtered_courses if c.get('course_size') == course_size_filter]
            
            # Search in topic and instructions
            search_query = request.query_params.get('search')
            if search_query:
                search_lower = search_query.lower()
                filtered_courses = [
                    c for c in filtered_courses 
                    if search_lower in c.get('topic', '').lower() 
                    or search_lower in c.get('instructions', '').lower()
                ]
            
            # Apply ordering
            ordering = request.query_params.get('ordering', '-created_at')
            reverse = ordering.startswith('-')
            order_field = ordering.lstrip('-')
            
            try:
                filtered_courses.sort(
                    key=lambda x: x.get(order_field, ''),
                    reverse=reverse
                )
            except Exception as e:
                log.warning(f"Could not sort by {order_field}: {e}")
            
            # Process each course to add attachment_count and rename created_at to created
            processed_courses = []
            for course in filtered_courses:
                # Create a copy of the course to avoid modifying the original
                processed_course = course.copy()
                
                # Add attachment_count based on attachment_path
                attachment_path = course.get('attachment_path', '')
                if attachment_path and attachment_path.strip():
                    # Count comma-separated values, filtering out empty strings
                    attachment_count = len([path.strip() for path in attachment_path.split(',') if path.strip()])
                else:
                    attachment_count = 0
                processed_course['attachment_count'] = attachment_count
                
                # Rename created_at to created
                if 'created_at' in processed_course:
                    processed_course['created'] = processed_course.pop('created_at')
                
                processed_courses.append(processed_course)
            
            # Build response matching original API format
            response_data = {
                'courses': processed_courses,
                'total': len(processed_courses)
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except requests.exceptions.Timeout:
            log.error("External API request timed out")
            return Response(
                {"error": "Request to external API timed out"},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except requests.exceptions.RequestException as e:
            log.error(f"Error calling external API: {str(e)}")
            return Response(
                {"error": f"Failed to connect to external API: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            log.error(f"Unexpected error in AICourseListView: {str(e)}")
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
## AI Course Detail View
@view_auth_classes(is_authenticated=True)
class AICourseDetailView(APIView):
    """
    API endpoint for getting an AI course detail from external AICC API.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get AI course detail from external AICC API"""
        try:
            # Get API key from settings
            
            API_KEY = settings.BLENDX_AICC_KEY
            API_URL = settings.BLENDX_AICC_APP_URL
            if not API_KEY:
                return Response(
                    {"error": "BLENDX_AICC_KEY not configured"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Make request to external AICC API
            external_url = f"{API_URL}/api/v1/courses/{course_id}"
            headers = {
                'accept': 'application/json',
                'X-API-Key': API_KEY
            }
            
            response = requests.get(external_url, headers=headers, timeout=30)
            
            # Return the response data directly
            if response.status_code == 200:
                return Response(
                data={
                    "course": response.json(),
                    "status": "success"
                },
                status=status.HTTP_200_OK
            )
            else:
                return Response(
                    {"error": f"External API returned status {response.status_code}", "detail": response.text},
                    status=response.status_code
                )
                
        except requests.exceptions.RequestException as e:
            log.error(f"Error calling external AICC API: {e}")
            return Response(
                {"error": "Failed to fetch course data from external API", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            log.error(f"Unexpected error in AICourseDetailView: {e}")
            return Response(
                {"error": "Internal server error", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
## Course Creator Task Status View
@view_auth_classes(is_authenticated=True)
class CourseCreatorTaskStatusView(APIView):
    """
    API endpoint for getting a course creator task status from external AICC API.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get course creator task status from external AICC API"""
        try:
            # Get API key and URL from settings
            API_KEY = settings.BLENDX_AICC_KEY
            API_URL = settings.BLENDX_AICC_APP_URL
            if not API_KEY:
                return Response(
                    {"error": "BLENDX_AICC_KEY not configured"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Make request to external AICC API
            external_url = f"{API_URL}/api/v1/courses/{course_id}"
            headers = {
                'accept': 'application/json',
                'X-API-Key': API_KEY
            }
            
            response = requests.get(external_url, headers=headers, timeout=30)
            
            # Return the response data directly
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": f"External API returned status {response.status_code}", "detail": response.text},
                    status=response.status_code
                )
                
        except requests.exceptions.RequestException as e:
            log.error(f"Error calling external AICC API: {e}")
            return Response(
                {"error": "Failed to fetch course creator task status from external API", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            log.error(f"Unexpected error in CourseCreatorTaskStatusView: {e}")
            return Response(
                {"error": "Internal server error", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )