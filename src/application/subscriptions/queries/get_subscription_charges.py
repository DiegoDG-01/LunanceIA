from dataclasses import dataclass
from typing import List

from domain.repositories.subscription_charge_repository import SubscriptionChargeRepository
from application.dto.subscription_dto import SubscriptionChargeDetailResponseDTO


@dataclass
class GetSubscriptionChargesQuery:
    user_id: int
    limit: int = 100
    offset: int = 0


class GetSubscriptionChargesHandler:

    def __init__(
        self,
        subscription_charge_repository: SubscriptionChargeRepository,
    ):
        self.subscription_charge_repository = subscription_charge_repository

    def handle(self, query: GetSubscriptionChargesQuery) -> List[SubscriptionChargeDetailResponseDTO]:
        charges = self.subscription_charge_repository.get_by_user_with_details(
            user_id=query.user_id
        )

        return [
            SubscriptionChargeDetailResponseDTO.from_entity(
                charge, sub_name, trans_uuid, trans_amount, trans_desc, cat_name, acc_name
            )
            for charge, sub_name, trans_uuid, trans_amount, trans_desc, cat_name, acc_name in charges
        ]
