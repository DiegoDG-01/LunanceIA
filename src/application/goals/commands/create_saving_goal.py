from dataclasses import dataclass

from domain.entities.saving_goal import SavingGoal

from application.dto.saving_goal_dto import CreateSavingGoalDTO, SavingGoalResponseDTO
from domain.repositories.account_repository import AccountRepository
from domain.repositories.saving_goal_repository import SavingGoalRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from shared.exceptions.domain import UserNotFoundError, AccountNotFoundError


@dataclass
class CreateSavingGoalCommand:
    dto: CreateSavingGoalDTO


class CreateSavingGoalHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        account_repository: AccountRepository,
        goal_repository: SavingGoalRepository,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.goal_repository = goal_repository
        self.uow = uow

    async def handle(self, command: CreateSavingGoalCommand) -> SavingGoalResponseDTO:
        dto = command.dto

        user = await self.user_repository.get_by_id(dto.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=dto.account_uuid, user_id=dto.user_id
        )
        if not account:
            raise AccountNotFoundError(account_uuid=dto.account_uuid)

        goal = SavingGoal.create_new(
            user_id=user.id,
            account_id=account.id,
            name=dto.name,
            target_amount=dto.target_amount,
            target_date=dto.target_date,
            description=dto.description,
        )

        async with self.uow:
            saved_goal = await self.goal_repository.create(goal)
            await self.uow.commit()

        return SavingGoalResponseDTO.from_entity(
            goal=saved_goal,
            account_name=account.name,
            account_uuid=account.uuid,
            current_amount=account.current_balance.amount,
        )