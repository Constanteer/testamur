from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.web.hosted_app import (
    WORKSPACE_COOKIE,
    build_hosted_server,
    dispatch_account_get,
    dispatch_account_write,
)
from apps.web.identity import AccountError, AccountStore
from testamur.web_app import dispatch_api_write


class HostedOrganizationModelTest(unittest.TestCase):
    def test_invitation_membership_and_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            alice, _ = store.sign_up(
                username="alice-org",
                email="alice-org@example.com",
                password="alice-organization-password",
            )
            bob, _ = store.sign_up(
                username="bob-org",
                email="bob-org@example.com",
                password="bob-organization-password",
            )
            charlie, _ = store.sign_up(
                username="charlie-org",
                email="charlie-org@example.com",
                password="charlie-organization-password",
            )

            org = store.create_organization(
                user_id=alice["user_id"],
                slug="research-lab",
                display_name="Research Lab",
            )
            self.assertEqual(org["role"], "owner")
            self.assertEqual(store.resolve_workspace(user_id=alice["user_id"], workspace_id=org["org_id"])["role"], "owner")

            with self.assertRaises(AccountError) as denied:
                store.resolve_workspace(user_id=bob["user_id"], workspace_id=org["org_id"])
            self.assertEqual(denied.exception.status, 403)

            invitation = store.invite_to_organization(
                inviter_user_id=alice["user_id"],
                org_ref=org["org_id"],
                username="bob-org",
                role="admin",
            )
            pending = store.list_invitations(user_id=bob["user_id"])
            self.assertEqual([item["invitation_id"] for item in pending], [invitation["invitation_id"]])

            accepted = store.respond_to_invitation(
                user_id=bob["user_id"],
                invitation_id=invitation["invitation_id"],
                accept=True,
            )
            self.assertEqual(accepted["status"], "accepted")
            self.assertEqual(
                store.resolve_workspace(user_id=bob["user_id"], workspace_id=org["org_id"])["role"],
                "admin",
            )

            bob_invite = store.invite_to_organization(
                inviter_user_id=bob["user_id"],
                org_ref=org["org_id"],
                username="charlie-org",
                role="member",
            )
            store.respond_to_invitation(
                user_id=charlie["user_id"],
                invitation_id=bob_invite["invitation_id"],
                accept=True,
            )
            organization, members = store.list_organization_members(
                user_id=alice["user_id"],
                org_ref="research-lab",
            )
            self.assertEqual(organization["org_id"], org["org_id"])
            self.assertEqual(
                {member["username"]: member["role"] for member in members},
                {"alice-org": "owner", "bob-org": "admin", "charlie-org": "member"},
            )

            with self.assertRaises(AccountError) as member_cannot_invite:
                store.invite_to_organization(
                    inviter_user_id=charlie["user_id"],
                    org_ref=org["org_id"],
                    username="alice-org",
                    role="member",
                )
            self.assertEqual(member_cannot_invite.exception.status, 403)

    def test_declined_invitation_does_not_grant_workspace_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp) / "accounts.sqlite3")
            owner, _ = store.sign_up(
                username="decline-owner",
                email="decline-owner@example.com",
                password="decline-owner-password",
            )
            invited, _ = store.sign_up(
                username="decline-user",
                email="decline-user@example.com",
                password="decline-user-password",
            )
            org = store.create_organization(
                user_id=owner["user_id"],
                slug="decline-org",
                display_name="Decline Org",
            )
            invitation = store.invite_to_organization(
                inviter_user_id=owner["user_id"],
                org_ref=org["org_id"],
                username="decline-user",
                role="member",
            )
            response = store.respond_to_invitation(
                user_id=invited["user_id"],
                invitation_id=invitation["invitation_id"],
                accept=False,
            )
            self.assertEqual(response["status"], "declined")
            with self.assertRaises(AccountError):
                store.resolve_workspace(user_id=invited["user_id"], workspace_id=org["org_id"])


