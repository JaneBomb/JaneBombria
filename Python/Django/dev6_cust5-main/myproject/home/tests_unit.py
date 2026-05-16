import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase, TransactionTestCase, override_settings
from home.ai_listing_agent import (
    MAX_LISTINGS_SENT,
    _trim_candidates,
    check_message_guardrails,
    get_ai_recommendations,
)
from home.consumers import AIListingAgentConsumer
from home.forms import CustomRegisterForm, RoommatePostForm
from home.models import AgentAd, Property, RoommatePost, SearchHistory
from socialPosts.serializers import serialize_listing


# Roommate Post Form
class RoommatePostFormTest(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "message": "Looking for a roommate.",
            "date": "2026-03-11",
            "status": "open",
            "rent": 1000,
            "property_type": "apartment",
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        """
        checks if Roommate form is valid
        """
        self.assertTrue(RoommatePostForm(data=self._valid_data()).is_valid())

    def test_missing_message_invalid(self):
        """
        Message field should be valid
        """
        form = RoommatePostForm(data=self._valid_data(message=""))
        self.assertFalse(form.is_valid())
        self.assertIn("message", form.errors)

    def test_missing_date_invalid(self):
        """
        Date should be valid
        """
        form = RoommatePostForm(data=self._valid_data(date=""))
        self.assertFalse(form.is_valid())
        self.assertIn("date", form.errors)

    def test_rent_is_optional(self):
        """
        Rent is optional
        """
        self.assertTrue(RoommatePostForm(data=self._valid_data(rent="")).is_valid())

    def test_invalid_status(self):
        """
        Status should either be open or closed not "maybe"
        """
        self.assertFalse(RoommatePostForm(data=self._valid_data(status="maybe")).is_valid())


# Roommate Post Model
class RoommatePostModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass")

    def test_default_status_is_open(self):
        """
        Check if status is open by default
        """
        post = RoommatePost.objects.create(user=self.user, message="Hi", date="2026-03-01")
        self.assertEqual(post.status, "open")

    def test_rent_is_optional(self):
        """
        Rent is optional
        """
        post = RoommatePost.objects.create(user=self.user, message="Hi", date="2026-03-01")
        self.assertIsNone(post.rent)

    def test_property_type_defaults_to_empty(self):
        """
        Property type defaults to empty string
        """
        post = RoommatePost.objects.create(user=self.user, message="Hi", date="2026-03-01")
        self.assertEqual(post.property_type, "")

    def test_user_deletion_cascades(self):
        """
        Deleting user = deleting posts
        """
        RoommatePost.objects.create(user=self.user, message="Hi", date="2026-03-01")
        self.user.delete()
        self.assertEqual(RoommatePost.objects.count(), 0)


# Property Model
class PropertyModelTest(TestCase):
    def test_description_is_optional(self):
        """
        DEscription of House is optional
        """
        prop = Property.objects.create(
            title="Test", location="Denver, CO", listing_type="rent", property_type="house", price=900
        )
        self.assertEqual(prop.description, "")

    def test_lat_lng_nullable(self):
        """
        Langitude and latitude can be null
        """
        prop = Property.objects.create(
            title="NoCoords", location="Denver, CO", listing_type="rent", property_type="house", price=900
        )
        self.assertIsNone(prop.latitude)
        self.assertIsNone(prop.longitude)

    def test_str_returns_title(self):
        prop = Property.objects.create(
            title="My Place", location="Boulder, CO", listing_type="rent", property_type="apartment", price=1000
        )
        self.assertEqual(str(prop), "My Place")


# Custom Register Form
class CustomRegisterFormTest(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "username": "newuser",
            "email": "",
            "password1": "StrongPassword@123",
            "password2": "StrongPassword@123",
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        """
        Form is valid
        """
        self.assertTrue(CustomRegisterForm(data=self._valid_data()).is_valid())

    def test_email_is_optional(self):
        """
        Email is optional
        """
        self.assertTrue(CustomRegisterForm(data=self._valid_data(email="")).is_valid())

    def test_mismatched_passwords_invalid(self):
        """
        If there's a mismatch when confirming password, the form is rejected
        """
        self.assertFalse(CustomRegisterForm(data=self._valid_data(password2="different")).is_valid())

    def test_missing_username_invalid(self):
        """
        Username is mandatory
        """
        self.assertFalse(CustomRegisterForm(data=self._valid_data(username="")).is_valid())


# Rentcast API
# Patch API_KEY so the function doesn't bail out before hitting requests.get
class RentcastAPITest(TestCase):
    @patch("home.rentcast_api.API_KEY", "fake-key")
    @patch("home.rentcast_api.requests.get")
    def test_returns_list_on_200(self, mock_get):
        """
        API returns json/ is successful
        """
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"formattedAddress": "123 Main St", "price": 1200}],
            text="[...]",
        )
        from home.rentcast_api import get_properties

        result = get_properties("Denver, CO")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    @patch("home.rentcast_api.API_KEY", "fake-key")
    @patch("home.rentcast_api.requests.get")
    def test_returns_empty_list_on_non_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404, text="not found")
        from home.rentcast_api import get_properties

        result = get_properties("Denver, CO")
        self.assertEqual(result, [])

    @patch("home.rentcast_api.API_KEY", None)
    def test_returns_empty_list_when_no_api_key(self):
        """
        If no API key, no list is returned
        """
        from home.rentcast_api import get_properties

        result = get_properties("Denver, CO")
        self.assertEqual(result, [])

    @patch("home.rentcast_api.API_KEY", "fake-key")
    @patch("home.rentcast_api.requests.get")
    def test_filters_by_min_price(self, mock_get):
        """
        Testing API by min price
        """
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"price": 900}, {"price": 1500}, {"price": 500}],
            text="[...]",
        )
        from home.rentcast_api import get_properties

        result = get_properties("Denver, CO", min_price=1000)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["price"], 1500)

    @patch("home.rentcast_api.API_KEY", "fake-key")
    @patch("home.rentcast_api.requests.get")
    def test_filters_by_max_price(self, mock_get):
        """
        Testing API by max price
        """
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"price": 900}, {"price": 1500}],
            text="[...]",
        )
        from home.rentcast_api import get_properties

        result = get_properties("Denver, CO", max_price=1000)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["price"], 900)

    @patch("home.rentcast_api.API_KEY", "fake-key")
    @patch("home.rentcast_api.requests.get")
    def test_property_type_mapped_to_rentcast_value(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [], text="[]")
        from home.rentcast_api import get_properties

        get_properties("Denver, CO", property_type="apartment")
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["propertyType"], "Apartment")

    @patch("home.rentcast_api.API_KEY", "fake-key")
    @patch("home.rentcast_api.requests.get")
    def test_response_wrapping_in_data_key(self, mock_get):
        """API sometimes wraps results under a 'data' key."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [{"price": 1000}]},
            text="{...}",
        )
        from home.rentcast_api import get_properties

        result = get_properties("Denver, CO")
        self.assertEqual(len(result), 1)


# geocode_residential - US Census geocoding helper
class GeocodeResidentialTest(TestCase):
    @patch("home.views.requests.get")
    def test_returns_coords_on_match(self, mock_get):
        """
        Returns Lat/Long coords when there's a match
        """
        mock_get.return_value = MagicMock(
            json=lambda: {"result": {"addressMatches": [{"coordinates": {"y": 40.01, "x": -105.27}}]}}
        )
        from home.views import geocode_residential

        lat, lng = geocode_residential("123 Main St, Boulder CO")
        self.assertAlmostEqual(lat, 40.01)
        self.assertAlmostEqual(lng, -105.27)

    @patch("home.views.requests.get")
    def test_returns_none_when_no_match(self, mock_get):
        mock_get.return_value = MagicMock(json=lambda: {"result": {"addressMatches": []}})
        from home.views import geocode_residential

        result = geocode_residential("Completely Fake Address, XX 00000")
        self.assertIsNone(result)


# fetch_filtered_properties - wraps get_properties with price parsing
class FetchFilteredPropertiesTest(TestCase):
    @patch("home.views.get_properties", return_value=[])
    def test_returns_empty_when_api_empty(self, _):
        from home.views import fetch_filtered_properties

        self.assertEqual(fetch_filtered_properties("Boulder, CO"), [])

    @patch("home.views.get_properties", side_effect=Exception("API down"))
    def test_returns_empty_on_exception(self, _):
        from home.views import fetch_filtered_properties

        self.assertEqual(fetch_filtered_properties("Boulder, CO"), [])

    @patch("home.views.get_properties", return_value=[])
    def test_price_range_parsed_and_passed_to_api(self, mock_api):
        from home.views import fetch_filtered_properties

        fetch_filtered_properties("Boulder, CO", price_range="800-1500")
        mock_api.assert_called_once_with("Boulder, CO", property_type=None, min_price=800, max_price=1500)

    @patch("home.views.get_properties", return_value=[])
    def test_invalid_price_range_silently_ignored(self, mock_api):
        from home.views import fetch_filtered_properties

        result = fetch_filtered_properties("Boulder, CO", price_range="bad-range")
        self.assertEqual(result, [])
        # min/max fall back to None when parsing fails
        mock_api.assert_called_once_with("Boulder, CO", property_type=None, min_price=None, max_price=None)


# map_view - POST path (search bar on the map page itself)
class MapViewPostTest(TestCase):
    """
    How Map looks after POST
    """

    @patch("home.views.get_properties", return_value=[])
    def test_post_returns_200(self, _):
        response = self.client.post("/map/", {"city": "Boulder", "state": "CO"})
        self.assertEqual(response.status_code, 200)

    @patch("home.views.get_properties")
    def test_post_with_api_results_puts_data_in_context(self, mock_api):
        mock_api.return_value = [
            {
                "latitude": 40.01,
                "longitude": -105.27,
                "formattedAddress": "1 Test Ave, Boulder, CO",
                "propertyType": "apartment",
                "price": 1000,
                "bedrooms": 2,
                "bathrooms": 1,
                "squareFootage": 800,
            }
        ]
        response = self.client.post("/map/", {"city": "Boulder", "state": "CO"})
        self.assertEqual(response.status_code, 200)
        data = response.context["properties"]
        self.assertEqual(len(data), 1)
        self.assertIn("latitude", data[0])

    @patch("home.views.get_properties")
    def test_map_geocodes_when_no_lat_lng(self, mock_api):
        """When API returns a property without coords, geocode_residential is called."""
        mock_api.return_value = [
            {
                "formattedAddress": "1 Test Ave, Boulder, CO",
                "propertyType": "apartment",
                "price": 1000,
                # no latitude/longitude
            }
        ]
        with patch("home.views.geocode_residential", return_value=(40.01, -105.27)):
            response = self.client.get("/map/", {"city": "Boulder", "state": "CO"})
        self.assertEqual(response.status_code, 200)
        data = response.context["properties"]
        self.assertEqual(len(data), 1)


# roommate_create GET path
class RoommateCreateGetTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass")
        self.client.login(username="u", password="pass")

    def test_get_create_page_returns_form(self):
        """
        Create Page returns a form
        """
        response = self.client.get("/roommate-posts/create/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)


# register — invalid form path
class RegisterErrorTest(TestCase):
    """
    Checking invalid cases while registering new users
    """

    def test_register_with_mismatched_passwords_shows_errors(self):
        response = self.client.post(
            "/register/",
            {
                "username": "u",
                "password1": "StrongPass@123",
                "password2": "Different@456",
            },
        )
        # View renders homepage with errors (200) or redirects (302)
        self.assertIn(response.status_code, [200, 302])

    def test_duplicate_username_register_fails(self):
        User.objects.create_user(username="existing", password="pass")
        self.client.post(
            "/register/",
            {
                "username": "existing",
                "password1": "StrongPass@123",
                "password2": "StrongPass@123",
            },
        )
        # Only one user with that name should exist
        self.assertEqual(User.objects.filter(username="existing").count(), 1)


# setup_2fa - POST paths (totp_verify, email_send, email_verify)
class TwoFAPostTest(TestCase):
    """
    Verifies QR code and Email
    """

    def setUp(self):
        self.user = User.objects.create_user(username="u", password="StrongPass@99", email="u@example.com")
        self.client.login(username="u", password="StrongPass@99")

    def _set_session(self, **kwargs):
        session = self.client.session
        for k, v in kwargs.items():
            session[k] = v
        session.save()

    def test_totp_verify_wrong_code_shows_error(self):
        import pyotp

        self._set_session(totp_secret=pyotp.random_base32())
        response = self.client.post(
            "/auth/2fa/setup/",
            {
                "method": "totp_verify",
                "otp_code": "000000",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("totp_error", response.context)

    def test_totp_verify_correct_code_redirects(self):
        import pyotp

        secret = pyotp.random_base32()
        self._set_session(totp_secret=secret)
        valid_code = pyotp.TOTP(secret).now()
        response = self.client.post(
            "/auth/2fa/setup/",
            {
                "method": "totp_verify",
                "otp_code": valid_code,
            },
        )
        self.assertEqual(response.status_code, 302)

    @patch("django.core.mail.send_mail")
    def test_email_send_with_valid_email_sends_mail(self, mock_mail):
        response = self.client.post("/auth/2fa/setup/", {"method": "email_send"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_mail.called)
        self.assertIn("email_sent", response.context)

    def test_email_send_without_email_shows_error(self):
        self.user.email = ""
        self.user.save()
        response = self.client.post("/auth/2fa/setup/", {"method": "email_send"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("email_error", response.context)

    def test_email_verify_correct_code_redirects(self):
        import time as _time

        # The fix for the "email OTP never expires" vulnerability now
        # requires an expiration timestamp to live alongside the code
        # — without it, the OTP is rejected as expired. Seed a fresh
        # one (5 min in the future) for this happy-path test.
        self._set_session(
            email_otp="123456",
            email_otp_expires=int(_time.time()) + 300,
        )
        response = self.client.post(
            "/auth/2fa/setup/",
            {
                "method": "email_verify",
                "email_code": "123456",
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_email_verify_wrong_code_shows_error(self):
        import time as _time

        self._set_session(
            email_otp="123456",
            email_otp_expires=int(_time.time()) + 300,
        )
        response = self.client.post(
            "/auth/2fa/setup/",
            {
                "method": "email_verify",
                "email_code": "999999",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("email_error", response.context)


# chat Message model
class MessageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass")

    def test_message_str(self):
        """
        Creating message
        """
        from chat.models import Message

        msg = Message.objects.create(
            posting_id=1,
            sender=self.user,
            sender_label="user",
            content="Hello there",
        )
        self.assertIn("Hello there", str(msg))

    def test_message_ordering_by_timestamp(self):
        """
        Ordering messages by their timestamp
        """
        from chat.models import Message

        m1 = Message.objects.create(posting_id=1, sender=self.user, sender_label="user", content="First")
        m2 = Message.objects.create(posting_id=1, sender=self.user, sender_label="user", content="Second")
        messages = list(Message.objects.filter(posting_id=1))
        self.assertEqual(messages[0].id, m1.id)
        self.assertEqual(messages[1].id, m2.id)

    def test_message_sender_nullable(self):
        from chat.models import Message

        msg = Message.objects.create(posting_id=1, sender=None, sender_label="anonymous", content="Hi")
        self.assertIsNone(msg.sender)


# WebSocket consumer - connect, receive, disconnect
# Overrides CHANNEL_LAYERS to use the in-memory backend (no Redis needed)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatConsumerTest(TestCase):
    """
    Checks connection and if messages can be received
    """

    def setUp(self):
        self.user = User.objects.create_user(username="wsuser", password="pass")

    def _make_app(self):
        import chat.routing
        from channels.auth import AuthMiddlewareStack
        from channels.routing import URLRouter

        return AuthMiddlewareStack(URLRouter(chat.routing.websocket_urlpatterns))

    def test_consumer_connects_and_disconnects(self):
        """
        Check Connection and Disconnection
        """
        from asgiref.sync import async_to_sync
        from channels.testing import WebsocketCommunicator

        app = self._make_app()
        user_id = self.user.id

        async def run():
            comm = WebsocketCommunicator(app, f"ws/chat/1/{user_id}/")
            comm.scope["user"] = self.user  # inject authenticated user
            connected, _ = await comm.connect()
            assert connected, "WebSocket did not connect"
            await comm.disconnect()

        async_to_sync(run)()

    def test_save_message_persists_to_db(self):
        """
        save_message() writes a Message row without needing a live WebSocket
        """
        from asgiref.sync import async_to_sync
        from chat.consumers import ChatConsumer
        from chat.models import Message

        consumer = ChatConsumer()
        consumer.posting_id = 99
        consumer.inquirer_id = self.user.id
        async_to_sync(consumer.save_message)(self.user, "direct save")
        self.assertEqual(Message.objects.filter(posting_id=99).count(), 1)

    def test_get_history_returns_existing_messages(self):
        from asgiref.sync import async_to_sync
        from chat.consumers import ChatConsumer
        from chat.models import Message

        Message.objects.create(
            posting_id=77, inquirer_id=self.user.id, sender=self.user, sender_label="user", content="History msg"
        )
        consumer = ChatConsumer()
        consumer.posting_id = 77
        consumer.inquirer_id = self.user.id
        consumer.scope = {"user": self.user}  # add this
        history = async_to_sync(consumer.get_history)()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["message"], "History msg")

    def test_consumer_serves_message_history_on_connect(self):
        """
        Messages already in DB for a posting are sent on connect
        """
        from asgiref.sync import async_to_sync
        from channels.testing import WebsocketCommunicator
        from chat.models import Message

        # Pre-seed a message
        Message.objects.create(
            posting_id=1, inquirer_id=self.user.id, sender=self.user, sender_label="user", content="Old message"
        )

        app = self._make_app()
        user_id = self.user.id

        async def run():
            comm = WebsocketCommunicator(app, f"ws/chat/1/{user_id}/")
            comm.scope["user"] = self.user  # inject authenticated user
            connected, _ = await comm.connect()
            assert connected, "WebSocket did not connect"
            await comm.disconnect()

        async_to_sync(run)()


def test_anonymous_user_cannot_connect(self):
    # Simulate a WebSocket Connection to test the authentication
    from asgiref.sync import async_to_sync
    from channels.auth import AuthMiddlewareStack
    from channels.routing import URLRouter
    from channels.testing import WebsocketCommunicator
    from chat.consumers import ChatConsumer
    from chat.models import Message
    from django.urls import re_path

    # Runs that connection
    application = AuthMiddlewareStack(
        URLRouter(
            [
                re_path(r"ws/chat/(?P<posting_id>\d+)/(?P<inquirer_id>\d+)/$", ChatConsumer.as_asgi()),
            ]
        )
    )

    # Tests if the user is anonymous
    async def inner():
        communicator = WebsocketCommunicator(application, "/ws/chat/1/1/")
        connected, code = await communicator.connect()

        self.assertFalse(connected, "Anonymous user should not be able to connect")
        await communicator.disconnect()

    async_to_sync(inner)()

    # Test that no messages are saved
    self.assertEqual(Message.objects.filter(posting_id=1).count(), 0)


# ----------------------------- SPRINT 3 ---------------------------------#
# TESTS IF A MODEL HAS CERTAIN FIELDS, ETC.
class MapPriceFilter(TestCase):
    """
    Tests the integration of the price filter on the map
    """

    @patch("home.views.get_neighborhood_profile")
    @patch("home.views.fetch_filtered_properties")
    def test_price_filter_returns_utilities_price_field(self, mock_api, mock_neighborhood):
        """
        Parameters: self, intercepts RentCast API (to avoid unnecessary calls)
        Creates a mock map_property using mock neighborhood profile data
        Asserts that the field has been populated/exists
        """
        # Mock data for the API response
        mock_api.return_value = [
            {"id": "1", "price": 1500, "latitude": 40.01, "longitude": -105.27, "formattedAddress": "123 Main St"},
            {"id": "2", "price": 3000, "latitude": 40.02, "longitude": -105.28, "formattedAddress": "456 Elm St"},
            {"id": "3", "price": 800, "latitude": 40.03, "longitude": -105.29, "formattedAddress": "789 Oak St"},
        ]

        # Mock data for neighborhood profile (utilities, services, amenities)
        mock_neighborhood.return_value = (
            "Downtown",
            {
                "monthly_utilities": 210,
                "monthly_services": 95,
                "nearby_amenities": ["Gym"],
            },
        )

        response = self.client.get("/map/", {"city": "Boulder", "state": "CO", "sort": "total_cost_asc"})

        # Returns list of properties
        # properties = [{entry1}, {entry2}, ...]
        properties = response.context.get("properties", [])

        # Asserts that monthly_utilities and monthly_services fields are present in the returned properties
        for i in properties:
            self.assertIn("monthly_utilities", i)
            self.assertIn("monthly_services", i)

    # END OF PRICE FILTER TEST


class RealTimePostBroadcasts(TestCase):
    def setUp(self):
        """
        Creates a user for the tests
        """
        self.user = User.objects.create_user(username="testuser", password="pass")

    @override_settings(TESTING=True)
    def test_signal_skips_broadcast_during_testing(self):
        """
        Creates a roommate post and checks that the message is saved correctly
        """
        post = RoommatePost.objects.create(
            user=self.user,
            message="Test post",
            date=date(2026, 1, 1),
        )
        self.assertEqual(post.message, "Test post")

    @override_settings(TESTING=True)
    def test_signal_skips_update(self):
        """
        Creates a roommate post, updates the message, and checks that the update is saved correctly
        """
        post = RoommatePost.objects.create(
            user=self.user,
            message="Original",
            date=date(2026, 1, 1),
        )
        post.message = "Updated"
        post.save()
        self.assertEqual(post.message, "Updated")

    @override_settings(TESTING=True)
    def test_serializer_handles_string_date(self):
        """
        Create a roommate post and checks that the serializer correctly formats the date
        """
        post = RoommatePost.objects.create(
            user=self.user,
            message="Hello",
            date="2026-03-01",
        )
        result = serialize_listing(post)
        self.assertEqual(result["created_at"], "1 Mar 2026")

    @override_settings(TESTING=False)  # Ensure the TESTING bypass is off
    @patch("socialPosts.signals.get_channel_layer")
    def test_new_post_broadcasts_to_feed(self, mock_get_channel_layer):
        """
        Tests that creation of a new roommate posts gets broadcasted
        """
        # Create a mock channel layer with a mock group_send
        mock_channel_layer = MagicMock()  # creates a mock channel layer (does not call redis)
        mock_channel_layer.group_send = AsyncMock()  # creates a mock group_send method for the channel layer
        mock_get_channel_layer.return_value = mock_channel_layer

        # Creates a new roommate post
        # This should trigger the signal and attempt to broadcast to the channel layer
        RoommatePost.objects.create(
            user=self.user,
            message="Test post",
            date=date(2026, 1, 1),
        )

        # Assert group_send was called once
        mock_channel_layer.group_send.assert_called_once()

        # Assert it was sent to the right group with the right shape
        args, kwargs = mock_channel_layer.group_send.call_args
        self.assertEqual(args[0], "listing_feed")
        self.assertEqual(args[1]["type"], "listing_created")
        self.assertIn("listing", args[1])

    # END OF NEW POST BROADCASTS TEST

    @override_settings(TESTING=False)
    @patch("socialPosts.signals.get_channel_layer")
    def test_broadcast_failure_does_not_affect_post_creation(self, mock_get_channel_layer):
        """
        Tests for when a broadcast fails
        Post will still be created and saved, but broadcast will fail silently
        """
        mock_channel_layer = MagicMock()
        mock_channel_layer.group_send = AsyncMock(side_effect=Exception("Failure"))
        mock_get_channel_layer.return_value = mock_channel_layer

        post = RoommatePost.objects.create(
            user=self.user,
            message="Test post",
            date=date(2026, 1, 1),
        )

        # Broadcast was attempted
        mock_channel_layer.group_send.assert_called_once()

        # But the post was still saved correctly
        self.assertEqual(post.message, "Test post")
        self.assertTrue(RoommatePost.objects.filter(id=post.id).exists())

    # END OF BROADCAST FAILURE TEST


def _mock_openai_response(content):
    """Build a MagicMock that quacks like an OpenAI ChatCompletion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.choices[0].message.tool_calls = None
    response.choices[0].finish_reason = "stop"
    return response


