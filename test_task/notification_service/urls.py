from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, UserContactViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'contacts', UserContactViewSet, basename='contact')

urlpatterns = [
    path('', include(router.urls)),
]