from typing import cast

from fastapi import APIRouter, Depends, Request, Response, status, HTTPException

from domain.entities.user import User
from application.dto.api_key_dto import CreateAPIKeyDTO
from application.api_keys.commands.create_api_key import (
    CreateAPIKeyCommand,
    CreateAPIKeyHandler,
)
from application.api_keys.commands.revoke_api_key import (
    RevokeAPIKeyCommand,
    RevokeAPIKeyHandler,
)
from application.api_keys.commands.delete_api_key import (
    DeleteAPIKeyCommand,
    DeleteAPIKeyHandler,
)
from application.api_keys.queries.list_api_keys import (
    ListAPIKeysQuery,
    ListAPIKeysHandler,
)
from presentation.schemas.requests.api_key import CreateAPIKeyRequest
from presentation.schemas.responses.api_key import (
    APIKeyCreatedResponse,
    APIKeyResponse,
)
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.dependencies.api_key_deps import (
    get_create_api_key_handler,
    get_list_api_keys_handler,
    get_revoke_api_key_handler,
    get_delete_api_key_handler,
)
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_50_per_minute,
    limiter_10_per_minute,
)

router = APIRouter()


@router.post(
    "/", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    request: Request,
    api_key_request: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_active_user),
    handler: CreateAPIKeyHandler = Depends(get_create_api_key_handler),
):
    """Crea una API key para el usuario autenticado. La key completa se devuelve UNA sola vez."""
    enforce_rate_limit(limiter_10_per_minute, request)

    dto = CreateAPIKeyDTO(
        user_id=cast(int, current_user.id),
        name=api_key_request.name,
        scopes=[scope.value for scope in api_key_request.scopes],
        expires_at=api_key_request.expires_at,
    )

    result = await handler.handle(CreateAPIKeyCommand(dto=dto))
    return APIKeyCreatedResponse(**result.__dict__)


@router.get("/", response_model=list[APIKeyResponse])
async def list_api_keys(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    handler: ListAPIKeysHandler = Depends(get_list_api_keys_handler),
):
    """Lista las API keys del usuario autenticado (sin exponer la key ni el hash)."""
    enforce_rate_limit(limiter_50_per_minute, request)

    query = ListAPIKeysQuery(user_id=cast(int, current_user.id))
    keys = await handler.handle(query)
    return [APIKeyResponse(**key.__dict__) for key in keys]


@router.patch("/{api_key_uuid}/revoke/", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    request: Request,
    api_key_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: RevokeAPIKeyHandler = Depends(get_revoke_api_key_handler),
):
    """Revoca (desactiva) una API key del usuario sin borrarla: deja de autenticar
    pero se conserva en el listado para auditoría. 204 si revoca, 404 si no existe
    o no es suya."""
    enforce_rate_limit(limiter_10_per_minute, request)

    command = RevokeAPIKeyCommand(uuid=api_key_uuid, user_id=cast(int, current_user.id))
    revoked = await handler.handle(command)

    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{api_key_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    request: Request,
    api_key_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: DeleteAPIKeyHandler = Depends(get_delete_api_key_handler),
):
    """Elimina permanentemente una API key del usuario (desaparece del listado).
    204 si elimina, 404 si no existe o no es suya."""
    enforce_rate_limit(limiter_10_per_minute, request)

    command = DeleteAPIKeyCommand(uuid=api_key_uuid, user_id=cast(int, current_user.id))
    deleted = await handler.handle(command)

    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