# AI Listing Agent
class AIListingAgentUnitTests(TestCase):

    def _sample_listing(self, **overrides):
        base = {
            "location": "123 Test St, Boulder, CO",
            "property_type": "Apartment",
            "rent": 1200,
            "beds": 2,
            "baths": 1,
            "sqft": 700,
            "neighborhood": "Downtown",
            "monthly_utilities": 200,
            "monthly_services": 80,
            "nearby_amenities": ["Gym", "Transit"],
            "total_monthly_cost": 1480,
        }
        base.update(overrides)
        return base

    def test_trim_candidates_assigns_sequential_ids_and_caps_count(self):
        """
        _trim_candidates should reindex listings starting at 0 and never send
        more than MAX_LISTINGS_SENT to the model.
        """
        # Generate one more listing than the cap to verify trimming
        listings = [self._sample_listing(rent=1000 + i) for i in range(MAX_LISTINGS_SENT + 3)]
        trimmed = _trim_candidates(listings)

        self.assertEqual(len(trimmed), MAX_LISTINGS_SENT)
        # IDs should be 0..N-1 in order
        self.assertEqual([c["id"] for c in trimmed], list(range(MAX_LISTINGS_SENT)))
        # Trimmed objects should expose the fields the model needs
        self.assertIn("address", trimmed[0])
        self.assertIn("total_monthly_cost", trimmed[0])
        self.assertIn("nearby_amenities", trimmed[0])

    def test_get_ai_recommendations_with_no_listings_skips_api_call(self):
        """
        With an empty candidate list we should short-circuit and never hit OpenAI.
        Patching _get_client lets us prove the API client was never asked for.
        """
        with patch("home.ai_listing_agent._get_client") as mock_get_client:
            result = get_ai_recommendations(preferences={"city": "Boulder"}, listings=[])

        self.assertTrue(result["ok"])
        self.assertEqual(result["picks"], [])
        self.assertIn("No listings matched", result["summary"])
        mock_get_client.assert_not_called()

    @patch("home.ai_listing_agent._get_client")
    def test_get_ai_recommendations_parses_valid_json_and_enriches_picks(self, mock_get_client):
        """
        When OpenAI returns valid JSON, picks should be enriched with the
        original listing object and the score should be clamped to 0-100.
        """
        ai_payload = json.dumps(
            {
                "summary": "1 strong match.",
                "picks": [
                    {
                        "id": 0,
                        "score": 150,  # out-of-range
                        "reasoning": "Great fit.",
                        "highlights": ["match: budget"],
                    }
                ],
                "advice": "Consider visiting in person.",
            }
        )
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = _mock_openai_response(ai_payload)
        mock_get_client.return_value = (fake_client, None)

        listings = [self._sample_listing(location="99 Curated Way")]
        result = get_ai_recommendations(
            preferences={"city": "Boulder", "state": "CO"},
            listings=listings,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"], "1 strong match.")
        self.assertEqual(len(result["picks"]), 1)

        pick = result["picks"][0]
        # Score clamped to the 0-100 range
        self.assertEqual(pick["score"], 100)
        self.assertEqual(pick["listing"]["location"], "99 Curated Way")
        self.assertEqual(pick["highlights"], ["match: budget"])
        # The OpenAI client should have been called exactly once
        fake_client.chat.completions.create.assert_called_once()

    @patch("home.ai_listing_agent._get_client")
    def test_get_ai_recommendations_handles_malformed_json(self, mock_get_client):
        """If the model returns hallucinated/improper output, the feature should fail gracefully (not crash)."""
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = _mock_openai_response("this is definitely not json {{{")
        mock_get_client.return_value = (fake_client, None)

        result = get_ai_recommendations(
            preferences={"city": "Boulder", "state": "CO"},
            listings=[self._sample_listing()],
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["picks"], [])
        self.assertIn("malformed", result["error"].lower())


# AI chatbot
IN_MEMORY_CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}


