import tempfile
import unittest
from pathlib import Path

from onshape_export_manager.app import create_app
from onshape_export_manager.core.api_pool import ApiPool
from onshape_export_manager.core.models import OnshapeAccount
from onshape_export_manager.core.settings import AppPaths


class ArchitectureTests(unittest.TestCase):
    def test_app_paths_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp))

            self.assertTrue(app.paths.config_dir.exists())
            self.assertTrue(app.paths.exports_dir.exists())
            self.assertTrue(app.paths.logs_dir.exists())
            self.assertTrue(app.paths.database_dir.exists())

    def test_account_pool_leases_enabled_accounts(self) -> None:
        pool = ApiPool(
            [
                OnshapeAccount(name="disabled", access_key="a", secret_key="s", enabled=False),
                OnshapeAccount(name="active", access_key="a", secret_key="s", enabled=True),
            ]
        )

        lease = pool.lease()

        self.assertEqual(lease.account.name, "active")
        self.assertIsNotNone(lease.account.last_used)

    def test_paths_from_base_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            paths = AppPaths.from_base_dir(tmp_path)

            self.assertEqual(paths.package_dir, tmp_path / "onshape_export_manager")


if __name__ == "__main__":
    unittest.main()
