/* Presentation-only renderer for canonical recorded constraint semantics.
 * Presence means Testamur recorded the constraint. It does not mean the
 * credential is valid or the capability is authorized. Missing fields remain
 * unknown; the browser never treats omission as unrestricted authority.
 */
(() => {
  const LABELS = Object.freeze({
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

  const values = value => Array.isArray(value) ? value : [value];

  function render(record, esc) {
    const semantics = record && record.recorded_constraint_semantics;
    if (!semantics || typeof semantics !== 'object' || Array.isArray(semantics)) return '';
    const rows = Object.entries(LABELS)
      .filter(([key]) => Object.prototype.hasOwnProperty.call(semantics, key))
      .map(([key, label]) => {
        const rendered = values(semantics[key]).map(value => `<code>${esc(typeof value === 'object' ? JSON.stringify(value) : String(value))}</code>`).join('');
        return `<div class="authority-semantic-row"><span>${label}</span><div>${rendered}</div></div>`;
      }).join('');
    if (!rows) return '';
    return `<div class="authority-recorded-semantics"><strong>Recorded constraint semantics</strong><p>Projection only — recorded does not mean valid, and omitted does not mean unrestricted.</p>${rows}</div>`;
  }

  globalThis.testamurAuthorityConstraintSemantics = Object.freeze({ render });
})();
