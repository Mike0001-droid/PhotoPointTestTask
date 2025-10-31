from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import UserContact, DeliveryTracker, VerificationCode
from .producers import notification_producer
from .serializers import (
    UserContactSerializer, 
    DeliveryTrackerSerializer,
    DeliveryTrackerListSerializer,
    DeliveryStatusSerializer
)
from .services import NotificationDeliveryService


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def send(self, request):
        title = request.data.get('title')
        message = request.data.get('message')
        channel = request.data.get('channel')
        if not title or not message:
            return Response(
                {'error': 'Title and message required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if channel:
            contact_exists = UserContact.objects.filter(
                user=request.user,
                channel=channel,
                is_verified=True
            ).exists()
            
            if not contact_exists:
                return Response(
                    {'error': f'No verified {channel} contact found'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        message_id = notification_producer.send_notification(
            user_id=request.user.id,
            title=title,
            message=message,
            preferred_channel=channel
        )
        
        if message_id:
            return Response({'message_id': message_id})
        else:
            return Response(
                {'error': 'Send failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def channels(self, request):
        contacts = UserContact.objects.filter(
            user=request.user, 
            is_verified=True
        ).order_by('-is_primary')
        channels = []
        for contact in contacts:
            channels.append({
                'channel': contact.channel,
                'value': contact.value,
                'is_primary': contact.is_primary
            })
        
        return Response({'channels': channels})
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        serializer = DeliveryStatusSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        message_id = serializer.validated_data.get('message_id')
        if message_id:
            try:
                tracker = DeliveryTracker.objects.get(
                    message_id=message_id,
                    user_id=request.user.id
                )
                serializer = DeliveryTrackerSerializer(tracker)
                return Response(serializer.data)
                
            except DeliveryTracker.DoesNotExist:
                return Response({'error': 'Delivery not found'}, status=404)
        else:
            trackers = DeliveryTracker.objects.filter(
                user_id=request.user.id
            ).order_by('-created_at')[:50]
            
            serializer = DeliveryTrackerListSerializer(trackers, many=True)
            return Response({'deliveries': serializer.data})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        user_trackers = DeliveryTracker.objects.filter(user_id=request.user.id)
        stats = {
            'total': user_trackers.count(),
            'delivered': user_trackers.filter(status='delivered').count(),
            'failed': user_trackers.filter(status='failed').count(),
            'pending': user_trackers.filter(status='pending').count(),
            'retrying': user_trackers.filter(status='retrying').count(),
            'by_channel': {},
            'recent_activity': []
        }
        for channel in DeliveryTracker._meta.get_field('channel').choices:
            channel_name = channel[0]
            channel_trackers = user_trackers.filter(channel=channel_name)
            stats['by_channel'][channel_name] = {
                'total': channel_trackers.count(),
                'delivered': channel_trackers.filter(status='delivered').count(),
                'failed': channel_trackers.filter(status='failed').count(),
                'success_rate': round(
                    (channel_trackers.filter(status='delivered').count() / 
                     max(channel_trackers.count(), 1)) * 100, 2
                )
            }
        recent_trackers = user_trackers.order_by('-created_at')[:10]
        stats['recent_activity'] = DeliveryTrackerListSerializer(
            recent_trackers, many=True
        ).data
        
        return Response(stats)


class UserContactViewSet(viewsets.ModelViewSet):
    serializer_class = UserContactSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserContact.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_verified=False)
    
    @action(detail=True, methods=['post'])
    def send_verification(self, request, pk=None):
        contact = self.get_object()
        
        recent_codes = VerificationCode.objects.filter(
            user_contact=contact,
            created_at__gte=timezone.now() - timedelta(minutes=1)
        ).count()
        
        if recent_codes > 0:
            return Response(
                {'error': 'Verification code already sent recently. Please wait 1 minute.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        delivery_service = NotificationDeliveryService()
        success, result = delivery_service.send_verification_code(contact)
        
        if success:
            return Response({
                'message': 'Verification code sent',
                'verification_id': result,
                'channel': contact.channel
            })
        else:
            return Response(
                {'error': f'Failed to send verification code: {result}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        contact = self.get_object()
        code = request.data.get('code')
        
        if not code:
            return Response(
                {'error': 'Verification code required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        delivery_service = NotificationDeliveryService()
        success, message = delivery_service.verify_contact(contact, code)
        if success:
            serializer = UserContactSerializer(contact)
            return Response({
                'message': message,
                'contact': serializer.data
            })
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        contact = self.get_object()
        
        if not contact.is_verified:
            return Response(
                {'error': 'Only verified contacts can be set as primary'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        UserContact.objects.filter(
            user=request.user,
            channel=contact.channel
        ).update(is_primary=False)
        contact.is_primary = True
        contact.save()
        serializer = UserContactSerializer(contact)
        return Response({
            'message': f'Contact set as primary for {contact.channel}',
            'contact': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        contacts = UserContact.objects.filter(user=request.user)
        stats = {
            'total': contacts.count(),
            'verified': contacts.filter(is_verified=True).count(),
            'primary': contacts.filter(is_primary=True).count(),
            'by_channel': {}
        }
        
        for channel in UserContact._meta.get_field('channel').choices:
            channel_name = channel[0]
            channel_contacts = contacts.filter(channel=channel_name)
            stats['by_channel'][channel_name] = {
                'total': channel_contacts.count(),
                'verified': channel_contacts.filter(is_verified=True).count(),
                'primary': channel_contacts.filter(is_primary=True).count(),
            }
        
        return Response(stats)