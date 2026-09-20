from __future__ import annotations

import pytest

from testamur.authority_cli_projection import authority_explain_cli, authority_subject_cli


class _Service:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def authority_subject(self, ref: str):
        self.calls.append(("subject", ref))
        return {"schema": "testamur.authority-subject.v1", "ref": ref}

    def authority_explain(self, edge_ids, **options):
        self.calls.append(("explain", list(edge_ids), options))
        return {
            "schema": "testamur.authority-explanation.v1",
            "path_edge_ids": list(edge_ids),
            "supporting_edge_ids": list(options.get("supporting_edge_ids") or []),
        }


def test_subject_cli_is_exact_pass_through_read():
    service = _Service()
    result = authority_subject_cli(service, "  subject:alice  ")
    assert result["ref"] == "subject:alice"
    assert service.calls == [("subject", "subject:alice")]


def test_explain_cli_keeps_path_and_supporting_evidence_separate():
    service = _Service()
    result = authority_explain_cli(
        service,
        [" edge:delegate ", "edge:capability"],
        starting_ref="subject:alice",
        expected_target_ref="resource:repo",
        supporting_edge_ids=[" edge:credential "],
    )
    assert result["path_edge_ids"] == ["edge:delegate", "edge:capability"]
    assert result["supporting_edge_ids"] == ["edge:credential"]
    _, path, options = service.calls[0]
    assert path == ["edge:delegate", "edge:capability"]
    assert options["supporting_edge_ids"] == ["edge:credential"]
    assert "edge:credential" not in path


@pytest.mark.parametrize("edge_ids", [[], [""], ["edge:a", "   "]])
def test_explain_cli_rejects_missing_exact_path_evidence(edge_ids):
    service = _Service()
    with pytest.raises(ValueError, match="exact edge ids"):
        authority_explain_cli(service, edge_ids)
    assert service.calls == []


def test_explain_cli_rejects_blank_supporting_evidence_before_service_call():
    service = _Service()
    with pytest.raises(ValueError, match="supporting authority edge ids"):
        authority_explain_cli(service, ["edge:path"], supporting_edge_ids=[" "])
    assert service.calls == []


def test_subject_cli_rejects_blank_ref_before_service_call():
    service = _Service()
    with pytest.raises(ValueError, match="non-empty ref"):
        authority_subject_cli(service, "   ")
    assert service.calls == []
