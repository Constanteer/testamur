from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

from testamur.front_router import _product_argv, main


class TestamurFrontRouterTest(unittest.TestCase):
    def test_product_command_routes_without_entering_legacy_front(self) -> None:
        with patch("testamur.front_router.product_dispatch", return_value=0) as product:
            with patch("testamur.front_router.core_main") as core:
                code = main(["product", "status"])
        self.assertEqual(code, 0)
        product.assert_called_once_with(["status"])
        core.assert_not_called()

    def test_global_json_is_redundant_but_accepted_for_product(self) -> None:
        with patch("testamur.front_router.product_dispatch", return_value=0) as product:
            with patch("testamur.front_router.core_main") as core:
                code = main(["--json", "product", "temporal-events", "tst:record:x"])
        self.assertEqual(code, 0)
        product.assert_called_once_with(["temporal-events", "tst:record:x"])
        core.assert_not_called()

    def test_non_product_commands_delegate_unchanged(self) -> None:
        argv = ["run", "--", "tool", "--json", "product"]
        with patch("testamur.front_router.product_dispatch") as product:
            with patch("testamur.front_router.core_main", return_value=7) as core:
                code = main(argv)
        self.assertEqual(code, 7)
        core.assert_called_once_with(argv)
        product.assert_not_called()

    def test_wrapped_command_product_token_is_not_misrouted(self) -> None:
        self.assertIsNone(_product_argv(["run", "--", "product", "status"]))
        self.assertIsNone(_product_argv(["--json", "run", "--", "product", "status"]))

    def test_front_help_mentions_product_temporal_surfaces(self) -> None:
        output = io.StringIO()
        with patch("testamur.front_router.core_main", return_value=0) as core:
            with contextlib.redirect_stdout(output):
                code = main(["--help"])
        self.assertEqual(code, 0)
        core.assert_called_once_with(["--help"])
        rendered = output.getvalue()
        self.assertIn("testamur product status", rendered)
        self.assertIn("testamur product temporal", rendered)
        self.assertIn("testamur product temporal-events", rendered)


if __name__ == "__main__":
    unittest.main()
