import httpx

from application.interfaces.email import EmailDeliveryError, EmailSender, OutgoingEmail


class ResendEmailSender(EmailSender):
    """API HTTP de Resend (https://resend.com/docs/api-reference/emails/send-email)."""

    name = "resend"
    ENDPOINT = "https://api.resend.com/emails"

    def __init__(
        self,
        *,
        api_key: str,
        sender: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("ResendEmailSender necesita RESEND_API_KEY")
        self._api_key = api_key
        self._sender = sender
        self._timeout = timeout
        # Para tests: `httpx.MockTransport`.
        self._transport = transport

    def _payload(self, email: OutgoingEmail) -> dict:
        payload: dict = {
            "from": self._sender,
            "to": list(email.to),
            "subject": email.subject,
            "text": email.text,
            "tags": [{"name": "category", "value": email.tag}],
        }
        if email.html:
            payload["html"] = email.html
        return payload

    async def send(self, email: OutgoingEmail) -> None:
        async with httpx.AsyncClient(
            timeout=self._timeout, transport=self._transport
        ) as client:
            try:
                response = await client.post(
                    self.ENDPOINT,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=self._payload(email),
                )
            except httpx.HTTPError as error:
                raise EmailDeliveryError(
                    self.name, f"sin respuesta: {type(error).__name__}"
                ) from error
        if response.is_error:
            raise EmailDeliveryError(
                self.name, f"HTTP {response.status_code}: {response.text[:300]}"
            )
