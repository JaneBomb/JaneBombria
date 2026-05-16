import base64
import io
import time

import pyotp
import qrcode
import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import permissions, viewsets

from .ai_listing_agent import get_ai_recommendations
from .forms import AgentAdForm, AgentInquiryForm, CustomRegisterForm, RoommatePostForm
from .models import AgentAd, Property, RoommatePost, SearchHistory
from .rentcast_api import get_properties
from .security import EMAIL_OTP_TTL_SECONDS, rate_limit
from .serializers import RoommatePostSerializer

# ---------------------- NEIGHBORHOOD MOCK DATA ---------------------- #

NEIGHBORHOOD_COSTS = {
    ("Austin", "TX"): {
        "Downtown": {
            "monthly_utilities": 190,
            "monthly_services": 85,
            "nearby_amenities": ["Gym", "Restaurants", "Transit", "Coffee Shop", "Grocery Store"],
        },
        "University Area": {
            "monthly_utilities": 170,
            "monthly_services": 70,
            "nearby_amenities": ["Gym", "Transit", "Coffee Shop", "Restaurants"],
        },
        "Default": {
            "monthly_utilities": 160,
            "monthly_services": 65,
            "nearby_amenities": ["Grocery Store", "Gym", "Restaurants", "Transit", "Coffee Shop"],
        },
    },
    ("Boulder", "CO"): {
        "Downtown": {
            "monthly_utilities": 210,
            "monthly_services": 95,
            "nearby_amenities": ["Grocery Store", "Gym", "Bus Stop", "Coffee Shop"],
        },
        "University Hill": {
            "monthly_utilities": 180,
            "monthly_services": 70,
            "nearby_amenities": ["Campus", "Restaurants", "Transit"],
        },
        "Default": {
            "monthly_utilities": 160,
            "monthly_services": 60,
            "nearby_amenities": ["Grocery Store", "Gym", "Restaurants", "Transit", "Coffee Shop"],
        },
    },
    ("Denver", "CO"): {
        "Downtown": {
            "monthly_utilities": 220,
            "monthly_services": 120,
            "nearby_amenities": ["Transit", "Gym", "Grocery", "Restaurants", "Coffee Shop"],
        },
        "Capitol Hill": {
            "monthly_utilities": 175,
            "monthly_services": 80,
            "nearby_amenities": ["Transit", "Coffee Shops", "Grocery", "Restaurants", "Gym"],
        },
        "Default": {
            "monthly_utilities": 165,
            "monthly_services": 75,
            "nearby_amenities": ["Grocery Store", "Gym", "Restaurants", "Transit", "Coffee Shop"],
        },
    },
}


def get_neighborhood_profile(city, state, address):
    city_data = NEIGHBORHOOD_COSTS.get((city, state), {})
    address_lower = (address or "").lower()

    if "downtown" in address_lower:
        neighborhood = "Downtown"
    elif "hill" in address_lower:
        neighborhood = "University Hill" if city == "Boulder" else "Capitol Hill"
    else:
        neighborhood = f"{city} Area"

    profile = city_data.get(neighborhood)
    if not profile:
        profile = city_data.get(
            "Default",
            {
                "monthly_utilities": 150,
                "monthly_services": 50,
                "nearby_amenities": [],
            },
        )

    return neighborhood, profile


# ---------------------- AGENT ADVERTISING HELPERS ---------------------- #


