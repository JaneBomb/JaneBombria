"""
AI Listing Agent WebSocket Consumer
===================================
Handles the conversational chat-with-listings feature.

Flow:
    1. Browser opens ws://.../ws/ai-agent/?city=...&state=...&...
    2. connect() authenticates, seeds conversation history with the
       initial listings + filters, sends the assistant greeting.
    3. Each user message arrives via receive(). We append it to
       history and call ai_listing_agent.chat_turn().
    4. chat_turn() may call refine_search, which invokes our
       _refine_callback -> build_enriched_listings. If that happens,
       we send a 'listings_updated' event so the map redraws.
    5. We send the assistant's reply as an 'assistant_message' event.

State is held in-memory on `self`, per connection. Reload = new chat.
Anonymous users are rejected in connect() to prevent burning OpenAI
credits on unauthenticated traffic.
"""

import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from . import ai_listing_agent
from .models import SearchHistory

logger = logging.getLogger(__name__)


class AIListingAgentConsumer(AsyncWebsocketConsumer):
    """
    One WebSocket per browser tab. All conversation state (history,
    current filters, current listings) lives on the instance.
    """

    async def connect(self):
        # Auth gate: anonymous users never reach the LLM.
        user = self.scope.get("user")
        if not (user and user.is_authenticated):
            await self.close(code=4401)
            return

        self.user = user

        # Parse starting filters from the querystring (same shape as
        # the /ai-agent/ HTTP endpoint).
        qs = parse_qs((self.scope.get("query_string") or b"").decode())

        def _first(k, default=""):
            vals = qs.get(k, [])
            return vals[0].strip() if vals else default

        self.filters = {
            "city": _first("city").title(),
            "state": _first("state").upper(),
            "listing_type": _first("intent"),
            "property_type": _first("type"),
            "budget": _first("budget"),
            "amenity": _first("amenity"),
            "keyword": _first("keyword"),
        }

        if not (self.filters["city"] and self.filters["state"]):
            await self.accept()
            await self._send_error("Please run a property search before opening the chat.")
            await self.close(code=4400)
            return

        await self.accept()

        # Initial listing fetch + conversation seed. Both hit the DB
        # and/or network, so run off the event loop.
        self.listings = await self._fetch_listings(self.filters)
        self.history = ai_listing_agent.build_initial_history(self.filters, self.listings)

        await self._send(
            {
                "type": "ready",
                "greeting": self.history[-1]["content"],
                "notice": ai_listing_agent.LANGUAGE_NOTICE,
                "listings": self.listings,
                "filters": self.filters,
            }
        )

    async def disconnect(self, close_code):
        # No cleanup needed — in-memory state is garbage-collected.
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self._send_error("Could not parse your message.")
            return

        msg_type = data.get("type")
        if msg_type != "user_message":
            await self._send_error(f"Unknown message type: {msg_type!r}")
            return

        user_text = (data.get("text") or "").strip()
        if not user_text:
            return
        if len(user_text) > 2000:
            user_text = user_text[:2000]

        await self._send({"type": "user_message", "text": user_text})

        # Guardrails
        guard = ai_listing_agent.check_message_guardrails(user_text)
        if not guard["ok"]:
            logger.info(
                "Chat guardrail blocked message (reason=%s, user=%s)",
                guard.get("reason"),
                getattr(self.user, "username", "?"),
            )
            await self._send(
                {
                    "type": "system_message",
                    "text": guard["reply"],
                    "reason": guard.get("reason", ""),
                }
            )
            return

        self.history.append({"role": "user", "content": user_text})
        await self._send({"type": "thinking"})

        result = await self._run_chat_turn()

        if not result["ok"]:
            await self._send_error(result.get("error") or "AI chat failed.")
            return

        # If refine_search ran, push new listings before the assistant reply so the map redraws just ahead of the text.
        if result.get("refined"):
            await self._send(
                {
                    "type": "listings_updated",
                    "listings": self.listings,
                    "filters": self.filters,
                }
            )
            await self._log_search(self.filters, len(self.listings))

        await self._send(
            {
                "type": "assistant_message",
                "text": result["reply"],
            }
        )

    # ---------- helpers ------------------------------------------------

    async def _send(self, payload):
        await self.send(text_data=json.dumps(payload, default=str))

    async def _send_error(self, message):
        await self._send({"type": "error", "error": str(message)})

    @database_sync_to_async
    def _fetch_listings(self, filters):
        # Imported lazily to avoid circular imports at module load.
        from .views import build_enriched_listings

        try:
            return build_enriched_listings(
                filters.get("city", ""),
                filters.get("state", ""),
                filters.get("listing_type", ""),
                filters.get("property_type", ""),
                filters.get("budget", ""),
                filters.get("amenity", ""),
                filters.get("keyword", ""),
            )
        except Exception:
            logger.exception("build_enriched_listings failed")
            return []

    @database_sync_to_async
    def _log_search(self, filters, result_count):
        try:
            SearchHistory.objects.create(
                user=self.user,
                session_key="",
                city=filters.get("city", ""),
                state=filters.get("state", ""),
                listing_type=filters.get("listing_type", ""),
                property_type=filters.get("property_type", ""),
                budget=filters.get("budget", ""),
                amenity_filter=filters.get("amenity", ""),
                sort_by="",
                keyword=filters.get("keyword", ""),
                result_count=result_count,
            )
        except Exception:
            logger.exception("Failed to log refined search")

    @database_sync_to_async
    def _run_chat_turn(self):
        """
        The OpenAI call is blocking, and refine_callback hits DB /
        RentCast, so we run the whole turn in a worker thread.
        """

        def refine(new_filters):
            from .views import build_enriched_listings

            return build_enriched_listings(
                new_filters.get("city", ""),
                new_filters.get("state", ""),
                new_filters.get("listing_type", ""),
                new_filters.get("property_type", ""),
                new_filters.get("budget", ""),
                new_filters.get("amenity", ""),
                new_filters.get("keyword", ""),
            )

        return ai_listing_agent.chat_turn(
            self.history,
            self.filters,
            self.listings,
            refine,
        )
