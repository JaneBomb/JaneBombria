import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from home.models import RoommatePost

from .filters import filter_message
from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.posting_id = self.scope["url_route"]["kwargs"]["posting_id"]

        # Fix: convert inquirer_id once at connect, catch malformed values early
        try:
            self.inquirer_id = int(self.scope["url_route"]["kwargs"]["inquirer_id"])
        except (ValueError, TypeError):
            await self.close(code=4003)
            return

        self.room_group = f"chat_posting_{self.posting_id}_inquirer_{self.inquirer_id}"

        # Fix 1: Reject unauthenticated connections
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4003)
            return

        # Fix 2: Reject users who are not the posting owner or the designated inquirer
        if not await self.user_can_access(user):
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()
        history = await self.get_history()
        for msg in history:
            await self.send(text_data=json.dumps(msg))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        raw_message = data["message"]
        clean_message = filter_message(raw_message)

        user = self.scope["user"]

        # Fix: defensive auth check in case connect() guard ever changes
        if not user.is_authenticated:
            return

        sender_name = user.username

        await self.save_message(user, clean_message)
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat_message",
                "message": clean_message,
                "sender": sender_name,
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "sender": event["sender"],
                }
            )
        )

    @database_sync_to_async
    def user_can_access(self, user):
        """
        Allow access if the user owns the posting or is the designated inquirer.
        inquirer_id is already cast to int in connect().
        """
        is_owner = RoommatePost.objects.filter(id=self.posting_id, user=user).exists()
        is_inquirer = user.id == self.inquirer_id
        return is_owner or is_inquirer

    @database_sync_to_async
    def save_message(self, user, content):
        # Record inquirer_id so conversations remain scoped per inquirer
        Message.objects.create(
            posting_id=self.posting_id,
            inquirer_id=self.inquirer_id,
            sender=user,
            sender_label=user.username,
            content=content,
        )

    @database_sync_to_async
    def get_history(self):
        # Filter by both IDs, order chronologically, fetch only needed fields
        messages = (
            Message.objects.filter(posting_id=self.posting_id, inquirer_id=self.inquirer_id)
            .order_by("timestamp")
            .values("content", "sender_label")
        )
        return [{"message": m["content"], "sender": m["sender_label"]} for m in messages]
