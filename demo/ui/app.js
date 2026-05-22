// munshi workbench controller

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function loadJSON(path) {
  const res = await fetch(path);
  return res.json();
}

// ── Section tab switching (Agent / World / Scenario) ──────────────────────
function initSectionTabs() {
  $$('.section-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('.section-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.section;
      $$('.section-panel').forEach(p => p.classList.add('hidden'));
      $(`#panel-${target}`).classList.remove('hidden');
    });
  });
}

// ── Inner tabs (Tools / Rules / Schemas / Failure Modes inside World panel) ──
function initInnerTabs() {
  $$('[data-tab]').forEach(tab => {
    tab.addEventListener('click', () => {
      const group = tab.closest('.section-panel, [class*="border-b"]');
      const allTabs = group.querySelectorAll('[data-tab]');
      allTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.tab;
      $$('.tab-content').forEach(c => c.classList.add('hidden'));
      $(`#tab-${target}`).classList.remove('hidden');
    });
  });
}

// ── Render world ──────────────────────────────────────────────────────────
function renderWorld(world) {
  $('#world-name').textContent = world.name;
  $('#world-subtitle').textContent = world.subtitle;
  $('#regime-note').textContent = world.regime_note;

  // Tools
  $('#tools-grid').innerHTML = world.tools.map((t, i) => `
    <div class="panel p-4">
      <div class="flex items-start justify-between mb-1">
        <code class="mono text-sm text-[var(--amber)]">${t.name}</code>
        <span class="mono text-[10px] text-[var(--text-muted)]">T-0${i + 1}</span>
      </div>
      <p class="text-sm text-[var(--text-dim)]">${t.purpose}</p>
    </div>
  `).join('');

  // Rules
  $('#rules-list').innerHTML = world.rules.map(r => `
    <div class="panel p-4 flex gap-4">
      <div class="mono text-xs text-[var(--amber)] min-w-[44px] mt-0.5">${r.code}</div>
      <div>
        <div class="font-semibold text-sm mb-1">${r.name}</div>
        <p class="text-sm text-[var(--text-dim)]">Blocks: ${r.blocks}</p>
      </div>
    </div>
  `).join('');

  // Schemas
  $('#schemas-list').innerHTML = world.schemas.map(s => `
    <div class="panel p-4">
      <div class="mono text-sm text-[var(--amber)] mb-2">${s.name}</div>
      <div class="mono text-xs text-[var(--text-dim)]">${s.fields}</div>
    </div>
  `).join('');

  // Failure modes
  $('#fm-list').innerHTML = world.failure_modes.map(fm => `
    <div class="panel p-4 flex gap-4">
      <div class="mono text-xs text-[var(--amber)] min-w-[44px] mt-0.5">${fm.code}</div>
      <div>
        <div class="font-semibold text-sm mb-1">${fm.name}</div>
        <p class="text-xs text-[var(--text-dim)]"><span class="mono text-[var(--text-muted)]">EVIDENCE:</span> ${fm.evidence}</p>
      </div>
    </div>
  `).join('');

  // Agent
  $('#agent-framework').textContent = world.agent.framework;
  $('#agent-model').textContent = world.agent.model;
  $('#agent-tools').textContent = `${world.agent.tools_bound} world tools`;
  $('#agent-prompt').textContent = `"${world.agent.system_prompt_excerpt}"`;
}

// ── Render scenario ───────────────────────────────────────────────────────
const TAG_CLASS = { clean: 'tag-clean', ghost: 'tag-anomaly', 'account-swap': 'tag-anomaly', 'npci-diverged': 'tag-anomaly', 'expired-life-cert': 'tag-anomaly', 'already-paid': 'tag-amber' };

function renderScenario(scenario) {
  $('#scenario-name').textContent = scenario.name;
  $('#scenario-description').textContent = scenario.description;
  $('#pensioners-grid').innerHTML = scenario.pensioners.map(p => `
    <div class="panel p-4">
      <div class="flex items-start justify-between mb-2">
        <div>
          <div class="font-semibold">${p.name}</div>
          <div class="mono text-[11px] text-[var(--text-muted)]">${p.ppo}</div>
        </div>
        <span class="tag ${TAG_CLASS[p.tag] || 'tag-info'}">${p.expected}</span>
      </div>
      <div class="mono text-[11px] text-[var(--text-dim)] mb-2">${p.scheme} · ${p.district}</div>
      ${p.anomaly
        ? `<p class="text-sm border-l-2 border-l-[var(--red)] pl-3">${p.anomaly}</p>`
        : `<p class="text-sm text-[var(--text-muted)] italic">clean — should disburse</p>`}
    </div>
  `).join('');
}

// ── Render results ────────────────────────────────────────────────────────
const ACTION_LABELS = {
  disbursement_success:              { label: 'DISBURSED', cls: 'pill-pass' },
  pensioner_marked_deceased:         { label: 'CANCELLED — deceased', cls: 'pill-pass' },
  pensioner_suspended_for_life_cert: { label: 'SUSPENDED — life cert', cls: 'pill-pass' },
  pensioner_flagged_for_audit:       { label: 'FLAGGED FOR AUDIT', cls: 'pill-pass' },
};