def score_listing_for_agent(property_data, user_preferences):
    """
    Scores a property based on the user's filters/search choices.
    Higher score = better curated agent recommendation.
    """
    score = 0

    rent = property_data.get("rent") or 0
    total_cost = property_data.get("total_monthly_cost") or 0
    listing_property_type = (property_data.get("property_type") or "").strip()
    amenities = property_data.get("nearby_amenities", [])

    budget = user_preferences.get("budget")
    desired_type = user_preferences.get("property_type")
    desired_amenity = user_preferences.get("amenity")
    listing_type = user_preferences.get("listing_type")

    # Stronger property type match
    if desired_type and listing_property_type == desired_type:
        score += 5

    # Stronger amenity match
    if desired_amenity and desired_amenity.lower() != "any":
        if any(desired_amenity.lower() in amenity.lower() for amenity in amenities):
            score += 8

    # Budget match + reward cheaper listings inside the selected range
    if budget and budget != "any":
        try:
            min_price, max_price = map(int, budget.split("-"))
            if min_price <= rent <= max_price:
                score += 6
                score += max(0, (max_price - rent) // 100)
        except ValueError:
            pass

    # Favor lower total monthly cost
    if total_cost:
        if total_cost < 1200:
            score += 6
        elif total_cost < 1600:
            score += 4
        elif total_cost < 2000:
            score += 2

    # Ownership-friendly preference for buy searches
    if listing_type == "for_sale" and listing_property_type in ["Condo", "Townhouse", "House"]:
        score += 3

    return score


def generate_agent_message(user_preferences, recommended_properties):
    """
    Creates a short message explaining why the agent picks were selected.
    """
    city = user_preferences.get("city") or "this area"
    listing_type = user_preferences.get("listing_type") or ""
    amenity = user_preferences.get("amenity") or "your preferred amenities"

    if not recommended_properties:
        return "No curated recommendations are available yet for your current filters."

    if listing_type == "for_rent":
        return (
            f"Based on your rental search in {city}, these agent picks best "
            "match your budget, property preferences, and nearby amenities "
            f"like {amenity}."
        )
    elif listing_type == "for_sale":
        return (
            f"Based on your home-buying search in {city}, these curated "
            "listings are strong matches for your selected filters and neighborhood preferences."
        )
    else:
        return (
            f"Based on your search in {city}, these curated listings best match "
            "your filters, searched amenities, and likely housing needs."
        )


def get_buyer_readiness_message(user_preferences):
    """
    Optional message for renters who may also be good candidates to buy.
    """
    listing_type = user_preferences.get("listing_type")
    budget = user_preferences.get("budget")

    if listing_type == "for_rent" and budget in ["1400-2000", "2000-999999"]:
        return (
            "Agent Insight: Based on your budget, you may also be a strong candidate "
            "for entry-level homeownership options in this area. A real estate agent "
            "could help you compare renting versus buying."
        )

    return ""


def user_is_verified_agent(user):
    return user.is_authenticated and hasattr(user, "profile") and user.profile.is_agent_verified


def get_relevant_agent_ads(city="", state="", limit=3):
    """
    Return active, complete ads matching the search location when possible.
    If no city/state is provided, it returns active complete ads generally.
    """
    ads = AgentAd.objects.filter(active=True).select_related("agent")

    if city:
        ads = ads.filter(city__iexact=city)

    if state:
        ads = ads.filter(state__iexact=state)

    complete_ads = [ad for ad in ads if ad.is_complete]
    return complete_ads[:limit]


# Checks if user is authenticated
# Redirects to correct page
def agent_ad_list(request):
    # Checks if user is logged in or not
    if not request.user.is_authenticated:
        messages.warning(request, "Please log in.")
        return redirect("bear_estate_homepage")  # redirects to homepage

    # Checks if user is a verified agent
    if not user_is_verified_agent(request.user):
        return render(request, "agent_ads/not_verified.html", status=403)

    ads = AgentAd.objects.filter(agent=request.user)
    return render(request, "agent_ads/list.html", {"ads": ads})


@login_required
def agent_ad_create(request):
    if not user_is_verified_agent(request.user):
        return render(request, "agent_ads/not_verified.html", status=403)

    if request.method == "POST":
        form = AgentAdForm(request.POST)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.agent = request.user
            ad.state = ad.state.upper()
            ad.save()
            return redirect("agent_ad_list")
    else:
        form = AgentAdForm(
            initial={
                "email": request.user.email,
            }
        )

    return render(
        request,
        "agent_ads/form.html",
        {
            "form": form,
            "title": "Create Agent Advertisement",
        },
    )


@login_required
def agent_ad_edit(request, ad_id):
    if not user_is_verified_agent(request.user):
        return render(request, "agent_ads/not_verified.html", status=403)

    ad = get_object_or_404(AgentAd, id=ad_id, agent=request.user)

    if request.method == "POST":
        form = AgentAdForm(request.POST, instance=ad)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.state = ad.state.upper()
            ad.save()
            return redirect("agent_ad_list")
    else:
        form = AgentAdForm(instance=ad)

    return render(
        request,
        "agent_ads/form.html",
        {
            "form": form,
            "title": "Edit Agent Advertisement",
        },
    )


@login_required
def agent_ad_deactivate(request, ad_id):
    if not user_is_verified_agent(request.user):
        return render(request, "agent_ads/not_verified.html", status=403)

    ad = get_object_or_404(AgentAd, id=ad_id, agent=request.user)

    if request.method == "POST":
        ad.active = False
        ad.save(update_fields=["active", "updated_at"])

    return redirect("agent_ad_list")


@rate_limit(
    "agent_inquiry",
    limit=5,
    window_seconds=300,
    key_extra=lambda req: req.resolver_match.kwargs.get("ad_id", ""),
)
def agent_profile(request, ad_id):
    ad = get_object_or_404(AgentAd, pk=ad_id, active=True)

    if not ad.is_complete:
        raise Http404("Agent profile is incomplete.")

    if request.method == "POST":
        form = AgentInquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.ad = ad

            if request.user.is_authenticated:
                inquiry.user = request.user

            inquiry.save()

            return render(
                request,
                "agent_ads/profile.html",
                {
                    "ad": ad,
                    "form": AgentInquiryForm(),
                    "message_sent": True,
                },
            )
    else:
        initial = {}

        if request.user.is_authenticated:
            initial = {
                "name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
            }

        form = AgentInquiryForm(initial=initial)

    return render(
        request,
        "agent_ads/profile.html",
        {
            "ad": ad,
            "form": form,
        },
    )


# ------------------------------- HTML views -------------------------------- #


# Home page
def search(request):
    properties = Property.objects.all()

    city = request.GET.get("city", "").strip().title()
    state = request.GET.get("state", "").strip().upper()
    agent_ads = get_relevant_agent_ads(city=city, state=state)

    return render(
        request,
        "search.html",
        {
            "properties": properties,
            "agent_ads": agent_ads,
        },
    )


# See all roommate posts
def roommate_list(request):
    posts = RoommatePost.objects.all().order_by("-date")
    return render(request, "roommate_postings_view.html", {"posts": posts})


# Creates a roommate post
# Login required (redirects to LOGIN_URL with ?next= preserved)
@login_required
def roommate_create(request):
    if request.method == "POST":
        form = RoommatePostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            return redirect("roommate_list")
    else:
        form = RoommatePostForm(initial={"date": timezone.now().date()})

    return render(request, "roommate_create.html", {"form": form})


# Changes roommate post status to closed
# Requires user to be logged in (can only close own posts)
@login_required
def roommate_close(request, post_id):
    post = get_object_or_404(RoommatePost, id=post_id, user=request.user)

    if request.method == "POST":
        post.status = "closed"
        post.save()

    return redirect("roommate_list")


# Deletes a roommate post
# Login required
@login_required
def roommate_delete(request, post_id):
    post = get_object_or_404(RoommatePost, id=post_id, user=request.user)

    if request.method == "POST":
        post.delete()

    return redirect("roommate_list")


# --------------------------------- MAP ------------------------------------------ #


# Map View
def map_view(request):
    """
    Handles user input from map page or landing page. Gets coordinates for addresses
    from RentCast API or geocoding if necessary. Passes coordinates to template for map display.
    Also builds curated agent recommendations from user filters and matched listings.
    """

    map_properties = []
    recommended_properties = []
    agent_message = ""
    buyer_readiness_message = ""

    # Default values so nothing breaks
    city = ""
    state = ""
    listing_type = ""
    property_type = ""
    price_range = ""
    sort_by = ""
    amenity_filter = ""
    keyword = ""

    # Read params from POST (search bar)
    if request.method == "POST":
        city = request.POST.get("city", "").strip().title()
        state = request.POST.get("state", "").strip().upper()
        listing_type = request.POST.get("intent", "").strip()
        property_type = request.POST.get("type", "").strip()
        price_range = request.POST.get("budget", "").strip()
        sort_by = request.POST.get("sort", "").strip()
        amenity_filter = request.POST.get("amenity", "").strip()
        keyword = request.POST.get("keyword", "").strip()
        print("FROM POST:", city, state)

    # Read params from GET (redirect from landing page)
    elif request.method == "GET":
        city = request.GET.get("city", "").strip().title()
        state = request.GET.get("state", "").strip().upper()
        listing_type = request.GET.get("intent", "").strip()
        property_type = request.GET.get("type", "").strip()
        price_range = request.GET.get("budget", "").strip()
        sort_by = request.GET.get("sort", "").strip()
        amenity_filter = request.GET.get("amenity", "").strip()
        keyword = request.GET.get("keyword", "").strip()
        print("FROM GET:", city, state)

    # If input was given
    if city and state:
        location_str = f"{city}, {state}"

        # Fetch filtered listings from RentCast
        rentcast_results = fetch_filtered_properties(location_str, listing_type, property_type, price_range)

        # Loop through results from API
        for prop in rentcast_results:
            # Use coordinates from RentCast if available, otherwise geocode the address
            lat = prop.get("latitude")
            lng = prop.get("longitude")

            address = prop.get("formattedAddress", "Unknown address")

            # Geocode address if applicable
            if not lat or not lng:
                if address:
                    coords = geocode_residential(address)
                    if coords:
                        lat, lng = coords

            # Create entry for map context
            if lat and lng:
                neighborhood, profile = get_neighborhood_profile(city, state, address)

                rent = prop.get("price") or 0
                monthly_utilities = profile["monthly_utilities"]
                monthly_services = profile["monthly_services"]
                nearby_amenities = profile["nearby_amenities"]
                total_monthly_cost = rent + monthly_utilities + monthly_services

                map_properties.append(
                    {
                        "latitude": lat,
                        "longitude": lng,
                        "location": address,
                        "property_type": prop.get("propertyType", "Unknown type"),
                        "rent": rent,
                        "beds": prop.get("bedrooms"),
                        "baths": prop.get("bathrooms"),
                        "sqft": prop.get("squareFootage"),
                        "neighborhood": neighborhood,
                        "monthly_utilities": monthly_utilities,
                        "monthly_services": monthly_services,
                        "nearby_amenities": nearby_amenities,
                        "total_monthly_cost": total_monthly_cost,
                    }
                )

        # Optional amenity filter
        if amenity_filter and amenity_filter.lower() != "any":
            map_properties = [
                p
                for p in map_properties
                if any(amenity_filter.lower() in amenity.lower() for amenity in p.get("nearby_amenities", []))
            ]

        # Optional sorting
        if sort_by == "rent_asc":
            map_properties.sort(key=lambda p: p.get("rent") or 0)
        elif sort_by == "rent_desc":
            map_properties.sort(key=lambda p: p.get("rent") or 0, reverse=True)
        elif sort_by == "total_cost_asc":
            map_properties.sort(key=lambda p: p.get("total_monthly_cost") or 0)
        elif sort_by == "total_cost_desc":
            map_properties.sort(key=lambda p: p.get("total_monthly_cost") or 0, reverse=True)

        # ---------------- AGENT ADVERTISING / CURATED PICKS ---------------- #

        user_preferences = {
            "city": city,
            "state": state,
            "listing_type": listing_type,
            "property_type": property_type,
            "budget": price_range,
            "amenity": amenity_filter,
            "sort_by": sort_by,
        }

        for prop in map_properties:
            prop["agent_score"] = score_listing_for_agent(prop, user_preferences)

        recommended_properties = sorted(map_properties, key=lambda p: p.get("agent_score", 0), reverse=True)[:3]

        agent_message = generate_agent_message(user_preferences, recommended_properties)
        buyer_readiness_message = get_buyer_readiness_message(user_preferences)

    else:
        # Defaults context to empty / existing DB properties
        all_properties = Property.objects.exclude(latitude=None, longitude=None)
        map_properties = list(all_properties.values("latitude", "longitude", "location"))

    context = {
        "properties": map_properties,
        "properties_count": len(map_properties),
        "city": city,
        "state": state,
        "listing_type": listing_type,
        "property_type": property_type,
        "price_range": price_range,
        "sort_by": sort_by,
        "amenity_filter": amenity_filter,
        "keyword": keyword,
        "recommended_properties": recommended_properties,
        "agent_message": agent_message,
        "buyer_readiness_message": buyer_readiness_message,
        "agent_ads": get_relevant_agent_ads(city=city, state=state),
    }

    return render(request, "map.html", context)


# Geocode helper function
def geocode_residential(address):
    """
    Uses the US Census Bureau API to convert an address to coordinates.
    Returns a tuple of (latitude, longitude) or None if the address could not be found.
    """
    url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
    params = {"address": address, "benchmark": "Public_AR_Current", "format": "json"}
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    matches = data["result"]["addressMatches"]
    if matches:
        coords = matches[0]["coordinates"]
        return coords["y"], coords["x"]  # lat, lng
    return None


# FILTER FUNCTION FOR MAP VIEW (taken from index)
def fetch_filtered_properties(location, listing_type=None, property_type=None, price_range=None):
    """
    Parameters: a location, listing type, property type and price range
    Will filter out properties from RentCast API with the filters passed in.
    Return: Returns a list of RentCast properties
    """
    min_price, max_price = None, None
    if price_range and price_range != "any":
        try:
            min_price, max_price = map(int, price_range.split("-"))
        except ValueError:
            pass

    try:
        return get_properties(
            location,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
        )
    except Exception as e:
        print("API Error:", e)
        return []


# ------------------------ HOME PAGE -------------------------- #


# Home page
@rate_limit(
    "login",
    limit=5,  # 5 failed attempts...
    window_seconds=300,  # ...per 5 minutes per IP
    only_on_failure=True,  # successful logins don't burn the budget
)
def index(request):
    context = {}

    # ---------------- LOGIN HANDLING ----------------
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            profile = getattr(user, "profile", None)
            if profile and profile.totp_enabled and profile.two_fa_method in ("totp", "email"):
                # Pre-auth state: user proved the password but is not
                # yet logged in. Django's session is anonymous here.
                request.session["pre_2fa_user_id"] = user.id
                request.session["pre_2fa_method"] = profile.two_fa_method
                request.session["pre_2fa_started_at"] = int(time.time())
                # Make sure no stale email OTP is left over.
                request.session.pop("login_email_otp", None)
                request.session.pop("login_email_otp_expires", None)
                return redirect("2fa_verify_login")

            # No 2FA configured: log in normally.
            login(request, user)
            return redirect("bear_estate_homepage")
        else:
            # counts this attempt.
            request._ratelimit_failure = True
            context["login_error"] = "Invalid username or password."
            context["show_login_modal"] = True

    # ---------------- PROPERTY SEARCH ----------------
    # properties = Property.objects.none()

    location = request.GET.get("location", "").strip()
    city = ""
    state = ""

    if location:
        parts = location.split(",")
        city = parts[0].strip() if len(parts) > 0 else ""
        state = parts[1].strip() if len(parts) > 1 else ""

    listing_type = request.GET.get("mode", "").strip()
    property_type = request.GET.get("type", "").strip()
    price_range = request.GET.get("budget", "").strip()

    """
    SEARCHES PROPERTY MODEL
    if listing_type in ["rent", "buy"]:
        properties = properties.filter(listing_type=listing_type)

    if property_type and property_type.lower() != "any type":
        properties = properties.filter(property_type=property_type.lower())

    if min_price is not None and max_price is not None:
        properties = properties.filter(price__gte=min_price, price__lte=max_price)

    context.update({
        "properties": properties,
        "api_properties": api_properties,
        "selected_location": location,
        "selected_intent": listing_type,
        "selected_type": property_type,
        "selected_budget": price_range,
        "result_count": properties.count(),
    })
    """

    if location:
        return redirect(
            f"/map/?city={city}&state={state}&intent={listing_type}&type={property_type}&budget={price_range}"
        )

    return render(request, "bear_estate_homepage.html", context)


# ------------------------ 2FA LOGIN CHALLENGE -------------------------- #

# How long the user has to complete the 2FA challenge after entering
# their password before we discard the pre-auth state.
_PRE_2FA_TTL_SECONDS = 10 * 60  # 10 minutes


def _clear_pre_2fa_session(request):
    for k in (
        "pre_2fa_user_id",
        "pre_2fa_method",
        "pre_2fa_started_at",
        "login_email_otp",
        "login_email_otp_expires",
    ):
        request.session.pop(k, None)


def _get_pre_2fa_user(request):
    """
    Returns the User who passed password auth but hasn't completed
    2FA, or None if no valid pre-auth state is in the session.
    """
    user_id = request.session.get("pre_2fa_user_id")
    started_at = request.session.get("pre_2fa_started_at", 0)
    if not user_id:
        return None
    if int(time.time()) - int(started_at) > _PRE_2FA_TTL_SECONDS:
        _clear_pre_2fa_session(request)
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        _clear_pre_2fa_session(request)
        return None


@rate_limit("2fa_verify", limit=10, window_seconds=300, only_on_failure=True)
def verify_2fa_login(request):
    """
    Second-factor challenge page used during login.

    GET  -> show the challenge form (TOTP code field, or email-code
            field with a "send code" button depending on user method).
    POST -> verify the supplied factor. Only on success do we call
            login() and complete the authentication.
    """
    import random

    from django.core.mail import send_mail

    user = _get_pre_2fa_user(request)
    if user is None:
        return redirect("bear_estate_homepage")

    method = request.session.get("pre_2fa_method", "totp")
    profile = user.profile
    ctx = {
        "method": method,
        "masked_email": _mask_email(user.email) if user.email else "",
        "email_sent": bool(request.session.get("login_email_otp")),
    }

    if request.method == "POST":
        action = request.POST.get("action", "")

        # User asked us to (re)send the email code.
        if action == "email_send" and method == "email":
            if not user.email:
                ctx["error"] = "No email address on file for this account."
                return render(request, "2fa_verify.html", ctx)
            code = f"{random.randint(0, 999999):06d}"
            request.session["login_email_otp"] = code
            request.session["login_email_otp_expires"] = int(time.time()) + EMAIL_OTP_TTL_SECONDS
            send_mail(
                subject="Your BearEstate sign-in code",
                message=(
                    f"Your one-time sign-in code is: {code}\n\n" f"It expires in {EMAIL_OTP_TTL_SECONDS // 60} minutes."
                ),
                from_email="noreply@bearestate.me",
                recipient_list=[user.email],
                fail_silently=False,
            )
            ctx["email_sent"] = True
            return render(request, "2fa_verify.html", ctx)

        # Verify TOTP.
        if method == "totp":
            entered = (request.POST.get("otp_code") or "").strip()
            secret = profile.totp_secret or ""
            if secret and pyotp.TOTP(secret).verify(entered):
                _clear_pre_2fa_session(request)
                login(request, user)
                return redirect("bear_estate_homepage")
            request._ratelimit_failure = True
            ctx["error"] = "Incorrect code. please try again."
            return render(request, "2fa_verify.html", ctx)

        # Verify email code.
        if method == "email":
            entered = (request.POST.get("email_code") or "").strip()
            stored = request.session.get("login_email_otp", "")
            expires_at = request.session.get("login_email_otp_expires", 0)
            now = int(time.time())

            if not stored:
                request._ratelimit_failure = True
                ctx["error"] = 'No code has been sent yet. Click "Send code".'
                return render(request, "2fa_verify.html", ctx)

            if now > int(expires_at):
                # Expired clear it and force resend.
                request.session.pop("login_email_otp", None)
                request.session.pop("login_email_otp_expires", None)
                request._ratelimit_failure = True
                ctx["email_sent"] = False
                ctx["error"] = "That code has expired. Please request a new one."
                return render(request, "2fa_verify.html", ctx)

            if entered and entered == stored:
                _clear_pre_2fa_session(request)
                login(request, user)
                return redirect("bear_estate_homepage")

            request._ratelimit_failure = True
            ctx["error"] = "Incorrect code. please try again."
            return render(request, "2fa_verify.html", ctx)

    return render(request, "2fa_verify.html", ctx)


def _mask_email(email):
    """Return a privacy-safe rendering like 'a***@example.com'."""
    if not email or "@" not in email:
        return ""
    local, _, domain = email.partition("@")
    if len(local) <= 1:
        return f"{local}***@{domain}"
    return f"{local[0]}***@{domain}"


# User Register
@rate_limit("register", limit=5, window_seconds=60 * 60)  # 5/hour per IP
def register(request):
    if request.method == "POST":
        form = CustomRegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("2fa_setup")
        else:
            errors = [error for field in form for error in field.errors]
            errors += list(form.non_field_errors())

            return render(
                request,
                "bear_estate_homepage.html",
                {
                    "show_signup_modal": True,
                    "register_errors": errors,
                },
            )

    return redirect("bear_estate_homepage")


# ------------------------------- API views -------------------------------- #


class RoommatePostViewSet(viewsets.ModelViewSet):
    serializer_class = RoommatePostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = RoommatePost.objects.all()
        # Reads stay open; writes are scoped to the user's own posts.
        if self.action in ("update", "partial_update", "destroy"):
            if self.request.user.is_authenticated:
                return qs.filter(user=self.request.user)
            return qs.none()
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, date=timezone.localdate())


