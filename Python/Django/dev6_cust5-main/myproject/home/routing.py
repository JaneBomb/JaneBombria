from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/ai-agent/", consumers.AIListingAgentConsumer.as_asgi()),
]
