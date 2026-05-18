from behave import *
from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse

# ──────────────────────────────────────────────
# Helper: shared Django test client
# ──────────────────────────────────────────────
def get_client(context):
    if not hasattr(context, "client"):
        context.client = Client()
    return context.client


# ══════════════════════════════════════════════
# Feature: register
# ══════════════════════════════════════════════

@given("we have a register page")
def step_register_page(context):
    client = get_client(context)
    response = client.get("/register/")          # adjust URL to your route
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}"
    )
    context.response = response


@when('we enter a {username} and {password} and click the "Sign Up" button')
def step_register_submit(context, username, password):
    client = get_client(context)
    context.username = username
    context.response = client.post("/register/", {
        "username": username,
        "password": password,
    })


@then("we have a newly created account")
def step_account_created(context):
    assert User.objects.filter(username=context.username).exists(), (
        f"User '{context.username}' was not created in the database"
    )


# ══════════════════════════════════════════════
# Feature: login
# ══════════════════════════════════════════════

@given("we have a login page")
def step_login_page(context):
    client = get_client(context)
    response = client.get("/login/")             # adjust URL to your route
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}"
    )
    context.response = response

@given("we have an existing user")
def step_existing_user(context):
    context.username = "user"
    context.password = "password"
    user, _ = User.objects.get_or_create(username=context.username)
    user.set_password(context.password)
    user.save()


@when('we enter the {username} and {password} and click the "Sign In" button')
def step_login_submit(context, username, password):
    client = get_client(context)
    context.username = username
    context.response = client.post("/login/", {
        "username": username,
        "password": password,
    })


@then("the {username} will appear next to the login button")
def step_username_visible(context, username):
    # After login, the user should be redirected to a page showing their name.
    # Check the session to confirm authentication succeeded.
    client = get_client(context)
    assert "_auth_user_id" in client.session, (
        "User is not authenticated — session has no auth user"
    )
    response = client.get(reverse("movies"))
    assert f'<span class="username">{username}</span>'.encode() in response.content


# ══════════════════════════════════════════════
# Feature: view movies
# ══════════════════════════════════════════════

@given("we have a home page")
def step_home_page(context):
    client = get_client(context)
    response = client.get("/bookings/")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}"
    )
    context.response = response


@when('we click the "All Movies" button')
def step_click_all_movies(context):
    client = get_client(context)
    context.response = client.get("/movies/")
    assert context.response.status_code == 200


@then("we get a list of all movies")
def step_see_movies_list(context):
    print("Context data:", context.response.context)
    # Confirm the response contains movie data.
    # Adjust the key to match your template context variable name.
    assert "movies" in context.response.context, (
        "No 'movies' key found in template context"
    )
    movies = context.response.context["movies"]
    assert len(movies) > 0, "Movie list is empty"


# ══════════════════════════════════════════════
# Feature: make booking
# ══════════════════════════════════════════════

@given("we have a booking page")
def step_booking_page(context):
    client = get_client(context)
    response = client.get("/book/Toy%20Story/")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}"
    )
    context.response = response


@when("we click an available seat on the seat grid")
def step_select_seat(context):
    client = get_client(context)
    # POST the selected seat to the booking endpoint
    context.response = client.post("/book/Toy%20Story/", {
        "seat": "1",                            # adjust to a known available seat
    })


@then("we can confirm the booking for the seat")
def step_confirm_booking(context):
    # A successful booking should redirect (302) or return 200 with confirmation.
    assert context.response.status_code in (200, 302), (
        f"Unexpected status code: {context.response.status_code}"
    )


# ══════════════════════════════════════════════
# Feature: check bookings
# ══════════════════════════════════════════════

@given("we have a user account")
def step_user_account(context):
    context.username = "test"
    context.password = "password"
    user, created = User.objects.get_or_create(username=context.username)
    if created or not user.has_usable_password():
        user.set_password(context.password)
        user.save()
    client = get_client(context)
    client.login(username=context.username, password=context.password)


@when('we click the account button')
def step_click_account(context):
    client = get_client(context)
    context.response = client.get("/account/")   # adjust URL to your route
    assert context.response.status_code == 200


@then("we have a list of all bookings made")
def step_see_bookings(context):
    # Confirm the response contains booking data.
    # Adjust the key to match your template context variable name.
    assert "current_bookings" in context.response.context, (
        "No 'bookings' key found in template context"
    )