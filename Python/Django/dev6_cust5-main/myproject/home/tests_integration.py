import json
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from home.ai_listing_agent import build_initial_history, chat_turn
from home.models import Property, RoommatePost

MOCK_API_RESULT = [
    {
        "id": "p1",
        "formattedAddress": "100 Elm St, Boulder, CO",
        "city": "Boulder",
        "state": "CO",
        "price": 900,
        "latitude": 40.01,
        "longitude": -105.27,
        "propertyType": "Apartment",
        "bedrooms": 2,
        "bathrooms": 1,
        "squareFootage": 700,
    }
]


# Auth Flow
class AuthFlowIntegrationTest(TestCase):
    """Full register -> login -> logout flow."""

    def test_register_then_login_flow(self):
        self.client.post(
            "/register/",
            {
                "username": "flowuser",
                "password1": "StrongPassword@123",
                "password2": "StrongPassword@123",
            },
        )
        self.assertTrue(User.objects.filter(username="flowuser").exists())

        response = self.client.post(
            "/",
            {
                "username": "flowuser",
                "password": "StrongPassword@123",
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_invalid_login_stays_on_page(self):
        response = self.client.post(
            "/",
            {
                "username": "nobody",
                "password": "wrongpass",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username="existing", password="pass")
        self.client.post(
            "/register/",
            {
                "username": "existing",
                "password1": "StrongPassword@123",
                "password2": "StrongPassword@123",
            },
        )
        self.assertEqual(User.objects.filter(username="existing").count(), 1)


# Roommate Post Flow
class RoommatePostFlowIntegrationTest(TestCase):
    """Full create -> view -> close -> delete flow."""

    def setUp(self):
        self.user = User.objects.create_user(username="poster", password="Password123!")
        self.other = User.objects.create_user(username="other", password="Password123!")
        self.client.login(username="poster", password="Password123!")

    def _create_post(self):
        return RoommatePost.objects.create(
            user=self.user,
            message="Need a roommate ASAP.",
            date="2026-03-11",
            status="open",
            rent=950,
            property_type="apartment",
        )

    def test_create_then_view_post(self):
        self.client.post(
            "/roommate-posts/create/",
            {
                "message": "Need a roommate ASAP.",
                "date": "2026-03-11",
                "status": "open",
                "rent": 950,
                "property_type": "apartment",
            },
        )
        response = self.client.get("/roommate-posts/")
        self.assertContains(response, "Need a roommate ASAP.")

    def test_create_then_close_then_status_shows_closed(self):
        post = self._create_post()
        self.client.post(f"/roommate-posts/{post.id}/close/")
        post.refresh_from_db()
        self.assertEqual(post.status, "closed")
        response = self.client.get("/roommate-posts/")
        self.assertContains(response, "Closed")

    def test_create_then_delete_removes_from_list(self):
        post = self._create_post()
        self.client.post(f"/roommate-posts/{post.id}/delete/")
        response = self.client.get("/roommate-posts/")
        self.assertNotContains(response, "Need a roommate ASAP.")

    def test_unauthenticated_create_redirects_to_login(self):
        self.client.logout()
        response = self.client.get("/roommate-posts/create/")
        self.assertRedirects(response, "/?next=/roommate-posts/create/")

    def test_other_user_delete_returns_404(self):
        post = self._create_post()
        self.client.login(username="other", password="Password123!")
        response = self.client.post(f"/roommate-posts/{post.id}/delete/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(RoommatePost.objects.count(), 1)

    def test_other_user_close_returns_404(self):
        post = self._create_post()
        self.client.login(username="other", password="Password123!")
        response = self.client.post(f"/roommate-posts/{post.id}/close/")
        self.assertEqual(response.status_code, 404)
        post.refresh_from_db()
        self.assertEqual(post.status, "open")


# Map Search Integration
class MapSearchIntegrationTest(TestCase):
    """Full map-search flow: submit city/state -> API called -> markers rendered."""

    @patch("home.views.get_properties", return_value=MOCK_API_RESULT)
    def test_city_state_search_calls_api_and_renders_map(self, mock_api):
        response = self.client.get("/map/", {"city": "Boulder", "state": "CO"})
        self.assertEqual(response.status_code, 200)
        mock_api.assert_called_once()
        data = response.context["properties"]
        self.assertEqual(len(data), 1)
        self.assertIn("latitude", data[0])
        self.assertIn("longitude", data[0])

    @patch("home.views.get_properties", return_value=[])
    def test_empty_api_result_renders_empty_map(self, _):
        response = self.client.get("/map/", {"city": "Nowhere", "state": "XX"})
        self.assertEqual(response.status_code, 200)
        data = response.context["properties"]
        self.assertEqual(data, [])

    @patch("home.views.get_properties", return_value=[])
    def test_missing_state_does_not_call_api(self, mock_api):
        """city without state must not trigger an API call."""
        self.client.get("/map/", {"city": "Boulder"})
        mock_api.assert_not_called()

    @patch("home.views.get_properties", return_value=MOCK_API_RESULT)
    def test_budget_filter_forwarded_to_api(self, mock_api):
        self.client.get("/map/", {"city": "Boulder", "state": "CO", "budget": "500-1500"})
        _, kwargs = mock_api.call_args
        self.assertEqual(kwargs.get("min_price"), 500)
        self.assertEqual(kwargs.get("max_price"), 1500)

    @patch("home.views.get_properties", return_value=MOCK_API_RESULT)
    def test_property_type_filter_forwarded_to_api(self, mock_api):
        self.client.get("/map/", {"city": "Boulder", "state": "CO", "type": "apartment"})
        _, kwargs = mock_api.call_args
        self.assertEqual(kwargs.get("property_type"), "apartment")

    def test_no_search_shows_local_db_properties_with_coords(self):
        """With no city/state, the map falls back to local DB properties that have coords."""
        Property.objects.create(
            title="Local Prop",
            location="Boulder, CO",
            listing_type="rent",
            property_type="apartment",
            price=1000,
            latitude=40.01,
            longitude=-105.27,
        )
        response = self.client.get("/map/")
        self.assertEqual(response.status_code, 200)
        data = response.context["properties"]
        self.assertEqual(len(data), 1)

    @patch("home.views.get_properties", return_value=MOCK_API_RESULT)
    def test_post_to_map_also_works(self, mock_api):
        """Searching via POST (from the map's own search bar) renders results."""
        response = self.client.post("/map/", {"city": "Boulder", "state": "CO"})
        self.assertEqual(response.status_code, 200)
        data = response.context["properties"]
        self.assertGreater(len(data), 0)

    @patch("home.views.get_properties")
    def test_property_without_coords_is_geocoded(self, mock_api):
        """If API omits lat/lng, the view falls back to geocoding."""
        mock_api.return_value = [
            {
                "formattedAddress": "1 Main St, Boulder, CO",
                "propertyType": "Apartment",
                "price": 900,
            }
        ]
        with patch("home.views.geocode_residential", return_value=(40.0, -105.0)):
            response = self.client.get("/map/", {"city": "Boulder", "state": "CO"})
        data = response.context["properties"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["latitude"], 40.0)


# Keyword Search Flow
class KeywordSearchFlowTest(TestCase):
    """Search page returns local Property records; keyword filtering TBD."""

    def setUp(self):
        Property.objects.create(
            title="Studio near Campus",
            price=900,
            property_type="studio",
            listing_type="rent",
            location="Boulder, CO",
        )
        Property.objects.create(
            title="Downtown Loft",
            price=1800,
            property_type="apartment",
            listing_type="rent",
            location="Denver, CO",
        )

    def test_search_page_loads(self):
        response = self.client.get("/roommate-posts/search/")
        self.assertEqual(response.status_code, 200)

    def test_all_properties_appear_in_results(self):
        response = self.client.get("/roommate-posts/search/")
        self.assertContains(response, "Studio near Campus")
        self.assertContains(response, "Downtown Loft")

    def test_keyword_param_does_not_crash_page(self):
        response = self.client.get("/roommate-posts/search/", {"q": "studio"})
        self.assertEqual(response.status_code, 200)

    def test_unknown_keyword_still_returns_200(self):
        response = self.client.get("/roommate-posts/search/", {"q": "zzznomatch"})
        self.assertEqual(response.status_code, 200)


# Instant Messaging Flow
class InstantMessagingFlowTest(TestCase):
    """Create posting -> access chat room -> messages persist -> show in inbox."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="Pass123!")
        self.bob = User.objects.create_user(username="bob", password="Pass123!")

    def _create_post(self, owner):
        return RoommatePost.objects.create(
            user=owner,
            message="Room available.",
            date="2026-03-11",
            status="open",
            rent=1000,
            property_type="apartment",
        )

    def test_poster_inbox_shows_their_posts(self):
        self.client.login(username="bob", password="Pass123!")
        self._create_post(self.bob)
        response = self.client.get("/chat/inbox/")
        self.assertEqual(response.status_code, 200)
        # inbox context has posts_with_chats
        self.assertIn("posts_with_chats", response.context)

    def test_inquirer_can_open_chat_room(self):
        post = self._create_post(self.bob)
        self.client.login(username="alice", password="Pass123!")
        response = self.client.get(f"/chat/{post.id}/{self.alice.id}/")
        self.assertEqual(response.status_code, 200)

    def test_message_persisted_shows_in_inbox_count(self):
        from chat.models import Message

        post = self._create_post(self.bob)
        Message.objects.create(
            posting_id=post.id,
            inquirer_id=self.alice.id,
            sender=self.alice,
            sender_label="user",
            content="Is the room still available?",
        )
        self.client.login(username="bob", password="Pass123!")
        response = self.client.get("/chat/inbox/")
        posts_with_chats = response.context["posts_with_chats"]
        self.assertEqual(posts_with_chats[0]["message_count"], 1)

    def test_participated_posts_appear_in_alice_inbox(self):
        from chat.models import Message

        post = self._create_post(self.bob)
        Message.objects.create(
            posting_id=post.id, inquirer_id=self.alice.id, sender=self.alice, sender_label="user", content="Hello!"
        )
        self.client.login(username="alice", password="Pass123!")
        response = self.client.get("/chat/inbox/")
        self.assertEqual(response.status_code, 200)
        participated = response.context["participated_chats"]
        self.assertEqual(len(participated), 1)

    def test_unauthenticated_user_cannot_view_chat_room(self):
        post = self._create_post(self.bob)
        response = self.client.get(f"/chat/{post.id}/{self.alice.id}/")
        self.assertNotEqual(response.status_code, 200)

    def test_multiple_messages_in_same_room_all_counted(self):
        from chat.models import Message

        post = self._create_post(self.bob)
        for i in range(3):
            Message.objects.create(
                posting_id=post.id,
                inquirer_id=self.alice.id,
                sender=self.alice,
                sender_label="user",
                content=f"Message {i}",
            )
        self.client.login(username="bob", password="Pass123!")
        response = self.client.get("/chat/inbox/")
        self.assertEqual(response.context["posts_with_chats"][0]["message_count"], 3)


# Two-Factor Auth Flow
class TwoFAFlowTest(TestCase):
    """Login -> 2FA setup -> verify TOTP/email flows."""

    def setUp(self):
        self.user = User.objects.create_user(username="secure", password="StrongPass@99", email="secure@test.com")
        self.client.login(username="secure", password="StrongPass@99")

    def test_setup_page_accessible_after_login(self):
        response = self.client.get("/auth/2fa/setup/")
        self.assertEqual(response.status_code, 200)

    def test_setup_page_has_totp_secret_and_qr(self):
        response = self.client.get("/auth/2fa/setup/")
        self.assertIn("totp_secret", response.context)
        self.assertIn("qr_code", response.context)
        self.assertTrue(len(response.context["totp_secret"]) > 0)

    def test_logout_then_setup_redirects(self):
        self.client.logout()
        response = self.client.get("/auth/2fa/setup/")
        self.assertNotEqual(response.status_code, 200)

    @patch("django.core.mail.send_mail")
    def test_email_2fa_flow_sends_email(self, mock_mail):
        response = self.client.post("/auth/2fa/setup/", {"method": "email_send"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_mail.called)

    def test_totp_2fa_wrong_code_does_not_save_profile(self):
        import pyotp
        from home.models import UserProfile

        secret = pyotp.random_base32()
        session = self.client.session
        session["totp_secret"] = secret
        session.save()
        self.client.post(
            "/auth/2fa/setup/",
            {
                "method": "totp_verify",
                "otp_code": "000000",
            },
        )
        profile = UserProfile.objects.get(user=self.user)
        self.assertFalse(profile.totp_enabled)

    def test_totp_2fa_correct_code_saves_profile_and_redirects(self):
        import pyotp
        from home.models import UserProfile

        secret = pyotp.random_base32()
        session = self.client.session
        session["totp_secret"] = secret
        session.save()
        valid_code = pyotp.TOTP(secret).now()
        response = self.client.post(
            "/auth/2fa/setup/",
            {
                "method": "totp_verify",
                "otp_code": valid_code,
            },
        )
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.totp_enabled)
        self.assertEqual(profile.two_fa_method, "totp")

    def test_email_verify_correct_code_saves_profile(self):
        import time as _time

        from home.models import UserProfile

        session = self.client.session
        session["email_otp"] = "654321"
        # The fix requires an expiration timestamp to live alongside
        # the code so stale codes can't be replayed forever. Seed a
        # fresh one (expires in 5 min) for this happy-path test.
        session["email_otp_expires"] = int(_time.time()) + 300
        session.save()
        response = self.client.post(
            "/auth/2fa/setup/",
            {
                "method": "email_verify",
                "email_code": "654321",
            },
        )
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.two_fa_method, "email")


# ----------------------------- SPRINT 3 ---------------------------------#
class MapPriceFilter(TestCase):
    """
    Tests the integration of the price filter on the map
    """

    @patch("home.views.get_neighborhood_profile")
    @patch("home.views.fetch_filtered_properties")
    def test_price_filter_returns_correct_properties(self, mock_api, mock_neighborhood):
        """
        Parameters: self, intercepts RentCast API (to avoid unnecessary calls)
        Creates mock data, which includes map_property and neighborhood profile (utilities, services, amenities)
        Sets the price filter to "Total Cost: Low to High" and runs the view logic
        Asserts whether the returned data is filtered correctly
        """
        # Mock data for the API response
        mock_api.return_value = [
            {"id": "1", "price": 1500, "latitude": 40.01, "longitude": -105.27, "formattedAddress": "123 Main St"},
            {"id": "2", "price": 3000, "latitude": 40.02, "longitude": -105.28, "formattedAddress": "456 Elm St"},
            {"id": "3", "price": 800, "latitude": 40.03, "longitude": -105.29, "formattedAddress": "789 Oak St"},
        ]

        # Mock data for neighborhood profile (utilities, services, amenities) which is was added to the views.py
        mock_neighborhood.return_value = (
            "Downtown",
            {
                "monthly_utilities": 210,
                "monthly_services": 95,
                "nearby_amenities": ["Gym"],
            },
        )

        # Simulates what input the user may make
        response = self.client.get("/map/", {"city": "Boulder", "state": "CO", "sort": "total_cost_asc"})
        self.assertEqual(response.status_code, 200)  # Ensures the view returns a successful response

        # Extracts the properties from the response context
        properties = response.context.get("properties", [])
        total = [p["total_monthly_cost"] for p in properties]

        # Asserts that the returned data is in the correct order
        self.assertEqual(
            total,
            [
                1105,
                1805,
                3305,
            ],
        )

    # END OF PRICE FILTER TEST (TOTAL COST LOW TO HIGH)


class SocialPostsSignalTest(TestCase):
    def setUp(self):
        """
        Creates a user for the tests
        """
        self.user = User.objects.create_user(username="testuser", password="pass")

    @override_settings(TESTING=False)
    @patch("socialPosts.signals.get_channel_layer")
    def test_post_creation_flow_broadcasts_to_feed(self, mock_get_channel_layer):
        """
        Tests the 'flow' of creating a post and having it broadcast to the feed
        User logs in -> creates a post -> post is saved -> signal fires -> broadcast is sent to channel layer
        """

        # Set up mock channel layer
        mock_channel_layer = MagicMock()
        mock_channel_layer.group_send = AsyncMock()
        mock_get_channel_layer.return_value = mock_channel_layer

        # User logs in
        login_response = self.client.post(
            "/",
            {
                "username": "testuser",
                "password": "pass",
            },
        )
        self.assertEqual(login_response.status_code, 302)

        # Creates a new post
        self.client.post(
            "/roommate-posts/create/",
            {
                "message": "A_test_message",
                "date": "2026-01-01",
                "user": self,
                "status": "closed",
                "rent": 100,
                "property_type": "apartment",
            },
        )
        response = self.client.get("/roommate-posts/")
        self.assertContains(response, "A_test_message")  # Checks if post was successfully created

        # Check post exists in the database
        self.assertTrue(RoommatePost.objects.filter(message="A_test_message").exists())

        # Checks broadcast status
        mock_channel_layer.group_send.assert_called_once()
        args, kwargs = mock_channel_layer.group_send.call_args
        self.assertEqual(args[0], "listing_feed")
        self.assertEqual(args[1]["type"], "listing_created")

    # END OF BROADCAST FLOW


# AI listing Mock results
MOCK_RENTCAST_PROPERTIES = [
    {
        "id": "p1",
        "formattedAddress": "100 Pearl St, Boulder, CO",
        "city": "Boulder",
        "state": "CO",
        "price": 1200,
        "latitude": 40.01,
        "longitude": -105.27,
        "propertyType": "Apartment",
        "bedrooms": 2,
        "bathrooms": 1,
        "squareFootage": 750,
    },
    {
        "id": "p2",
        "formattedAddress": "200 Mapleton Ave, Boulder, CO",
        "city": "Boulder",
        "state": "CO",
        "price": 1800,
        "latitude": 40.02,
        "longitude": -105.28,
        "propertyType": "House",
        "bedrooms": 3,
        "bathrooms": 2,
        "squareFootage": 1400,
    },
]


def _ai_response(content="", tool_calls=None):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.choices[0].message.tool_calls = tool_calls
    response.choices[0].finish_reason = "stop"
    return response


def _tool_call(call_id, name, arguments):
    """Build a fake tool_call object as it would appear on the OpenAI message."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


# AI Listing Agent
class AIRecommendationFlowIntegrationTest(TestCase):
    """
    End-to-end flow for the HTTP curation endpoint:
    User logs in -> hits /ai-agent/ with filters -> RentCast is called (mocked)
    -> listings are enriched with neighborhood data -> OpenAI is called (mocked)
    -> JSON response with curated picks is returned.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="aiuser", password="Password123!")
        self.client.login(username="aiuser", password="Password123!")

    @patch("home.ai_listing_agent._get_client")
    @patch("home.views.fetch_filtered_properties", return_value=MOCK_RENTCAST_PROPERTIES)
    def test_full_ai_recommendation_flow_returns_curated_picks(self, mock_rentcast, mock_get_client):
        # OpenAI mock output: return a valid curation JSON referencing both listings by index.
        ai_payload = json.dumps(
            {
                "summary": "2 solid options in Boulder.",
                "picks": [
                    {
                        "id": 0,
                        "score": 92,
                        "reasoning": "Cheaper and near transit.",
                        "highlights": ["match: budget", "match: transit nearby"],
                    },
                    {
                        "id": 1,
                        "score": 74,
                        "reasoning": "Bigger but pricier.",
                        "highlights": ["more space"],
                    },
                ],
                "advice": "Tour the cheaper one first.",
            }
        )
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = _ai_response(ai_payload)
        mock_get_client.return_value = (fake_client, None)

        # Simulates user hitting the AI endpoint after running a Boulder rental search.
        response = self.client.get(
            "/ai-agent/",
            {
                "city": "Boulder",
                "state": "CO",
                "intent": "for_rent",
                "budget": "900-1400",
            },
        )

        # Endpoint returns a JsonResponse (always 200).
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["summary"], "2 solid options in Boulder.")
        self.assertEqual(body["advice"], "Tour the cheaper one first.")
        self.assertEqual(len(body["picks"]), 2)

        first_pick = body["picks"][0]
        self.assertEqual(first_pick["address"], "100 Pearl St, Boulder, CO")
        self.assertEqual(first_pick["score"], 92)
        self.assertIn("transit", first_pick["reasoning"].lower())
        self.assertGreater(first_pick["total_monthly_cost"], first_pick["rent"])

        # Assert we actually called the API exactly once for this request.
        fake_client.chat.completions.create.assert_called_once()


class AIChatTurnIntegrationTest(TestCase):
    """
    history seeded -> user asks for cheaper places -> model calls refine_search ->
    refine_callback is invoked with merged filters -> model generates a final
    text reply on the next turn. This exercises the full tool-calling loop in
    chat_turn() without needing a live WebSocket.
    """

    @patch("home.ai_listing_agent._get_client")
    def test_chat_turn_invokes_refine_search_then_returns_text_reply(self, mock_get_client):
        # Initial state
        initial_filters = {
            "city": "Boulder",
            "state": "CO",
            "listing_type": "for_rent",
            "property_type": "",
            "budget": "900-1400",
            "amenity": "any",
            "keyword": "",
        }
        initial_listings = [
            {"location": "100 Pearl St", "rent": 1200, "total_monthly_cost": 1505, "nearby_amenities": ["Gym"]},
        ]
        history = build_initial_history(initial_filters, initial_listings)
        history.append({"role": "user", "content": "Show me cheaper places under $900."})

        # Refine callback returns a new listing set when called with merged filters.
        new_listings_after_refine = [
            {"location": "50 Cheaper Rd", "rent": 800, "total_monthly_cost": 1050, "nearby_amenities": ["Transit"]},
        ]
        refine_callback = MagicMock(return_value=new_listings_after_refine)

        # OpenAI mock output: first call returns a tool_call, second call returns the reply text.
        first_response = _ai_response(
            content="",
            tool_calls=[_tool_call("call_001", "refine_search", json.dumps({"budget": "0-900"}))],
        )
        second_response = _ai_response(
            content="Here's a cheaper option near transit for $800/mo.",
            tool_calls=None,
        )
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = [first_response, second_response]
        mock_get_client.return_value = (fake_client, None)

        # Run the turn
        result = chat_turn(history, initial_filters, initial_listings, refine_callback)

        # Assistant reply
        self.assertTrue(result["ok"])
        self.assertIn("cheaper", result["reply"].lower())
        self.assertTrue(result["refined"])

        # The callback should have been invoked once with the merged filters
        refine_callback.assert_called_once()
        merged = refine_callback.call_args[0][0]
        self.assertEqual(merged["budget"], "0-900")
        self.assertEqual(merged["city"], "Boulder")

        # Filters and listings should have been mutated in place to the new state
        self.assertEqual(initial_filters["budget"], "0-900")
        self.assertEqual(initial_listings, new_listings_after_refine)

        # OpenAI should have been called twice (tool calling + reply)
        self.assertEqual(fake_client.chat.completions.create.call_count, 2)


# Agent Advertising
class AgentAdFlowIntegrationTest(TestCase):
    """End-to-end flow for the agent advertising feature."""

    def setUp(self):
        from home.models import AgentAd

        self.AgentAd = AgentAd

        # Verified agent
        self.agent = User.objects.create_user(
            username="verified_agent",
            password="Pass123!",
            email="agent@example.com",
        )
        profile = self.agent.profile
        profile.is_agent_verified = True
        profile.save()

        # Unverified user
        self.regular_user = User.objects.create_user(
            username="regular",
            password="Pass123!",
        )

        # Valid POST payload for AgentAdForm
        self.valid_ad_data = {
            "headline": "Top agent in Boulder",
            "city": "Boulder",
            "state": "co",
            "brokerage": "Mountain Realty",
            "license_number": "LIC-12345",
            "phone": "303-555-0100",
            "email": "agent@example.com",
            "website": "https://example.com",
            "bio": "Helping students find housing for 8 years.",
            "specialties": "Rentals, condos",
            "active": "on",
        }

    def test_verified_agent_can_create_ad(self):
        """Verified agent POSTs the form, ad is saved, state is uppercased."""
        self.client.login(username="verified_agent", password="Pass123!")
        response = self.client.post("/agents/ads/create/", self.valid_ad_data)

        # Successful create redirects to the list page.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/agents/ads/")
        self.assertEqual(self.AgentAd.objects.count(), 1)

        ad = self.AgentAd.objects.first()
        self.assertEqual(ad.agent, self.agent)
        self.assertEqual(ad.state, "CO")  # uppercased by the view
        self.assertEqual(ad.city, "Boulder")
        self.assertTrue(ad.active)

    def test_create_form_get_prefills_email(self):
        """GET to create page initialises the email field with the agent's email."""
        self.client.login(username="verified_agent", password="Pass123!")
        response = self.client.get("/agents/ads/create/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "agent@example.com")

    def test_unverified_user_create_returns_403(self):
        """Logged-in but unverified users see the not_verified page (403)."""
        self.client.login(username="regular", password="Pass123!")
        response = self.client.get("/agents/ads/create/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.AgentAd.objects.count(), 0)

    def test_anonymous_create_redirects_to_login(self):
        """Anonymous users hitting create are redirected to LOGIN_URL with ?next=."""
        response = self.client.get("/agents/ads/create/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response.url)

    def test_invalid_form_does_not_create_ad(self):
        """Missing required fields keeps the user on the form, no DB write."""
        self.client.login(username="verified_agent", password="Pass123!")
        bad_data = self.valid_ad_data.copy()
        bad_data["headline"] = ""  # required
        bad_data["license_number"] = ""  # required

        response = self.client.post("/agents/ads/create/", bad_data)
        self.assertEqual(response.status_code, 200)  # form re-rendered
        self.assertEqual(self.AgentAd.objects.count(), 0)

    def _make_ad(self, **overrides):
        defaults = dict(
            agent=self.agent,
            headline="Original Headline",
            city="Boulder",
            state="CO",
            brokerage="Mountain Realty",
            license_number="LIC-12345",
            email="agent@example.com",
            bio="Helping students.",
            active=True,
        )
        defaults.update(overrides)
        return self.AgentAd.objects.create(**defaults)

    def test_verified_agent_can_edit_own_ad(self):
        """Editing updates the fields and redirects back to the list."""
        ad = self._make_ad()
        self.client.login(username="verified_agent", password="Pass123!")

        edit_data = self.valid_ad_data.copy()
        edit_data["headline"] = "Updated Headline"
        edit_data["city"] = "Denver"

        response = self.client.post(f"/agents/ads/{ad.id}/edit/", edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/agents/ads/")

        ad.refresh_from_db()
        self.assertEqual(ad.headline, "Updated Headline")
        self.assertEqual(ad.city, "Denver")

    def test_agent_cannot_edit_someone_elses_ad(self):
        """Editing an ad you don't own returns 404 (filtered by agent=request.user)."""
        # Make an ad owned by a different verified agent
        other = User.objects.create_user(username="other_agent", password="Pass123!")
        other.profile.is_agent_verified = True
        other.profile.save()
        ad = self.AgentAd.objects.create(
            agent=other,
            headline="Theirs",
            city="Aspen",
            state="CO",
            brokerage="B",
            license_number="L",
            email="o@e.com",
            bio="b",
        )

        self.client.login(username="verified_agent", password="Pass123!")
        response = self.client.get(f"/agents/ads/{ad.id}/edit/")
        self.assertEqual(response.status_code, 404)

    def test_unverified_user_edit_returns_403(self):
        ad = self._make_ad()
        self.client.login(username="regular", password="Pass123!")
        response = self.client.get(f"/agents/ads/{ad.id}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_verified_agent_can_deactivate_ad(self):
        """POST to deactivate flips active=False and redirects back to list."""
        ad = self._make_ad(active=True)
        self.client.login(username="verified_agent", password="Pass123!")

        response = self.client.post(f"/agents/ads/{ad.id}/deactivate/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/agents/ads/")

        ad.refresh_from_db()
        self.assertFalse(ad.active)

    def test_get_to_deactivate_does_not_change_state(self):
        """Only POST deactivates; GET should leave the ad active."""
        ad = self._make_ad(active=True)
        self.client.login(username="verified_agent", password="Pass123!")

        self.client.get(f"/agents/ads/{ad.id}/deactivate/")
        ad.refresh_from_db()
        self.assertTrue(ad.active)

    def test_unverified_user_deactivate_returns_403(self):
        ad = self._make_ad()
        self.client.login(username="regular", password="Pass123!")
        response = self.client.post(f"/agents/ads/{ad.id}/deactivate/")
        self.assertEqual(response.status_code, 403)
        ad.refresh_from_db()
        self.assertTrue(ad.active)

    def test_public_profile_loads_for_complete_active_ad(self):
        """Anyone (no login) can view a complete, active ad's public profile."""
        ad = self._make_ad()
        response = self.client.get(f"/agents/{ad.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Original Headline")
        self.assertContains(response, "Mountain Realty")

    def test_inactive_ad_profile_returns_404(self):
        """Inactive ads are not publicly accessible."""
        ad = self._make_ad(active=False)
        response = self.client.get(f"/agents/{ad.id}/")
        self.assertEqual(response.status_code, 404)

    def test_incomplete_ad_profile_returns_404(self):
        """Ads missing required fields render the not_found page (404)."""
        ad = self._make_ad(bio="")  # incomplete -> is_complete is False
        response = self.client.get(f"/agents/{ad.id}/")
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_can_submit_inquiry(self):
        """Anonymous visitor POSTs the inquiry form; AgentInquiry is saved."""
        from home.models import AgentInquiry

        ad = self._make_ad()

        response = self.client.post(
            f"/agents/{ad.id}/",
            {
                "name": "Jane Student",
                "email": "jane@example.com",
                "message": "Hi, I am looking for a 1-bedroom near campus.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "inquiry was sent successfully")
        self.assertEqual(AgentInquiry.objects.count(), 1)

        inquiry = AgentInquiry.objects.first()
        self.assertEqual(inquiry.ad, ad)
        self.assertIsNone(inquiry.user)  # anonymous
        self.assertEqual(inquiry.name, "Jane Student")

    def test_authenticated_user_inquiry_links_user(self):
        """Logged-in user's inquiry stores the FK on AgentInquiry.user."""
        from home.models import AgentInquiry

        ad = self._make_ad()
        self.client.login(username="regular", password="Pass123!")

        self.client.post(
            f"/agents/{ad.id}/",
            {
                "name": "Regular User",
                "email": "r@e.com",
                "message": "Looking for a place.",
            },
        )

        inquiry = AgentInquiry.objects.first()
        self.assertIsNotNone(inquiry)
        self.assertEqual(inquiry.user, self.regular_user)

    def test_invalid_inquiry_does_not_create_record(self):
        """Empty required fields keep the user on the page with no DB write."""
        from home.models import AgentInquiry

        ad = self._make_ad()

        response = self.client.post(
            f"/agents/{ad.id}/",
            {
                "name": "",
                "email": "not-an-email",
                "message": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AgentInquiry.objects.count(), 0)

    def test_get_relevant_agent_ads_filters_by_city_and_state(self):
        """The helper used by /search/ and /map/ filters by city/state."""
        from home.views import get_relevant_agent_ads

        self._make_ad(city="Boulder", state="CO", headline="Boulder Ad")
        self._make_ad(city="Denver", state="CO", headline="Denver Ad")

        boulder_ads = get_relevant_agent_ads(city="Boulder", state="CO")
        self.assertEqual(len(boulder_ads), 1)
        self.assertEqual(boulder_ads[0].headline, "Boulder Ad")

    def test_get_relevant_agent_ads_excludes_incomplete(self):
        """Ads missing required fields are filtered out."""
        from home.views import get_relevant_agent_ads

        self._make_ad(headline="Complete Ad")
        self._make_ad(headline="Incomplete", bio="")  # bio empty -> incomplete

        ads = get_relevant_agent_ads(city="Boulder", state="CO")
        self.assertEqual(len(ads), 1)
        self.assertEqual(ads[0].headline, "Complete Ad")

    def test_get_relevant_agent_ads_excludes_inactive(self):
        """Inactive ads do not appear in search/map sidebars."""
        from home.views import get_relevant_agent_ads

        self._make_ad(headline="Active", active=True)
        self._make_ad(headline="Hidden", active=False)

        ads = get_relevant_agent_ads(city="Boulder", state="CO")
        headlines = [a.headline for a in ads]
        self.assertIn("Active", headlines)
        self.assertNotIn("Hidden", headlines)

    def test_get_relevant_agent_ads_respects_limit(self):
        """The limit parameter caps how many ads are returned."""
        from home.views import get_relevant_agent_ads

        for i in range(5):
            self._make_ad(headline=f"Ad {i}")

        ads = get_relevant_agent_ads(city="Boulder", state="CO", limit=2)
        self.assertEqual(len(ads), 2)

    def test_search_page_shows_relevant_agent_ads(self):
        """The /roommate-posts/search/ page surfaces the agent ads sidebar."""
        self._make_ad(headline="Featured Boulder Agent", city="Boulder", state="CO")
        response = self.client.get(
            "/roommate-posts/search/",
            {"city": "Boulder", "state": "CO"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Featured Boulder Agent")


# Street View
class StreetViewIntegrationTest(TestCase):
    """End-to-end checks that make sure the map's Street View deeplink works."""

    STREET_VIEW_PATTERN = "maps/@?api=1&map_action=pano"

    MOCK_API_RESULT = [
        {
            "id": "sv1",
            "formattedAddress": "100 Pearl St, Boulder, CO",
            "city": "Boulder",
            "state": "CO",
            "price": 1200,
            "latitude": 40.0190,
            "longitude": -105.2747,
            "propertyType": "Apartment",
            "bedrooms": 2,
            "bathrooms": 1,
            "squareFootage": 700,
        },
        {
            "id": "sv2",
            "formattedAddress": "200 Walnut St, Boulder, CO",
            "city": "Boulder",
            "state": "CO",
            "price": 1500,
            "latitude": 40.0182,
            "longitude": -105.2780,
            "propertyType": "Apartment",
            "bedrooms": 1,
            "bathrooms": 1,
            "squareFootage": 600,
        },
    ]

    @patch("home.views.get_properties")
    def test_map_context_carries_lat_lng_for_each_property(self, mock_api):
        """Every map marker must have latitude AND longitude in the context."""
        mock_api.return_value = self.MOCK_API_RESULT
        response = self.client.get("/map/", {"city": "Boulder", "state": "CO"})

        self.assertEqual(response.status_code, 200)
        properties = response.context["properties"]
        self.assertEqual(len(properties), 2)

        for prop in properties:
            self.assertIn("latitude", prop)
            self.assertIn("longitude", prop)
            self.assertIsNotNone(prop["latitude"])
            self.assertIsNotNone(prop["longitude"])

    @patch("home.views.get_properties")
    def test_map_html_contains_street_view_url_pattern(self, mock_api):
        """The rendered map.html must include the Street View deeplink template."""
        mock_api.return_value = self.MOCK_API_RESULT
        response = self.client.get("/map/", {"city": "Boulder", "state": "CO"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.STREET_VIEW_PATTERN, response.content.decode())

    @patch("home.views.get_properties")
    def test_map_html_serializes_properties_for_js(self, mock_api):
        """json_script must put properties into the page so the JS can read them."""
        mock_api.return_value = self.MOCK_API_RESULT
        response = self.client.get("/map/", {"city": "Boulder", "state": "CO"})

        body = response.content.decode()
        # Confirm json_script tag is rendered with the expected id
        self.assertIn('id="map-properties-data"', body)
        # Confirm the actual lat/lng made it into the embedded JSON payload
        self.assertIn("40.019", body)
        self.assertIn("-105.2747", body)

    @patch("home.views.get_properties")
    def test_geocoded_property_still_gets_street_view_coords(self, mock_api):
        """When the API omits coords and geocoding fills them in, Street View still works."""
        mock_api.return_value = [
            {
                "formattedAddress": "1 Main St, Boulder, CO",
                "propertyType": "Apartment",
                "price": 950,
                # no latitude/longitude on purpose
            }
        ]
        with patch("home.views.geocode_residential", return_value=(40.0150, -105.2705)):
            response = self.client.get("/map/", {"city": "Boulder", "state": "CO"})

        properties = response.context["properties"]
        self.assertEqual(len(properties), 1)
        # Geocoded lat/lng landed on the marker -> Street View deeplink will work
        self.assertEqual(properties[0]["latitude"], 40.0150)
        self.assertEqual(properties[0]["longitude"], -105.2705)
        # And the deeplink template is still on the page
        self.assertIn(self.STREET_VIEW_PATTERN, response.content.decode())

    def test_local_db_properties_carry_coords_for_street_view(self):
        """Local-DB fallback (no city/state) also supplies lat/lng for Street View."""
        Property.objects.create(
            title="Local With Coords",
            location="Boulder, CO",
            listing_type="rent",
            property_type="apartment",
            price=1000,
            latitude=40.01,
            longitude=-105.27,
        )
        Property.objects.create(
            title="Local Without Coords",
            location="Denver, CO",
            listing_type="rent",
            property_type="apartment",
            price=1100,
            latitude=None,
            longitude=None,
        )
        response = self.client.get("/map/")
        self.assertEqual(response.status_code, 200)

        properties = response.context["properties"]
        self.assertEqual(len(properties), 1)
        self.assertIn("latitude", properties[0])
        self.assertIn("longitude", properties[0])
        # Street View URL template is in the page so the JS can build the link
        self.assertIn(self.STREET_VIEW_PATTERN, response.content.decode())

    @patch("home.views.get_properties")
    def test_empty_results_still_render_street_view_template(self, mock_api):
        """No properties returned still renders the JS that would build links."""
        mock_api.return_value = []
        response = self.client.get("/map/", {"city": "Nowhere", "state": "XX"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["properties"], [])

        self.assertIn(self.STREET_VIEW_PATTERN, response.content.decode())