class HostedOrganizationWorkspaceTest(unittest.TestCase):
    def _signup(self, server, username: str) -> tuple[dict, str]:
        response = dispatch_account_write(
            server.account_store,
            "/v1/account/signup",
            {
                "username": username,
                "email": f"{username}@example.com",
                "password": f"{username}-secure-password",
            },
            cookie_header=None,
            delete_workspace=server.delete_user_workspace,
            delete_org_workspace=server.delete_organization_workspace,
        )
        self.assertEqual(response["status"], 200)
        return response["body"]["user"], response["headers"]["Set-Cookie"].split(";", 1)[0]

    def test_organization_http_contract_create_invite_accept_and_select(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = build_hosted_server(data_dir=tmp, port=0)
            try:
                owner, owner_cookie = self._signup(server, "api-owner")
                invited, invited_cookie = self._signup(server, "api-invited")

                created = dispatch_account_write(
                    server.account_store,
                    "/v1/account/organizations",
                    {"slug": "api-lab", "display_name": "API Lab"},
                    cookie_header=owner_cookie,
                    delete_workspace=server.delete_user_workspace,
                    delete_org_workspace=server.delete_organization_workspace,
                )
                self.assertEqual(created["status"], 200)
                org = created["body"]["organization"]

                invitation = dispatch_account_write(
                    server.account_store,
                    f"/v1/account/organizations/{org['org_id']}/invite",
                    {"username": invited["username"], "role": "member"},
                    cookie_header=owner_cookie,
                    delete_workspace=server.delete_user_workspace,
                    delete_org_workspace=server.delete_organization_workspace,
                )
                self.assertEqual(invitation["status"], 200)
                invitation_id = invitation["body"]["invitation"]["invitation_id"]

                pending = dispatch_account_get(
                    server.account_store,
                    "/v1/account/invitations",
                    cookie_header=invited_cookie,
                )
                self.assertEqual([item["invitation_id"] for item in pending["body"]["invitations"]], [invitation_id])

                accepted = dispatch_account_write(
                    server.account_store,
                    "/v1/account/invitations/respond",
                    {"invitation_id": invitation_id, "accept": True},
                    cookie_header=invited_cookie,
                    delete_workspace=server.delete_user_workspace,
                    delete_org_workspace=server.delete_organization_workspace,
                )
                self.assertEqual(accepted["body"]["invitation"]["status"], "accepted")

                detail = dispatch_account_get(
                    server.account_store,
                    "/v1/account/organizations/api-lab",
                    cookie_header=invited_cookie,
                )
                self.assertEqual(detail["status"], 200)
                self.assertEqual(detail["body"]["organization"]["role"], "member")
                self.assertEqual(len(detail["body"]["members"]), 2)

                selected = dispatch_account_write(
                    server.account_store,
                    "/v1/account/workspace",
                    {"workspace_id": org["org_id"]},
                    cookie_header=invited_cookie,
                    delete_workspace=server.delete_user_workspace,
                    delete_org_workspace=server.delete_organization_workspace,
                )
                self.assertEqual(selected["status"], 200)
                self.assertIn(f"{WORKSPACE_COOKIE}={org['org_id']}", selected["headers"]["Set-Cookie"])
            finally:
                server.server_close()

    def test_personal_and_shared_organization_workspaces_are_isolated_and_authorized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = build_hosted_server(data_dir=tmp, port=0)
            try:
                alice, _ = self._signup(server, "workspace-alice")
                bob, _ = self._signup(server, "workspace-bob")
                charlie, _ = self._signup(server, "workspace-charlie")
                org = server.account_store.create_organization(
                    user_id=alice["user_id"],
                    slug="shared-lab",
                    display_name="Shared Lab",
                )
                invitation = server.account_store.invite_to_organization(
                    inviter_user_id=alice["user_id"],
                    org_ref=org["org_id"],
                    username="workspace-bob",
                    role="member",
                )
                server.account_store.respond_to_invitation(
                    user_id=bob["user_id"],
                    invitation_id=invitation["invitation_id"],
                    accept=True,
                )

                alice_personal = server.product_service_for_workspace(
                    user_id=alice["user_id"],
                    workspace_id="personal",
                )
                alice_org = server.product_service_for_workspace(
                    user_id=alice["user_id"],
                    workspace_id=org["org_id"],
                )
                bob_org = server.product_service_for_workspace(
                    user_id=bob["user_id"],
                    workspace_id=org["org_id"],
                )
                bob_personal = server.product_service_for_workspace(
                    user_id=bob["user_id"],
                    workspace_id="personal",
                )

                dispatch_api_write(
                    alice_personal,
                    "/v1/projects",
                    {"name": "Alice Private", "visibility": "private"},
                )
                dispatch_api_write(
                    alice_org,
                    "/v1/projects",
                    {"name": "Shared Project", "visibility": "private"},
                )

                self.assertEqual(len(alice_personal.dashboard(limit=20)["projects"]), 1)
                self.assertEqual(bob_personal.dashboard(limit=20)["projects"], [])
                self.assertEqual(
                    [item["name"] for item in bob_org.dashboard(limit=20)["projects"]],
                    ["Shared Project"],
                )
                self.assertEqual(alice_org.database_path, bob_org.database_path)
                self.assertNotEqual(alice_personal.database_path, alice_org.database_path)

                with self.assertRaises(AccountError) as forbidden:
                    server.product_service_for_workspace(
                        user_id=charlie["user_id"],
                        workspace_id=org["org_id"],
                    )
                self.assertEqual(forbidden.exception.status, 403)
            finally:
                server.server_close()

    def test_workspace_selection_cookie_and_account_me(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = build_hosted_server(data_dir=tmp, port=0)
            try:
                user, session_cookie = self._signup(server, "cookie-owner")
                org = server.account_store.create_organization(
                    user_id=user["user_id"],
                    slug="cookie-org",
                    display_name="Cookie Org",
                )
                selected = dispatch_account_write(
                    server.account_store,
                    "/v1/account/workspace",
                    {"workspace_id": org["org_id"]},
                    cookie_header=session_cookie,
                    delete_workspace=server.delete_user_workspace,
                    delete_org_workspace=server.delete_organization_workspace,
                )
                self.assertEqual(selected["status"], 200)
                workspace_cookie = selected["headers"]["Set-Cookie"].split(";", 1)[0]
                self.assertTrue(workspace_cookie.startswith(f"{WORKSPACE_COOKIE}="))
                combined_cookie = f"{session_cookie}; {workspace_cookie}"

                me = dispatch_account_get(
                    server.account_store,
                    "/v1/account/me",
                    cookie_header=combined_cookie,
                )
                self.assertEqual(me["body"]["active_workspace"]["workspace_id"], org["org_id"])
                self.assertEqual(
                    {workspace["workspace_id"] for workspace in me["body"]["workspaces"]},
                    {"personal", org["org_id"]},
                )
            finally:
                server.server_close()

    def test_owner_must_delete_organization_before_account_and_org_deletion_removes_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = build_hosted_server(data_dir=tmp, port=0)
            try:
                user, session_cookie = self._signup(server, "org-delete-owner")
                org = server.account_store.create_organization(
                    user_id=user["user_id"],
                    slug="deletion-org",
                    display_name="Deletion Org",
                )
                org_service = server.product_service_for_workspace(
                    user_id=user["user_id"],
                    workspace_id=org["org_id"],
                )
                dispatch_api_write(
                    org_service,
                    "/v1/projects",
                    {"name": "Organization Private", "visibility": "private"},
                )
                org_workspace = server.workspace_root / "organizations" / org["org_id"]
                self.assertTrue(org_workspace.exists())

                blocked = dispatch_account_write(
                    server.account_store,
                    "/v1/account/delete",
                    {
                        "password": "org-delete-owner-secure-password",
                        "confirmation": "org-delete-owner",
                    },
                    cookie_header=session_cookie,
                    delete_workspace=server.delete_user_workspace,
                    delete_org_workspace=server.delete_organization_workspace,
                )
                self.assertEqual(blocked["status"], 409)
                self.assertEqual(
                    blocked["body"]["error"]["code"],
                    "organization_ownership_requires_cleanup",
                )

                mismatch_delete = dispatch_account_write(
                    server.account_store,
                    f"/v1/account/organizations/{org['org_id']}/delete",
                    {"confirmation": "wrong-slug"},
                    cookie_header=session_cookie,
                    delete_workspace=server.delete_user_workspace,
                    delete_org_workspace=server.delete_organization_workspace,
                )
                self.assertEqual(mismatch_delete["status"], 400)
                self.assertTrue(org_workspace.exists())

                deleted_org = dispatch_account_write(
                    server.account_store,
                    f"/v1/account/organizations/{org['org_id']}/delete",
                    {"confirmation": "deletion-org"},
                    cookie_header=session_cookie,
                    delete_workspace=server.delete_user_workspace,
                    delete_org_workspace=server.delete_organization_workspace,
                )
                self.assertEqual(deleted_org["status"], 200)
                self.assertFalse(org_workspace.exists())
                self.assertEqual(server.account_store.list_organizations(user_id=user["user_id"]), [])

                deleted_account = dispatch_account_write(
                    server.account_store,
                    "/v1/account/delete",
                    {
                        "password": "org-delete-owner-secure-password",
                        "confirmation": "org-delete-owner",
                    },
                    cookie_header=session_cookie,
                    delete_workspace=server.delete_user_workspace,
                    delete_org_workspace=server.delete_organization_workspace,
                )
                self.assertEqual(deleted_account["status"], 200)
            finally:
                server.server_close()


if __name__ == "__main__":
    unittest.main()
