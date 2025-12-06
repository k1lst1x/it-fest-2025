from django.conf import settings


ENABLE_DJANGO_TRANSLATION_ACTIVATE: bool = False
TRANSLATION_CACHE_TTL_SECONDS: int = 60 * 8


DEFAULT_LANGUAGE_STARTUP: str = "ru"
DEFAULT_REFERENCE_LANGUAGE: str = "ru"
AUTO_COPY_REFERENCE_TEXT: bool = True


LANGUAGE_EXCLUDED_URL_PREFIXES: list[str] = [
    "/api",
    "/dj-admin"
]


SUPPORTED_LANGUAGES: list[dict[str, str | bool]] = [
    {"code": "ru", "name": "Русский", "visible_in_ui": True},
    {"code": "en", "name": "English", "visible_in_ui": True},
    {"code": "kk", "name": "Қазақша", "visible_in_ui": True},
]


def get_supported_language_codes() -> list[str]:
    return [lang["code"] for lang in SUPPORTED_LANGUAGES]


def get_visible_languages() -> list[dict[str, str]]:
    return [
        {"code": lang["code"], "name": lang["name"]}
        for lang in SUPPORTED_LANGUAGES
        if lang.get("visible_in_ui")
    ]


def get_language_name(lang_code: str) -> str:
    return next(
        (lang["name"] for lang in SUPPORTED_LANGUAGES if lang["code"] == lang_code),
        lang_code,
    )


def get_language_dict() -> dict[str, str]:
    return {lang["code"]: lang["name"] for lang in SUPPORTED_LANGUAGES}


def is_openai_enabled() -> bool:
    return bool(getattr(settings, "OPENAI_KEY", "").strip())


def validate_translation_config() -> None:
    codes = get_supported_language_codes()

    if DEFAULT_LANGUAGE_STARTUP not in codes:
        raise ValueError(
            f"DEFAULT_LANGUAGE_STARTUP ('{DEFAULT_LANGUAGE_STARTUP}') is not in SUPPORTED_LANGUAGES."
        )

    if DEFAULT_REFERENCE_LANGUAGE not in codes:
        raise ValueError(
            f"DEFAULT_REFERENCE_LANGUAGE ('{DEFAULT_REFERENCE_LANGUAGE}') is not in SUPPORTED_LANGUAGES."
        )

    seen = set()
    for lang in SUPPORTED_LANGUAGES:
        code = lang.get("code")
        name = lang.get("name")
        if not code or not name:
            raise ValueError(
                f"Each language must have 'code' and 'name'. Invalid entry: {lang}"
            )
        if code in seen:
            raise ValueError(f"Duplicate language code detected: '{code}'")
        seen.add(code)

    for path in LANGUAGE_EXCLUDED_URL_PREFIXES:
        if not path.startswith("/"):
            raise ValueError(f"Excluded path must start with '/': '{path}'")


validate_translation_config()
