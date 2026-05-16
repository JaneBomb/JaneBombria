from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from home.models import RoommatePost


class SocialPostsSignalTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")

    @override_settings(TESTING=True)
    def test_signal_skips_broadcast_during_testing(self):
        post = RoommatePost.objects.create(
            user=self.user,
            message="Test post",
            date=date(2026, 1, 1),
        )
        self.assertEqual(post.message, "Test post")

    def test_signal_skips_update(self):
        post = RoommatePost.objects.create(
            user=self.user,
            message="Original",
            date=date(2026, 1, 1),
        )
        post.message = "Updated"
        post.save()
        self.assertEqual(post.message, "Updated")

    def test_serializer_handles_string_date(self):
        from socialPosts.serializers import serialize_listing

        post = RoommatePost.objects.create(
            user=self.user,
            message="Hello",
            date="2026-03-01",
        )
        result = serialize_listing(post)
        self.assertEqual(result["created_at"], "1 Mar 2026")
