from __future__ import annotations

from pathlib import Path

from testamur.release_gate import CANONICAL_CLI_TARGET, audit_release_surface


ROOT = Path(__file__).resolve().parents[1]


def _fixture(
    tmp_path: Path,
    *,
    include: str,
    source: str,
    target: str = CANONICAL_CLI_TARGET,
    extra_scripts: tuple[str, ...] = (),
) -> Path:
    (tmp_path / "testamur").mkdir()
    (tmp_path / "testamur" / "module.py").write_text(source, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    script_lines = [f'testamur = "{target}"', *extra_scripts]
    (tmp_path / "pyproject.toml").write_text(
        "\n".join([
            "[project]", 'name = "testamur"', "[project.scripts]", *script_lines,
            "[tool.setuptools.packages.find]", f"include = [{include}]", "",
        ]),
        encoding="utf-8",
    )
    return tmp_path


def test_release_audit_accepts_testamur_only_surface(tmp_path: Path) -> None:
    root = _fixture(tmp_path, include='"testamur*"', source="from .runtime_protocol import canonical_json\n")
    result = audit_release_surface(root)
    assert result["ok"] is True
    assert result["cli"]["canonical"] is True
    assert result["cli"]["legacy_entries"] == []
    assert result["package"]["testamur_included"] is True
    assert result["package"]["testamur_only"] is True
    assert result["runtime"]["testamur_only"] is True
    assert result["runtime"]["legacy_test_import_count"] == 0
    assert result["runtime"]["mathhub_legacy_import_count"] == 0


def test_release_audit_reports_packaged_and_imported_witness(tmp_path: Path) -> None:
    root = _fixture(
        tmp_path,
        include='"testamur*", "witness*", "witness_service*"',
        source="from witness.runtime_protocol import canonical_json\n",
        extra_scripts=('witness = "witness.runtime_cli:main"',),
    )
    result = audit_release_surface(root)
    assert result["ok"] is False
    codes = [item["code"] for item in result["violations"]]
    assert codes.count("legacy_runtime_package_in_distribution") == 2
    assert codes.count("legacy_runtime_import") == 1
    assert codes.count("legacy_cli_entrypoint") == 1
    assert result["semantics"]["recorded_implies_verified"] is False
    assert result["semantics"]["fetched_implies_relied"] is False
    assert result["semantics"]["changed_implies_invalid"] is False
    assert result["semantics"]["stale_implies_false"] is False
    assert result["semantics"]["lineage_implies_affectedness_verdict"] is False


def test_release_audit_reports_witness_service_import(tmp_path: Path) -> None:
    root = _fixture(
        tmp_path,
        include='"testamur*"',
        source="from witness_service.app import create_app\n",
    )
    result = audit_release_surface(root)
    assert result["ok"] is False
    assert result["runtime"]["legacy_import_count"] == 1
    assert any(item["code"] == "legacy_runtime_import" for item in result["violations"])


def test_release_audit_reports_testamur_test_dependency_on_retired_runtime(tmp_path: Path) -> None:
    root = _fixture(tmp_path, include='"testamur*"', source="VALUE = 1\n")
    (root / "tests" / "test_testamur_bad.py").write_text(
        "from witness.runtime_protocol import canonical_json\n",
        encoding="utf-8",
    )
    result = audit_release_surface(root)
    assert result["ok"] is False
    assert result["runtime"]["legacy_test_import_count"] == 1
    assert any(item["code"] == "legacy_runtime_test_import" for item in result["violations"])


def test_release_audit_ignores_non_testamur_legacy_test_fixture(tmp_path: Path) -> None:
    root = _fixture(tmp_path, include='"testamur*"', source="VALUE = 1\n")
    (root / "tests" / "test_historical_fixture.py").write_text(
        "from witness.runtime_protocol import canonical_json\n",
        encoding="utf-8",
    )
    result = audit_release_surface(root)
    assert result["ok"] is True
    assert result["runtime"]["legacy_test_import_count"] == 0


def test_release_audit_reports_mathhub_dependency_on_retired_runtime(tmp_path: Path) -> None:
    root = _fixture(tmp_path, include='"testamur*"', source="VALUE = 1\n")
    (root / "mathhub.py").write_text("from witness.http_api import handle_get\n", encoding="utf-8")
    result = audit_release_surface(root)
    assert result["ok"] is False
    assert result["runtime"]["mathhub_legacy_import_count"] == 1
    assert any(item["code"] == "mathhub_legacy_runtime_import" for item in result["violations"])


def test_release_audit_rejects_distribution_that_omits_testamur(tmp_path: Path) -> None:
    root = _fixture(tmp_path, include='"other*"', source="VALUE = 1\n")
    result = audit_release_surface(root)
    assert result["ok"] is False
    assert result["package"]["testamur_included"] is False
    assert any(item["code"] == "canonical_runtime_package_missing" for item in result["violations"])


def test_repository_release_surface_is_testamur_only() -> None:
    result = audit_release_surface(ROOT)
    assert result["ok"] is True, result["violations"]
    assert result["cli"] == {"public_command": "testamur", "target": CANONICAL_CLI_TARGET, "canonical": True, "legacy_entries": []}
    assert result["package"]["testamur_included"] is True
    assert result["package"]["legacy_runtime_patterns"] == []
    assert result["package"]["testamur_only"] is True
    assert result["runtime"]["legacy_import_count"] == 0
    assert result["runtime"]["legacy_test_import_count"] == 0
    assert result["runtime"]["mathhub_legacy_import_count"] == 0
    assert result["runtime"]["testamur_only"] is True
