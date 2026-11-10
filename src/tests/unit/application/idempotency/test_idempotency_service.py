"""IdempotencyService con un repositorio en memoria que simula lo que ve cada transacción."""

from datetime import UTC, datetime, timedelta

import pytest

from application.idempotency.commands.purge_idempotency_keys import (
    PurgeIdempotencyKeysCommand,
    PurgeIdempotencyKeysHandler,
)
from application.idempotency.service import IdempotencyService
from application.interfaces.idempotency import (
    IdempotencyRecord,
    IdempotencyRepository,
    StoredResponse,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.application import (
    IdempotencyKeyInUseError,
    IdempotencyKeyReusedError,
)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class FakeRepository(IdempotencyRepository):
    """`committed` es lo confirmado; `reads` permite simular lo que se ve en cada lectura."""

    def __init__(self):
        self.committed: dict[tuple[int, str], IdempotencyRecord] = {}
        self.created: dict[tuple[int, str], datetime] = {}
        self.claimed: list[tuple[int, str]] = []
        self.saved: list[StoredResponse] = []
        self.reads: list[IdempotencyRecord | None] = []

    async def try_claim(self, *, user_id, key, request_hash, created_at):
        if (user_id, key) in self.committed:
            return False
        self.claimed.append((user_id, key))
        return True

    async def get(self, *, user_id, key):
        if self.reads:
            return self.reads.pop(0)
        return self.committed.get((user_id, key))

    async def save_response(self, *, user_id, key, request_hash, response, created_at):
        self.saved.append(response)
        self.committed[(user_id, key)] = IdempotencyRecord(request_hash, response)

    async def purge(self, *, created_before):
        old = [k for k, created in self.created.items() if created < created_before]
        for k in old:
            self.committed.pop(k, None)
            self.created.pop(k)
        return len(old)


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    async def sleep(self, seconds: float) -> None:
        self.value += seconds


@pytest.fixture
def repo():
    return FakeRepository()


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def service(repo, uow, clock):
    return IdempotencyService(
        repo,
        uow,
        wait_timeout=1.0,
        poll_interval=0.1,
        now=lambda: NOW,
        monotonic=clock,
        sleep=clock.sleep,
    )


def operation(response: StoredResponse, calls: list):
    async def run() -> StoredResponse:
        calls.append(1)
        return response

    return run


CREATED = StoredResponse(status_code=201, body={"uuid": "abc"})


@pytest.mark.unit
@pytest.mark.asyncio
class TestIdempotencyService:
    async def test_new_key_runs_operation_and_saves_response(self, service, repo, uow):
        calls = []

        result = await service.execute(
            user_id=1, key="k", request_hash="h", operation=operation(CREATED, calls)
        )

        assert result.response == CREATED and result.replayed is False
        assert calls == [1]
        assert repo.claimed == [(1, "k")]
        assert repo.saved == [CREATED]
        assert uow.commits == 1

    async def test_stored_response_is_replayed_without_running(self, service, repo):
        repo.committed[(1, "k")] = IdempotencyRecord("h", CREATED)
        calls = []

        result = await service.execute(
            user_id=1, key="k", request_hash="h", operation=operation(CREATED, calls)
        )

        assert result.response == CREATED and result.replayed is True
        assert calls == []

    async def test_different_request_hash_is_rejected(self, service, repo):
        repo.committed[(1, "k")] = IdempotencyRecord("h", CREATED)

        with pytest.raises(IdempotencyKeyReusedError):
            await service.execute(
                user_id=1, key="k", request_hash="other", operation=operation(CREATED, [])
            )

    async def test_mismatch_is_reported_even_while_original_is_in_flight(
        self, service, repo
    ):
        repo.committed[(1, "k")] = IdempotencyRecord("h", None)

        with pytest.raises(IdempotencyKeyReusedError):
            await service.execute(
                user_id=1, key="k", request_hash="other", operation=operation(CREATED, [])
            )

    async def test_waits_for_the_original_to_store_its_response(
        self, service, repo, clock
    ):
        """La original confirmó el handler pero aún no guardó la respuesta."""
        repo.committed[(1, "k")] = IdempotencyRecord("h", CREATED)
        repo.reads = [IdempotencyRecord("h", None), IdempotencyRecord("h", None)]
        calls = []

        result = await service.execute(
            user_id=1, key="k", request_hash="h", operation=operation(CREATED, calls)
        )

        # Tras dos lecturas sin respuesta, la tercera ve la que guardó la original.
        assert result.replayed is True and result.response == CREATED
        assert calls == []
        assert clock.value == pytest.approx(0.2)

    async def test_key_without_response_after_timeout_is_409(self, service, repo, uow):
        repo.committed[(1, "k")] = IdempotencyRecord("h", None)
        calls = []

        with pytest.raises(IdempotencyKeyInUseError):
            await service.execute(
                user_id=1, key="k", request_hash="h", operation=operation(CREATED, calls)
            )

        assert calls == []
        # Cada lectura va en una transacción propia (rollback antes y después).
        assert uow.rollbacks >= 2

    async def test_claims_again_if_the_original_rolled_back(self, service, repo):
        """Clave duplicada, pero al releer ya no existe: la original se deshizo."""
        repo.committed[(1, "k")] = IdempotencyRecord("h", None)

        async def disappear(*, user_id, key):
            repo.committed.pop((user_id, key))
            return None

        repo.get = disappear
        calls = []

        result = await service.execute(
            user_id=1, key="k", request_hash="h", operation=operation(CREATED, calls)
        )

        assert result.replayed is False
        assert calls == [1]

    async def test_operation_error_rolls_back_and_saves_nothing(self, service, repo, uow):
        async def boom() -> StoredResponse:
            raise ValueError("handler failed")

        with pytest.raises(ValueError):
            await service.execute(user_id=1, key="k", request_hash="h", operation=boom)

        assert uow.rollbacks == 1
        assert uow.commits == 0
        assert repo.saved == []

    async def test_redact_changes_only_the_stored_body(self, service, repo):
        response = StoredResponse(status_code=201, body={"secret": "s", "id": 1})

        result = await service.execute(
            user_id=1,
            key="k",
            request_hash="h",
            operation=operation(response, []),
            redact=lambda body: {**body, "secret": None},
        )

        assert result.response.body == {"secret": "s", "id": 1}
        assert repo.saved == [StoredResponse(201, {"secret": None, "id": 1})]

    async def test_keys_are_per_user(self, service, repo):
        repo.committed[(1, "k")] = IdempotencyRecord("h", CREATED)
        calls = []

        result = await service.execute(
            user_id=2, key="k", request_hash="h", operation=operation(CREATED, calls)
        )

        assert result.replayed is False
        assert calls == [1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_purge_deletes_keys_older_than_24_hours(repo, uow):
    repo.created = {
        (1, "old"): NOW - timedelta(hours=25),
        (1, "edge"): NOW - timedelta(hours=23, minutes=59),
        (1, "new"): NOW - timedelta(minutes=5),
    }
    handler = PurgeIdempotencyKeysHandler(repository=repo, uow=uow)

    deleted = await handler.handle(PurgeIdempotencyKeysCommand(now=NOW))

    assert deleted == 1
    assert set(repo.created) == {(1, "edge"), (1, "new")}
    assert uow.commits == 1
