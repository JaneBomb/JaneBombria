# socialPosts/apps.py
from django.apps import AppConfig


class SocialPostsConfig(AppConfig):
    name = "socialPosts"

    def ready(self):
        import socialPosts.signals  # noqa
