from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import include, path
from home import views
from home.security import rate_limit

admin.site.login = rate_limit("admin_login", limit=5, window_seconds=300)(admin.site.login)

_logout_view = rate_limit("logout", limit=30, window_seconds=300)(auth_views.LogoutView.as_view(next_page="/"))

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="bear_estate_homepage"),
    path("health/", lambda request: HttpResponse("ok")),
    path("roommate-posts/", include("home.urls")),
    path("register/", views.register, name="register"),
    path("logout/", _logout_view, name="logout"),
    path("ai-agent/", views.ai_listing_agent_view, name="ai_listing_agent"),
    path("map/", views.map_view, name="map"),
    path("auth/2fa/setup/", views.setup_2fa, name="2fa_setup"),
    path("auth/2fa/verify/", views.verify_2fa_login, name="2fa_verify_login"),
    path("chat/", include("chat.urls")),
    path("agents/ads/", views.agent_ad_list, name="agent_ad_list"),
    path("agents/ads/create/", views.agent_ad_create, name="agent_ad_create"),
    path("agents/ads/<int:ad_id>/edit/", views.agent_ad_edit, name="agent_ad_edit"),
    path("agents/ads/<int:ad_id>/deactivate/", views.agent_ad_deactivate, name="agent_ad_deactivate"),
    path("agents/<int:ad_id>/", views.agent_profile, name="agent_profile"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static("/static/", document_root=settings.STATIC_ROOT)
