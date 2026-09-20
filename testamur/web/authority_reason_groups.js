/* Canonical Authority blocked-reason projection renderer.
 *
 * This module is deliberately presentation-only. It consumes ProductService
 * `reason_groups`; it does not classify reason strings, traverse graphs, or
 * infer authority from lineage/reliance/affectedness/connectivity.
 */
(() => {
  const ORDER = [
    ['credential_or_token', 'Credential / token'],
    ['capability_or_delegation', 'Capability / delegation'],
    ['approval_or_mfa', 'Approval / MFA'],
    ['trust_boundary_policy', 'Trust-boundary policy'],
    ['other', 'Other / unclassified'],
  ];

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

  // Export a narrow presentation surface for authority.js. Grouping comes
  // exclusively from ProductService. Raw reasons are audit-only and are never
  // inspected to derive a category, permission, validity, or reachability.
  globalThis.testamurAuthorityReasonGroups = Object.freeze({
    canonicalReasonGroups,
    render: renderAuthorityReasonGroups,
    renderRawReasons,
    renderBlockedReasons,
  });
})();
