import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from home.models import RoommatePost
from socialPosts.serializers import serialize_listing

FEED_GROUP = "listing_feed"


class ListingFeedConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.channel_layer.group_add(FEED_GROUP, self.channel_name)
        await self.accept()
        listings = await self.get_recent_listings()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "initial_listings",
                    "listings": listings,
                }
            )
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(FEED_GROUP, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def listing_created(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "new_listing",
                    "listing": event["listing"],
                }
            )
        )

    @database_sync_to_async
    def get_recent_listings(self, limit=20):
        qs = RoommatePost.objects.select_related("user").filter(status="open").order_by("-date")[:limit]
        return [serialize_listing(lst) for lst in qs]