# Two-Factor Auth
@login_required
@rate_limit("2fa_setup", limit=15, window_seconds=300, only_on_failure=True)
def setup_2fa(request):
    """
    GET -> render setup page with both TOTP and email options.
    POST method=totp_verify -> confirm TOTP code, save TOTP as 2FA method.
    POST method=email_send -> generate + email a 6-digit code, re-render for verify step.
    POST method=email_verify -> confirm emailed code, save email as 2FA method.
    """
    import random

    from django.core.mail import send_mail

    def _totp_context():
        secret = request.session.get("totp_secret") or pyotp.random_base32()
        request.session["totp_secret"] = secret
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=request.user.username, issuer_name="BearEstate")
        qr_img = qrcode.make(totp_uri)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        return {
            "qr_code": base64.b64encode(buf.getvalue()).decode(),
            "short_key": " ".join(secret[i: i + 4] for i in range(0, len(secret), 4)),
            "totp_secret": secret,
        }

    if request.method == "POST":
        method = request.POST.get("method")

        # TOTP verify
        if method == "totp_verify":
            secret = request.session.get("totp_secret", "")
            if secret and pyotp.TOTP(secret).verify(request.POST.get("otp_code", "")):
                p = request.user.profile
                p.totp_secret = secret
                p.totp_enabled = True
                p.two_fa_method = "totp"
                p.save()
                return redirect("bear_estate_homepage")
            request._ratelimit_failure = True
            ctx = _totp_context()
            ctx["totp_error"] = "Incorrect code. please try again."
            return render(request, "2fa_setup.html", ctx)

        # Send code to Email
        if method == "email_send":
            email = request.user.email
            if not email:
                ctx = _totp_context()
                ctx["email_error"] = "No email address on your account. Please update your profile first."
                return render(request, "2fa_setup.html", ctx)
            code = f"{random.randint(0, 999999):06d}"
            # Store the code AND its expiration timestamp so the
            # verify branch below can reject stale codes (5 min TTL).
            request.session["email_otp"] = code
            request.session["email_otp_expires"] = int(time.time()) + EMAIL_OTP_TTL_SECONDS
            send_mail(
                subject="Your BearEstate verification code",
                message=(f"Your one-time code is: {code}\n\n" f"It expires in {EMAIL_OTP_TTL_SECONDS // 60} minutes."),
                from_email="noreply@bearestate.me",
                recipient_list=[email],
                fail_silently=False,
            )
            ctx = _totp_context()
            ctx["email_sent"] = True
            ctx["email_address"] = email
            return render(request, "2fa_setup.html", ctx)

        # Email Verify
        if method == "email_verify":
            entered = request.POST.get("email_code", "").strip()
            stored = request.session.get("email_otp", "")
            expires_at = request.session.get("email_otp_expires", 0)
            now = int(time.time())

            if not stored or not expires_at or now > int(expires_at):
                # Drop the stale code so the next attempt has to
                # request a fresh one.
                request.session.pop("email_otp", None)
                request.session.pop("email_otp_expires", None)
                request._ratelimit_failure = True
                ctx = _totp_context()
                ctx["email_sent"] = False
                ctx["email_address"] = request.user.email
                ctx["email_error"] = "That code has expired. Please request a new one."
                return render(request, "2fa_setup.html", ctx)

            if entered == stored:
                p = request.user.profile
                p.totp_enabled = True
                p.two_fa_method = "email"
                p.save()
                # Single-use: clear the code on success.
                request.session.pop("email_otp", None)
                request.session.pop("email_otp_expires", None)
                return redirect("bear_estate_homepage")

            request._ratelimit_failure = True
            ctx = _totp_context()
            ctx["email_sent"] = True
            ctx["email_address"] = request.user.email
            ctx["email_error"] = "Incorrect code. please try again."
            return render(request, "2fa_setup.html", ctx)

    return render(request, "2fa_setup.html", _totp_context())


