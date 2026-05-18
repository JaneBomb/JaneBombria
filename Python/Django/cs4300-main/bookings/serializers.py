from rest_framework import serializers
from .models import Movie, Seat, Booking

# Movie serializer
class MovieSerializer(serializers.ModelSerializer):
    '''
    Transforms data types from Django to json, so they appear on webpage/server.
    '''
    class Meta:
        model = Movie
        
        # Specific fields from movie model being displayed on server
        fields = (
            'title',
            'description',
            'release_date',
            'duration',
        )

# Seat serializer
class SeatSerializer(serializers.ModelSerializer):
    '''
    Transforms data types from Django to json, so they appear on webpage/server.
    '''
    class Meta:
        model = Seat
        
        # Specific fields from seat to display on server
        fields = (
            'number',
            'booking_status',
        )


# Bookings serializer
class BookingSerializer(serializers.ModelSerializer):
    '''
    Transforms data types from Django to json, so they appear on webpage/server.
    '''

    class Meta:
        model = Booking
            
        # Specific fields from seat to display on server
        fields = (
            'movie',
            'seat',
            'user',
            'booking_date'
        )
        read_only_fields = ['user']