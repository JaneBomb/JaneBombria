import json
from unittest.mock import patch

from behave import given, then, when
from django.contrib.auth.models import User
from home.models import Property, RoommatePost


# Registration
# Given Statement
@given("I am on the homepage")
def step_on_homepage(context):
    context.response = context.test.client.get("/")


# When Statement
@when('I submit the registration form with username "{username}" and password "{password}"')
def step_register(context, username, password):
    context.test.client.post(
        "/register/",
        {
            "username": username,
            "password1": password,
            "password2": password,
        },
    )


# When Statement
@when("I submit the registration form with mismatched passwords")
def step_register_mismatch(context):
    context.test.client.post(
        "/register/",
        {
            "username": "baduser",
            "password1": "StrongPassword@123",
            "password2": "DifferentPassword@123",
        },
    )


# Then Statement
@then('a user with username "{username}" exists in the database')
def step_user_exists(context, username):
    assert User.objects.filter(username=username).exists()


# Then Statement
@then("no new user is created")
def step_no_user_created(context):
    assert not User.objects.filter(username="baduser").exists()


# Shared auth helpers
# Given Statement
@given('a user "{username}" exists and is logged in')
def step_user_logged_in(context, username):
    user, _ = User.objects.get_or_create(username=username)
    user.set_password("Password123!")
    user.save()
    context.user = user
    context.test.client.login(username=username, password="Password123!")


# Given Statement
@given('a logged-in user "{username}" with email "{email}"')
def step_user_with_email_logged_in(context, username, email):
    user, _ = User.objects.get_or_create(username=username)
    user.set_password("Password123!")
    user.email = email
    user.save()
    context.user = user
    context.test.client.login(username=username, password="Password123!")


# Given Statement
@given('user "{username}" is logged in')
def step_other_user_logged_in(context, username):
    user, _ = User.objects.get_or_create(username=username)
    user.set_password("Password123!")
    user.save()
    context.test.client.login(username=username, password="Password123!")


# Given Statement
@given("the user logs out")
def step_user_logs_out(context):
    context.test.client.logout()


# Roommate Postings
# Given Statement
@given('a roommate post exists for "{username}"')
def step_post_exists(context, username):
    user = User.objects.get(username=username)
    context.post = RoommatePost.objects.create(
        user=user,
        message="Test post message",
        date="2026-03-11",
        status="open",
        rent=1000,
        property_type="apartment",
    )


# When Statement
@when('I submit a roommate post with message "{message}"')
def step_create_post(context, message):
    context.test.client.post(
        "/roommate-posts/create/",
        {
            "message": message,
            "date": "2026-03-11",
            "status": "open",
            "rent": 1000,
            "property_type": "apartment",
        },
    )


# When Statement
@when("I close the post")
def step_close_post(context):
    context.test.client.post(f"/roommate-posts/{context.post.id}/close/")


# When Statement
@when("I delete the post")
def step_delete_post(context):
    context.test.client.post(f"/roommate-posts/{context.post.id}/delete/")


# When Statement
@when('"{username}" tries to delete the post')
def step_other_delete_post(context, username):
    context.test.client.post(f"/roommate-posts/{context.post.id}/delete/")


# Then Statement
@then('the post "{message}" appears on the listings page')
def step_post_in_listings(context, message):
    response = context.test.client.get("/roommate-posts/")
    assert message in response.content.decode()


# Then Statement
@then('the post status is "{status}"')
def step_post_status(context, status):
    context.post.refresh_from_db()
    assert context.post.status == status


# Then Statement
@then("the post no longer exists in the database")
def step_post_deleted(context):
    assert not RoommatePost.objects.filter(id=context.post.id).exists()


# Then Statement
@then("the post still exists in the database")
def step_post_still_exists(context):
    assert RoommatePost.objects.filter(id=context.post.id).exists()


# Property Map Search (replacing old property-filter steps)
# Given Statement
@given('the Rentcast API returns a property at "{address}"')
def step_api_returns_property(context, address):
    context.mock_api_result = [
        {
            "formattedAddress": address,
            "latitude": 40.01,
            "longitude": -105.27,
            "propertyType": "Apartment",
            "price": 1200,
        }
    ]


