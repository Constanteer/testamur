from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _isolated_env(site: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(site)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def test_fresh_install_exposes_testamur_without_witness(tmp_path: Path) -> None:
    """Gate the release artifact boundary, not the repository checkout.

    Build isolation is disabled so this smoke test never reaches the network. The
    subprocess runs outside the repository with an explicit target site on
    PYTHONPATH; therefore an in-tree ``witness`` directory cannot make the check
    pass accidentally.
    """

    site = tmp_path / "site"
    work = tmp_path / "work"
    work.mkdir()

    install_env = dict(os.environ)
    install_env["PYTHONNOUSERSITE"] = "1"
    install_env.pop("PYTHONPATH", None)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-build-isolation",
            "--target",
            str(site),
            str(ROOT),
        ],
        cwd=work,
        env=install_env,
        check=True,
        capture_output=True,
        text=True,
    )

    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "import importlib.util",
                    "from pathlib import Path",
                    "import testamur",
                    "import testamur.front_router",
                    "import testamur.web_app",
                    "assert importlib.util.find_spec('witness') is None, 'fresh install exposes witness'",
                    "assert importlib.util.find_spec('witness_service') is None, 'fresh install exposes witness_service'",
                    "web = Path(testamur.__file__).with_name('web')",
                    "assert (web / 'index.html').is_file(), f'missing packaged web asset: {web / \"index.html\"}'",
                    "assert (web / 'app.js').is_file(), f'missing packaged web asset: {web / \"app.js\"}'",
                    "assert (web / 'styles.css').is_file(), f'missing packaged web asset: {web / \"styles.css\"}'",
                    "print(testamur.__name__)",
                ]
            ),
        ],
        cwd=work,
        env=_isolated_env(site),
        check=False,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, (
        "fresh-install probe failed\n"
        f"stdout:\n{probe.stdout}\n"
        f"stderr:\n{probe.stderr}"
    )
    assert probe.stdout.strip() == "testamur"