def _qs(**params):
    """Build a urlencoded querystring (bytes) for the consumer scope."""
    return urlencode(params).encode()


def _build_communicator(user, query_string=b""):
    communicator = WebsocketCommunicator(
        AIListingAgentConsumer.as_asgi(),
        "/ws/ai-agent/",
    )
    communicator.scope["user"] = user
    communicator.scope["query_string"] = query_string
    return communicator


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class AIListingAgentConsumerConnectTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sahana", password="pw12345678!")

    def test_anonymous_user_rejected_with_4401(self):
        """An unauthenticated connection is closed with code 4401."""

        async def body():
            communicator = _build_communicator(AnonymousUser())
            connected, close_code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(close_code, 4401)

        async_to_sync(body)()

    def test_missing_city_or_state_sends_error_then_closes(self):
        """Connect with no city+state: accept, emit error, close with 4400."""

        async def body():
            communicator = _build_communicator(
                self.user,
                _qs(intent="for_rent"),  # no city/state
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            msg = await communicator.receive_json_from()
            self.assertEqual(msg["type"], "error")
            self.assertIn("property search", msg["error"].lower())
            await communicator.disconnect()

        async_to_sync(body)()

    def test_happy_connect_sends_ready_event_with_listings(self):
        """Valid user + city/state: seeds history, emits 'ready' event."""
        fake_listings = [
            {
                "location": "100 Test St, Boulder, CO",
                "rent": 1200,
                "property_type": "Apartment",
                "nearby_amenities": ["Gym"],
                "total_monthly_cost": 1480,
                "beds": 2,
                "baths": 1,
                "sqft": 700,
                "neighborhood": "Downtown",
                "monthly_utilities": 200,
                "monthly_services": 80,
            }
        ]

        async def body():
            with patch(
                "home.views.build_enriched_listings",
                return_value=fake_listings,
            ):
                communicator = _build_communicator(
                    self.user,
                    _qs(city="Boulder", state="CO", intent="for_rent"),
                )
                connected, _ = await communicator.connect()
                self.assertTrue(connected)

                ready = await communicator.receive_json_from()
                self.assertEqual(ready["type"], "ready")
                self.assertEqual(ready["filters"]["city"], "Boulder")
                self.assertEqual(ready["filters"]["state"], "CO")
                self.assertEqual(ready["listings"], fake_listings)
                self.assertTrue("1 listings" in ready["greeting"] or "Boulder" in ready["greeting"])
                await communicator.disconnect()

        async_to_sync(body)()

    def test_connect_swallows_build_enriched_listings_exception(self):
        """If build_enriched_listings raises, listings is [] and 'ready' still fires."""

        async def body():
            with patch(
                "home.views.build_enriched_listings",
                side_effect=RuntimeError("rentcast down"),
            ):
                communicator = _build_communicator(
                    self.user,
                    _qs(city="Boulder", state="CO"),
                )
                connected, _ = await communicator.connect()
                self.assertTrue(connected)

                ready = await communicator.receive_json_from()
                self.assertEqual(ready["type"], "ready")
                self.assertEqual(ready["listings"], [])
                await communicator.disconnect()

        async_to_sync(body)()


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class AIListingAgentConsumerReceiveTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sahana", password="pw12345678!")

    def _build(self):
        return _build_communicator(self.user, _qs(city="Boulder", state="CO"))

    def test_receive_non_json_sends_error(self):
        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]):
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()  # 'ready'

                await communicator.send_to(text_data="not-json {{{")
                err = await communicator.receive_json_from()
                self.assertEqual(err["type"], "error")
                self.assertIn("parse", err["error"].lower())
                await communicator.disconnect()

        async_to_sync(body)()

    def test_receive_unknown_type_sends_error(self):
        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]):
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()  # 'ready'

                await communicator.send_to(text_data=json.dumps({"type": "weird", "text": "hi"}))
                err = await communicator.receive_json_from()
                self.assertEqual(err["type"], "error")
                self.assertIn("unknown", err["error"].lower())
                await communicator.disconnect()

        async_to_sync(body)()

    def test_receive_empty_text_is_silently_ignored(self):
        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]):
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()  # 'ready'

                await communicator.send_to(text_data=json.dumps({"type": "user_message", "text": "   "}))
                self.assertTrue(await communicator.receive_nothing(timeout=0.3))
                await communicator.disconnect()

        async_to_sync(body)()

    def test_receive_happy_path_echoes_and_returns_assistant_message(self):
        """user_message -> echo, thinking, assistant_message."""
        fake_turn_result = {
            "ok": True,
            "reply": "Here's what I think.",
            "refined": False,
            "filters": {},
            "listings": [],
            "error": None,
        }

        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]), patch(
                "home.ai_listing_agent.chat_turn",
                return_value=fake_turn_result,
            ):
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()  # 'ready'

                await communicator.send_to(text_data=json.dumps({"type": "user_message", "text": "hi"}))

                echo = await communicator.receive_json_from()
                self.assertEqual(echo, {"type": "user_message", "text": "hi"})

                thinking = await communicator.receive_json_from()
                self.assertEqual(thinking, {"type": "thinking"})

                reply = await communicator.receive_json_from()
                self.assertEqual(reply["type"], "assistant_message")
                self.assertEqual(reply["text"], "Here's what I think.")
                await communicator.disconnect()

        async_to_sync(body)()

    def test_receive_truncates_text_over_2000_chars(self):
        fake_turn_result = {
            "ok": True,
            "reply": "ok",
            "refined": False,
            "filters": {},
            "listings": [],
            "error": None,
        }
        long_text = "a" * 2500

        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]), patch(
                "home.ai_listing_agent.chat_turn",
                return_value=fake_turn_result,
            ):
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()  # 'ready'

                await communicator.send_to(text_data=json.dumps({"type": "user_message", "text": long_text}))

                echo = await communicator.receive_json_from()
                self.assertEqual(echo["type"], "user_message")
                self.assertEqual(len(echo["text"]), 2000)
                await communicator.receive_json_from()  # thinking
                await communicator.receive_json_from()  # assistant_message
                await communicator.disconnect()

        async_to_sync(body)()

    def test_receive_refine_path_emits_listings_updated_and_logs_history(self):
        new_listings = [{"location": "999 New Place"}]
        fake_turn_result = {
            "ok": True,
            "reply": "I updated your search.",
            "refined": True,
            "filters": {},
            "listings": new_listings,
            "error": None,
        }

        # chat_turn is expected to mutate the `listings` arg in place
        def fake_chat_turn(history, filters, listings, refine):
            listings[:] = new_listings
            return fake_turn_result

        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]), patch(
                "home.ai_listing_agent.chat_turn",
                side_effect=fake_chat_turn,
            ):
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()  # 'ready'

                await communicator.send_to(text_data=json.dumps({"type": "user_message", "text": "cheaper"}))

                await communicator.receive_json_from()  # echo
                await communicator.receive_json_from()  # thinking

                listings_evt = await communicator.receive_json_from()
                self.assertEqual(listings_evt["type"], "listings_updated")
                self.assertEqual(listings_evt["listings"], new_listings)

                reply_evt = await communicator.receive_json_from()
                self.assertEqual(reply_evt["type"], "assistant_message")
                await communicator.disconnect()

        before = SearchHistory.objects.count()
        async_to_sync(body)()
        self.assertEqual(SearchHistory.objects.count(), before + 1)

    def test_receive_chat_turn_failure_sends_error(self):
        fake_turn_result = {
            "ok": False,
            "reply": "",
            "refined": False,
            "filters": {},
            "listings": [],
            "error": "LLM blew up",
        }

        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]), patch(
                "home.ai_listing_agent.chat_turn",
                return_value=fake_turn_result,
            ):
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()  # 'ready'

                await communicator.send_to(text_data=json.dumps({"type": "user_message", "text": "hi"}))
                await communicator.receive_json_from()  # echo
                await communicator.receive_json_from()  # thinking
                err = await communicator.receive_json_from()
                self.assertEqual(err["type"], "error")
                self.assertIn("LLM blew up", err["error"])
                await communicator.disconnect()

        async_to_sync(body)()

    def test_disconnect_runs_cleanly(self):
        """disconnect() is a no-op but must not raise."""

        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]):
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()
                await communicator.disconnect()

        async_to_sync(body)()


