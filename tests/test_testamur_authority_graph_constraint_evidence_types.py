from testamur.authority_graph_constraints import graph_context_constraints_satisfied


def test_graph_resource_constraint_does_not_stringify_object_evidence():
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": {"ref": "repo:one"}}, source_ref="actor:one", target_ref="repo:one", unresolved=["resource"]
    )
    assert not ok
    assert reasons == ["resource_constraint_malformed"]
    assert unresolved == []


def test_graph_principal_aliases_are_alternate_encodings_not_additive_grants():
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"principal": "actor:one", "principals": ["actor:two"]}, source_ref="actor:one", target_ref="repo:one", unresolved=["principal", "principals"]
    )
    assert not ok
    assert reasons == ["principal_constraint_malformed_or_conflicting"]
    assert unresolved == []


def test_equivalent_graph_principal_aliases_are_accepted():
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"principal": "actor:one", "principals": ["actor:one"]}, source_ref="actor:one", target_ref="repo:one", unresolved=["principal", "principals"]
    )
    assert ok
    assert reasons == []
    assert unresolved == []


def test_malformed_subject_alias_cannot_become_graph_authority_evidence():
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"principal": "alias:operator"}, source_ref="actor:one", target_ref="repo:one",
        source_subject={"principal": {"ref": "alias:operator"}}, unresolved=["principal"]
    )
    assert not ok
    assert reasons == ["principal_evidence_malformed_or_conflicting"]
    assert unresolved == []


def test_conflicting_subject_resource_aliases_fail_closed():
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": "repo:alias"}, source_ref="actor:one", target_ref="repo:one",
        target_subject={"resource": "repo:alias", "resources": ["repo:other"]}, unresolved=["resource"]
    )
    assert not ok
    assert reasons == ["resource_evidence_malformed_or_conflicting"]
    assert unresolved == []


def test_canonical_subject_ref_remains_exact_evidence_without_aliases():
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": "repo:one"}, source_ref="actor:one", target_ref="repo:one", unresolved=["resource"]
    )
    assert ok
    assert reasons == []
    assert unresolved == []
