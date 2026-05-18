from django.core.management.base import BaseCommand
from datetime import date, timedelta
from bookings.models import Movie, Seat
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Adds movies and seats to the database. Also create an admin"
    def handle(self, *args, **kwargs):
        '''
        Populates the movie and seat database
        Create an admin
        '''
        # Checks if data is already added
        # Prevents duplicate data in Render
        if not Movie.objects.filter(title="Toy Story").exists():
            Movie.objects.create(
                title="Toy Story", 
                description="A cowboy doll is profoundly jealous when a new spaceman action figure supplants him as the top toy in a boy's bedroom. When circumstances separate them from their owner, the duo have to put aside their differences to return to him.",
                release_date=date(1995, 11, 22),
                duration=timedelta(hours=1, minutes=21)
            )
            self.stdout.write(self.style.SUCCESS("Successfully added Toy Story!"))
        else:
            self.stdout.write("DUPLICATE")

        # TOY STORY 2
        if not Movie.objects.filter(title="Toy Story 2").exists():
            Movie.objects.create(
                title="Toy Story 2",
                description="When Woody is stolen by a toy collector, Buzz and his friends set out on a rescue mission to save Woody before he becomes a museum toy property with his roundup gang Jessie, Prospector, and Bullseye.",
                release_date=date(1999, 11, 24),
                duration=timedelta(hours=1, minutes=32)
            )
            self.stdout.write(self.style.SUCCESS("Successfully added Toy Story 2!"))
        else:
            self.stdout.write("DUPLICATE")

        # TOY STORY 3
        if not Movie.objects.filter(title="Toy Story 3").exists():
            Movie.objects.create(
                title="Toy Story 3",
                description="The toys are mistakenly delivered to a day-care center instead of the attic right before Andy leaves for college, and it's up to Woody to convince the other toys that they weren't abandoned and to return home.",
                release_date=date(2010, 6, 18),
                duration=timedelta(hours=1, minutes=43)
            )
            self.stdout.write(self.style.SUCCESS("Successfully added Toy Story 3!"))
        else:
            self.stdout.write("DUPLICATE")

        # TOY STORY 4
        if not Movie.objects.filter(title="Toy Story 4").exists():
            Movie.objects.create(
                title="Toy Story 4",
                description="When Woody, Buzz, and the gang join Bonnie on a road trip with her new craft project turned toy, Forky, the innocent little spork's antics launch Woody on a wild quest.",
                release_date=date(2019, 6, 21),
                duration=timedelta(hours=1, minutes=40)
            )
            self.stdout.write(self.style.SUCCESS("Successfully added Toy Story 4!"))
        else:
            self.stdout.write("DUPLICATE")

        # Checks if the Seat dataabse is empty or not
        # Prevents duplicate seats in Render
        if Seat.objects.count() == 0:
            # Populates the Seat database
            # Creates 32 seats
            for i in range(1, 33):
                Seat.objects.get_or_create(number=i, booking_status=True)
        else:
            self.stdout.write("ENOUGH SEATS")

        from django.contrib.auth import get_user_model

        # Creates an admin for Render
        User = get_user_model()

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="",
                password="jbombria"
            )
            self.stdout.write("ADMIN MADE")
        else:
            self.stdout.write("ADMIN ALREADY EXISTS")
        

        