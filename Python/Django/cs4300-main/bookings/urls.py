from django.urls import include, path
from . import views
from rest_framework.routers import DefaultRouter                # for API viewsets

from rest_framework.authtoken.views import obtain_auth_token            # for login authentication

# Routers for API view
router = DefaultRouter()
router.register('movies', views.MovieViewSet, basename='movies')
router.register('seats', views.SeatViewSet, basename='seats')
router.register('bookings', views.BookingsViewSet, basename='bookings')

# creates an URL for bookings
urlpatterns = [
    # Frontend URLs
    path('bookings/', views.bookings_home, name='bookings'),
    path('movies/', views.movies_view, name='movies'),
    path('book/<str:title>/', views.book_seat, name='book_seat'),
    path('book/<str:title>/<int:seat_id>/confirm/', views.confirm_booking, name='confirmation'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    
    # Account URLs
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', views.account, name='account'),
    
    # API URLs
    path('api/', include(router.urls)),
]