"""
URLs for blendxcoursecreator.
"""
import os
from django.urls import re_path, include , path # pylint: disable=unused-import
from .hello import urls as hello_urls
from django.conf import settings
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import permissions

class SchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super(SchemaGenerator, self).get_schema(request, public)
        schema.basePath = os.path.join(schema.basePath, 'blendxcoursecreator/')
        return schema
schema_view = get_schema_view(
    openapi.Info(
        title="BlendxCourseCreator",
        default_version='v1',
        description="API documentation for blendxcoursecreator",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    urlconf='blendxcoursecreator.urls',
    generator_class=SchemaGenerator,
)
    
urlpatterns = []

if settings.DEBUG:
    urlpatterns += [
        re_path(r'^docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
        re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0)),
    ]

urlpatterns += [
    path("hello/", include(hello_urls)),
]
