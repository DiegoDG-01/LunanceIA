"""Qué monedas necesitan tipo de cambio aunque no haya acciones en ellas.

El job de precios pide el tipo de cambio de una moneda cuando algo lo usa: un valor que se
sigue, y también cuentas y apartados en esa moneda (el patrimonio y la historia de lo
invertido los convierten a pesos).
"""

from abc import ABC, abstractmethod
from datetime import date


class CurrencyDemandRepository(ABC):
    @abstractmethod
    async def since(self) -> dict[str, date | None]:
        """Moneda (no MXN) → desde qué día hace falta su tipo de cambio.

        Con apartados, el día en que empezó el más antiguo (la historia lo valúa desde ahí).
        Si solo hay cuentas, `None`: basta con los días recientes.
        """
