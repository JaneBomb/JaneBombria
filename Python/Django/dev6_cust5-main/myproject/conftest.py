import os

import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()


# Use pytest to stop ASGI from breaking the runtime testing
def pytest_configure():
    settings.TESTING = True
