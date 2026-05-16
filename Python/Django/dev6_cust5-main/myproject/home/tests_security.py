"""
Tests for 2FA, rate limiting, Missing security flags, Email OTP expiration, Anonymous WebSocket Access to Private Chats,
IDOR- Unauthorized Access to Any Chat Room and Stored XSS via WebSocket innerHTML
"""

import time

import pyotp
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

# 2FA


@override_settings(RATE_LIMIT_DISABLED=True)
class TwoFactorEnforcedAtLoginTests(TestCase):
    """
    Vulnerability: index() called login() immediately after authenticate()
    succeeded, even when the user had configured TOTP or email 2FA.
    Fix: when a 2FA method is enabled on the profile, password auth
    only puts the user in a 'pre_2fa' session state and redirects to
    /auth/2fa/verify/. login() is not called until the second factor
    verifies.
    """

    def setUp(self):
        cache.clear()
        self.password = "StrongPassword@123"
        self.user = User.objects.create_user(
            username="totp_user",
            password=self.password,
            email="totp@example.com",
        )
        # Configure TOTP 2FA on this user.
        self.totp_secret = pyotp.random_base32()
        p = self.user.profile
        p.totp_secret = self.totp_secret
        p.totp_enabled = True
        p.two_fa_method = "totp"
        p.save()

    def test_password_alone_does_not_log_user_in_when_totp_enabled(self):
        """Submitting username+password for a 2FA user must NOT establish
        an authenticated session."""
        response = self.client.post(
            "/",
            {
                "username": "totp_user",
                "password": self.password,
            },
        )
        # We expect a redirect to the 2FA challenge.
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/2fa/verify/", response["Location"])

        # Critically: the session is NOT yet authenticated.
        protected = self.client.get("/roommate-posts/create/")
        self.assertNotEqual(protected.status_code, 200)

        # And the pre-auth state is in the session, not a real login.
        self.assertIn("pre_2fa_user_id", self.client.session)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_2fa_verify_with_correct_totp_completes_login(self):
        """Once the user supplies the correct TOTP code on the verify
        page, login() runs and the session becomes authenticated."""
        # password.
        self.client.post(
            "/",
            {
                "username": "totp_user",
                "password": self.password,
            },
        )
        # correct TOTP.
        valid_code = pyotp.TOTP(self.totp_secret).now()
        response = self.client.post(
            "/auth/2fa/verify/",
            {
                "otp_code": valid_code,
            },
        )
        self.assertEqual(response.status_code, 302)
        # logged in
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)


# Rate Limiting Fix
class LoginRateLimitTests(TestCase):
    """
    Vulnerability: no rate limiting anywhere
    Fix: a cache-backed rate limiter on / (login), /register/, and the
    2FA endpoints. Login limit is 5 failed attempts per 5 minutes per IP.
    """

    def setUp(self):
        cache.clear()
        # A real user so we can confirm the limiter only counts FAILURES
        # (success path shouldn't burn the budget).
        User.objects.create_user(username="real_user", password="StrongPassword@123")

    def test_repeated_failed_logins_get_blocked_with_429(self):
        """6 wrong-password attempts in a row from the same IP —
        the 6th must be rejected with HTTP 429 instead of the normal
        200 error page. Limit is 5 per 5-minute window."""
        for i in range(5):
            r = self.client.post(
                "/",
                {
                    "username": "real_user",
                    "password": "wrong_password",
                },
            )
            self.assertEqual(r.status_code, 200, f"attempt {i + 1} should still be allowed but got {r.status_code}")

        # 6th attempt
        blocked = self.client.post(
            "/",
            {
                "username": "real_user",
                "password": "wrong_password",
            },
        )
        self.assertEqual(blocked.status_code, 429)
        # And the limiter advertises Retry-After so clients can back off.
        self.assertIn("Retry-After", blocked)

    def test_admin_login_is_also_rate_limited(self):
        """Django admin has its own login form at /admin/login/ that
        bypasses our index() view entirely. It's a high-value brute
        force target, so urls.py wraps admin.site.login with the same
        rate_limit decorator. 6th POST should be 429."""
        for i in range(5):
            r = self.client.post(
                "/admin/login/",
                {
                    "username": "admin_brute",
                    "password": "wrong",
                    "next": "/admin/",
                },
            )

            self.assertNotEqual(
                r.status_code,
                429,
                f"attempt {i + 1} should still be allowed",
            )

        blocked = self.client.post(
            "/admin/login/",
            {
                "username": "admin_brute",
                "password": "wrong",
                "next": "/admin/",
            },
        )
        self.assertEqual(blocked.status_code, 429)


