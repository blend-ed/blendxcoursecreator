from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from drf_yasg import openapi

from edx_api_doc_tools import schema
from openedx.core.lib.api.view_utils import view_auth_classes

import logging

log = logging.getLogger(__name__)

@view_auth_classes(is_authenticated=True)
class HelloView(APIView):
    """
    Test view for checking if the API is working.
    """
    @schema(
        responses={
            200: openapi.Response(
                description="API is working",
            ),
            500: openapi.Response(
                description="API is not working",
            ),
        }
    )
    def get(self, request):
        """
        Test view for checking if the API is working.
        """
        try:

            return Response(status=status.HTTP_200_OK, data={"message": "API is working"})

            
        except Exception as e:
            log.error(f"Error occurred while checking if the API is working: {e}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)