# When Statement
@when("I visit the map page")
def step_visit_map(context):
    context.response = context.test.client.get("/map/")


# When Statement
@when('I search the map with city "{city}" and state "{state}"')
def step_search_map_city_state(context, city, state):
    api_result = getattr(context, "mock_api_result", [])
    with patch("home.views.get_properties", return_value=api_result):
        context.response = context.test.client.get("/map/", {"city": city, "state": state})


# When Statement
@when('I search the map with city "{city}" and no state')
def step_search_map_city_only(context, city):
    with patch("home.views.get_properties", return_value=[]):
        context.response = context.test.client.get("/map/", {"city": city})


# When Statement
@when('I search the map with city "{city}" state "{state}" and budget "{budget}"')
def step_search_map_with_budget(context, city, state, budget):
    api_result = getattr(context, "mock_api_result", [])
    with patch("home.views.get_properties", return_value=api_result):
        context.response = context.test.client.get("/map/", {"city": city, "state": state, "budget": budget})


# Then Statement
@then("the map page returns 200")
def step_map_200(context):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"


# Then Statement
@then("the map context has at least 1 property")
def step_map_has_properties(context):
    data = context.response.context["properties"]
    if isinstance(data, str):
        data = json.loads(data)
    assert len(data) >= 1, f"Expected >= 1 property, got {len(data)}"


# Then Statement
@then("the map context has 0 properties")
def step_map_has_no_properties(context):
    data = context.response.context["properties"]
    if isinstance(data, str):
        data = json.loads(data)
    assert len(data) == 0, f"Expected 0 properties, got {len(data)}"


# Keyword Search
# Given Statement
@given("the following properties exist:")
def step_properties_exist(context):
    for row in context.table:
        Property.objects.create(
            title=row["title"],
            price=int(row["price"]),
            property_type=row["type"],
            listing_type="rent",
            location=row["location"],
        )


# When Statement
@when('I search by keyword "{keyword}"')
def step_search_keyword(context, keyword):
    context.response = context.test.client.get("/roommate-posts/search/", {"q": keyword})


# When Statement
@when("I visit the search page with no keyword")
def step_visit_search_no_keyword(context):
    context.response = context.test.client.get("/roommate-posts/search/")


# Then Statement
@then("the search page returns 200")
def step_search_200(context):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"


# Then Statement
@then('I see "{text}" in the results')
def step_see_in_results(context, text):
    assert text in context.response.content.decode(), f'Expected "{text}" in response but not found'


# Then Statement
@then('I do not see "{text}" in the results')
def step_not_see_in_results(context, text):
    assert text not in context.response.content.decode(), f'Expected "{text}" NOT in response but it was found'


# Instant Messaging
# Given Statement
@given('a message "{content}" is sent on the posting')
def step_message_sent(context, content):
    from chat.models import Message

    sender = getattr(context, "user", None)
    Message.objects.create(
        posting_id=context.post.id,
        inquirer_id=sender.id if sender else None,
        sender=sender,
        sender_label=sender.username if sender else "anonymous",
        content=content,
    )


# When Statement
@when("I visit the chat inbox")
def step_visit_inbox(context):
    context.response = context.test.client.get("/chat/inbox/")


# When Statement
@when("I open the chat room for the posting")
def step_open_chat_room(context):
    user = getattr(context, "user", None)
    user_id = user.id if user else 0
    context.response = context.test.client.get(f"/chat/{context.post.id}/{user_id}/")


# Then Statement
@then("the inbox returns 200")
def step_inbox_200(context):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"


# Then Statement
@then("the chat room returns 200")
def step_chat_room_200(context):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"


# Then Statement
@then("I am redirected away from the page")
def step_redirected(context):
    assert context.response.status_code != 200, f"Expected redirect, got {context.response.status_code}"


# Then Statement
@then("the inbox shows {count:d} message for that post")
def step_inbox_message_count(context, count):
    posts_with_chats = context.response.context["posts_with_chats"]
    assert len(posts_with_chats) > 0, "No posts in inbox"
    actual = posts_with_chats[0]["message_count"]
    assert actual == count, f"Expected {count} messages, got {actual}"


