from google import genai
from google.genai import types
from infrastructure.config.config import settings
from json import loads, JSONDecodeError
from shared.utils.promts import LUNANCE_PROMPT
from OLD.schemas.gemini import GeminiReceipt, GeminiErrorResponse


class Gemini:
    """
    A Singleton class to handle interactions with the Google Gemini API.

    This class ensures that only one instance of the Gemini client is created
    throughout the application's lifecycle, which is an efficient way to manage
    API connections.
    """
    _instance = None

    def __new__(cls):
        """
        Implements the Singleton pattern.

        If an instance of the class does not exist, it creates one and initializes
        the Gemini client with the API key from the settings. Otherwise, it returns
        the existing instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize the Gemini client upon first instance creation.
            cls._instance.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return cls._instance

    def analyze_receipt(self, image_data: bytes) -> dict | bool:
        """
        Analyzes a receipt image and extracts structured data as JSON.

        Args:
            image_data: The receipt image data in bytes.

        Returns:
            A dictionary containing the extracted receipt data on success,
            or False if an error occurs during the API call or JSON parsing.
        """
        try:
            # Send the image data to the Gemini model for analysis.
            # The system instruction guides the model to return a specific JSON format.
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL_ID,
                config=types.GenerateContentConfig(
                    system_instruction=LUNANCE_PROMPT
                ),
                contents=types.Part.from_bytes(
                    data=image_data,
                    mime_type='image/jpeg'
                )
            )
        except Exception as e:
            # Handle potential exceptions during the API call (e.g., network issues).
            print(f"Error calling Gemini API: {e}")
            return False

        try:
            # Clean the response text to ensure it's valid JSON.
            # LLMs can sometimes wrap their JSON output in markdown backticks or add "json".
            text_to_json = response.text.replace("`", "").replace("json", "")
            # Parse the cleaned string into a Python dictionary.
            json_response = loads(text_to_json)
        except JSONDecodeError as e:
            # Handle cases where the response is not valid JSON.
            print(f"JSON decoding failed: {e}")
            return False
        except Exception as e:
            # Handle other unexpected errors during post-processing.
            print(f"An unexpected error occurred during response parsing: {e}")
            return False

        try:
            GeminiReceipt.model_validate(json_response)
            return json_response
        except Exception as e:
            try:
                GeminiErrorResponse.model_validate(json_response)
                return json_response
            except Exception as e:
                print(f"An unexpected error occurred during response validation: {e}")
                return False


# Create a global instance of the Gemini service for easy access across the application.
# This leverages the Singleton pattern to ensure a single, shared client.
gemini = Gemini()