# Security Settings Fix


@override_settings(RATE_LIMIT_DISABLED=True)
class SecuritySettingsTests(TestCase):
    """
    Vulnerability: Cookies, HSTS, and Content-Type sniffing protections
    were not configured.
    Fix: settings.py now sets nosniff, samesite, httponly, X-Frame DENY
    unconditionally, and the secure-cookie + HSTS + SSL-redirect
    settings inside an `if not DEBUG:` block (so prod gets them).
    """

    def test_always_on_security_headers_and_cookies_configured(self):
        """The headers and cookie attributes that are safe to enable in
        every environment must actually be set."""
        # Header settings:
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.X_FRAME_OPTIONS, "DENY")
        self.assertEqual(settings.SECURE_REFERRER_POLICY, "same-origin")

        # Cookie settings:
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")

        # And the SecurityMiddleware that enforces these is wired in.
        self.assertIn(
            "django.middleware.security.SecurityMiddleware",
            settings.MIDDLEWARE,
        )
        self.assertIn(
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            settings.MIDDLEWARE,
        )

    def test_production_https_hardening_block_is_configured(self):
        """When DEBUG is False the settings module must enable HSTS,
        secure cookies, and SSL redirect. We verify the conditional
        block works by reloading settings with DEBUG=False env."""
        import importlib
        import os

        import myproject.settings as project_settings

        original_debug = os.environ.get("DEBUG")
        original_key = os.environ.get("DJANGO_SECRET_KEY")
        try:
            os.environ["DEBUG"] = "False"
            os.environ["DJANGO_SECRET_KEY"] = "x" * 50
            importlib.reload(project_settings)

            self.assertFalse(project_settings.DEBUG)
            self.assertTrue(project_settings.SESSION_COOKIE_SECURE)
            self.assertTrue(project_settings.CSRF_COOKIE_SECURE)
            self.assertTrue(project_settings.SECURE_SSL_REDIRECT)
            self.assertGreaterEqual(
                project_settings.SECURE_HSTS_SECONDS,
                60 * 60 * 24 * 30,
                "HSTS must be at least 30 days in production",
            )
            self.assertTrue(project_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS)
            self.assertTrue(project_settings.SECURE_HSTS_PRELOAD)
        finally:
            # Restore the environment + reload so later tests aren't
            # affected by our temporary override.
            if original_debug is None:
                os.environ.pop("DEBUG", None)
            else:
                os.environ["DEBUG"] = original_debug
            if original_key is None:
                os.environ.pop("DJANGO_SECRET_KEY", None)
            else:
                os.environ["DJANGO_SECRET_KEY"] = original_key
            importlib.reload(project_settings)

    def test_secret_key_has_no_predictable_fallback(self):
        from pathlib import Path

        import myproject.settings as project_settings

        src = Path(project_settings.__file__).read_text()
        self.assertNotIn(
            "test-secret-key",
            src,
            "settings.py still references 'test-secret-key'. The " "predictable fallback hasn't been removed.",
        )

        self.assertNotEqual(settings.SECRET_KEY, "test-secret-key")
        self.assertGreaterEqual(
            len(settings.SECRET_KEY),
            32,
            "SECRET_KEY is suspiciously short. Likely still a "
            "hardcoded fallback rather than a generated/env-supplied key.",
        )


