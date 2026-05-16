from django.urls import path

from . import views

urlpatterns = [
    path("<int:posting_id>/<int:inquirer_id>/", views.chat_room, name="chat_room"),
    path("inbox/", views.inbox, name="chat_inbox"),
]
