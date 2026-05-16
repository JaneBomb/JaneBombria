from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/chat/<int:posting_id>/<int:inquirer_id>/", consumers.ChatConsumer.as_asgi()),
]