# Email OTP Expiration Fix
@override_settings(RATE_LIMIT_DISABLED=True)
class EmailOTPExpirationTests(TestCase):
    """
    Vulnerability: setup_2fa stored 'email_otp' in the session with no
    expiration, so a captured code was valid forever.
    Fix: setup_2fa now stores 'email_otp_expires' alongside the code
    (5-minute TTL). The verify branch rejects expired or unexpiring
    codes.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="otp_user",
            password="StrongPassword@123",
            email="otp@example.com",
        )
        self.client.login(username="otp_user", password="StrongPassword@123")

    def test_expired_email_otp_is_rejected(self):
        from home.models import UserProfile

        session = self.client.session
        session["email_otp"] = "111222"
        # Expired 1 second ago.
        session["email_otp_expires"] = int(time.time()) - 1
        session.save()

        response = self.client.post(
            "/auth/2fa/setup/",
            {
                "method": "email_verify",
                "email_code": "111222",
            },
        )

        # Should re-render the page (200), NOT redirect (302) on success.
        self.assertEqual(response.status_code, 200)
        # The profile should still NOT have email 2FA enabled.
        profile = UserProfile.objects.get(user=self.user)
        self.assertNotEqual(profile.two_fa_method, "email")
        self.assertFalse(profile.totp_enabled)

        self.assertNotIn("email_otp", self.client.session)

    def test_email_send_records_an_expiration_timestamp(self):

        before = int(time.time())
        response = self.client.post("/auth/2fa/setup/", {"method": "email_send"})
        after = int(time.time())

        self.assertEqual(response.status_code, 200)
        self.assertIn("email_otp", self.client.session)
        self.assertIn("email_otp_expires", self.client.session)

        expires = int(self.client.session["email_otp_expires"])
        ttl = expires - before
        # Must be in the future, and a sensible window.
        self.assertGreater(expires, after)
        self.assertGreaterEqual(ttl, 60)
        self.assertLessEqual(ttl, 15 * 60)


@override_settings(
    RATE_LIMIT_DISABLED=True,
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class ChatWebSocketSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        from home.models import RoommatePost

        self.owner = User.objects.create_user(username="post_owner", password="StrongPassword@123")
        self.inquirer = User.objects.create_user(username="post_inquirer", password="StrongPassword@123")
        self.outsider = User.objects.create_user(username="random_outsider", password="StrongPassword@123")
        self.post = RoommatePost.objects.create(
            user=self.owner,
            message="Need a roommate.",
            date="2026-03-11",
            status="open",
            rent=1000,
            property_type="apartment",
        )

    def _build_communicator(self, user):
        import chat.routing
        from channels.routing import URLRouter
        from channels.testing import WebsocketCommunicator

        app = URLRouter(chat.routing.websocket_urlpatterns)
        comm = WebsocketCommunicator(app, f"/ws/chat/{self.post.id}/{self.inquirer.id}/")
        comm.scope["user"] = user
        return comm

    # Anonymous WebSocket Access
    def test_anonymous_user_cannot_open_chat_websocket(self):
        """An AnonymousUser must not be able to connect to the chat
        WebSocket. The consumer should close with code 4003 and no
        Message rows should be created during the attempted handshake."""
        from asgiref.sync import async_to_sync
        from chat.models import Message
        from django.contrib.auth.models import AnonymousUser

        async def body():
            comm = self._build_communicator(AnonymousUser())
            connected, close_code = await comm.connect()
            self.assertFalse(
                connected,
                "Anonymous user should not be able to connect to chat WS",
            )
            self.assertEqual(close_code, 4003)
            await comm.disconnect()

        async_to_sync(body)()
        self.assertEqual(Message.objects.filter(posting_id=self.post.id).count(), 0)

    # Cross-User WebSocket Access (logged in but not owner/not inquirer)
    def test_logged_in_outsider_cannot_open_chat_websocket(self):
        """A logged-in user who is neither the posting owner nor the
        designated inquirer must be rejected with code 4003"""
        from asgiref.sync import async_to_sync

        async def body():
            comm = self._build_communicator(self.outsider)
            connected, close_code = await comm.connect()
            self.assertFalse(
                connected,
                "Outsider (not owner, not inquirer) should be rejected",
            )
            self.assertEqual(close_code, 4003)
            await comm.disconnect()

        async_to_sync(body)()

    # Stored XSS via WebSocket innerHTML
    def test_chat_room_template_does_not_render_messages_via_innerHTML(self):
        """Regression test for the stored XSS fix in chat_room.html."""
        import re

        self.client.login(username="post_owner", password="StrongPassword@123")
        response = self.client.get(f"/chat/{self.post.id}/{self.inquirer.id}/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()

        # Safe pattern is in place: textContent is used for socket data.
        self.assertIn(
            "textContent = message",
            body,
            "chat_room.html should assign incoming message via " "element.textContent (XSS-safe), not innerHTML.",
        )
        self.assertIn(
            "textContent = sender",
            body,
            "chat_room.html should assign sender label via " "element.textContent (XSS-safe), not innerHTML.",
        )

        # No innerHTML write that interpolates a socket-supplied field.
        socket_fields = ("data.message", "data.sender", "data.user_message", "data.bot_reply", "message}", "sender}")
        innerhtml_writes = re.findall(r"innerHTML\s*[+]?=\s*[`'\"][^`'\"]*[`'\"]", body)
        for snippet in innerhtml_writes:
            for field in socket_fields:
                self.assertNotIn(
                    field,
                    snippet,
                    f"chat_room.html still writes WebSocket-supplied "
                    f"field into innerHTML — stored XSS regression. "
                    f"Offending snippet: {snippet!r}",
                )