# Two-Factor Authentication
# When Statement
@when("I visit the 2FA setup page")
def step_visit_2fa(context):
    context.response = context.test.client.get("/auth/2fa/setup/")


# Then Statement
@then("the setup page returns 200")
def step_2fa_200(context):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"


# Then Statement
@then('the response context contains a non-empty "{key}"')
def step_context_has_key(context, key):
    value = context.response.context.get(key)
    assert value, f'Expected non-empty "{key}" in context, got: {value}'


# When Statement
@when("I submit a wrong TOTP code on the setup page")
def step_submit_wrong_totp(context):
    import pyotp

    secret = pyotp.random_base32()
    session = context.test.client.session
    session["totp_secret"] = secret
    session.save()
    context.response = context.test.client.post(
        "/auth/2fa/setup/",
        {
            "method": "totp_verify",
            "otp_code": "000000",
        },
    )


# Then Statement
@then("the setup page shows a TOTP error")
def step_totp_error_shown(context):
    assert context.response.status_code == 200
    assert "totp_error" in context.response.context, "Expected totp_error in context"


# When Statement
@when("I request an email verification code")
def step_request_email_code(context):
    with patch("django.core.mail.send_mail"):
        context.response = context.test.client.post("/auth/2fa/setup/", {"method": "email_send"})


# Then Statement
@then("the setup page confirms the email was sent")
def step_email_sent_confirmed(context):
    assert context.response.status_code == 200
    assert context.response.context.get("email_sent"), "Expected email_sent to be truthy in context"


# Property Map — extra steps
# When Statement
@when('I search the map with city "{city}" state "{state}" and type "{ptype}"')
def step_search_map_with_type(context, city, state, ptype):
    api_result = getattr(context, "mock_api_result", [])
    with patch("home.views.get_properties", return_value=api_result):
        context.response = context.test.client.get("/map/", {"city": city, "state": state, "type": ptype})


# Given Statement
@given("a local property with coordinates exists")
def step_local_property_with_coords(context):
    from home.models import Property

    Property.objects.create(
        title="Local Prop",
        location="Boulder, CO",
        listing_type="rent",
        property_type="apartment",
        price=1000,
        latitude=40.01,
        longitude=-105.27,
    )


# Then Statement
@then("every property in the map context has coordinates")
def step_all_have_coords(context):
    import json

    data = context.response.context["properties"]
    if isinstance(data, str):
        data = json.loads(data)
    assert len(data) > 0, "No properties in map context"
    for prop in data:
        assert "latitude" in prop, f"Missing latitude: {prop}"
        assert "longitude" in prop, f"Missing longitude: {prop}"


# Map Filter By Price
# When Statement
@when('I submit a map search with price range "{budget}" for "{city}, {state}"')
def step_search_map_capture_price(context, budget, city, state):
    from unittest.mock import MagicMock

    api_result = getattr(context, "mock_api_result", [])
    mock = MagicMock(return_value=api_result)
    with patch("home.views.get_properties", mock):
        context.response = context.test.client.get("/map/", {"city": city, "state": state, "budget": budget})
    context.get_properties_mock = mock


# Then Statement
@then("the property API was called with min_price {mn:d} and max_price {mx:d}")
def step_api_called_with_prices(context, mn, mx):
    mock = context.get_properties_mock
    assert mock.called, "get_properties was never called"
    kwargs = mock.call_args.kwargs
    assert kwargs.get("min_price") == mn, f"Expected min_price={mn}, got {kwargs.get('min_price')}"
    assert kwargs.get("max_price") == mx, f"Expected max_price={mx}, got {kwargs.get('max_price')}"


# Social Posts Feed
# When Statement
@when("I serialize the post for the social feed")
def step_serialize_post(context):
    from socialPosts.serializers import serialize_listing

    context.serialized = serialize_listing(context.post)


# Then Statement
@then('the serialized listing has status "{status}"')
def step_serialized_status(context, status):
    assert context.serialized["status"] == status, f"Expected status={status}, got {context.serialized['status']}"