def _recent_history_for(request, limit=5):
    qs = SearchHistory.objects.none()
    if request.user.is_authenticated:
        qs = SearchHistory.objects.filter(user=request.user)
    elif request.session.session_key:
        qs = SearchHistory.objects.filter(
            session_key=request.session.session_key,
            user__isnull=True,
        )
    return [h.to_prompt_dict() for h in qs[:limit]]


def build_enriched_listings(city, state, listing_type, property_type, price_range, amenity_filter, keyword):
    if not (city and state):
        return []

    location_str = f"{city}, {state}"
    rentcast_results = fetch_filtered_properties(
        location_str,
        listing_type,
        property_type,
        price_range,
    )

    enriched = []
    for prop in rentcast_results:
        lat = prop.get("latitude")
        lng = prop.get("longitude")
        address = prop.get("formattedAddress", "Unknown address")
        if not (lat and lng) and address:
            coords = geocode_residential(address)
            if coords:
                lat, lng = coords
        if not (lat and lng):
            continue

        neighborhood, profile = get_neighborhood_profile(city, state, address)
        rent = prop.get("price") or 0
        enriched.append(
            {
                "latitude": lat,
                "longitude": lng,
                "location": address,
                "property_type": prop.get("propertyType", "Unknown type"),
                "rent": rent,
                "beds": prop.get("bedrooms"),
                "baths": prop.get("bathrooms"),
                "sqft": prop.get("squareFootage"),
                "neighborhood": neighborhood,
                "monthly_utilities": profile["monthly_utilities"],
                "monthly_services": profile["monthly_services"],
                "nearby_amenities": profile["nearby_amenities"],
                "total_monthly_cost": rent + profile["monthly_utilities"] + profile["monthly_services"],
            }
        )

    # Apply amenity filter
    if amenity_filter and amenity_filter.lower() != "any":
        enriched = [
            p for p in enriched if any(amenity_filter.lower() in a.lower() for a in p.get("nearby_amenities", []))
        ]

    # Apply keyword filter
    if keyword:
        kw = keyword.lower()

        def _match(p):
            hs = [
                str(p.get("location", "")).lower(),
                str(p.get("property_type", "")).lower(),
                str(p.get("neighborhood", "")).lower(),
            ] + [str(a).lower() for a in p.get("nearby_amenities", [])]
            return any(kw in h for h in hs)

        enriched = [p for p in enriched if _match(p)]

    return enriched


