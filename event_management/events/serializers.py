from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Event, Review, Booking, Query

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class EventSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(source='get_average_rating', read_only=True)
    
    class Meta:
        model = Event
        fields = ('id', 'name', 'description', 'date', 'location', 
                 'capacity', 'available_seats', 'price', 'average_rating')

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = ('id', 'user', 'event', 'content', 'rating', 'created_at')
        read_only_fields = ('created_at',)

class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    event = EventSerializer(read_only=True)
    
    class Meta:
        model = Booking
        fields = ('id', 'user', 'event', 'booking_date', 'notes', 'status')
        read_only_fields = ('booking_date',)

class QuerySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Query
        fields = ('id', 'user', 'content', 'response', 'created_at')
        read_only_fields = ('created_at',)
