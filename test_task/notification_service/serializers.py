from rest_framework import serializers
from .models import UserContact, DeliveryTracker


class UserContactSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    
    class Meta:
        model = UserContact
        fields = [
            'id', 'channel', 'channel_display', 'value', 
            'is_primary', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        user = self.context['request'].user
        channel = data.get('channel')
        value = data.get('value')
        
        if UserContact.objects.filter(
            user=user, 
            channel=channel, 
            value=value
        ).exists():
            raise serializers.ValidationError(
                f'Contact with {channel} and value {value} already exists'
            )
        return data
    

class DeliveryTrackerSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DeliveryTracker
        fields = [
            'id', 'message_id', 'user_id', 'channel', 'channel_display',
            'status', 'status_display', 'contact_info', 'attempt_count',
            'last_error', 'created_at', 'delivered_at'
        ]
        read_only_fields = ['id', 'created_at']


class DeliveryTrackerListSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DeliveryTracker
        fields = [
            'message_id', 'channel', 'channel_display', 'status', 
            'status_display', 'attempt_count', 'created_at', 'delivered_at'
        ]


class DeliveryStatusSerializer(serializers.Serializer):
    message_id = serializers.UUIDField(required=False)
    
    def validate_message_id(self, value):
        from .models import DeliveryTracker
        if value and not DeliveryTracker.objects.filter(message_id=value).exists():
            raise serializers.ValidationError("Delivery not found")
        return value