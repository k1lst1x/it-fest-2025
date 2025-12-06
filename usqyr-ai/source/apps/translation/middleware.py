import logging

from django.http import HttpResponseRedirect
from django.utils.translation import (
    activate as django_activate,
    get_supported_language_variant,
)

from ._core.active_language_context import set_language
from ._core.conf import (
    get_supported_language_codes,
    DEFAULT_LANGUAGE_STARTUP,
    ENABLE_DJANGO_TRANSLATION_ACTIVATE,
    LANGUAGE_EXCLUDED_URL_PREFIXES,
)

logger = logging.getLogger("data.translation.middleware")


class CustomLocaleMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        self.supported_codes = set(get_supported_language_codes())
        self.excluded_prefixes = tuple(LANGUAGE_EXCLUDED_URL_PREFIXES)

    def __call__(self, request):
        path_parts = request.path.split("/")
        lang = None

        if len(path_parts) > 1 and path_parts[1] in self.supported_codes:
            lang = path_parts[1]
            request.path_info = "/" + "/".join(path_parts[2:])
            request.session["django_language"] = lang
        else:
            lang = request.session.get("django_language", DEFAULT_LANGUAGE_STARTUP)
            if not request.path.startswith(self.excluded_prefixes):
                redirect_path = f"/{lang}{request.path}"
                if request.GET:
                    redirect_path += f"?{request.GET.urlencode()}"
                return HttpResponseRedirect(redirect_path)

        if lang not in self.supported_codes:
            lang = DEFAULT_LANGUAGE_STARTUP

        set_language(lang)
        request.LANGUAGE_CODE = lang

        if ENABLE_DJANGO_TRANSLATION_ACTIVATE:
            try:
                django_activate(get_supported_language_variant(lang))
            except Exception:
                logger.info(
                    "Django does not support language '%s', skipping activate()",
                    lang,
                )

        return self.get_response(request)
