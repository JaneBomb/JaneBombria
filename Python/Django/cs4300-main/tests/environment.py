import os
import sys
import django
from django.test.utils import setup_test_environment

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "move_theater_booking.settings")

django.setup()
setup_test_environment()

def before_scenario(context, scenario):
    from django.contrib.auth.models import User
    User.objects.all().delete()
    from django.core.management import call_command
    from datetime import date, timedelta
    from bookings.models import Movie, Seat

    call_command("migrate", "--run-syncdb", verbosity=0)

    # Initialize movies
    if not Movie.objects.filter(title="Toy Story").exists():
        Movie.objects.create(
            title="Toy Story",
            description="A cowboy doll is profoundly jealous when a new spaceman action figure supplants him as the top toy in a boy's bedroom. When circumstances separate them from their owner, the duo have to put aside their differences to return to him.",
            release_date=date(1995, 11, 22),
            duration=timedelta(hours=1, minutes=21)
        )

    # Initialize seats
    if Seat.objects.count() == 0:
        for i in range(1, 33):
            Seat.objects.get_or_create(number=i, booking_status=True)