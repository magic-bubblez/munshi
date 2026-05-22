// munshi live workbench

const _BACKEND = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : 'http://51.21.191.238:8000';

const _MCP_SSE = `${_BACKEND}/mcp/up_pension/sse`;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

// ── Tab switching ─────────────────────────────────────────────────────────

function initTabs() {
  $$('.wb-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('.wb-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      $$('.wb-panel').forEach(p => p.classList.remove('active'));
      $(`#panel-${tab.dataset.panel}`).classList.add('active');
      if (tab.dataset.panel === 'leaderboard') renderLeaderboard();
    });
  });
}

// ── World sub-tabs ────────────────────────────────────────────────────────

function initWorldTabs() {
  $$('[data-wtab]').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('[data-wtab]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      $$('[id^="wtab-"]').forEach(c => c.classList.add('hidden'));
      $(`#wtab-${tab.dataset.wtab}`).classList.remove('hidden');
    });
  });
}

// ── Health check ─────────────────────────────────────────────────────────

async function checkHealth() {
  try {
    const res = await fetch(`${_BACKEND}/health`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    $('#status-dot').style.background = 'var(--green)';
    $('#status-text').textContent = 'backend live';
    $('#status-text').style.color = 'var(--green)';
    $('#health-display').innerHTML = `
      <div class="text-[var(--green)] mb-1">● online</div>
      <div class="text-[var(--text-dim)]">world: ${data.world}</div>
      <div class="text-[var(--text-dim)]">mcp: <a href="${_BACKEND}${data.mcp_endpoint || '/mcp/up_pension'}" class="text-[var(--amber)]">${data.mcp_endpoint || '/mcp/up_pension'}</a></div>
    `;
  } catch {
    $('#status-dot').style.background = 'var(--red)';
    $('#status-text').textContent = 'backend offline';
    $('#status-text').style.color = 'var(--red)';
    $('#health-display').innerHTML = `<div class="text-[var(--red)]">● unreachable at ${_BACKEND}</div>`;
  }
}

// ── Connect panel ─────────────────────────────────────────────────────────

const _PY_SNIPPET = `\
<span class="cm"># 1. pip install langchain-mcp-adapters langchain-anthropic langgraph</span>
<span class="cm"># 2. export ANTHROPIC_API_KEY=sk-...</span>

<span class="kw">import</span> asyncio
<span class="kw">from</span> langchain_anthropic <span class="kw">import</span> ChatAnthropic
<span class="kw">from</span> langchain_core.messages <span class="kw">import</span> HumanMessage, SystemMessage
<span class="kw">from</span> langchain_mcp_adapters.client <span class="kw">import</span> MultiServerMCPClient
<span class="kw">from</span> langchain_mcp_adapters.tools <span class="kw">import</span> load_mcp_tools
<span class="kw">from</span> langgraph.prebuilt <span class="kw">import</span> create_react_agent

MCP_URL = <span class="str">"${_MCP_SSE}"</span>

<span class="kw">async def</span> main():
    client = MultiServerMCPClient(
        {<span class="str">"munshi"</span>: {<span class="str">"transport"</span>: <span class="str">"sse"</span>, <span class="str">"url"</span>: MCP_URL}}
    )
    <span class="kw">async with</span> client.session(<span class="str">"munshi"</span>) <span class="kw">as</span> session:
        tools = <span class="kw">await</span> load_mcp_tools(session)
        llm = ChatAnthropic(model=<span class="str">"claude-sonnet-4-6"</span>, temperature=0)
        agent = create_react_agent(llm, tools)
        <span class="kw">await</span> agent.ainvoke({
            <span class="str">"messages"</span>: [
                SystemMessage(content=<span class="str">"Process every pending UP pension case..."</span>),
                HumanMessage(content=<span class="str">"Run all cases and submit as 'my-agent-v1'."</span>),
            ]
        }, config={<span class="str">"recursion_limit"</span>: 250})

asyncio.run(main())`;

const _ANY_SNIPPET = `\
<span class="cm"># MCP SSE endpoint:</span>
<span class="str">${_MCP_SSE}</span>

<span class="cm"># Available tools (8 world tools + submit_run):</span>
list_pending_disbursements()
query_pensioner_status(ppo_number)
verify_aadhaar_ekyc(aadhaar)
check_npci_mapper(aadhaar)
disburse_pension(ppo_number)
flag_death_and_cancel(ppo_number, reason)
suspend_for_life_cert(ppo_number, reason)
flag_for_audit(ppo_number, reason)
submit_run(agent_name)            <span class="cm"># call this when done — scores + publishes</span>

<span class="cm"># Each SSE connection is isolated: fresh world state, independent scoring.</span>
<span class="cm"># Health: ${_BACKEND}/health</span>
<span class="cm"># Leaderboard: ${_BACKEND}/api/leaderboard</span>`;

function initConnectPanel() {
  $('#mcp-url-display').textContent = _MCP_SSE;

  $('#copy-mcp-url').addEventListener('click', () => {
    navigator.clipboard.writeText(_MCP_SSE);
    $('#copy-mcp-url').textContent = 'copied!';
    setTimeout(() => { $('#copy-mcp-url').textContent = 'copy'; }, 1500);
  });

  $('#snip-py-code').innerHTML = _PY_SNIPPET;
  $('#snip-any-code').innerHTML = _ANY_SNIPPET;

  $('#copy-snip-py').addEventListener('click', () => {
    const plain = $('#snip-py-code').textContent;
    navigator.clipboard.writeText(plain);
    $('#copy-snip-py').textContent = 'copied!';
    setTimeout(() => { $('#copy-snip-py').textContent = 'copy'; }, 1500);
  });

  $('#snip-tab-py').addEventListener('click', () => {
    $('#snip-py').style.display = 'block';
    $('#snip-any').style.display = 'none';
    $('#snip-tab-py').style.color = 'var(--amber)';
    $('#snip-tab-py').style.borderColor = 'var(--amber)';
    $('#snip-tab-any').style.color = '';
    $('#snip-tab-any').style.borderColor = '';
  });

  $('#snip-tab-any').addEventListener('click', () => {
    $('#snip-any').style.display = 'block';
    $('#snip-py').style.display = 'none';
    $('#snip-tab-any').style.color = 'var(--amber)';
    $('#snip-tab-any').style.borderColor = 'var(--amber)';
    $('#snip-tab-py').style.color = '';
    $('#snip-tab-py').style.borderColor = '';
  });
}

// ── World panel ───────────────────────────────────────────────────────────

async function renderWorld() {
  const res = await fetch('data/world.json');
  const world = await res.json();

  $('#tools-grid').innerHTML = world.tools.map((t, i) => `
    <div class="panel p-4">
      <div class="flex items-start justify-between mb-1">
        <code class="mono text-sm text-[var(--amber)]">${t.name}</code>
        <span class="mono text-[10px] text-[var(--text-muted)]">T-${String(i+1).padStart(2,'0')}</span>
      </div>
      <p class="text-sm text-[var(--text-dim)]">${t.purpose}</p>
    </div>`).join('');

  $('#rules-list').innerHTML = world.rules.map(r => `
    <div class="panel p-4 flex gap-4">
      <div class="mono text-xs text-[var(--amber)] min-w-[44px] mt-0.5">${r.code}</div>
      <div>
        <div class="font-semibold text-sm mb-1">${r.name}</div>
        <p class="text-sm text-[var(--text-dim)]">Blocks: ${r.blocks}</p>
      </div>
    </div>`).join('');

  $('#schemas-list').innerHTML = world.schemas.map(s => `
    <div class="panel p-4">
      <div class="mono text-sm text-[var(--amber)] mb-2">${s.name}</div>
      <div class="mono text-xs text-[var(--text-dim)]">${s.fields}</div>
    </div>`).join('');

  $('#fm-list').innerHTML = world.failure_modes.map(fm => `
    <div class="panel p-4 flex gap-4">
      <div class="mono text-xs text-[var(--amber)] min-w-[44px] mt-0.5">${fm.code}</div>
      <div>
        <div class="font-semibold text-sm mb-1">${fm.name}</div>
        <p class="text-xs text-[var(--text-dim)]"><span class="mono text-[var(--text-muted)]">EVIDENCE:</span> ${fm.evidence}</p>
      </div>
    </div>`).join('');
}

// ── Scenario panel ────────────────────────────────────────────────────────

const _TAG = {
  clean:            'tag-clean',
  ghost:            'tag-anomaly',
  'account-swap':   'tag-anomaly',
  'npci-diverged':  'tag-anomaly',
  'life-cert':      'tag-anomaly',
  'biometric':      'tag-anomaly',
  'name-mismatch':  'tag-anomaly',
  'invalid-aadhaar':'tag-anomaly',
  'npci-inactive':  'tag-anomaly',
  'already-paid':   'tag-amber',
};

async function renderScenario() {
  const res = await fetch('data/scenario.json');
  const scenario = await res.json();

  $('#pensioners-grid').innerHTML = scenario.pensioners.map(p => `
    <div class="panel p-4">
      <div class="flex items-start justify-between mb-2">
        <div>
          <div class="font-semibold">${p.name}</div>
          <div class="mono text-[11px] text-[var(--text-muted)]">${p.ppo}</div>
        </div>
        <span class="tag ${_TAG[p.tag] || 'tag-info'}">${p.expected}</span>
      </div>
      <div class="mono text-[11px] text-[var(--text-dim)] mb-2">${p.scheme} · ${p.district}</div>
      ${p.anomaly
        ? `<p class="text-sm border-l-2 border-l-[var(--red)] pl-3">${p.anomaly}</p>`
        : `<p class="text-sm text-[var(--text-muted)] italic">clean — should disburse</p>`}
    </div>`).join('');
}

// ── Leaderboard ───────────────────────────────────────────────────────────

function _scoreColor(pct) {
  if (pct >= 80) return 'score-high';
  if (pct >= 50) return 'score-mid';
  return 'score-low';
}

function _relTime(isoStr) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 2) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

