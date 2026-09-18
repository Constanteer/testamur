from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.web.hosted_app import (
    build_hosted_server,
    dispatch_account_get,
    dispatch_account_write,
)
from apps.web.identity import AccountStore
from testamur.web_app import dispatch_api_write


class HostedWebAccountTest(unittest.TestCase):
    def test_account_http_contract_sets_and_resolves_session_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            signup = dispatch_account_write(
                store,
                "/v1/account/signup",
                {
                    "username": "hosted-user",
                    "email": "hosted@example.com",
                    "password": "a-secure-hosted-password",
                    "display_name": "Hosted User",
                },
                cookie_header=None,
            )
            self.assertEqual(signup["status"], 200)
            set_cookie = signup["headers"]["Set-Cookie"]
            self.assertIn("HttpOnly", set_cookie)
            self.assertIn("SameSite=Lax", set_cookie)
            cookie = set_cookie.split(";", 1)[0]

            me = dispatch_account_get(store, "/v1/account/me", cookie_header=cookie)
            self.assertTrue(me["body"]["authenticated"])
            self.assertEqual(me["body"]["user"]["username"], "hosted-user")

            profile = dispatch_account_write(
                store,
                "/v1/account/profile",
                {"display_name": "Renamed User"},
                cookie_header=cookie,
            )
            self.assertEqual(profile["body"]["user"]["display_name"], "Renamed User")

            public = dispatch_account_get(store, "/v1/users/hosted-user", cookie_header=None)
            self.assertEqual(public["status"], 200)
            self.assertEqual(public["body"]["profile"]["display_name"], "Renamed User")
            self.assertNotIn("email", public["body"]["profile"])

            sessions = dispatch_account_get(store, "/v1/account/sessions", cookie_header=cookie)
            self.assertEqual(sessions["status"], 200)
            self.assertEqual(len(sessions["body"]["sessions"]), 1)
            self.assertTrue(sessions["body"]["sessions"][0]["current"])

            signout = dispatch_account_write(
                store,
                "/v1/account/signout",
                {},
                cookie_header=cookie,
            )
            self.assertIn("Max-Age=0", signout["headers"]["Set-Cookie"])
            after = dispatch_account_get(store, "/v1/account/me", cookie_header=cookie)
            self.assertFalse(after["body"]["authenticated"])

    def test_session_revocation_api_keeps_requests_user_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            first = dispatch_account_write(
                store,
                "/v1/account/signup",
                {
                    "username": "first-hosted",
                    "email": "first-hosted@example.com",
                    "password": "a-secure-hosted-password",
                },
                cookie_header=None,
            )
            first_cookie = first["headers"]["Set-Cookie"].split(";", 1)[0]
            second = dispatch_account_write(
                store,
                "/v1/account/signin",
                {"identifier": "first-hosted", "password": "a-secure-hosted-password"},
                cookie_header=None,
            )
            second_cookie = second["headers"]["Set-Cookie"].split(";", 1)[0]

            sessions = dispatch_account_get(store, "/v1/account/sessions", cookie_header=first_cookie)
            other_session = next(item for item in sessions["body"]["sessions"] if not item["current"])
            revoked = dispatch_account_write(
                store,
                "/v1/account/sessions/revoke",
                {"session_id": other_session["session_id"]},
                cookie_header=first_cookie,
            )
            self.assertTrue(revoked["body"]["revoked"])
            self.assertFalse(dispatch_account_get(store, "/v1/account/me", cookie_header=second_cookie)["body"]["authenticated"])

    def test_password_change_api_revokes_other_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            first = dispatch_account_write(
                store,
                "/v1/account/signup",
                {
                    "username": "password-hosted",
                    "email": "password-hosted@example.com",
                    "password": "old-hosted-password",
                },
                cookie_header=None,
            )
            first_cookie = first["headers"]["Set-Cookie"].split(";", 1)[0]
            second = dispatch_account_write(
                store,
                "/v1/account/signin",
                {"identifier": "password-hosted", "password": "old-hosted-password"},
                cookie_header=None,
            )
            second_cookie = second["headers"]["Set-Cookie"].split(";", 1)[0]

            changed = dispatch_account_write(
                store,
                "/v1/account/password",
                {
                    "current_password": "old-hosted-password",
                    "new_password": "new-hosted-password",
                },
                cookie_header=first_cookie,
            )
            self.assertEqual(changed["status"], 200)
            self.assertEqual(changed["body"]["revoked_other_sessions"], 1)
            self.assertFalse(
                dispatch_account_get(store, "/v1/account/me", cookie_header=second_cookie)["body"]["authenticated"]
            )
            self.assertTrue(
                dispatch_account_get(store, "/v1/account/me", cookie_header=first_cookie)["body"]["authenticated"]
            )

    def test_account_deletion_removes_identity_sessions_and_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = build_hosted_server(data_dir=tmp, port=0)
            try:
                signup = dispatch_account_write(
                    server.account_store,
                    "/v1/account/signup",
                    {
                        "username": "delete-hosted",
                        "email": "delete-hosted@example.com",
                        "password": "delete-hosted-password",
                    },
                    cookie_header=None,
                )
                cookie = signup["headers"]["Set-Cookie"].split(";", 1)[0]
                user = signup["body"]["user"]
                service = server.product_service_for_user(user["user_id"])
                dispatch_api_write(
                    service,
                    "/v1/projects",
                    {"name": "Private Project", "visibility": "private"},
                )
                workspace = server.workspace_root / user["user_id"]
                self.assertTrue(workspace.exists())

                mismatch = dispatch_account_write(
                    server.account_store,
                    "/v1/account/delete",
                    {"password": "delete-hosted-password", "confirmation": "wrong-user"},
                    cookie_header=cookie,
                    delete_workspace=server.delete_user_workspace,
                )
                self.assertEqual(mismatch["status"], 400)
                self.assertTrue(workspace.exists())

                deleted = dispatch_account_write(
                    server.account_store,
                    "/v1/account/delete",
                    {"password": "delete-hosted-password", "confirmation": "delete-hosted"},
                    cookie_header=cookie,
                    delete_workspace=server.delete_user_workspace,
                )
                self.assertEqual(deleted["status"], 200)
                self.assertTrue(deleted["body"]["deleted"])
                self.assertIn("Max-Age=0", deleted["headers"]["Set-Cookie"])
                self.assertFalse(workspace.exists())
                self.assertIsNone(server.account_store.public_user("delete-hosted"))
                self.assertFalse(
                    dispatch_account_get(server.account_store, "/v1/account/me", cookie_header=cookie)["body"]["authenticated"]
                )
            finally:
                server.server_close()

    def test_hosted_users_receive_isolated_product_databases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = build_hosted_server(data_dir=tmp, port=0)
            try:
                alice = server.product_service_for_user("usr_alice")
                bob = server.product_service_for_user("usr_bob")
                created = dispatch_api_write(
                    alice,
                    "/v1/projects",
                    {"name": "Alice Project", "visibility": "private"},
                )
                self.assertEqual(created["status"], 200)
                self.assertEqual(len(alice.dashboard(limit=20)["projects"]), 1)
                self.assertEqual(bob.dashboard(limit=20)["projects"], [])
                self.assertNotEqual(alice.database_path, bob.database_path)
            finally:
                server.server_close()

    def test_hosted_server_discovers_codex_monitor_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = build_hosted_server(data_dir=tmp, port=0)
            try:
                service = server.product_service_for_user("usr_provider")
                extensions = service.status()["extensions"]
                self.assertIn("github_branch", extensions["monitor_target_providers"])
                spec = extensions["monitor_target_provider_specs"]["github_branch"]
                self.assertEqual(spec["label"], "GitHub branch")
                provider = service.extensions.monitor_target_provider("github_branch")
                self.assertIsNotNone(provider)
                resolved = provider(
                    {"repository": "Constanteer/Mathub", "branch": "main"}
                )
                self.assertEqual(
                    resolved["locator"],
                    "https://github.com/Constanteer/Mathub/commits/main.atom",
                )
            finally:
                server.server_close()

    def test_account_api_rejects_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            response = dispatch_account_write(
                store,
                "/v1/account/signup",
                {
                    "username": "hosted-user",
                    "email": "hosted@example.com",
                    "password": "a-secure-hosted-password",
                    "admin": True,
                },
                cookie_header=None,
            )
            self.assertEqual(response["status"], 400)
            self.assertEqual(response["body"]["error"]["code"], "invalid_argument")


if __name__ == "__main__":
    unittest.main()
