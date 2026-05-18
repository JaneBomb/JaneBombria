from django.test import TestCase
from datetime import date
from bookings.models import Booking, Movie, Seat
from django.urls import reverse
from datetime import date, timedelta

from django.contrib.auth.models import User
from rest_framework import status

# Create your tests here.
#-------- INTEGRATION TESTS ------------#
class IntegrationTestCase(TestCase):
    def setUp(self):
        '''
        Creates objects in the API(s) for testing
        Temporary objects
        '''
        self.user1 = User.objects.create_user(username='Alice', password='test')
        self.user2 = User.objects.create_user(username='Bob', password='test')
        self.movie1 = Movie.objects.create(title='Movie1', description='Test movie', release_date=date(2000, 1, 1), duration=timedelta(hours=1, minutes=30))
        self.seat = Seat.objects.create(number=1, booking_status=True)

        Booking.objects.create(movie=self.movie1, seat=self.seat, user=self.user1, booking_date=date(2026, 1, 1))
        Booking.objects.create(movie=self.movie1, seat=self.seat, user=self.user1, booking_date=date(2027, 2, 14))
        Booking.objects.create(movie=self.movie1, seat=self.seat, user=self.user2, booking_date=date(2026, 1, 1))

    def test_user_booking_endpoint_only_retrieves_authenticated_user_bookings(self):
        '''
        Tests to see if the correct bookings are shown based on username/user
        '''
        #user = User.objects.get(username='Alice')               #Change string based on user checking
        self.client.force_login(self.user1)
        response = self.client.get(
            reverse('bookings-list'),
            {'user': self.user1.id}
        )

        assert response.status_code == status.HTTP_200_OK
        bookings = response.json()
        self.assertTrue(all(booking['user'] == self.user1.id for booking in bookings) )

    def test_user_booking_unauthenticated_user(self):
        '''
        If there is no authenticated user (logged in user)
        Tests if the 401 (unauthorized) status is used, when there is no authenticated user
        Ensures only users can see their OWN bookings
        '''
        response = self.client.get(
            reverse('bookings-list'),
            {'user': self.user1.id}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)