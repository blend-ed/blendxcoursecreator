from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from drf_yasg import openapi

from edx_api_doc_tools import schema
from openedx.core.lib.api.view_utils import view_auth_classes

import logging
import os
from django.conf import settings
from django.contrib.auth.models import User
import json
from .utils import import_course_from_path

log = logging.getLogger(__name__)
from django.conf import settings


@view_auth_classes(is_authenticated=False)
class UploadCourseView(APIView):
    """
    Webhook endpoint to receive a .tar.gz course export and import it.

    Expected multipart field name: "file". Filename should follow
    pattern: <org>_<something>_<number>_<run>.tar.gz
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @schema(
        responses={
            200: openapi.Response(
                description="Course imported successfully",
            ),
            400: openapi.Response(description="Bad request"),
            500: openapi.Response(description="Server error"),
        },
    )
    def post(self, request):
        """
        Receive .tar.gz file and import as a course, or handle webhook test JSON.
        """
        # api_key for blendx_ai_cc
        BLENDX_AICC_KEY = settings.BLENDX_AICC_KEY

        try:
            # Handle pure JSON test webhook: event=webhook.test
            content_type = request.META.get("CONTENT_TYPE", "")
            if "application/json" in content_type:
                body_data = request.data if hasattr(request, 'data') else None
                if not body_data:
                    try:
                        body_data = json.loads(request.body.decode("utf-8")) if request.body else {}
                    except Exception:
                        body_data = {}

                event = body_data.get("event")
                data_node = body_data.get("data", {})
                incoming_api_key = data_node.get("api_key") or body_data.get("api_key")
                if event == "webhook.test":
                    if not BLENDX_AICC_KEY or incoming_api_key != BLENDX_AICC_KEY:
                        return Response(status=status.HTTP_401_UNAUTHORIZED, data={"error": "Invalid API key"})
                    return Response(status=status.HTTP_200_OK, data={"status": "ok", "message": "Webhook test successful"})

            # Multipart path: expect payload JSON + course_file
            payload_str = request.data.get("payload")
            if not payload_str:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "Missing 'payload'"})
            try:
                payload = json.loads(payload_str)
            except Exception:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "Invalid 'payload' JSON"})

            data_node = payload.get("data", {})
            incoming_api_key = data_node.get("api_key") or payload.get("api_key")
            if not BLENDX_AICC_KEY or incoming_api_key != BLENDX_AICC_KEY:
                return Response(status=status.HTTP_401_UNAUTHORIZED, data={"error": "Invalid API key"})

            uploaded = request.FILES.get("course_file") or request.FILES.get("file")
            user_email = data_node.get("user_email") or request.data.get("user_email")
            course_key = data_node.get("course_key")

            if not uploaded:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "Missing 'course_file'"})
            if not user_email or not course_key:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "Missing required fields in payload: user_email, course_key"})

            # Parse course_key to extract org, number, and run
            # Expected format: course-v1:{org}+{number}+{run}
            try:
                if not course_key.startswith("course-v1:"):
                    return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "Invalid course_key format. Expected: course-v1:{org}+{number}+{run}"})
                
                course_key_parts = course_key.replace("course-v1:", "").split("+")
                if len(course_key_parts) != 3:
                    return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "Invalid course_key format. Expected: course-v1:{org}+{number}+{run}"})
                
                org, number, run = course_key_parts
            except Exception as e:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": f"Failed to parse course_key: {str(e)}"})

            filename = getattr(uploaded, "name", None) or "uploaded.tar.gz"
            if not filename.endswith(".tar.gz"):
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "File must be a .tar.gz"})

            exports_dir = "course_exports"
            os.makedirs(exports_dir, exist_ok=True)
            output_path = os.path.join(exports_dir, filename)

            with open(output_path, "wb") as destination:
                for chunk in uploaded.chunks():
                    destination.write(chunk)

            # Defer heavy imports to runtime to avoid module cost if endpoint unused
            from cms.djangoapps.contentstore.views.course import create_new_course

            # Resolve user from email
            try:
                user = User.objects.get(email=str(user_email))
            except User.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": f"No user found with email: {user_email}"})
            except User.MultipleObjectsReturned:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": f"Multiple users found with email: {user_email}. Provide a unique email."})

            created_course = create_new_course(
                user=user,
                org=str(org),
                number=str(number),
                run=str(run),
                fields={},
            )

            log.info(f"Created course: %s", created_course)

            course_key = f"course-v1:{org}+{number}+{run}"
            import_course_from_path(int(user.id), course_key, output_path, 'en')

            course_url = f"{settings.LMS_ROOT_URL}/courses/{course_key}/course/"

            return Response(
                status=status.HTTP_200_OK,
                data={
                    "course_url": course_url,
                    "course_key": course_key,
                },
            )

        except Exception as e:
            log.error(f"Error occurred while importing course: {e}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={"error": "Internal server error"})