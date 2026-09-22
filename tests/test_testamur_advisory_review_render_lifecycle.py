from pathlib import Path
import unittest


class AdvisoryReviewRenderLifecycleTests(unittest.TestCase):
    def test_review_surface_coalesces_and_filters_self_mutations(self) -> None:
        asset = (Path(__file__).parents[1] / "testamur" / "web" / "advisory-review-ui.js").read_text()

        self.assertIn("function queueRender()", asset)
        self.assertIn("renderQueued", asset)
        self.assertIn("data-advisory-review-state", asset)
        self.assertIn("mutationIsOnlyReviewSurface", asset)
        self.assertNotIn("new MutationObserver(render)", asset)


if __name__ == "__main__":
    unittest.main()
