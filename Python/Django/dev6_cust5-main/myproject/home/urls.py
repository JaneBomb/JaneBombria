from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# Routers for API view
router = DefaultRouter()
router.register("", views.RoommatePostViewSet, basename="rm_post")

urlpatterns = [
    path("", views.roommate_list, name="roommate_list"),
    path("create/", views.roommate_create, name="roommate_create"),
    path("<int:post_id>/delete/", views.roommate_delete, name="roommate_delete"),
    path("<int:post_id>/close/", views.roommate_close, name="roommate_close"),
    path("api/", include(router.urls)),
    path("search/", views.search, name="search"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
