from shared.constants.validation_messages import (
    ERROR_DETAIL_MESSAGES,
    get_error_detail_message,
)


def get_error_message(code: str, lang: str = "es") -> str:
    return get_error_detail_message(lang, code)


ERROR_MESSAGES = ERROR_DETAIL_MESSAGES
