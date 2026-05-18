from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# Movie model
'''
Includes:
Title: String
Description: String
Release Date: Date type [date(YYYY, MM, DD)]
Duration: Duration type (hours=x minutes=x)
'''
class Movie(models.Model):
    title = models.CharField(max_length = 50)       # 50 characters for movie title
    description = models.CharField(max_length = 300)    # Description have 300 character limit
    release_date = models.DateField()    # Format: date(YYYY, MM, DD)
    duration = models.DurationField()    # Format: deltatime(hours=x, minutes=x)


# Seat Model
'''
Includes:
Seat number: positive interger
Booking Status: boolean (for taken or not)
'''
class Seat(models.Model):
    number = models.PositiveIntegerField(unique=True)      # Positive integers for seat numbers
    booking_status = models.BooleanField(default=True)      # Bool for if seat is free (True = Free, False = Taken)
    

# Booking Model
'''
Includes:
Movie title: string
Seat: positive integer
User: foreign key ()
Booking data: Date type [date(YYYY/mm/dd)]
'''
class Booking(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    booking_date = models.DateField()    # Format: date(YYYY/mm/dd))