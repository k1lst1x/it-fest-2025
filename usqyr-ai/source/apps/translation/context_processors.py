from ._core.active_language_context import get_language
from ._core.conf import (
    get_visible_languages,
    get_supported_language_codes,
    get_language_name,
)


def current_language(request) -> dict:
    codes = get_supported_language_codes()
    lang_code = get_language()

    path_parts = request.path.strip("/").split("/")
    if path_parts and path_parts[0] in codes:
        trimmed_path = "/" + "/".join(path_parts[1:])
    else:
        trimmed_path = request.path or "/"

    query_string = request.META.get("QUERY_STRING")
    if query_string:
        trimmed_path += f"?{query_string}"

    return {
        "current_lang_code": lang_code,
        "current_lang_name": get_language_name(lang_code),
        "current_path_without_lang": trimmed_path,
        "show_languages_extended": get_visible_languages(),
    }
