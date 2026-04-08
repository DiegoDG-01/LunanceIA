from os import environ
from pydantic_ai.models import Model
from infrastructure.config.settings import settings


def build_model() -> Model:
    match settings.AI_PROVIDER:
        case "ollama":
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
        case "google-gla":
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider

            provider = GoogleProvider(api_key=settings.AI_API_KEY)
            return GoogleModel(model_name=settings.AI_MODEL_ID, provider=provider)
        case _:
            raise ValueError("Invalid AI provider")
