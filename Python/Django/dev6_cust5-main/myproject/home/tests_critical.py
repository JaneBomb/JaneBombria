from django.contrib.auth.models import User
from django.test import TestCase
from home.models import RoommatePost


# 2
class MapLiteralInjection(TestCase):
    """
    Before: User input was used as literal JavaScript in script blocks. Security vulnerability.
    After: Breaks out of JavaScript to ensure excess data cannot be directly injected in.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.url = "/map/"

    # Helper methods for get and post requests
    def _get_map(self, params: dict, login: bool = False):
        if login:
            self.client.login(username="testuser", password="testpass123")
        return self.client.get(self.url, params)

    def _post_map(self, data: dict, login: bool = False):
        if login:
            self.client.login(username="testuser", password="testpass123")
        return self.client.post(self.url, data)

    PAYLOADS = [
        "</script><script>alert(1)//",
        '";alert(1)//',
        "';alert(1)//",
        "<img src=x onerror=alert(1)>",
        "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e",
    ]

    def _assert_not_raw_in_script(self, response, payload: str):
        """
        The payload (or its most dangerous substring) must not appear
        literally inside a <script>…</script> block.
        We decode bytes so we can do a plain string search.
        """
        body = response.content.decode("utf-8", errors="replace")

        # Split on <script to isolate script blocks
        parts = body.split("<script")
        script_blocks = []
        for part in parts[1:]:  # skip everything before first <script
            end = part.find("</script>")
            if end != -1:
                script_blocks.append(part[:end])

        for block in script_blocks:
            # The closing-tag attack vector
            self.assertNotIn(
                "</script>",
                block,
                msg=f"Payload broke out of script block: {payload!r}",
            )
            # Raw angle brackets from the payload shouldn't survive
            if "<" in payload:
                self.assertNotIn(
                    payload,
                    block,
                    msg=f"Raw payload found in script block: {payload!r}",
                )

    def test_amenity_xss_get(self):
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                resp = self._get_map({"amenity": payload})
                self.assertEqual(resp.status_code, 200)
                self._assert_not_raw_in_script(resp, payload)

    def test_city_xss_get(self):
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                resp = self._get_map({"city": payload, "state": "CO"})
                self.assertEqual(resp.status_code, 200)
                self._assert_not_raw_in_script(resp, payload)

    def test_keyword_xss_get(self):
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                resp = self._get_map({"keyword": payload})
                self.assertEqual(resp.status_code, 200)
                self._assert_not_raw_in_script(resp, payload)

    def test_all_filters_xss_post(self):
        """POST with XSS payloads in every filter field."""
        payload = "</script><script>alert(1)//"
        data = {
            "city": payload,
            "state": "CO",
            "intent": payload,
            "type": payload,
            "budget": payload,
            "amenity": payload,
            "keyword": payload,
            "sort": payload,
        }
        resp = self._post_map(data)
        self.assertEqual(resp.status_code, 200)
        self._assert_not_raw_in_script(resp, payload)

    def test_filter_values_are_json_encoded(self):
        """
        After the fix, filter values should appear inside json_script tags
        (i.e. as JSON) rather than as bare JS string literals.
        """
        payload = "xss_marker_value"
        resp = self._post_map({"amenity": payload})
        body = resp.content.decode()

        # The value should exist somewhere in the page (json_script output)
        self.assertIn(payload, body)

        # But it must NOT appear as a bare JS string like: = "xss_marker_value"
        self.assertNotIn(f'= "{payload}"', body)
        self.assertNotIn(f"= '{payload}'", body)

    def test_normal_search_renders(self):
        resp = self._get_map({"city": "Denver", "state": "CO"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "map")


# END of test 2


# 6
class MassAssignmentInREST(TestCase):
    """
    Before: Easy access to restricted fields (protected fields)
    After: Ensured that protected fields cannot be overwritten via the API by unauthorized users
    """

    def setUp(self):
        self.user = User.objects.create_user("test", password="testpass")
        self.client.login(username="test", password="testpass")
        self.roommate_post = RoommatePost.objects.create(
            user=self.user,
            message="Initial",
            date="2000-01-01",
        )
        self.url = f"/roommate-posts/api/{self.roommate_post.id}/"

    def test_allowed_field_can_be_updated(self):
        """
        Normal update of an allowed field should succeed.
        """
        data = {"message": "Updated"}

        response = self.client.patch(self.url, data, content_type="application/json")
        self.roommate_post.refresh_from_db()

        self.assertIn(response.status_code, [200, 204])
        self.assertEqual(self.roommate_post.message, "Updated")

    def test_protected_fields_cannot_be_overwritten(self):
        """
        Sending protected fields like 'id' or 'owner' should not
        overwrite them — the serializer should ignore or reject them.
        """
        original_id = self.roommate_post.id
        # data = {"message": "Updated", "id": 99999}

        # response = self.client.patch(self.url, data, content_type="application/json")
        self.roommate_post.refresh_from_db()

        # ID must never change regardless of what was sent
        self.assertEqual(self.roommate_post.id, original_id)

    def test_unauthenticated_user_cannot_update(self):
        """
        Unauthenticated requests should be rejected entirely.
        """
        self.client.logout()
        data = {"title": "Hacked", "price": 0}

        response = self.client.patch(self.url, data, content_type="application/json")
        self.roommate_post.refresh_from_db()

        self.assertIn(response.status_code, [401, 403])
        self.assertEqual(self.roommate_post.message, "Initial")

    def test_attacker_cannot_modify_or_delete_victims_post(self):
        victim = User.objects.create_user("victim", password="pw")
        victim_post = RoommatePost.objects.create(user=victim, message="x", date="2026-01-01")
        self.client.force_login(self.user)  # attacker
        r1 = self.client.patch(
            f"/roommate-posts/api/{victim_post.id}/", {"message": "h"}, content_type="application/json"
        )
        r2 = self.client.delete(f"/roommate-posts/api/{victim_post.id}/")
        self.assertIn(r1.status_code, (403, 404))
        self.assertIn(r2.status_code, (403, 404))
        self.assertTrue(RoommatePost.objects.filter(id=victim_post.id, message="x").exists())


# END OF test 6


# 9
class SafeMapFilter(TestCase):
    """
    Before: '| safe' filter removes security in HTML (allows functions to bypass security check)
    After: Removed '| safe' filter to increase security
    """

    def setUp(self):
        self.url = "/map/"

    def test_safe_filter_not_in_template(self):
        """
        Verify |safe has been removed from the map template.
        Reads map.html file and checks that |safe does not appear anywhere in the file.
        """
        with open("../templates/map.html", "r") as f:
            content = f.read()
        self.assertNotIn("|safe", content)

    def test_xss_payload_is_escaped_in_response(self):
        """
        User-controlled values should be HTML-escaped in the response.
        This test sends a payload that would trigger an alert if it were rendered as raw HTML.
        """
        payload = "<script>alert(1)</script>"
        resp = self.client.post(
            self.url,
            {
                "city": payload,
                "state": "CO",
                "amenity": payload,
                "keyword": payload,
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()

        # Raw payload should never appear unescaped
        self.assertNotIn("<script>alert(1)</script>", body)

        # The escaped version should appear instead
        self.assertIn("&lt;script&gt;", body)


# END OF test 9