async function renderLeaderboard() {
  $('#lb-content').innerHTML = '<div class="mono text-xs text-[var(--text-muted)]">Loading…</div>';
  try {
    const res = await fetch(`${_BACKEND}/api/leaderboard`, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const rows = await res.json();

    if (!rows.length) {
      $('#lb-content').innerHTML = '<div class="mono text-xs text-[var(--text-muted)]">No runs yet — be the first to submit.</div>';
      return;
    }

    const tbody = rows.map((r, i) => `
      <tr class="lb-row" data-run-id="${r.run_id}">
        <td class="rank">${i + 1}</td>
        <td class="agent-name">${escHtml(r.agent_name)}</td>
        <td class="mono text-xs text-[var(--text-muted)]">${escHtml(r.world || 'up_pension_v1')}</td>
        <td class="${_scoreColor(r.completion * 100)}">${(r.completion * 100).toFixed(1)}%</td>
        <td class="${_scoreColor(r.compliance * 100)}">${(r.compliance * 100).toFixed(1)}%</td>
        <td class="mono text-xs">${r.tool_calls}</td>
        <td class="mono text-xs text-[var(--text-muted)]">$${Number(r.cost_usd).toFixed(4)}</td>
        <td class="mono text-xs text-[var(--text-muted)]">${_relTime(r.ran_at)}</td>
        <td class="mono text-xs text-[var(--amber)]">${escHtml(r.run_id)}</td>
      </tr>`).join('');

    $('#lb-content').innerHTML = `
      <table class="lb-table">
        <thead>
          <tr>
            <th>#</th><th>Agent</th><th>World</th>
            <th>Completion</th><th>Compliance</th><th>Calls</th><th>Cost</th><th>When</th><th>Run ID</th>
          </tr>
        </thead>
        <tbody>${tbody}</tbody>
      </table>
      <p class="mono text-[10px] text-[var(--text-muted)] mt-4">Click a row to load its trace →</p>`;

    $$('.lb-row').forEach(row => {
      row.addEventListener('click', () => {
        const runId = row.dataset.runId;
        $('#trace-run-id').value = runId;
        $$('.wb-tab').forEach(t => t.classList.remove('active'));
        $$('.wb-panel').forEach(p => p.classList.remove('active'));
        $('[data-panel="traces"]').classList.add('active');
        $('#panel-traces').classList.add('active');
        loadTrace(runId);
      });
    });
  } catch (e) {
    $('#lb-content').innerHTML = `<div class="mono text-xs text-[var(--red)]">Failed to load leaderboard: ${escHtml(String(e))}</div>`;
  }
}

// ── Traces ────────────────────────────────────────────────────────────────

function _kindLabel(kind) {
  const map = { tool_call: 'CALL', tool_result: 'RESULT', rule_violation: 'VIOLATION', state_delta: 'DELTA', agent_message: 'MSG' };
  return map[kind] || kind;
}

function _shortTime(isoStr) {
  try {
    return new Date(isoStr).toISOString().replace('T', ' ').slice(11, 23);
  } catch { return isoStr; }
}

function _truncate(obj, maxLen = 200) {
  const s = JSON.stringify(obj, null, 0);
  return s.length > maxLen ? s.slice(0, maxLen) + '…' : s;
}

async function loadTrace(runId) {
  $('#trace-content').innerHTML = '<div class="mono text-xs text-[var(--text-muted)]">Loading…</div>';
  try {
    const res = await fetch(`${_BACKEND}/api/runs/${encodeURIComponent(runId)}/trace`, { signal: AbortSignal.timeout(10000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data || !data.run_id) throw new Error('run not found');

    const events = data.trace?.events || [];
    const summary = `
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 mono text-xs">
        <div><span class="text-[var(--text-muted)]">agent </span><span class="text-[var(--text)]">${escHtml(data.agent_name)}</span></div>
        <div><span class="text-[var(--text-muted)]">completion </span><span class="text-[var(--green)]">${(data.completion * 100).toFixed(1)}%</span></div>
        <div><span class="text-[var(--text-muted)]">compliance </span><span class="text-[var(--green)]">${(data.compliance * 100).toFixed(1)}%</span></div>
        <div><span class="text-[var(--text-muted)]">cost </span><span class="text-[var(--text)]">$${Number(data.cost_usd).toFixed(4)}</span></div>
      </div>`;

    const timeline = events.length
      ? events.map(ev => `
        <div class="trace-event">
          <span class="trace-ts">${_shortTime(ev.timestamp)}</span>
          <span class="trace-kind kind-${ev.kind}">${_kindLabel(ev.kind)}</span>
          <span class="text-[var(--text-dim)] break-all">${escHtml(_truncate(ev.payload))}</span>
        </div>`).join('')
      : '<div class="mono text-xs text-[var(--text-muted)]">No events recorded.</div>';

    $('#trace-content').innerHTML = summary +
      `<div class="mono text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-3">${events.length} events</div>` +
      `<div class="panel p-4" style="max-height:60vh; overflow-y:auto;">${timeline}</div>`;
  } catch (e) {
    $('#trace-content').innerHTML = `<div class="mono text-xs text-[var(--red)]">Error: ${escHtml(String(e))}</div>`;
  }
}

function initTracePanel() {
  $('#trace-load-btn').addEventListener('click', () => {
    const runId = $('#trace-run-id').value.trim();
    if (runId) loadTrace(runId);
  });
  $('#trace-run-id').addEventListener('keydown', e => {
    if (e.key === 'Enter') $('#trace-load-btn').click();
  });
}

function initLeaderboardRefresh() {
  $('#lb-refresh').addEventListener('click', renderLeaderboard);
}

// ── XSS guard ─────────────────────────────────────────────────────────────

function escHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ── Boot ──────────────────────────────────────────────────────────────────

async function init() {
  initTabs();
  initWorldTabs();
  initConnectPanel();
  initTracePanel();
  initLeaderboardRefresh();

  checkHealth();
  renderWorld();
  renderScenario();
}

init();
