from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CertificateTemplateViewSet, CertificateViewSet, CertificateVerificationViewSet,
    CertificateBatchViewSet, CertificatePublicViewSet
)
from . import views

app_name = 'certificates'

router = DefaultRouter()
router.register(r'templates', CertificateTemplateViewSet, basename='certificate-template')
router.register(r'certificates', CertificateViewSet, basename='certificate')
router.register(r'verifications', CertificateVerificationViewSet, basename='certificate-verification')
router.register(r'batches', CertificateBatchViewSet, basename='certificate-batch')

urlpatterns = [
    path('', include(router.urls)),
    path('course/<uuid:course_id>/', views.course_certificate, name='course_certificate'),
    path('public/verify/<str:verification_code>/', CertificatePublicViewSet.as_view({'get': 'verify'}), name='certificate-public-verify'),
]
