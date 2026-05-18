from django.test import TestCase
from datetime import date
from bookings.models import Booking, Movie, Seat
from django.urls import reverse
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Create your tests here.
#-------- UNIT TESTS --------#
class UnitTestCases(TestCase):
    def setUp(self):
        '''
        Creates objects to test for correct info
        '''
        self.test_movie = Movie.objects.create(title="A Movie", description='Placeholder', release_date=date(2000, 1, 1), duration=timedelta(hours=1, minutes=30))
        self.test_seat = Seat.objects.create(number=1, booking_status=True)
        self.test_user = User.objects.create_user(username='user1', password='test')
        self.test_booking = Booking.objects.create(movie=self.test_movie, seat=self.test_seat, user=self.test_user, booking_date=date(2026, 1, 1))

        #def test_correct

    def test_seat_availability(self):
        '''
        Tests if changing the booking status of a seat works
        '''
        self.assertTrue(self.test_seat.booking_status)

        self.test_seat.booking_status = False
        self.test_seat.save()
        self.assertFalse(self.test_seat.booking_status)

    def test_view_prevents_double_booking(self):
        '''
        Based off the booking pagg:
        Tests to see if double booking the same seat for the same movie and date stops the user
        '''
        self.client.login(username="user2", password="testpass")

        url = reverse("confirmation", args=[self.test_movie.title, self.test_seat.id])
        response = self.client.get(url + "?date=2026-01-01")

        # Expect the view to reject the booking and redirect
        self.assertEqual(response.status_code, 302)

        # Ensure no second booking was created
        count = Booking.objects.filter(
            movie=self.test_movie,
            seat=self.test_seat,
            booking_date=date(2026, 1, 1)
        ).count()

        self.assertEqual(count, 1)
