from django.urls import path

from .views import UploadCourseView

urlpatterns = [
    path('import-course/', UploadCourseView.as_view(), name='upload_course'),
]