"""
Django settings for config project.
"""

import os
from pathlib import Path


# ==========================================================
# BASE DIRECTORY
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================================
# LOAD .ENV FILE
# ==========================================================

def _load_env_file(path):
    """
    Read KEY=VALUE lines into os.environ without overriding
    existing environment variables.

    This allows local development using a .env file while
    Render environment variables take priority in production.
    """

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return

    for line in lines:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export "):].strip()

        key, separator, value = line.partition("=")

        if not separator:
            continue

        key = key.strip()
        value = value.strip()

        # Remove surrounding quotes
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(BASE_DIR / ".env")


# ==========================================================
# HELPER FUNCTIONS FOR ENVIRONMENT VARIABLES
# ==========================================================

def env_bool(name, default=False):
    """
    Convert an environment variable to a real Python boolean.

    Supports:
        True / False
        true / false
        1 / 0
        yes / no
        on / off
    """

    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


# ==========================================================
# SECURITY
# ==========================================================

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-this-secret-key-in-production"
)

DEBUG = env_bool("DEBUG", False)


# ==========================================================
# ALLOWED HOSTS
# ==========================================================

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,[::1]"
    ).split(",")
    if host.strip()
]


# ==========================================================
# CSRF TRUSTED ORIGINS
# ==========================================================

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        ""
    ).split(",")
    if origin.strip()
]


# ==========================================================
# APPLICATIONS
# ==========================================================

INSTALLED_APPS = [

    # Third-party apps
    "unfold",

    # Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Project apps
    "accounts",
    "academics",
    "workload",
    "analytics",
    "academic_calendar",
    "reports",
]


# ==========================================================
# MIDDLEWARE
# ==========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Serve static files in production
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==========================================================
# URLS AND WSGI
# ==========================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# ==========================================================
# TEMPLATES
# ==========================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ==========================================================
# DATABASE
# SQLITE - KEEP SQLITE
# ==========================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ==========================================================
# PASSWORD VALIDATION
# ==========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator",
    },
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator",
    },
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator",
    },
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator",
    },
]


# ==========================================================
# INTERNATIONALIZATION
# ==========================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Kigali"

USE_I18N = True

USE_TZ = True


# ==========================================================
# STATIC FILES
# ==========================================================

STATIC_URL = "/static/"

# Development static folder
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Static files collected for production
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise production storage
STORAGES = {
    "staticfiles": {
        "BACKEND":
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# ==========================================================
# MEDIA FILES
# ==========================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ==========================================================
# DEFAULT PRIMARY KEY
# ==========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==========================================================
# CUSTOM USER MODEL
# ==========================================================

AUTH_USER_MODEL = "accounts.User"


# ==========================================================
# EMAIL SETTINGS
# ==========================================================

# SMTP server
EMAIL_HOST = os.environ.get(
    "EMAIL_HOST",
    "smtp.gmail.com"
)

# Gmail STARTTLS port
EMAIL_PORT = int(
    os.environ.get(
        "EMAIL_PORT",
        "587"
    )
)

# Gmail account
EMAIL_HOST_USER = os.environ.get(
    "EMAIL_HOST_USER",
    ""
)

# Gmail App Password
EMAIL_HOST_PASSWORD = os.environ.get(
    "EMAIL_HOST_PASSWORD",
    ""
)

# IMPORTANT:
# Render provides environment variables as strings.
# These functions convert True/False correctly to Python booleans.

EMAIL_USE_TLS = env_bool(
    "EMAIL_USE_TLS",
    True
)

EMAIL_USE_SSL = env_bool(
    "EMAIL_USE_SSL",
    False
)

# SMTP timeout
EMAIL_TIMEOUT = int(
    os.environ.get(
        "EMAIL_TIMEOUT",
        "10"
    )
)


# ==========================================================
# EMAIL BACKEND
# ==========================================================

if os.environ.get("EMAIL_BACKEND"):

    EMAIL_BACKEND = os.environ["EMAIL_BACKEND"]

elif EMAIL_HOST:

    EMAIL_BACKEND = (
        "django.core.mail.backends.smtp.EmailBackend"
    )

else:

    EMAIL_BACKEND = (
        "django.core.mail.backends.console.EmailBackend"
    )


# ==========================================================
# DEFAULT EMAIL ADDRESS
# ==========================================================

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "AUCA Workload Management System <no-reply@auca.ac.rw>"
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL


# ==========================================================
# SITE INFORMATION
# ==========================================================

SITE_NAME = "AUCA Workload Management System"

SITE_URL = os.environ.get(
    "SITE_URL",
    "http://127.0.0.1:8000"
)


# ==========================================================
# LOGGING
# ==========================================================

LOGGING = {

    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "simple": {
            "format":
                "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },

    "loggers": {
        "workload.notifications": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# ==========================================================
# DJANGO UNFOLD CONFIGURATION
# ==========================================================

UNFOLD = {

    # ======================================================
    # SITE INFORMATION
    # ======================================================

    "SITE_TITLE":
        "AUCA Workload Management System",

    "SITE_HEADER":
        "AUCA Workload Management System",

    "SITE_SUBHEADER":
        "Adventist University of Central Africa",


    # ======================================================
    # LOGO
    # ======================================================

    "SITE_LOGO":
        lambda request:
        "/static/images/AUCA Logo.png",

    "SITE_ICON":
        lambda request:
        "/static/images/AUCA Logo.png",


    # ======================================================
    # THEME
    # ======================================================

    "THEME":
        "light",

    "SHOW_THEME_SWITCHER":
        False,


    # ======================================================
    # AUCA COLORS
    # ======================================================

    "COLORS": {

        "primary": {

            "50": "#EAF3FB",
            "100": "#D5E9F8",
            "200": "#A8D1F0",
            "300": "#7AB8E8",
            "400": "#4C9FDB",
            "500": "#0056A6",
            "600": "#004987",
            "700": "#003B73",
            "800": "#002A55",
            "900": "#001A35",

        },

    },


    # ======================================================
    # CUSTOM CSS
    # ======================================================

    "STYLES": {

        "all": [

            "/static/css/unfold-custom.css",

        ],

    },


    # ======================================================
    # SIDEBAR
    # ======================================================

    "SIDEBAR": {

        "show_search": True,

        "show_all_applications": True,


        "navigation": [

            {

                "title":
                    "Academic Management",

                "separator": True,

                "items": [

                    {
                        "title": "Faculties",
                        "icon": "school",
                        "link": "/admin/academics/faculty/",
                    },

                    {
                        "title": "Programs",
                        "icon": "menu_book",
                        "link": "/admin/academics/program/",
                    },

                    {
                        "title": "Courses",
                        "icon": "book",
                        "link": "/admin/academics/course/",
                    },

                ]

            },


            {

                "title":
                    "People",

                "separator": True,

                "items": [

                    {
                        "title": "Lecturers",
                        "icon": "person",
                        "link": "/admin/academics/lecturer/",
                    },

                ]

            },


            {

                "title":
                    "Workload Management",

                "separator": True,

                "items": [

                    {
                        "title": "Workload Assignment",
                        "icon": "assignment",
                        "link": "/admin/workload/workload/",
                    },

                ]

            },

        ]

    },

}