import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase

# Mock API property data (to prevent unnecessary API calls)
MOCK_API_PROPERTIES = [
    {
        "id": "p1",
        "addressLine1": "100 Cheap St",
        "formattedAddress": "100 Cheap St, Boulder, CO",
        "city": "Boulder",
        "state": "CO",
        "price": 900,
        "latitude": 40.01,
        "longitude": -105.27,
        "propertyType": "apartment",
    },
    {
        "id": "p2",
        "addressLine1": "200 Pricey Ave",
        "formattedAddress": "200 Pricey Ave, Boulder, CO",
        "city": "Boulder",
        "state": "CO",
        "price": 3000,
        "latitude": 40.02,
        "longitude": -105.28,
        "propertyType": "house",
    },
]


# Registration
class RegisterTest(TestCase):
    def test_register_page_success(self):
        """Registration/login page loads without crashing."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user(self):
        """Submitting valid registration data creates a user in the database."""
        self.client.post(
            "/register/",
            {
                "username": "testuser",
                "password1": "StrongPassword@123",
                "password2": "StrongPassword@123",
            },
        )
        self.assertTrue(User.objects.filter(username="testuser").exists())


# Login
class LoginTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="StrongPassword@123")

    def test_login_page_success(self):
        """Login page is accessible and doesn't crash."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_valid_login_redirect(self):
        """Valid credentials log the user in and trigger a redirect."""
        response = self.client.post(
            "/",
            {
                "username": "testuser",
                "password": "StrongPassword@123",
            },
        )
        self.assertEqual(response.status_code, 302)


# Property Filter (map-based, backed by Rentcast API)
# Filtering now happens on /map/ with API results rendered as map markers.
# Tests use a mock so no real API calls are made.


class PropertyFilterTests(TestCase):
    @patch("home.views.get_properties", return_value=[])
    def test_map_page_loads_without_filters(self, mock_api):
        """Map page returns 200 with no search parameters."""
        response = self.client.get("/map/")
        self.assertEqual(response.status_code, 200)

    @patch("home.views.get_properties", return_value=MOCK_API_PROPERTIES)
    def test_map_returns_api_properties_in_context(self, mock_api):
        """API results are placed in the template context as a list."""
        response = self.client.get("/map/", {"city": "Boulder", "state": "CO"})
        self.assertEqual(response.status_code, 200)
        map_data = response.context["properties"]
        self.assertEqual(len(map_data), 2)

    @patch("home.views.get_properties", return_value=[])
    def test_filter_params_accepted_without_error(self, mock_api):
        """Passing budget and type filters to the map page does not crash."""
        response = self.client.get(
            "/map/",
            {
                "city": "Boulder",
                "state": "CO",
                "budget": "800-1000",
                "type": "apartment",
            },
        )
        self.assertEqual(response.status_code, 200)


# Roommate Postings
class RoommatePostingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="poster", password="Password123!")
        self.other_user = User.objects.create_user(username="other", password="Password123!")
        self.client.login(username="poster", password="Password123!")

    def _create_post(self):
        from home.models import RoommatePost

        return RoommatePost.objects.create(
            user=self.user,
            message="Looking for a roommate near campus.",
            date="2026-03-11",
            status="open",
            rent=1000,
            property_type="apartment",
        )

    def test_roommate_list_returns_200(self):
        response = self.client.get("/roommate-posts/")
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_cannot_access_create(self):
        self.client.logout()
        response = self.client.get("/roommate-posts/create/")
        self.assertNotEqual(response.status_code, 200)

    def test_create_post_saves_to_database(self):
        from home.models import RoommatePost

        self.client.post(
            "/roommate-posts/create/",
            {
                "message": "Looking for a roommate near campus.",
                "date": "2026-03-11",
                "status": "open",
                "rent": 1000,
                "property_type": "apartment",
            },
        )
        self.assertEqual(RoommatePost.objects.count(), 1)

    def test_owner_can_delete_post(self):
        from home.models import RoommatePost

        post = self._create_post()
        self.client.post(f"/roommate-posts/{post.id}/delete/")
        self.assertEqual(RoommatePost.objects.count(), 0)

    def test_non_owner_cannot_delete_post(self):
        from home.models import RoommatePost

        post = self._create_post()
        self.client.login(username="other", password="Password123!")
        self.client.post(f"/roommate-posts/{post.id}/delete/")
        self.assertEqual(RoommatePost.objects.count(), 1)

    def test_owner_can_close_post(self):

        post = self._create_post()
        self.client.post(f"/roommate-posts/{post.id}/close/")
        post.refresh_from_db()
        self.assertEqual(post.status, "closed")

    def test_non_owner_cannot_close_post(self):

        post = self._create_post()
        self.client.login(username="other", password="Password123!")
        self.client.post(f"/roommate-posts/{post.id}/close/")
        post.refresh_from_db()
        self.assertEqual(post.status, "open")


