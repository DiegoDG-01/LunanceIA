import logging
from typing import Optional

from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import OverflowAction
from domain.objects.money import Money
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from shared.exceptions.domain import InvalidOverflowTargetError

logger = logging.getLogger(__name__)

# Tope de saltos por si una cadena queda inconsistente en base de datos.
# La validación al configurar ya impide ciclos; esto es la red de seguridad.
MAX_OVERFLOW_HOPS = 10


class PositionOverflowService:
    """Reparte el excedente de un apartado por su cadena de destinos.

    Encadenar apartados con topes distintos es como se representan las tasas
    por tramo: A (tope 25,000 al 10%) desborda a B (al 5%). Este servicio
    recorre esa cadena y devuelve lo que no cupo en ningún apartado para que
    el que llama lo abone al saldo disponible.

    No toca la cuenta ni crea transacciones: quien llama ya tiene la cuenta
    lockeada y sabe qué descripción darle al movimiento.
    """

    def __init__(self, position_repository: InvestmentPositionRepository):
        self.position_repository = position_repository

    async def target_uuid(self, position: InvestmentPosition) -> Optional[str]:
        """uuid del apartado destino, para no exponer ids internos en la API."""
        if position.overflow_position_id is None:
            return None

        target = await self.position_repository.get_by_id(
            position_id=position.overflow_position_id
        )
        return target.uuid if target else None

    async def validate_target(self, source: InvestmentPosition, target_id: int) -> None:
        """Comprueba que `source` pueda desbordarse a `target_id`.

        Es la única validación de la cadena que necesita consultar la base de
        datos, por eso vive aquí y no en la entidad: que el destino exista,
        sea de la misma cuenta, pueda recibir dinero y no cierre un ciclo.
        """
        target = await self.position_repository.get_by_id(position_id=target_id)
        if target is None:
            raise InvalidOverflowTargetError(f"el apartado {target_id} no existe")

        if target.account_id != source.account_id:
            raise InvalidOverflowTargetError(
                "el apartado destino debe ser de la misma cuenta"
            )

        if not target.can_absorb():
            raise InvalidOverflowTargetError(
                "el apartado destino debe ser a la vista y estar activo"
            )

        if source.id is None:
            # Un apartado que todavía no existe no puede cerrar un ciclo.
            return

        # Un ciclo dejaría al dinero dando vueltas sin llegar nunca al
        # disponible, así que se corta al configurar y no en ejecución.
        visited = {source.id, target_id}
        current = target
        for _ in range(MAX_OVERFLOW_HOPS):
            if (
                current.overflow_action != OverflowAction.TO_POSITION
                or current.overflow_position_id is None
            ):
                return

            next_id = current.overflow_position_id
            if next_id == source.id:
                raise InvalidOverflowTargetError(
                    "la cadena de desbordamiento regresaría a este apartado"
                )
            if next_id in visited:
                raise InvalidOverflowTargetError(
                    "el apartado destino ya está en una cadena con un ciclo"
                )

            following = await self.position_repository.get_by_id(position_id=next_id)
            if following is None:
                return

            visited.add(next_id)
            current = following

        raise InvalidOverflowTargetError(
            f"la cadena de desbordamiento supera {MAX_OVERFLOW_HOPS} apartados"
        )

    async def spill(self, source: InvestmentPosition, amount: Money) -> Money:
        """Reparte `amount` por la cadena de `source`.

        Devuelve lo que debe ir al saldo disponible: puede ser cero (la cadena
        absorbió todo) o el monto completo (no hay destino, o el que había ya
        no sirve). Nunca se pierde dinero en el camino.
        """
        if amount.amount <= 0:
            return amount

        remaining = amount
        current = source
        # Los locks se toman siguiendo las aristas de la cadena, que no tiene
        # ciclos, así que dos cascadas concurrentes no pueden bloquearse
        # mutuamente. `visited` protege de un ciclo que se haya colado en BD.
        visited = {source.id}

        for _ in range(MAX_OVERFLOW_HOPS):
            if (
                current.overflow_action != OverflowAction.TO_POSITION
                or current.overflow_position_id is None
            ):
                return remaining

            target_id = current.overflow_position_id
            if target_id in visited:
                logger.error(
                    f"overflow chain from position {source.id} loops back to "
                    f"{target_id}; sending {remaining.amount} to available balance"
                )
                return remaining

            target = await self.position_repository.get_by_id(
                position_id=target_id, for_update=True
            )
            if target is None or not target.can_absorb():
                # El destino se liquidó o desapareció: el excedente va al
                # disponible en vez de heredar la cadena de un apartado muerto.
                logger.warning(
                    f"overflow target {target_id} of position {source.id} cannot "
                    f"absorb; sending {remaining.amount} to available balance"
                )
                return remaining

            visited.add(target_id)
            remaining = target.deposit(remaining)
            await self.position_repository.update(target)

            if remaining.amount <= 0:
                return remaining

            current = target

        logger.error(
            f"overflow chain from position {source.id} exceeded "
            f"{MAX_OVERFLOW_HOPS} hops; sending {remaining.amount} to available balance"
        )
        return remaining