function renderResults(scenario, run) {
  // Show results panel, keep active section tab visible too
  $$('.section-panel').forEach(p => p.classList.add('hidden'));
  $('#panel-results').classList.remove('hidden');
  // De-activate section tabs (none active while viewing results)
  $$('.section-tab').forEach(t => t.classList.remove('active'));

  // Scoreboard
  const SCORE_META = {
    goal_reached:  { title: 'Goal reached',  sub: 'All cases handled correctly?' },
    rules_upheld:  { title: 'Rules upheld',  sub: 'No invariant violated?' },
    cost_used:     { title: 'Cost',          sub: 'Dollars spent on the run' },
  };
  $('#scoreboard').innerHTML = Object.entries(run.scores).map(([name, s]) => {
    const m = SCORE_META[name] || { title: name, sub: '' };
    return `
      <div class="panel p-5">
        <div class="mono text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-1">${m.title}</div>
        <div class="text-xs text-[var(--text-dim)] mb-4">${m.sub}</div>
        <div class="flex items-center justify-between">
          <span class="${s.passed ? 'pill-pass' : 'pill-fail'}">${s.passed ? 'PASS ✓' : 'FAIL ✗'}</span>
          <span class="mono text-xs text-[var(--text-dim)]">${s.answer}</span>
        </div>
      </div>`;
  }).join('');

  // Per-pensioner outcomes
  $('#outcomes-list').innerHTML = scenario.pensioners.map(p => {
    const actions = run.actions[p.ppo] || [];
    const violations = run.violations.filter(v => v.ppo_number === p.ppo);
    const skipped = !actions.length && !violations.length;
    const final = actions[actions.length - 1];
    const meta = final ? (ACTION_LABELS[final.description] || { label: final.description.toUpperCase().replace(/_/g,' '), cls: 'pill-pass' }) : null;
    const badge = skipped ? `<span class="pill-pass">SKIPPED</span>` : meta ? `<span class="${meta.cls}">${meta.label}</span>` : `<span class="tag tag-amber">NO ACTION</span>`;
    const reasoning = skipped ? 'Already paid this quarter — agent correctly skipped.'
                    : final?.reason || '(no reasoning recorded)';

    const violated = violations.map(v => `
      <div class="mt-2 mono text-xs text-[var(--red)] border-l-2 border-l-[var(--red)] pl-3">
        [${v.rule_code}] ${v.reason}
      </div>`).join('');

    return `
      <div class="panel p-5">
        <div class="flex items-start justify-between mb-2">
          <div>
            <span class="font-semibold">${p.name}</span>
            <span class="mono text-xs text-[var(--text-muted)] ml-2">${p.ppo}</span>
          </div>
          ${badge}
        </div>
        <div class="text-xs text-[var(--text-dim)] mb-2">${p.anomaly || 'clean case'}</div>
        <p class="text-sm text-[var(--text-dim)] border-l-2 border-l-[var(--amber)] pl-3">${reasoning}</p>
        ${violated}
      </div>`;
  }).join('');

  // Summary
  $('#sum-duration').textContent = `${run.duration_sec}s`;
  $('#sum-tool-calls').textContent = run.tool_calls;
  $('#sum-tokens').textContent = (run.tokens.input + run.tokens.output).toLocaleString();
  $('#sum-dollars').textContent = `$${run.dollars.toFixed(4)}`;
}

// ── Run button ────────────────────────────────────────────────────────────
function initRunButton(scenario, run) {
  $('#run-btn').addEventListener('click', () => {
    $('#run-btn').disabled = true;
    $('#run-btn').style.opacity = '0.5';
    $('#reset-btn').classList.add('hidden');

    const stages = [
      { delay: 600,  msg: 'agent connected · seeding world ' },
      { delay: 900,  msg: 'calling list_pending_disbursements ' },
      { delay: 1400, msg: 'processing 7 pensioners ' },
      { delay: 900,  msg: 'world enforcing server-side rules ' },
      { delay: 600,  msg: 'scoring run ' },
    ];

    let elapsed = 0;
    stages.forEach(s => {
      elapsed += s.delay;
      setTimeout(() => {
        $('#run-status').innerHTML = `${s.msg}<span class="loader-dot"></span><span class="loader-dot"></span><span class="loader-dot"></span>`;
      }, elapsed);
    });

    setTimeout(() => {
      $('#run-status').innerHTML = `<span class="text-[var(--green)]">✓ complete</span>`;
      $('#reset-btn').classList.remove('hidden');
      renderResults(scenario, run);
    }, elapsed + 300);
  });

  $('#reset-btn').addEventListener('click', () => {
    $('#run-btn').disabled = false;
    $('#run-btn').style.opacity = '1';
    $('#reset-btn').classList.add('hidden');
    $('#run-status').textContent = '';
    // Go back to Agent tab
    $$('.section-panel').forEach(p => p.classList.add('hidden'));
    $('#panel-agent').classList.remove('hidden');
    $$('.section-tab').forEach(t => t.classList.remove('active'));
    $('.section-tab[data-section="agent"]').classList.add('active');
  });
}

// ── Boot ──────────────────────────────────────────────────────────────────
async function init() {
  const [world, scenario, run] = await Promise.all([
    loadJSON('data/world.json'),
    loadJSON('data/scenario.json'),
    loadJSON('data/run_result.json'),
  ]);

  renderWorld(world);
  renderScenario(scenario);
  initSectionTabs();
  initInnerTabs();
  initRunButton(scenario, run);
}

init();