# Property Map
class PropertyMapTest(TestCase):

    def test_property_map_endpoint_returns_200(self):
        """Map page is reachable with no params."""
        response = self.client.get("/map/")
        self.assertEqual(response.status_code, 200)

    @patch("home.views.get_properties", return_value=MOCK_API_PROPERTIES)
    def test_map_response_includes_coordinates_for_listings(self, mock_api):
        """Each listing returned by the API must carry lat/lng in the context."""
        response = self.client.get("/map/", {"city": "Boulder", "state": "CO"})
        self.assertEqual(response.status_code, 200)

        # context['properties'] is a list of map markers
        map_data = response.context["properties"]
        self.assertTrue(len(map_data) > 0, "map_data is empty")

        first = map_data[0]
        self.assertIn("latitude", first, "latitude missing from map property")
        self.assertIn("longitude", first, "longitude missing from map property")


# Keyword Search
# The search endpoint lives at /roommate-posts/search/.
# It currently returns all local Property records.
class KeywordSearchTests(TestCase):
    def setUp(self):
        from home.models import Property

        Property.objects.create(
            title="Cozy Studio near CU Campus",
            price=900,
            property_type="studio",
            listing_type="rent",
            location="Boulder, CO",
        )
        Property.objects.create(
            title="Downtown Loft with Rooftop",
            price=1800,
            property_type="apartment",
            listing_type="rent",
            location="Denver, CO",
        )

    def test_keyword_search_endpoint_returns_200(self):
        """Search page is reachable and does not crash."""
        response = self.client.get("/roommate-posts/search/", {"q": "studio"})
        self.assertEqual(response.status_code, 200)

    def test_search_lists_all_properties(self):
        """Without keyword filtering, all local properties appear in results."""
        response = self.client.get("/roommate-posts/search/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cozy Studio near CU Campus")
        self.assertContains(response, "Downtown Loft with Rooftop")

    def test_search_with_unknown_keyword_still_returns_200(self):
        """A keyword that matches nothing should not crash the page."""
        response = self.client.get("/roommate-posts/search/", {"q": "xyznonexistent"})
        self.assertEqual(response.status_code, 200)


# Instant Messaging
# Inbox: /chat/inbox/ (login required)
# Chat room: /chat/<posting_id>/ (login required)
# Messages are sent over WebSocket; persistence is via chat.models.Message.
class InstantMessagingTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="Pass123!")
        self.bob = User.objects.create_user(username="bob", password="Pass123!")
        self.client.login(username="alice", password="Pass123!")

    def _create_post(self, owner=None):
        from home.models import RoommatePost

        return RoommatePost.objects.create(
            user=owner or self.bob,
            message="Need a roommate.",
            date="2026-03-11",
            status="open",
            rent=1000,
            property_type="apartment",
        )

    def test_inbox_returns_200_for_authenticated_user(self):
        """Authenticated user can reach the chat inbox."""
        response = self.client.get("/chat/inbox/")
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_cannot_access_inbox(self):
        """Unauthenticated users are redirected away from the inbox."""
        self.client.logout()
        response = self.client.get("/chat/inbox/")
        self.assertNotEqual(response.status_code, 200)

    def test_chat_room_accessible_for_authenticated_user(self):
        """Authenticated user can open the chat room for a posting."""
        post = self._create_post()
        response = self.client.get(f"/chat/{post.id}/{self.alice.id}/")
        self.assertEqual(response.status_code, 200)

    def test_message_record_persists_to_database(self):
        """A Message object can be created and retrieved for a posting."""
        from chat.models import Message

        post = self._create_post()
        Message.objects.create(
            posting_id=post.id,
            sender=self.alice,
            sender_label="user",
            content="Hi, is the room still available?",
        )
        self.assertEqual(Message.objects.filter(posting_id=post.id).count(), 1)


# Two-Factor Authentication
class TwoFactorAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="secureuser", password="StrongPass@99")
        self.client.login(username="secureuser", password="StrongPass@99")

    def test_2fa_setup_page_returns_200(self):
        """2FA setup page is accessible to authenticated users."""
        response = self.client.get("/auth/2fa/setup/")
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_cannot_access_2fa_setup(self):
        """Unauthenticated users cannot reach the 2FA setup page."""
        self.client.logout()
        response = self.client.get("/auth/2fa/setup/")
        self.assertNotEqual(response.status_code, 200)

    def test_2fa_setup_provides_totp_secret_in_context(self):
        """Setup page exposes a non-empty TOTP secret for QR generation."""
        response = self.client.get("/auth/2fa/setup/")
        self.assertIn("totp_secret", response.context)
        self.assertTrue(len(response.context["totp_secret"]) > 0)