# ----------------------------- SPRINT 4 ---------------------------------#
class AgentAds(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="RealAgent", password="password")

        # Creates a verified agent
        self.profile = self.user.profile
        self.profile.is_authenticated = True
        self.profile.save()

    def test_agent_ad_model_fields_are_filled(self):
        """
        Creates a new agent ad object
        Checks that the fields have been filled with the correct info
        """
        new_agent = AgentAd.objects.create(
            agent=self.user,
            headline="Headline",
            city="Colorado Springs",
            state="CO",
            brokerage="Brokerage",
            license_number=123456,
        )

        self.assertEqual(new_agent.agent.username, "RealAgent")
        self.assertTrue(new_agent.agent.is_authenticated)
        self.assertEqual(new_agent.headline, "Headline")
        self.assertEqual(new_agent.brokerage, "Brokerage")


# Gaurdrails for AI Chatbot
class GuardrailUnitTests(TestCase):
    """Server-side topic + profanity gate, no LLM involved."""

    def test_housing_question_passes(self):
        result = check_message_guardrails("Which of these apartments has the lowest rent?")
        self.assertTrue(result["ok"])

    def test_short_followup_passes_even_without_keywords(self):
        for text in ["why?", "ok", "the cheaper one", "tell me more"]:
            self.assertTrue(check_message_guardrails(text)["ok"], text)

    def test_long_off_topic_message_is_blocked(self):
        result = check_message_guardrails("Can you write me a python function that solves my calculus homework?")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "off_topic")
        self.assertIn("place to live", result["reply"].lower())

    def test_off_topic_with_housing_word_passes(self):
        result = check_message_guardrails("Can I cook spicy recipes in this apartment without setting off alarms?")
        self.assertTrue(result["ok"])

    def test_profanity_is_blocked(self):

        with patch.object(
            __import__("home.ai_listing_agent", fromlist=["_is_profane"]),
            "_is_profane",
            return_value=True,
        ):
            result = check_message_guardrails("you are a [slur]")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "profanity")


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class GuardrailConsumerTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sahana", password="pw12345678!")

    def _build(self):
        return _build_communicator(self.user, _qs(city="Boulder", state="CO"))

    def test_ready_event_includes_language_notice(self):
        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]):
                communicator = self._build()
                await communicator.connect()
                ready = await communicator.receive_json_from()
                self.assertEqual(ready["type"], "ready")
                self.assertIn("notice", ready)
                self.assertIn("respectful", ready["notice"].lower())
                await communicator.disconnect()

        async_to_sync(body)()

    def test_off_topic_message_is_blocked_without_calling_llm(self):
        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]), patch(
                "home.ai_listing_agent.chat_turn"
            ) as mock_chat:
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()  # 'ready'

                await communicator.send_to(
                    text_data=json.dumps(
                        {"type": "user_message", "text": "Write me a python script to do my calculus homework."}
                    )
                )

                echo = await communicator.receive_json_from()
                self.assertEqual(echo["type"], "user_message")

                blocked = await communicator.receive_json_from()
                self.assertEqual(blocked["type"], "system_message")
                self.assertEqual(blocked["reason"], "off_topic")

                self.assertTrue(await communicator.receive_nothing(timeout=0.3))
                mock_chat.assert_not_called()
                await communicator.disconnect()

        async_to_sync(body)()

    def test_blocked_message_does_not_pollute_history(self):

        captured = {}

        def fake_chat_turn(history, filters, listings, refine):

            captured["user_msgs"] = [
                m["content"]
                for m in history
                if m["role"] == "user" and not m["content"].startswith("Here is the starting context")
            ]
            return {
                "ok": True,
                "reply": "ok",
                "refined": False,
                "filters": filters,
                "listings": listings,
                "error": None,
            }

        async def body():
            with patch("home.views.build_enriched_listings", return_value=[]), patch(
                "home.ai_listing_agent.chat_turn", side_effect=fake_chat_turn
            ):
                communicator = self._build()
                await communicator.connect()
                await communicator.receive_json_from()  # 'ready'

                # Blocked message
                await communicator.send_to(
                    text_data=json.dumps(
                        {
                            "type": "user_message",
                            "text": "translate this to spanish: hello world how are you doing today",
                        }
                    )
                )
                await communicator.receive_json_from()  # echo
                await communicator.receive_json_from()  # system_message

                # Legit message
                await communicator.send_to(
                    text_data=json.dumps({"type": "user_message", "text": "Which apartment has the cheapest rent?"})
                )
                await communicator.receive_json_from()  # echo
                await communicator.receive_json_from()  # thinking
                await communicator.receive_json_from()  # assistant_message
                await communicator.disconnect()

        async_to_sync(body)()
        self.assertEqual(
            captured["user_msgs"],
            ["Which apartment has the cheapest rent?"],
            "Blocked message should not appear in history sent to LLM",
        )
