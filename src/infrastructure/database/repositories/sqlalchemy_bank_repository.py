from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.repositories.bank_repository import BankRepository
from domain.entities.bank import Bank

# from shared.exceptions import BankNotFound
from infrastructure.database.models.bank import BankModel


class SQLAlchemyBankRepository(BankRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    def _model_to_entity(self, model: BankModel) -> Bank:
        return Bank(
            id=model.id,
            name=model.name,
            code=model.code,
            country=model.country,
            logo_url=model.logo_url,
            color=model.color,
            is_active=model.is_active,
        )

    async def get_all(self) -> List[Bank]:
        stmt = select(BankModel)
        result = await self.db.execute(stmt)
        bank_models = result.scalars().all()

        return [self._model_to_entity(model) for model in bank_models]

    async def get_by_id(self, bank_id: int) -> Optional[Bank]:
        bank_model = await self.db.get(BankModel, bank_id)
        if bank_model:
            return self._model_to_entity(bank_model)
        return None

    async def get_by_code(self, bank_code: str) -> Optional[Bank]:
        result = await self.db.execute(
            select(BankModel).where(BankModel.code == bank_code)
        )
        bank_model = result.scalar_one_or_none()
        return self._model_to_entity(bank_model) if bank_model else None

    async def create(self, bank: Bank) -> Bank:
        bank_model = BankModel(
            name=bank.name,
            code=bank.code,
            country=bank.country,
            logo_url=bank.logo_url,
            color=bank.color,
            is_active=bank.is_active,
        )
        self.db.add(bank_model)
        await self.db.commit()
        await self.db.refresh(bank_model)
        return self._model_to_entity(bank_model)

    async def update(self, bank: Bank) -> Bank:
        bank_model = await self.db.get(BankModel, bank.id)
        if not bank_model:
            raise ValueError("Bank not found")

        bank_model.name = bank.name
        bank_model.code = bank.code
        bank_model.country = bank.country
        bank_model.logo_url = bank.logo_url
        bank_model.color = bank.color
        bank_model.is_active = bank.is_active

        await self.db.commit()
        await self.db.refresh(bank_model)
        return self._model_to_entity(bank_model)

    async def delete(self, bank_id: int) -> None:
        bank_model = await self.db.get(BankModel, bank_id)
        if not bank_model:
            raise ValueError("Bank not found")

        await self.db.delete(bank_model)
        await self.db.commit()
