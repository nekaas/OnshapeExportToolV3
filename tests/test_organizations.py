import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from onshape_export_manager.app import create_app
from onshape_export_manager.core.organizations import (
    Credential,
    CredentialPool,
    CredentialState,
    OrganizationError,
    OrganizationManager,
    order_credentials,
    organizations_from_accounts,
)


def _cred(cid: str, priority: int, enabled: bool = True) -> Credential:
    return Credential(id=cid, name=cid, organization="Org", access_key="a", secret_key="s",
                      priority=priority, enabled=enabled)


class CredentialSelectionTests(unittest.TestCase):
    def test_priority_ordering(self) -> None:
        creds = [_cred("backup", 2), _cred("primary", 1), _cred("emergency", 3)]
        ordered = order_credentials(creds, {}, datetime.now(timezone.utc))
        self.assertEqual([c.id for c in ordered], ["primary", "backup", "emergency"])

    def test_disabled_excluded(self) -> None:
        creds = [_cred("primary", 1, enabled=False), _cred("backup", 2)]
        ordered = order_credentials(creds, {}, datetime.now(timezone.utc))
        self.assertEqual([c.id for c in ordered], ["backup"])

    def test_rate_limited_fails_over_to_lower_priority(self) -> None:
        now = datetime.now(timezone.utc)
        states = {
            "primary": CredentialState(credential_id="primary", rate_limit_status="rate_limited",
                                       rate_limited_until=now + timedelta(minutes=10)),
        }
        creds = [_cred("primary", 1), _cred("backup", 2)]
        ordered = order_credentials(creds, states, now)
        # backup (available) comes before the rate-limited primary
        self.assertEqual(ordered[0].id, "backup")
        self.assertEqual(ordered[1].id, "primary")


class CredentialPoolTests(unittest.TestCase):
    def test_lease_and_failover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            creds = [_cred("primary", 1), _cred("backup", 2)]
            pool = CredentialPool(creds, database=app.database)

            self.assertEqual(pool.lease().id, "primary")

            pool.record_rate_limited("primary")
            self.assertEqual(pool.lease().id, "backup")

            pool.record_success("backup", latency_ms=42.0)
            state = pool.state_for("backup")
            self.assertEqual(state.requests_today, 1)
            self.assertGreater(state.latency_ms, 0)

    def test_state_persists_across_pools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))
            creds = [_cred("primary", 1)]
            CredentialPool(creds, database=app.database).record_failure("primary", "boom")
            reloaded = CredentialPool(creds, database=app.database).state_for("primary")
            self.assertEqual(reloaded.failure_count, 1)
            self.assertEqual(reloaded.health(), "failed")


class OrganizationManagerTests(unittest.TestCase):
    def _manager(self, tmp: str) -> OrganizationManager:
        app = create_app(Path(tmp))
        return OrganizationManager(app.config_manager)

    def test_create_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = self._manager(tmp)
            manager.create_organization("High School", org_type="school", description="STEM")
            config = manager.load()
            self.assertEqual(len(config.organizations), 1)
            self.assertEqual(config.organizations[0].name, "High School")
            self.assertEqual(config.organizations[0].type.value, "school")

            with self.assertRaises(OrganizationError):
                manager.create_organization("High School")

    def test_credential_crud(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = self._manager(tmp)
            org = manager.create_organization("ABC Manufacturing", org_type="company")
            cred = manager.add_credential(org.id, name="Primary", access_key="env:A", secret_key="env:S", priority=1)
            manager.add_credential(org.id, name="Backup", access_key="env:A2", secret_key="env:S2", priority=2)

            config = manager.load()
            self.assertEqual(len(config.organizations[0].credentials), 2)

            with self.assertRaises(OrganizationError):
                manager.add_credential(org.id, name="Primary", access_key="x", secret_key="y")

            manager.delete_credential(org.id, cred.id)
            self.assertEqual(len(manager.load().organizations[0].credentials), 1)

    def test_duplicate_assigns_new_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = self._manager(tmp)
            org = manager.create_organization("Workshop", org_type="workshop")
            manager.add_credential(org.id, name="Primary", access_key="env:A", secret_key="env:S")
            clone = manager.duplicate_organization(org.id)
            self.assertNotEqual(clone.id, org.id)
            self.assertIn("copy", clone.name)
            originals = {c.id for c in manager.load().organizations[0].credentials}
            clones = {c.id for c in clone.credentials}
            self.assertFalse(originals & clones)

    def test_import_from_accounts(self) -> None:
        accounts = [
            {"name": "prod-east", "access_key": "AK1", "secret_key": "SK1", "description": "Primary"},
            {"name": "prod-west", "access_key": "AK2", "secret_key": "SK2"},
        ]
        config = organizations_from_accounts(accounts)
        self.assertEqual(len(config.organizations), 2)
        self.assertEqual(config.organizations[0].credentials[0].name, "Primary")
        self.assertEqual(config.organizations[0].name, "prod-east")
        creds = config.runtime_credentials()
        self.assertEqual(len(creds), 2)


if __name__ == "__main__":
    unittest.main()
