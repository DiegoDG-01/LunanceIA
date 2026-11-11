from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from application.auth.dto import ClientContext
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.users.user import User
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import CommandValidationError
from shared.exceptions.domain import UsernameAlreadyExistsError, UserNotFoundError
from shared.utils.time import utc_now


@dataclass
class ChangeUsernameCommand:
    user_id: int
    username: str
    context: ClientContext = field(default_factory=ClientContext)


class ChangeUsernameHandler:
    """Cambia el username (las cuentas de Google y Apple empiezan con uno generado). Debe
    estar libre entre las cuentas y los registros pendientes abiertos."""

    def __init__(
        self,
        user_repository: UserRepository,
        pending_signup_repository: PendingSignupRepository,
        auth_event_repository: AuthEventRepository,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.user_repository = user_repository
        self.pending_signup_repository = pending_signup_repository
        self.auth_event_repository = auth_event_repository
        self.uow = uow
        self._now = now

    async def handle(self, command: ChangeUsernameCommand) -> User:
        username = (command.username or "").strip()
        if not username:
            raise CommandValidationError(
                "ChangeUsernameCommand", ["El nombre es requerido"]
            )
        now = self._now()
        async with self.uow:
            user = await self.user_repository.get_by_id(
                command.user_id, for_update=True
            )
            if user is None:
                raise UserNotFoundError()
            if user.name == username:
                return user
            holder = await self.user_repository.get_by_username(username)
            if holder is not None and holder.id != user.id:
                raise UsernameAlreadyExistsError()
            signup = await self.pending_signup_repository.get_by_username(username)
            if (
                signup is not None
                and signup.email != user.email
                and signup.is_open(now)
            ):
                raise UsernameAlreadyExistsError()

            previous = user.name
            user.name = username
            try:
                user = await self.user_repository.update(user)
            except IntegrityError:
                raise UsernameAlreadyExistsError() from None
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.USERNAME_CHANGED,
                    created_at=now,
                    user_id=user.id,
                    ip=command.context.ip,
                    user_agent=command.context.user_agent,
                    details={"from": previous, "to": username},
                )
            )
            await self.uow.commit()
        return user
