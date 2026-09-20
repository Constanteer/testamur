/* Authority / Capability Graph UI.
 * This module consumes canonical authority projections only. It never derives
 * authorization from material lineage, reliance, affectedness, or adjacency.
 */
(() => {
  const baseNav = nav;
  nav = function authorityNav() {
    const html = baseNav();
    const active = location.pathname.startsWith('/authority');
    const link = `<a data-nav class="${active ? 'active' : ''}" href="/authority"${active ? ' aria-current="page"' : ''}>Authority</a>`;
    return html.replace('</nav>', `${link}</nav>`);
  };

  const baseRender = render;
  render = async function authorityAwareRender() {
    if (location.pathname === '/authority') return authorityPage();
    return baseRender();
  };

  const list = value => Array.isArray(value) ? value : [];
  const constraintSummary = capability => {
    const constraints = capability?.constraints || {};
    const entries = Object.entries(constraints);
    return entries.length ? entries.map(([key, value]) => `${key}=${typeof value === 'object' ? JSON.stringify(value) : value}`).join(' · ') : 'unconstrained';
  };
  const capabilityName = capability => capability?.capability || capability?.capability_id || capability?.name || capability?.action || 'capability';

  function semanticsNotice() {
    return `<div class="authority-semantics"><strong>Authority is explicit.</strong><span>Connectivity, material lineage, reliance and affectedness do not grant permission. Supporting credential evidence is shown separately from traversed authority edges.</span></div>`;
  }

  function authorityForm() {
    return `<form class="authority-query" data-authority-form>
      <label><span>Mode</span><select name="mode"><option value="reach">single-subject reachability</option><option value="blast">multi-seed blast radius</option></select></label>
      <label><span>Authority subject(s)</span><textarea name="refs" required rows="3" placeholder="credential:…&#10;connector:…"></textarea><small>One exact authority subject per line. Blast mode never treats lineage, reliance, affectedness or adjacency as compromise evidence.</small></label>
      <label><span>Compromise model</span><select name="compromise_model"><option value="credential_theft">credential theft</option><option value="runtime_compromise">runtime compromise</option><option value="principal_compromise">principal compromise</option><option value="connector_compromise">connector compromise</option></select></label>
      <button class="btn btn-primary" type="submit">Evaluate explicit authority</button>
    </form>`;
  }

  function exactRefs(raw) {
    return String(raw || '').split(/\r?\n/).map(value => value.trim()).filter(Boolean);
  }

  function pathEvidence(item) {
    const path = list(item.path_edge_ids);
    const support = list(item.supporting_edge_ids);
    return `<div class="authority-evidence"><div><span>Authority path</span>${path.length ? path.map(edge => `<code>${esc(edge)}</code>`).join('') : '<em>no traversed edge</em>'}</div><div><span>Supporting evidence</span>${support.length ? support.map(edge => `<code>${esc(edge)}</code>`).join('') : '<em>none</em>'}</div></div>`;
  }

  function capabilityCard(item) {
    const capability = item.capability || item;
    return `<article class="authority-card authority-allowed"><div class="authority-card-head"><strong>${esc(capabilityName(capability))}</strong>${badge(item.reachability_class || 'reachable', 'good')}</div><p>${esc(constraintSummary(capability))}</p>${pathEvidence(item)}</article>`;
  }

  function blockedCard(item) {
    const reasons = list(item.reasons || item.failure_reasons);
    const failed = list(item.failed_constraints);
    const unresolved = list(item.unresolved_constraints);
    const candidates = list(item.candidate_capabilities);
    const budget = list(item.inherited_capability_budget);
    return `<article class="authority-card authority-blocked"><div class="authority-card-head"><strong>${esc(item.target_ref || item.edge_id || 'Blocked transition')}</strong>${badge('blocked', 'warn')}</div>
      <p>${reasons.length ? reasons.map(reason => `<code>${esc(reason)}</code>`).join(' ') : 'Denied by explicit authority policy.'}</p>
      ${failed.length ? `<div class="authority-constraint"><span>Failed constraints</span>${failed.map(value => `<code>${esc(value)}</code>`).join('')}</div>` : ''}
      ${unresolved.length ? `<div class="authority-constraint"><span>Unresolved — not assumed valid</span>${unresolved.map(value => `<code>${esc(value)}</code>`).join('')}</div>` : ''}
      <details><summary>Candidate authority vs delegated budget</summary><div class="authority-budget"><div><h4>Candidate</h4><pre>${esc(pretty(candidates))}</pre></div><div><h4>Inherited budget</h4><pre>${esc(pretty(budget))}</pre></div></div></details>
      ${pathEvidence(item)}</article>`;
  }

  function crossingCard(item) {
    return `<article class="authority-crossing"><strong>${esc(item.boundary_ref || item.trust_boundary_ref || 'Trust boundary')}</strong><span>${esc(item.source_ref || '')} → ${esc(item.target_ref || '')}</span>${item.edge_id ? `<code>${esc(item.edge_id)}</code>` : ''}</article>`;
  }

  function authorityResults(value) {
    const capabilities = list(value.actionable_capabilities);
    const blocked = list(value.blocked_transitions);
    const crossings = list(value.trust_boundary_crossings);
    const reachable = list(value.reachable_subjects);
    return `<div class="authority-stats"><div><strong>${reachable.length}</strong><span>reachable subjects</span></div><div><strong>${capabilities.length}</strong><span>actionable capabilities</span></div><div><strong>${blocked.length}</strong><span>blocked transitions</span></div><div><strong>${crossings.length}</strong><span>boundary crossings</span></div></div>
      <div class="authority-columns"><section><div class="section-head"><h2>Reachable authority</h2><span>${capabilities.length}</span></div>${capabilities.length ? capabilities.map(capabilityCard).join('') : empty('No actionable capability', 'No explicit, valid authority path produced an actionable capability.')}</section>
      <section><div class="section-head"><h2>Why paths stop</h2><span>${blocked.length}</span></div>${blocked.length ? blocked.map(blockedCard).join('') : empty('No blocked transitions', 'No candidate authority transition was rejected in this traversal.')}</section></div>
      <section><div class="section-head"><h2>Trust-boundary crossings</h2><span>${crossings.length}</span></div>${crossings.length ? `<div class="authority-crossings">${crossings.map(crossingCard).join('')}</div>` : empty('No boundary crossing recorded', 'This result contains no explicit trust-boundary crossing.')}</section>`;
  }

  async function canonicalBlast(refs, compromiseModel) {
    const query = new URLSearchParams();
    refs.forEach(ref => query.append('ref', ref));
    query.set('compromise_model', compromiseModel);
    const response = await fetch(`/v1/authority/blast-radius?${query.toString()}`, { headers: { Accept: 'application/json' } });
    const value = await response.json();
    if (!response.ok || value?.ok === false) {
      const error = new Error(value?.error?.message || `HTTP ${response.status}`);
      error.code = value?.error?.code || 'authority_blast_failed';
      throw error;
    }
    return value;
  }

  async function authorityPage() {
    shell(`<div class="page-title"><div><h1>Authority</h1><p>Inspect explicit capabilities, delegation limits and compromise reachability.</p></div></div>${semanticsNotice()}${authorityForm()}<div data-authority-result>${empty('Run an authority query', 'Enter exact authority subjects. Testamur will not infer permission from connectivity.')}</div>`, true);
    document.querySelector('[data-authority-form]')?.addEventListener('submit', runAuthorityQuery);
    const query = params();
    const refs = query.getAll('ref');
    if (refs.length) {
      const form = document.querySelector('[data-authority-form]');
      form.elements.refs.value = refs.join('\n');
      form.elements.mode.value = query.get('mode') === 'blast' || refs.length > 1 ? 'blast' : 'reach';
      form.elements.compromise_model.value = query.get('compromise_model') || 'credential_theft';
      await runAuthorityQuery({ preventDefault() {}, currentTarget: form }, false);
    }
  }

  async function runAuthorityQuery(event, updateLocation = true) {
    event.preventDefault();
    const form = event.currentTarget;
    const result = document.querySelector('[data-authority-result]');
    const refs = exactRefs(form.elements.refs.value);
    const mode = form.elements.mode.value;
    const compromiseModel = form.elements.compromise_model.value;
    if (!refs.length) return;
    if (mode === 'reach' && refs.length !== 1) {
      result.innerHTML = `<div class="flash flash-danger"><strong>exact_seed_required</strong><span>Single-subject reachability requires exactly one authority subject. Use blast-radius mode for multiple explicit compromise seeds.</span></div>`;
      return;
    }
    result.innerHTML = loading(mode === 'blast' ? 'Evaluating explicit multi-seed blast radius…' : 'Evaluating explicit authority paths…');
    try {
      const value = mode === 'blast'
        ? await canonicalBlast(refs, compromiseModel)
        : await api('/v1/authority/reach', { ref: refs[0], compromise_model: compromiseModel });
      if (updateLocation) {
        const query = new URLSearchParams();
        query.set('mode', mode);
        refs.forEach(ref => query.append('ref', ref));
        query.set('compromise_model', compromiseModel);
        history.replaceState({}, '', `/authority?${query.toString()}`);
      }
      result.innerHTML = authorityResults(value);
      bindNavigation();
    } catch (error) {
      result.innerHTML = `<div class="flash flash-danger"><strong>${esc(error.code || 'authority_query_failed')}</strong><span>${esc(error.message || error)}</span></div>`;
    }
  }

  if (location.pathname === '/authority') queueMicrotask(() => render());
})();
