import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from onshape_export_manager.core.api_pool import (
    AllAccountsRateLimitedError,
    ApiPool,
    NoEnabledAccountsError,
)
from onshape_export_manager.core.database import Database
from onshape_export_manager.core.models import OnshapeAccount


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)

    def advance(self, delta: timedelta) -> None:
        self.now += delta

    def __call__(self) -> datetime:
        return self.now


class ApiPoolTests(unittest.TestCase):
    def accounts(self) -> list[OnshapeAccount]:
        return [
            OnshapeAccount(name="a", access_key="a", secret_key="s"),
            OnshapeAccount(name="b", access_key="b", secret_key="s"),
        ]

    def make_database(self) -> Database:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        database = Database(Path(tmp.name) / "exports.db")
        database.initialize()
        return database

    def test_lease_uses_enabled_accounts_only(self) -> None:
        pool = ApiPool(
            [
                OnshapeAccount(name="disabled", access_key="a", secret_key="s", enabled=False),
                OnshapeAccount(name="active", access_key="a", secret_key="s", enabled=True),
            ]
        )

        lease = pool.lease()

        self.assertEqual(lease.account.name, "active")
        self.assertIsNotNone(lease.account.last_used)

    def test_lease_respects_label_assignments(self) -> None:
        pool = ApiPool(self.accounts())

        lease = pool.lease(["b"])

        self.assertEqual(lease.account.name, "b")

    def test_load_balances_by_usage_and_last_used(self) -> None:
        clock = Clock()
        pool = ApiPool(self.accounts(), now_fn=clock)

        first = pool.lease()
        pool.record_success(first.account.name)
        clock.advance(timedelta(seconds=1))
        second = pool.lease()
        pool.record_success(second.account.name)

        self.assertEqual(first.account.name, "a")
        self.assertEqual(second.account.name, "b")

    def test_rate_limited_account_fails_over_then_recovers(self) -> None:
        clock = Clock()
        pool = ApiPool(
            self.accounts(),
            now_fn=clock,
            default_rate_limit_cooldown=timedelta(minutes=5),
        )

        pool.record_rate_limited("a")
        lease = pool.lease()
        self.assertEqual(lease.account.name, "b")

        pool.record_rate_limited("b")
        with self.assertRaises(AllAccountsRateLimitedError) as caught:
            pool.lease()
        self.assertEqual(
            caught.exception.next_available_at,
            datetime(2026, 6, 25, 12, 5, tzinfo=timezone.utc),
        )

        clock.advance(timedelta(minutes=6))
        recovered = pool.lease()
        self.assertEqual(recovered.account.name, "a")

    def test_state_persists_to_database(self) -> None:
        database = self.make_database()
        pool = ApiPool(self.accounts(), database=database)
        pool.record_success("a", api_calls=3)
        pool.record_failure("a", "timeout")

        loaded = ApiPool(self.accounts(), database=database)
        state = {item.name: item for item in loaded.snapshot()}["a"]

        self.assertEqual(state.api_usage, 3)
        self.assertEqual(state.failure_count, 1)
        self.assertEqual(state.rate_limit_status, "failed")
        self.assertEqual(state.last_error, "timeout")

    def test_no_enabled_accounts_raises(self) -> None:
        pool = ApiPool(
            [OnshapeAccount(name="disabled", access_key="a", secret_key="s", enabled=False)]
        )

        with self.assertRaises(NoEnabledAccountsError):
            pool.lease()


if __name__ == "__main__":
    unittest.main()
