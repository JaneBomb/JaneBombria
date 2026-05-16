import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RENTCAST_API_KEY")

# Rentcast's expected property type values
PROPERTY_TYPE_MAP = {
    "apartment": "Apartment",
    "house": "Single Family",
    "condo": "Condo",
    "townhouse": "Townhouse",
}


def get_properties(location, property_type=None, min_price=None, max_price=None):
    if not API_KEY:
        print("WARNING: RENTCAST_API_KEY is not set.")
        return []

    url = "https://api.rentcast.io/v1/listings/rental/long-term"
    headers = {"X-Api-Key": API_KEY}

    parts = location.split(",")
    city = parts[0].strip()
    state = parts[1].strip() if len(parts) > 1 else "CO"

    params = {
        "city": city,
        "state": state,
        "limit": 10,
        "status": "Active",
    }

    # map user-facing type to Rentcast's expected value
    if property_type and property_type.lower() not in ("", "any type"):
        rentcast_type = PROPERTY_TYPE_MAP.get(property_type.lower())
        if rentcast_type:
            params["propertyType"] = rentcast_type

    response = requests.get(url, headers=headers, params=params)

    # for debugging
    print("Rentcast status:", response.status_code)
    print("Rentcast response:", response.text[:300])

    if response.status_code != 200:
        return []

    data = response.json()
    results = data if isinstance(data, list) else data.get("data", [])

    # client-side price filtering if API doesn't pull requests based on price
    if min_price is not None:
        results = [p for p in results if p.get("price") and p["price"] >= min_price]
    if max_price is not None and max_price != 999999:
        results = [p for p in results if p.get("price") and p["price"] <= max_price]

    return results
