from datetime import datetime


def serialize_listing(post):
    raw_date = post.date
    if isinstance(raw_date, str):
        try:
            raw_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raw_date = None
    return {
        "id": post.pk,
        "slug": str(post.pk),
        "name": post.user.get_full_name() or post.user.username,
        "location": "",
        "rent": float(post.rent) if post.rent else None,
        "move_in": "",
        "type": post.property_type,
        "description": (post.message[:110] + "...") if len(post.message) > 110 else post.message,
        "avatar": None,
        "status": post.status,
        "created_at": f"{raw_date.day} {raw_date.strftime('%b %Y')}" if raw_date else "",
    }
