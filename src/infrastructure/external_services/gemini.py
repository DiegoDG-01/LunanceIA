from google import genai
import json
from google.genai import types
from typing import Optional
from decimal import Decimal
from datetime import date
from shared.utils.prompts import LUNANCE_PROMPT
from domain.objects.enums import TransactionType
from infrastructure.config.settings import settings
from shared.exceptions.domain import (
    GeminiProcessingError,
    GeminiInvalidResponseError,
    GeminiAPIError,
    InvalidImageError,
)


class GeminiTransactionResult:
    """Resultado del procesamiento de Gemini"""

    def __init__(
        self,
        amount: Decimal,
        transaction_type: TransactionType,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        transaction_date: Optional[date] = None,
        category_id: Optional[int] = None,
    ):
        self.amount = amount
        self.transaction_type = transaction_type
        self.description = description
        self.notes = notes
        self.transaction_date = transaction_date or date.today()
        self.category_id = category_id


class GeminiService:
    def __init__(self):
        # Configurar API key
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def extract_transaction_data(
        self, image_data: bytes
    ) -> GeminiTransactionResult:
        """Extrae datos de transacción de una imagen"""

        # 1. Validar imagen
        if not image_data or len(image_data) == 0 or not isinstance(image_data, bytes):
            raise InvalidImageError("La imagen proporcionada no es valida")

        # 2. Enviar a Gemini
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL_ID,
                config=types.GenerateContentConfig(system_instruction=LUNANCE_PROMPT),
                contents=types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
            )
        except Exception as e:
            raise GeminiAPIError(f"Error en la llamada a Gemini: {e}")

        # 3. Parsear respuesta JSON
        try:
            text_to_json = response.text.replace("`", "").replace("json", "")
            data = json.loads(text_to_json)
        except (json.JSONDecodeError, ValueError):
            # Fallback si Gemini no responde en JSON válido
            raise GeminiInvalidResponseError("Gemini devolvió una respuesta inválida")

        # 4. Validar respuesta
        if data.get("error"):
            raise GeminiInvalidResponseError(
                f"Gemini devolvió una respuesta inválida {data.get('error', 'Error desconocido')}"
            )

        # 5. Extraer datos
        try:
            return GeminiTransactionResult(
                amount=Decimal(str(data.get("amount", 0))),
                transaction_type=TransactionType(
                    data.get("transaction_type", "EXPENSE")
                ),
                description=data.get("description"),
                notes=data.get("notes"),
                transaction_date=date.fromisoformat(data.get("transaction_date"))
                if data.get("transaction_date")
                else None,
                category_id=None,  # Por ahora null, luego puedes agregar lógica de categorías
            )
        except Exception as e:
            raise GeminiProcessingError(f"Error procesando respuesta de Gemini: {e}")
