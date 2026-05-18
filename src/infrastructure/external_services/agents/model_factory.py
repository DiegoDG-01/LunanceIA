from os import environ
from pydantic_ai.models import Model
from infrastructure.config.settings import settings
from shared.exceptions.domain import InvalidAIProviderError
from enum import StrEnum


class AIProvider(StrEnum):
    OLLAMA = "ollama"
    GOOGLE = "google-gla"
    DEEPSEEK = "deepseek"
    TEST = "test"


def build_model() -> Model:
    match settings.AI_PROVIDER:
        case AIProvider.OLLAMA:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.ollama import OllamaProvider

            environ["OLLAMA_API_KEY"] = settings.AI_API_KEY

            if settings.AI_BASE_URL == "":
                return OpenAIChatModel(model_name=settings.AI_MODEL_ID)
            else:
                return OpenAIChatModel(
                    model_name=settings.AI_MODEL_ID,
                    provider=OllamaProvider(base_url=settings.AI_BASE_URL),
                )
        case AIProvider.GOOGLE:
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider

            return GoogleModel(
                model_name=settings.AI_MODEL_ID,
                provider=GoogleProvider(api_key=settings.AI_API_KEY),
            )
        case AIProvider.DEEPSEEK:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.deepseek import DeepSeekProvider

            return OpenAIChatModel(
                model_name=settings.AI_MODEL_ID,
                provider=DeepSeekProvider(api_key=settings.AI_API_KEY),
            )
        case AIProvider.TEST:
            return None
        case _:
            raise InvalidAIProviderError(provider=str(settings.AI_PROVIDER))
