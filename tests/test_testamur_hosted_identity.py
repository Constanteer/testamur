from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from apps.web.identity import AccountError, AccountStore


class HostedAccountStoreTest(unittest.TestCase):
    def test_signup_signin_session_profile_and_signout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            user, token = store.sign_up(
                username="Hank_Test",
                email="Hank@example.com",
                password="correct-horse-battery-staple",
                display_name="Hank",
            )
            self.assertEqual(user["username"], "hank_test")
            self.assertEqual(user["email"], "hank@example.com")
            self.assertEqual(store.user_for_session(token)["user_id"], user["user_id"])

            signed_in, second_token = store.sign_in(
                identifier="HANK_TEST",
                password="correct-horse-battery-staple",
            )
            self.assertEqual(signed_in["user_id"], user["user_id"])
            self.assertIsNotNone(store.user_for_session(second_token))

            updated = store.update_profile(user_id=user["user_id"], display_name="Hank W.")
            self.assertEqual(updated["display_name"], "Hank W.")
            public = store.public_user("HANK_TEST")
            self.assertEqual(public["display_name"], "Hank W.")
            self.assertNotIn("email", public)

            sessions = store.list_sessions(user_id=user["user_id"], current_token=second_token)
            self.assertEqual(len(sessions), 2)
            self.assertEqual(sum(1 for session in sessions if session["current"]), 1)
            first_session = next(session for session in sessions if not session["current"])
            self.assertTrue(store.revoke_session(user_id=user["user_id"], session_id=first_session["session_id"]))
            self.assertIsNone(store.user_for_session(token))

            store.sign_out(second_token)
            self.assertIsNone(store.user_for_session(second_token))

            with sqlite3.connect(store.path) as connection:
                digest = connection.execute(
                    "SELECT password_digest FROM users WHERE user_id = ?",
                    (user["user_id"],),
                ).fetchone()[0]
            self.assertTrue(digest.startswith("scrypt$"))
            self.assertNotIn("correct-horse-battery-staple", digest)

    def test_duplicate_identity_and_weak_password_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            store.sign_up(
                username="first-user",
                email="first@example.com",
                password="a-long-enough-password",
            )
            with self.assertRaises(AccountError) as duplicate:
                store.sign_up(
                    username="FIRST-USER",
                    email="other@example.com",
                    password="another-long-password",
                )
            self.assertEqual(duplicate.exception.code, "username_taken")

            with self.assertRaises(AccountError) as weak:
                store.sign_up(
                    username="second-user",
                    email="second@example.com",
                    password="short",
                )
            self.assertEqual(weak.exception.code, "weak_password")

    def test_revoke_other_sessions_keeps_current_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            user, current = store.sign_up(
                username="session-user",
                email="session@example.com",
                password="a-valid-password",
            )
            _, other = store.sign_in(identifier="session-user", password="a-valid-password")
            removed = store.revoke_other_sessions(user_id=user["user_id"], current_token=current)
            self.assertEqual(removed, 1)
            self.assertIsNotNone(store.user_for_session(current))
            self.assertIsNone(store.user_for_session(other))

    def test_password_change_rotates_credentials_and_revokes_other_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            user, current = store.sign_up(
                username="password-user",
                email="password@example.com",
                password="old-password-value",
            )
            _, other = store.sign_in(identifier="password-user", password="old-password-value")

            revoked = store.change_password(
                user_id=user["user_id"],
                current_password="old-password-value",
                new_password="new-password-value",
                current_token=current,
            )
            self.assertEqual(revoked, 1)
            self.assertIsNotNone(store.user_for_session(current))
            self.assertIsNone(store.user_for_session(other))

            with self.assertRaises(AccountError):
                store.sign_in(identifier="password-user", password="old-password-value")
            signed_in, _ = store.sign_in(identifier="password-user", password="new-password-value")
            self.assertEqual(signed_in["user_id"], user["user_id"])

    def test_delete_account_requires_password_and_cascades_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            user, token = store.sign_up(
                username="delete-user",
                email="delete@example.com",
                password="delete-password-value",
            )
            with self.assertRaises(AccountError):
                store.delete_account(user_id=user["user_id"], password="wrong-password")
            deleted = store.delete_account(user_id=user["user_id"], password="delete-password-value")
            self.assertEqual(deleted["username"], "delete-user")
            self.assertIsNone(store.user_for_session(token))
            self.assertIsNone(store.public_user("delete-user"))

    def test_invalid_credentials_do_not_create_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            store.sign_up(
                username="one-user",
                email="one@example.com",
                password="a-valid-password",
            )
            with self.assertRaises(AccountError) as context:
                store.sign_in(identifier="one-user", password="wrong-password")
            self.assertEqual(context.exception.status, 401)


if __name__ == "__main__":
    unittest.main()
