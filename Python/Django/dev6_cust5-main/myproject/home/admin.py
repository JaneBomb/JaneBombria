from django.contrib import admin

from .models import AgentAd, AgentInquiry, Property, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email_verified", "is_agent_verified", "two_fa_method")
    list_filter = ("is_agent_verified", "email_verified", "two_fa_method")
    search_fields = ("user__username", "user__email")


@admin.register(AgentAd)
class AgentAdAdmin(admin.ModelAdmin):
    list_display = ("headline", "agent", "city", "state", "active", "updated_at")
    list_filter = ("active", "state", "city")
    search_fields = ("headline", "agent__username", "brokerage", "license_number")


@admin.register(AgentInquiry)
class AgentInquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "ad", "created_at")
    search_fields = ("name", "email", "message", "ad__headline")


admin.site.register(Property)