def ai_listing_agent_view(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "ok": False,
                "error": "Sign in to unlock AI-curated listings based on your search history.",
                "summary": "",
                "advice": "",
                "picks": [],
            }
        )

    city = request.GET.get("city", "").strip().title()
    state = request.GET.get("state", "").strip().upper()
    listing_type = request.GET.get("intent", "").strip()
    property_type = request.GET.get("type", "").strip()
    price_range = request.GET.get("budget", "").strip()
    amenity_filter = request.GET.get("amenity", "").strip()
    keyword = request.GET.get("keyword", "").strip()

    if not (city and state):
        return JsonResponse(
            {
                "ok": False,
                "error": "Please run a property search first.",
                "summary": "",
                "advice": "",
                "picks": [],
            }
        )

    enriched = build_enriched_listings(
        city,
        state,
        listing_type,
        property_type,
        price_range,
        amenity_filter,
        keyword,
    )

    preferences = {
        "city": city,
        "state": state,
        "listing_type": listing_type,
        "property_type": property_type,
        "budget": price_range,
        "amenity": amenity_filter,
        "keyword": keyword,
    }
    history = _recent_history_for(request, limit=5)

    result = get_ai_recommendations(preferences, enriched, history=history)

    picks_out = [
        {
            "address": p["listing"].get("location", ""),
            "property_type": p["listing"].get("property_type", ""),
            "rent": p["listing"].get("rent", 0),
            "total_monthly_cost": p["listing"].get("total_monthly_cost", 0),
            "neighborhood": p["listing"].get("neighborhood", ""),
            "beds": p["listing"].get("beds"),
            "baths": p["listing"].get("baths"),
            "nearby_amenities": p["listing"].get("nearby_amenities", []),
            "score": p["score"],
            "reasoning": p["reasoning"],
            "highlights": p["highlights"],
        }
        for p in result["picks"]
    ]

    return JsonResponse(
        {
            "ok": result["ok"],
            "summary": result["summary"],
            "advice": result["advice"],
            "error": result["error"],
            "picks": picks_out,
        }
    )