# ----------------------------- SPRINT 3 ---------------------------------#
class MapPriceFilter(TestCase):
    """
    Tests the integration of the price filter on the map
    """

    @patch("home.views.get_properties", return_value=MOCK_API_PROPERTIES)
    def test_price_filter_applies_correctly_and_returns_correct_markers(self, mock_properties):
        """
        Parameters: self
        Applies a price filter to the map (Utilizes the MOCK_API_PROPERTIES initialized above)
        Asserts if the page returns 200
        """
        # Simulates possible input from user
        response = self.client.get("/map/", {"price_filter": "Total Cost: Low to High"})

        # Checks status code to ensure filtering was successful and page loaded correctly
        self.assertEqual(response.status_code, 200)

    # END OF PRICE FILTER TEST


class RealTimePosts(TestCase):
    def tests_for_real_time_posts_fetch(self):
        """
        Checks that the posts will load on the page
        Checks response from HTML file
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "feedList")
        self.assertContains(response, "feedStatus")

    # END OF REAL-TIME POSTS FETCH TEST


# For AI-listing
MOCK_ENRICHED_LISTINGS = [
    {
        "location": "100 Pearl St, Boulder, CO",
        "property_type": "Apartment",
        "rent": 1200,
        "beds": 2,
        "baths": 1,
        "sqft": 750,
        "neighborhood": "Downtown",
        "monthly_utilities": 210,
        "monthly_services": 95,
        "nearby_amenities": ["Gym", "Transit"],
        "total_monthly_cost": 1505,
        "latitude": 40.01,
        "longitude": -105.27,
    },
]

# A valid mock JSON payload that looks like it's been generated by the GPT model.
MOCK_AI_JSON = json.dumps(
    {
        "summary": "1 strong match for your filters.",
        "picks": [
            {
                "id": 0,
                "score": 88,
                "reasoning": "Matches your budget and is near transit.",
                "highlights": ["match: budget", "match: transit nearby"],
            }
        ],
        "advice": "",
    }
)


# Mock response
def _mock_openai_response(content):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.choices[0].message.tool_calls = None
    response.choices[0].finish_reason = "stop"
    return response


# AI Listing Agent - page load + auth
# The /ai-agent/ endpoint returns a JsonResponse (always 200). Auth is enforced.
class AIListingAgentPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aiuser", password="Password123!")

    def test_ai_agent_endpoint_requires_authentication(self):
        """Unauthenticated users get an error JSON."""
        response = self.client.get(
            "/ai-agent/",
            {
                "city": "Boulder",
                "state": "CO",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertIn("Sign in", body["error"])
        self.assertEqual(body["picks"], [])

    @patch("home.views.build_enriched_listings", return_value=MOCK_ENRICHED_LISTINGS)
    @patch("home.ai_listing_agent._get_client")
    def test_ai_agent_loads_for_authenticated_user(self, mock_get_client, mock_listings):
        """Logged-in user with valid filters gets a 200 + ok=True payload."""
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = _mock_openai_response(MOCK_AI_JSON)
        mock_get_client.return_value = (fake_client, None)

        self.client.login(username="aiuser", password="Password123!")
        response = self.client.get(
            "/ai-agent/",
            {
                "city": "Boulder",
                "state": "CO",
                "intent": "for_rent",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(len(body["picks"]), 1)


# ----------------------------- SPRINT 4 ---------------------------------#
class AgentAds(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="agent", password="test")

        # Creates an agent profile for the user
        self.profile = self.user.profile
        self.profile.is_agent_verified = True  # verifies user as agent
        self.profile.save()

    def test_agent_ads_verified_user(self):
        """
        When user is verified agent, agent ads list page loads
        """
        self.client.login(username="agent", password="test")  # logs in to verified user
        response = self.client.get("/agents/ads/")  # agent ad list URL
        self.assertEqual(response.status_code, 200)  # verified agent can view

    def test_agent_ads_unverified_user(self):
        """
        When user is not agent but still logged in, denies access
        """
        self.profile.is_agent_verified = False  # makes user unverified agent
        self.profile.save()

        self.client.login(username="agent", password="test")  # logs in

        response = self.client.get("/agents/ads/")  # agent ad list URL
        self.assertEqual(response.status_code, 403)  # forbidden user

    def test_agent_ads_not_logged_in(self):
        """
        When not authenticated (no log in), redirects to homepage
        """
        response = self.client.get("/agents/ads/")  # agent ad list URL
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.url)  # redirected to homepage
