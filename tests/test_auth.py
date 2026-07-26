import tempfile
import unittest
from pathlib import Path

from onshape_export_manager.core import auth
from onshape_export_manager.core.auth import AuthError, AuthService
from onshape_export_manager.core.database import Database


def _fresh_db(tmp: str) -> Database:
    database = Database(Path(tmp) / "auth.db")
    database.initialize()
    return database


class PasswordHashTests(unittest.TestCase):
    def test_hash_and_verify(self) -> None:
        encoded = auth.hash_password("correct horse battery")
        self.assertTrue(encoded.startswith("scrypt$"))
        self.assertTrue(auth.verify_password("correct horse battery", encoded))
        self.assertFalse(auth.verify_password("wrong", encoded))

    def test_hashes_are_salted(self) -> None:
        self.assertNotEqual(auth.hash_password("same"), auth.hash_password("same"))

    def test_empty_password_rejected(self) -> None:
        with self.assertRaises(AuthError):
            auth.hash_password("")


class AuthServiceTests(unittest.TestCase):
    def test_owner_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = AuthService(_fresh_db(tmp))
            self.assertFalse(service.is_configured())

            service.create_owner("admin", "supersecret")
            self.assertTrue(service.is_configured())
            self.assertTrue(service.authenticate("admin", "supersecret"))
            self.assertFalse(service.authenticate("admin", "nope"))
            self.assertFalse(service.authenticate("other", "supersecret"))

            with self.assertRaises(AuthError):
                service.create_owner("again", "supersecret")

    def test_password_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = AuthService(_fresh_db(tmp))
            with self.assertRaises(AuthError):
                service.create_owner("admin", "short")

    def test_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = AuthService(_fresh_db(tmp))
            service.create_owner("admin", "supersecret")

            token = service.create_session(remember=False)
            self.assertTrue(service.validate_session(token))
            self.assertFalse(service.validate_session("bogus"))

            service.destroy_session(token)
            self.assertFalse(service.validate_session(token))

    def test_change_password_invalidates_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = AuthService(_fresh_db(tmp))
            service.create_owner("admin", "supersecret")
            token = service.create_session()
            service.change_password("supersecret", "evenbettersecret")
            self.assertFalse(service.validate_session(token))
            self.assertTrue(service.authenticate("admin", "evenbettersecret"))


if __name__ == "__main__":
    unittest.main()