# Then Statement
@then("the serialized listing has rent {rent:d}")
def step_serialized_rent(context, rent):
    assert context.serialized["rent"] == float(rent), f"Expected rent={float(rent)}, got {context.serialized['rent']}"


# Then Statement
@then('the serialized listing name is "{name}"')
def step_serialized_name(context, name):
    assert context.serialized["name"] == name, f"Expected name={name}, got {context.serialized['name']}"


# AI Curated Listings
# Given Statement
@given('the AI agent recommends a property at "{address}"')
def step_ai_recommends(context, address):
    context.mock_ai_result = {
        "ok": True,
        "summary": "Top match for you.",
        "advice": "Tour it soon.",
        "error": None,
        "picks": [
            {
                "listing": {
                    "location": address,
                    "property_type": "Apartment",
                    "rent": 1200,
                    "total_monthly_cost": 1420,
                    "neighborhood": "Boulder Area",
                    "beds": 2,
                    "baths": 1,
                    "nearby_amenities": ["Transit", "Gym"],
                },
                "score": 92,
                "reasoning": "Great budget fit.",
                "highlights": ["Close to transit", "Under budget"],
            }
        ],
    }


# When Statement
@when('I request AI recommendations for city "{city}" and state "{state}"')
def step_request_ai(context, city, state):
    ai_result = getattr(
        context,
        "mock_ai_result",
        {
            "ok": False,
            "summary": "",
            "advice": "",
            "error": None,
            "picks": [],
        },
    )
    with patch("home.views.get_properties", return_value=[]), patch(
        "home.views.get_ai_recommendations", return_value=ai_result
    ):
        context.response = context.test.client.get("/ai-agent/", {"city": city, "state": state})


# Then Statement
@then("the AI agent response is OK")
def step_ai_response_ok(context):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"
    data = json.loads(context.response.content)
    assert data.get("ok") is True, f"Expected ok=True, got {data}"


# Then Statement
@then('the AI picks include an address containing "{needle}"')
def step_ai_pick_contains(context, needle):
    data = json.loads(context.response.content)
    picks = data.get("picks", [])
    assert any(needle in p.get("address", "") for p in picks), f'No pick address contained "{needle}". Picks: {picks}'


# Street View Deeplink
# Then Statement
@then("the map page contains the Street View deeplink template")
def step_map_has_street_view_template(context):
    body = context.response.content.decode()
    assert "maps/@?api=1&map_action=pano" in body, (
        "Expected Street View deeplink template " "'maps/@?api=1&map_action=pano' in map page HTML"
    )


# Agent Advertising
# When Statement
@when("I open the agent ad create page")
def step_open_agent_ad_create(context):
    context.response = context.test.client.get("/agents/ads/create/")


# Then Statement
@then("the page returns {code:d}")
def step_page_returns_code(context, code):
    assert context.response.status_code == code, f"Expected {code}, got {context.response.status_code}"


# Given Statement
@given('a verified agent "{username}" with a complete active ad in "{city}, {state}"')
def step_verified_agent_with_ad(context, username, city, state):
    from home.models import AgentAd

    user, _ = User.objects.get_or_create(username=username)
    user.set_password("Password123!")
    user.email = f"{username}@example.com"
    user.save()
    user.profile.is_agent_verified = True
    user.profile.save()
    context.ad = AgentAd.objects.create(
        agent=user,
        headline="Top-rated agent for your next home",
        city=city,
        state=state,
        brokerage="BearEstate Realty",
        license_number="CO-12345",
        phone="555-0100",
        email=user.email,
        bio="Helping buyers and renters find the right place since 2018.",
        specialties="First-time buyers, rentals",
        active=True,
    )
    context.user = user


# When Statement
@when("I open the agent profile page for that ad")
def step_open_agent_profile(context):
    context.response = context.test.client.get(f"/agents/{context.ad.id}/")


# Then Statement
@then("the profile page returns {code:d}")
def step_profile_returns(context, code):
    assert context.response.status_code == code, f"Expected {code}, got {context.response.status_code}"


# Then Statement
@then("the profile page shows the agent's headline")
def step_profile_shows_headline(context):
    body = context.response.content.decode()
    assert context.ad.headline in body, f'Expected headline "{context.ad.headline}" in profile page HTML'
