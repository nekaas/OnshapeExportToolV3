import tempfile
import time
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


class TotpTests(unittest.TestCase):
    def test_code_round_trip(self) -> None:
        secret = auth.generate_totp_secret()
        code = auth.totp_code(secret)
        self.assertTrue(auth.verify_totp(secret, code))
        self.assertFalse(auth.verify_totp(secret, "000000", window=0, at=time.time() + 10_000))

    def test_provisioning_uri(self) -> None:
        uri = auth.totp_provisioning_uri("ABC", account="owner")
        self.assertTrue(uri.startswith("otpauth://totp/"))
        self.assertIn("secret=ABC", uri)


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

    def test_totp_enrollment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = AuthService(_fresh_db(tmp))
            service.create_owner("admin", "supersecret")
            self.assertFalse(service.totp_enabled())

            secret = service.begin_totp_enrollment()
            self.assertFalse(service.confirm_totp("000000"))
            self.assertTrue(service.confirm_totp(auth.totp_code(secret)))
            self.assertTrue(service.totp_enabled())
            self.assertTrue(service.verify_login_totp(auth.totp_code(secret)))

            service.disable_totp()
            self.assertFalse(service.totp_enabled())


if __name__ == "__main__":
    unittest.main()
