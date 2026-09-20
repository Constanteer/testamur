/* Canonical Authority presentation renderers.
 *
 * This module is deliberately presentation-only. It consumes ProductService
 * projections; it does not classify reason strings, traverse graphs, validate
 * credentials, or infer authority from lineage/reliance/affectedness/connectivity.
 */
(() => {
  const ORDER = [
    ['credential_or_token', 'Credential / token'],
    ['capability_or_delegation', 'Capability / delegation'],
    ['approval_or_mfa', 'Approval / MFA'],
    ['trust_boundary_policy', 'Trust-boundary policy'],
    ['other', 'Other / unclassified'],
  ];
  const CONSTRAINT_LABELS = Object.freeze({
    audiences: 'Audience',
    scopes: 'Scope',
    issuer: 'Issuer',
    tenant: 'Tenant',
    binding: 'Binding',
    expires_at: 'Expiry / validity bound',
    repositories: 'Repository selection',
    resources: 'Resource selection',
    mfa_required: 'MFA requirement',
    approval_required: 'Approval requirement',
  });

  function canonicalReasonGroups(item) {
    const groups = item && typeof item.reason_groups === 'object' && item.reason_groups !== null
      ? item.reason_groups
      : {};
    return ORDER.map(([key, label]) => {
      const values = Array.isArray(groups[key])
        ? groups[key].filter(value => typeof value === 'string' && value.length)
        : [];
      return { key, label, values };
    }).filter(group => group.values.length);
  }

  function escapeFallback(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;');
  }

  function renderAuthorityReasonGroups(item, escapeHtml) {
    const groups = canonicalReasonGroups(item);
    if (!groups.length) return '';
    const escValue = typeof escapeHtml === 'function' ? escapeHtml : escapeFallback;
    return `<div class="authority-reason-groups">${groups.map(group =>
      `<section data-reason-group="${group.key}"><span>${group.label}</span>${group.values.map(reason => `<code>${escValue(reason)}</code>`).join('')}</section>`
    ).join('')}</div>`;
  }

  function renderRawReasons(item, escapeHtml) {
    const reasons = Array.isArray(item?.reasons)
      ? item.reasons.filter(value => typeof value === 'string' && value.length)
      : Array.isArray(item?.failure_reasons)
        ? item.failure_reasons.filter(value => typeof value === 'string' && value.length)
        : [];
    if (!reasons.length) return '';
    const escValue = typeof escapeHtml === 'function' ? escapeHtml : escapeFallback;
    return `<details class="authority-raw-reasons"><summary>Raw canonical denial reasons</summary><div>${reasons.map(reason => `<code>${escValue(reason)}</code>`).join(' ')}</div></details>`;
  }

  function renderBlockedReasons(item, escapeHtml) {
    const grouped = renderAuthorityReasonGroups(item, escapeHtml);
    const raw = renderRawReasons(item, escapeHtml);
    if (!grouped && !raw) return '';
    return `${grouped}${raw}`;
  }

  function renderRecordedConstraintSemantics(record, escapeHtml) {
    const semantics = record && record.recorded_constraint_semantics;
    if (!semantics || typeof semantics !== 'object' || Array.isArray(semantics)) return '';
    const escValue = typeof escapeHtml === 'function' ? escapeHtml : escapeFallback;
    const rows = Object.entries(CONSTRAINT_LABELS)
      .filter(([key]) => Object.prototype.hasOwnProperty.call(semantics, key))
      .map(([key, label]) => {
        const values = Array.isArray(semantics[key]) ? semantics[key] : [semantics[key]];
        const rendered = values.map(value => `<code>${escValue(typeof value === 'object' ? JSON.stringify(value) : String(value))}</code>`).join('');
        return `<div class="authority-semantic-row"><span>${label}</span><div>${rendered}</div></div>`;
      }).join('');
    if (!rows) return '';
    return `<div class="authority-recorded-semantics"><strong>Recorded constraint semantics</strong><p>Projection only — recorded does not mean valid, and omitted does not mean unrestricted.</p>${rows}</div>`;
  }

  function renderExactEvidenceRecord(record, role, escapeHtml) {
    if (!record || typeof record !== 'object' || Array.isArray(record)) return '';
    const escValue = typeof escapeHtml === 'function' ? escapeHtml : escapeFallback;
    const evidenceRole = role === 'supporting_evidence' ? 'Supporting credential / token evidence' : 'Traversed authority edge';
    const edgeId = record.edge_id || record.id || 'recorded-edge';
    const source = record.source_ref || record.source || '';
    const target = record.target_ref || record.target || '';
    const semantics = renderRecordedConstraintSemantics(record, escValue);
    return `<div class="authority-exact-evidence" data-evidence-role="${role === 'supporting_evidence' ? 'supporting_evidence' : 'authority_path'}"><div><strong>${evidenceRole}</strong><code>${escValue(edgeId)}</code></div>${source || target ? `<span>${escValue(source)} → ${escValue(target)}</span>` : ''}${semantics}<details><summary>Raw recorded edge</summary><pre>${escValue(JSON.stringify(record, null, 2))}</pre></details></div>`;
  }

  // Export one narrow production presentation surface for authority.js.
  // Grouping comes exclusively from ProductService. Raw reasons are audit-only;
  // recorded constraints are display-only and are never validated in-browser.
  // Exact evidence records preserve the backend role: supporting evidence never
  // becomes an authority-path edge merely because it is connected to one.
  globalThis.testamurAuthorityReasonGroups = Object.freeze({
    canonicalReasonGroups,
    render: renderAuthorityReasonGroups,
    renderRawReasons,
    renderBlockedReasons,
    renderRecordedConstraintSemantics,
    renderExactEvidenceRecord,
  });
})();
