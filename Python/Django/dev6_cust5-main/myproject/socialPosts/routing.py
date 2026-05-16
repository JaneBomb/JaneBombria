"""
routing.py  — place this in your project root (same folder as urls.py)

Then in asgi.py, wrap your Django app with the ProtocolTypeRouter:

    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    import your_project.routing as ws_routing

    application = ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(ws_routing.websocket_urlpatterns)
        ),
    })
"""

from django.urls import re_path
from socialPosts.consumer import ListingFeedConsumer  # adjust to your app name

websocket_urlpatterns = [
    re_path(r"^ws/feed/$", ListingFeedConsumer.as_asgi()),
]
