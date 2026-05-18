from django.shortcuts import render, redirect
from django.http import JsonResponse
from .serializers import MovieSerializer, SeatSerializer, BookingSerializer
from .models import Movie, Seat, Booking
from rest_framework import viewsets
from datetime import date, timedelta

#----- Used for login functionality -----#
from rest_framework import permissions
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


# Create your views here.
#---------------------------- HTML VIEWS ----------------------------------#
# Display the 'home page'
def bookings_home(request):
    '''
    Displays correct html template based on request from URL
    "Home" page
    '''
    movies = Movie.objects.all()            # gets the reference to all movie objects in the database

    # Sends the appropriate context to the template for rendering
    return render(request, 'bookings/base.html', {'movies': movies})

# Display all the movies from the API
def movies_view(request):
    '''
    Displays correct html template based on request from URL
    Lists all movies
    '''
    movies = Movie.objects.all()            # gets the reference to all movie objects in the database

    # Sends the appropriate context to the template for rendering
    return render(request, 'bookings/movies.html', {'movies': movies})

# Display the booking page for a specific movie
def book_seat(request, title):
    '''
    Displays correct html template based on request from URL
    Will display unique data based on Movie title
    Booking page for specific movie
    '''
    movie = Movie.objects.get(title=title)      # gets info from object related to specific movie title
    selected_date = request.GET.get('date', date.today().isoformat())       # uses todays date (for convenience and ease)
    seats = Seat.objects.all()                  # gets referencet to all seat objects

    # Checks bookings for booked seats for specific movie and date
    booked_seats = Booking.objects.filter(
        movie=movie,                # Filters for specific Movie
        booking_date=selected_date  # Filters for specific date
    ).values_list('seat', flat=True)

    # Calculate prev/next dates on the server
    current = date.fromisoformat(selected_date)
    prev_date = (current - timedelta(days=1)).isoformat()
    next_date = (current + timedelta(days=1)).isoformat()

    # Sends the appropriate context to the template for rendering
    return render(request, 'bookings/book_seat.html', {
        'movie': movie,
        'seats': seats,
        'booked_seats': booked_seats,
        'selected_date': selected_date,
        'prev_date': prev_date,
        'next_date': next_date,
    })
    
# Only allows logged in users to confirm their booking
@login_required(login_url='login')
def confirm_booking(request, title, seat_id):
    '''
    Displays correct html template based on request from URL
    Confirm booking page
    '''
    movie = Movie.objects.get(title=title)          # gets info from movie object with specific movie name
    seat = Seat.objects.get(id=seat_id)             # gets info from seat object with specific number
    selected_date = request.GET.get('date', date.today().isoformat())

    # Used to create new entries for API (POST)
    # Creates a new booking object
    if request.method == 'POST':
        Booking.objects.create(
            movie=movie,
            seat=seat,
            user=request.user,
            booking_date=selected_date
        )
        return redirect('movies')

    # Sends the appropriate context to the template for rendering
    return render(request, 'bookings/confirm_booking.html', {
        'movie': movie,
        'seat': seat,
        'selected_date': selected_date,
    })    

# Displays the registration page for users
def register(request):
    '''
    Displays correct html template based on request from URL
    Registration page
    '''
    # Creates a new user for built in User model
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        User.objects.create_user(username=username, password=password)
        return redirect('login')
    
    # Sends the appropriate context to the template for rendering
    return render(request, 'bookings/register.html')

# Displays the login page for users
def login_view(request):
    '''
    Displays correct html template based on request from URL
    Login page
    '''
    # Fetches info from in-built User to find existing info
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('movies')
        else:
            return render(request, 'bookings/login.html', {'error': 'Invalid credentials'})

    # Sends the appropriate context to the template for rendering
    return render(request, 'bookings/login.html')

# Displays a prompt to log out of account
def logout_view(request):
    '''
    Displays correct html template based on request from URL
    Logout prompt
    '''
    logout(request)
    return redirect('login')

# Account View
# Only allows logged in users to see "Account Center"
@login_required(login_url='login')
def account(request):
    '''
    Displays correct html template based on request from URL
    Account Center
    Allows user to see all bookings in their account
    Includes redirect to logout prompt
    '''

    # Used for tab formatting in template
    tab = request.GET.get('tab', 'bookings')
    today = date.today()

    # Gets all the bookings from specific user
    current_bookings = Booking.objects.filter(
        user=request.user,
        booking_date__gte=today        # today or future
    )
    past_bookings = Booking.objects.filter(
        user=request.user,
        booking_date__lt=today         # before today
    )

    # Sends the appropriate context to the template for rendering
    return render(request, 'bookings/account.html', {
        'tab': tab,
        'current_bookings': current_bookings,
        'past_bookings': past_bookings,
    })
    
@login_required(login_url='login')
def cancel_booking(request, booking_id):
    '''
    Displays correct html template based on request from URL
    Prompt to cancel booking
    '''

    # Gets bookings from objects with specific username
    # Deletes booking from API
    booking = Booking.objects.get(id=booking_id)
    if booking.user == request.user:  # make sure users can only cancel their own bookings
        booking.delete()

    # Sends the appropriate context to the template for rendering
    return redirect('movies')

#---------------------------- APIS ----------------------------------#
class MovieViewSet(viewsets.ModelViewSet):
    '''
    Recieves all the movies objects. Calls the serializer.
    Displays the data in json format.
    Ensures only authenticated people (admin) can edit
    '''

    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class SeatViewSet(viewsets.ModelViewSet):
    '''
    Recieves all the seat objects. Calls the serializer.
    Displays the data in json format.
    Ensures only authenticated people (admin) can edit
    '''
    queryset = Seat.objects.all()
    serializer_class = SeatSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class BookingsViewSet(viewsets.ModelViewSet):
    '''
    Recieves all the booking objects for the user. Calls the serializer.
    Displays the data in json format.
    Ensures only authenticated people (admin) can edit
    '''
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    
    def perform_create(self, serializer):
        '''
        Ensures only the logged in user can create a bookings
        '''
        serializer.save(user=self.request.user)
        
    def get_queryset(self):
        '''
        Returns bookings under a specific user
        '''
        return Booking.objects.filter(user=self.request.user)
        