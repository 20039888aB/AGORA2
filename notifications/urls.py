from django.urls import path, include
from rest_framework.routers import DefaultRouter

# We'll add views here when we implement them
router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
]
