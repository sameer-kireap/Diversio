import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diversio_hris.settings")
application = get_wsgi_application()
