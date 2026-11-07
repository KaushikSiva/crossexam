const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label = value => value.replaceAll('_', ' ');
const pct = score => score.total ? Math.round(1000 * score.detected / score.total) / 10 : 0;
let report = null, local = false, busy = false, replaying = false, selected = 0, currentView = 'overview', providers = {};
const titles = {overview:['The perfect-score problem.','Find the broken implementations your existing tests accept.'],learning:['The eval gets better.','Every proposed improvement must earn promotion on separate validation work.'],audit:['The unseen test.','Learning is finished. Now measure what transfers to different implementations.'],evidence:['Show your work.','Source hashes, provider usage, frozen suites, and an execution journal.']};

function showView(view) {
  if (!titles[view]) view = 'overview';
  currentView = view;
  $$('.view').forEach(el => el.classList.toggle('active', el.id === view));
  $$('.nav').forEach(el => el.classList.toggle('active', el.dataset.view === view));
  $('#view-title').textContent = titles[view][0];
  $('#view-description').textContent = titles[view][1];
  if (location.hash !== '#view='+view) history.replaceState(null, '', '#view='+view);
  window.scrollTo({top:0,behavior:'instant'});
  if (view === 'learning' && report) renderLearning();
}
$$('[data-view]').forEach(el => el.addEventListener('click', () => showView(el.dataset.view)));
window.addEventListener('hashchange', () => showView(location.hash.slice(1).replace('view=','')));

function toast(message) {
  $('#toast').textContent = message; $('#toast').classList.add('show');
  setTimeout(() => $('#toast').classList.remove('show'), 3300);
}
function exportReport() {
  if (!report) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(report,null,2)], {type:'application/json'}));
  const a = document.createElement('a'); a.href = url; a.download = 'crossexam-evidence.json'; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('#export').onclick = exportReport; $('#export2').onclick = exportReport;

function renderStats() {
  const before = report.audit_before, after = report.audit_after;
  const promoted = report.versions.filter(v => v.accepted && v.version > 0).length;
  const entries = [
    ['FINAL AUDIT DETECTION', `<span class="old">${before.detected}/${before.total}</span><span class="arrow">→</span>${after.detected}/${after.total}`, 'Different code variants · same defect families'],
    ['PROVEN BLIND SPOTS', report.counterexamples.length, 'Faulty patches that pass the original suite'],
    ['CORRECT CODE REJECTED', `${after.false_rejections}<span class="unit"> / ${after.controls}</span>`, 'Independent correct controls'],
    ['IMPROVEMENTS PROMOTED', `${promoted}<span class="unit"> / ${report.versions.length-1}</span>`, `Active evaluation: v${report.active_version}`]
  ];
  $('#stats').innerHTML = entries.map(([name,value,note])=>`<div class="stat"><div class="stat-label">${name}</div><div class="stat-value">${value}</div><div class="stat-note">${note}</div></div>`).join('');
}

function selectCase(index) {
  if (!report?.counterexamples.length) return;
  selected = Math.min(index, report.counterexamples.length-1);
  const c = report.counterexamples[selected], w = c.witness;
  $$('.case-button').forEach((el,i)=>el.classList.toggle('active',i===selected));
  const mismatch = w.actual.findIndex((a,i)=>JSON.stringify(a)!==JSON.stringify(w.expected[i]));
  const indices = w.actions.length <= 2 ? w.actions.map((_,i)=>i) : [Math.max(0,mismatch-1),mismatch];
  const traces = indices.map(i => {
    const a=w.actions[i], actual=w.actual[i], expected=w.expected[i];
    const wrong=JSON.stringify(actual)!==JSON.stringify(expected);
    const tenant = actual?.tenant;
    const returned = tenant ? `tenant: <strong class="${wrong?'bad-value':''}">${esc(tenant)}</strong>` : Object.entries(actual||{}).map(([k,v])=>`${esc(k)}: <strong class="${wrong?'bad-value':''}">${esc(v)}</strong>`).join('<br>');
    return `<div class="trace-step ${wrong?'wrong':''}"><div class="trace-label">REQUEST ${String(i+1).padStart(2,'0')} ${wrong?'<span>CONTRACT VIOLATION</span>':'<span style="color:var(--green)">OBSERVED</span>'}</div><div class="trace-action">${esc(a.op).toUpperCase()}<br>tenant: <strong>${esc(a.tenant)}</strong><br>${a.key!==undefined?`key: <strong>${esc(a.key)}</strong><br>`:''}${a.qty!==undefined?`qty: ${esc(a.qty)} · ${esc(a.sku)}`:a.sku?`sku: ${esc(a.sku)}`:''}</div><div class="trace-return">↳ ${returned}${wrong?`<div class="expected">Expected: ${esc(JSON.stringify(expected))}</div>`:'<div class="expected">Matches the independent contract model.</div>'}</div></div>`;
  }).join('');
  const diff=c.diff.split('\n').filter(line=>line.trim()&&!line.startsWith('@@')&&!line.startsWith('---')&&!line.startsWith('+++')).slice(0,8).map(line=>`<span class="${line.startsWith('+')?'added':line.startsWith('-')?'removed':'header'}">${esc(line)}</span>`).join('\n');
  $('#case-detail').innerHTML=`<div class="case-title"><h3>${esc(c.title)}</h3><div class="mono">${esc(c.origin).toUpperCase()}</div></div><div class="verdict-strip"><span>✓ EXISTING TESTS ${c.baseline_checks}/${c.baseline_checks}</span><span class="bad">× CONTRACT VIOLATED</span></div><div class="trace">${traces}</div><div class="code-label"><span>THE CHANGE THAT SLIPPED THROUGH</span><span>${w.actions.length} ACTION REPRODUCER</span></div><pre class="diff">${diff}</pre><div class="source-note">1-minimal failing action sequence. Expected results are computed outside the candidate sandbox.</div>`;
}
function renderCases(){
  $('#case-count').textContent = `${report.counterexamples.length} VERIFIED COUNTEREXAMPLES`;
  $('#case-list').innerHTML=report.counterexamples.map((c,i)=>`<button class="case-button ${i===selected?'active':''}" data-case="${i}"><div class="case-id"><span>${esc(c.id)} / ${esc(label(c.family).toUpperCase())}</span><em>FAIL</em></div><div class="case-name">${esc(c.title)}</div></button>`).join('');
  $$('.case-button').forEach(el=>el.onclick=()=>selectCase(+el.dataset.case));
  if(report.counterexamples.length)selectCase(selected);else $('#case-detail').innerHTML='<p class="empty">No proven blind spot found in this run. The report does not substitute an unverified example.</p>';
}

function curveSVG(){
  const versions=report.versions, W=650,H=270,L=43,R=26,T=27,B=42,iw=W-L-R,ih=H-T-B;
  const x=i=>L+i*iw/(versions.length-1), y=n=>T+(100-n)*ih/100;
  let active=versions[0].validation,points=[];
  versions.forEach((v,i)=>{if(v.accepted)active=v.validation;points.push([x(i),y(pct(active)),pct(active)]);});
  const grid=[0,25,50,75,100].map(n=>`<line x1="${L}" x2="${W-R}" y1="${y(n)}" y2="${y(n)}" stroke="#e1e1e1" stroke-dasharray="${n?'3 5':'0'}"/><text x="${L-12}" y="${y(n)+4}" text-anchor="end">${n}%</text>`).join('');
  const path=points.map((p,i)=>`${i?'L':'M'}${p[0]},${p[1]}`).join(' ');
  const fill=`${path} L${points.at(-1)[0]},${y(0)} L${L},${y(0)} Z`;
  const marks=points.map((p,i)=>`<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="#f7f7f7" stroke="#242424" stroke-width="2.5"><title>After v${i}: ${p[2]}% of validation defects detected</title></circle><text class="value-label" x="${p[0]}" y="${p[1]-12}" text-anchor="middle">${p[2]}%</text><text x="${p[0]}" y="${H-17}" text-anchor="middle">v${i}${versions[i].accepted?'':' ×'}</text>`).join('');
  const rejected=versions.map((v,i)=>!v.accepted?`<line x1="${x(i)}" x2="${x(i)}" y1="${points[i][1]+7}" y2="${y(pct(v.validation))-7}" stroke="#848484" stroke-dasharray="3 4"/><circle cx="${x(i)}" cy="${y(pct(v.validation))}" r="5" fill="#555555"><title>Rejected proposal v${i}: ${pct(v.validation)}%. Active suite retained.</title></circle>`:'').join('');
  return `<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Validation detection across evaluation versions">${grid}<path d="${fill}" fill="#e0e0e0" opacity=".45"/><path class="curve-path" d="${path}" fill="none" stroke="#242424" stroke-width="3"/>${marks}${rejected}</svg>`;
}
function renderLearning(){
  $('#curve').innerHTML=curveSVG();
  const before=report.validation_before, after=report.validation_after;
  $('#promotion-panel').innerHTML=`<div class="eyebrow">VALIDATION DETECTION</div><div class="big">${pct(after)}<span style="font-size:25px">%</span></div><p>${after.detected} of ${after.total} seeded validation defects caught.<br>${after.false_rejections} of ${after.controls} correct controls rejected.</p><div class="rollback"><strong>↶ Regression blocked</strong><br>The shorter smoke suite was evaluated and rejected. Version ${report.active_version} stays active.</div>`;
  const families=[...new Set(after.rows.filter(r=>!r.correct).map(r=>r.family))];
  $('#family-chart').innerHTML=families.map(f=>{
    const b=before.rows.filter(r=>r.family===f),a=after.rows.filter(r=>r.family===f),bn=b.filter(r=>r.detected).length,an=a.filter(r=>r.detected).length;
    return `<div class="bar-row"><span>${esc(label(f))}</span><div class="bar-track"><div class="bar-new" style="width:${an/a.length*100}%"></div><div class="bar-old" style="width:${bn/b.length*100}%"></div></div><span class="bar-number">${bn} → ${an}/${a.length}</span></div>`;
  }).join('');
  const max=Math.max(...report.versions.map(v=>v.suite.length));
  $('#cost-chart').innerHTML=report.versions.map(v=>`<div class="bar-row"><span>v${v.version} · ${v.suite.length} scenarios</span><div class="bar-track"><div class="bar-new ${v.accepted?'':'reject'}" style="width:${v.suite.length/max*100}%"></div></div><span class="bar-number">${v.validation.seconds.toFixed(2)}s</span></div>`).join('');
  $('#version-table').innerHTML=`<div class="table-scroll"><table class="data-table"><thead><tr><th>Version</th><th>Proposal</th><th>Detection</th><th>False rejects</th><th>Decision</th><th>Suite hash</th></tr></thead><tbody>${report.versions.map(v=>`<tr><td class="mono">v${v.version}</td><td>${esc(v.rationale)}<span class="muted">${esc(v.origin)}</span></td><td>${v.validation.detected}/${v.validation.total}</td><td>${v.validation.false_rejections}/${v.validation.controls}</td><td><span class="status ${v.accepted?'accepted':'rejected'}">${v.version===0?'BASELINE':v.accepted?'↑ PROMOTED':'↶ REJECTED'}</span></td><td class="mono" title="${esc(v.suite_sha256)}">${v.suite_sha256.slice(0,10)}</td></tr>`).join('')}</tbody></table></div>`;
}
function renderAudit(){
  const b=report.audit_before,a=report.audit_after;
  $('#audit-visual').innerHTML=`<div class="audit-score before"><div class="num">${b.detected}<span>/${b.total}</span></div><div class="mono">ORIGINAL EVALUATION</div></div><div class="audit-arrow">→</div><div class="audit-score after"><div class="num">${a.detected}<span>/${a.total}</span></div><div class="mono">PROMOTED EVALUATION</div></div>`;
  $('#audit-table').innerHTML=`<div class="table-scroll"><table class="data-table"><thead><tr><th>Variant</th><th>Behavior</th><th>Original suite</th><th>Promoted suite</th></tr></thead><tbody>${a.rows.map(r=>{const old=b.rows.find(x=>x.id===r.id);return `<tr><td class="mono">${esc(r.id)}</td><td>${esc(r.title)}<span class="muted">${r.correct?'Correct implementation control':esc(label(r.family))}</span></td><td><span class="status ${r.correct?!old.detected?'accepted':'rejected':old.detected?'accepted':'rejected'}">${r.correct?old.detected?'FALSE REJECTION':'ACCEPTED':old.detected?'CAUGHT':'MISSED'}</span></td><td><span class="status ${r.correct?!r.detected?'accepted':'rejected':r.detected?'accepted':'rejected'}">${r.correct?r.detected?'FALSE REJECTION':'ACCEPTED':r.detected?'CAUGHT':'MISSED'}</span></td></tr>`}).join('')}</tbody></table></div>`;
  $('#limitations').innerHTML=`<strong>Scope of this result</strong><br>${report.limitations.map(esc).join('<br>')}`;
}
function renderEvidence(){
  const m=report.manifest;
  const entries=[['RUN MODE',m.mode],['EXECUTION RUNTIME',m.runtime],['STARTED',m.created_at],['CODE COMMIT',m.commit],['CONTRACT SHA-256',m.contract_sha256],['BENCHMARK SHA-256',m.corpus_sha256],['EVENT CHAIN ROOT',report.event_root_sha256]];
  $('#provenance').innerHTML=entries.map(([k,v])=>`<dt>${k}</dt><dd class="${k.includes('SHA')||k.includes('ROOT')||k.includes('COMMIT')?'hash':''}">${esc(v)}</dd>`).join('');
  $('#partner-calls').innerHTML=report.provider_calls.length?report.provider_calls.map(c=>`<div class="partner-row">${esc(c.provider==='meta'?'Meta Model API':'Subquadratic')} · ${esc(c.purpose)}<div class="mono">${esc(c.model)} / ${esc(c.status)} / ${c.seconds}s / ${c.usage.input_tokens??c.usage.prompt_tokens??'—'} input tokens</div></div>`).join(''):'<p class="empty">No partner API calls in this local fixture run. The source includes live Meta and Subquadratic adapters; live results are labeled separately.</p>';
  $('#event-count').textContent=`${report.events.length} EVENTS`;
  $('#journal').innerHTML=report.events.map(e=>`<div class="event"><span>${String(e.sequence).padStart(2,'0')}</span><div><strong>${esc(label(e.kind))}</strong><p>${esc(e.message)}</p></div></div>`).join('');
}
function render(){
  if(!report)return;
  const modeLabel=report.manifest.mode==='live partners'?'LIVE PARTNERS':report.manifest.mode.startsWith('live Subquadratic')?'SUBQ + FIXTURES':'LOCAL FIXTURES';
  $('#mode').textContent=`${local?'Saved run':'Recorded evidence'} · ${modeLabel}`;
  $('#footer-mode').textContent=`${report.manifest.mode==='live partners'?'Live partner run':report.manifest.mode.startsWith('live Subquadratic')?'Live Subquadratic + local fixtures':'Local fixture run'} · ${report.elapsed_seconds}s · Synthetic benchmark`;
  renderStats();renderCases();renderLearning();renderAudit();renderEvidence();
  if(!local){$('#run').innerHTML='Run locally <span>↗</span>';$('#run').onclick=()=>window.open('https://github.com/KaushikSiva/crossexam#quick-start','_blank','noopener');}
}
async function poll(){
  if(replaying)return;
  try{
    const response=await fetch('api/state');if(!response.ok)throw Error('Static report');
    const state=await response.json();local=true;providers=state.providers;
    const wasBusy=busy;busy=state.busy;
    $('#progress').hidden=!busy;
    $('#run').disabled=busy;$('#replay').disabled=busy;
    if(busy){const e=state.events.at(-1);$('#progress-text').textContent=e?.message||'Probing sandbox isolation…';$('#progress-count').textContent=`${state.events.length} EVENTS`;$('#mode').textContent='Executing campaign';}
    if(state.report&&(!report||state.report.event_root_sha256!==report.event_root_sha256)){report=state.report;render();}
    if(wasBusy&&!busy){if(state.error){$('#notice').hidden=false;$('#notice').textContent=state.error;}else{render();toast('Campaign complete. Every chart now reflects the new run.');}}
    if(!report&&!busy){$('#notice').hidden=false;$('#notice').textContent='Start a local or live campaign to populate the evidence workspace.';}
  }catch(error){
    if(!report){try{const response=await fetch('report.json');if(!response.ok)throw Error('No report');report=await response.json();render();}catch{$('#notice').hidden=false;$('#notice').textContent='No saved report found. Run python3 -m crossexam run, then start the local server.';}}
  }
}
$('#run').onclick=()=>{
  $('#key-status').textContent=`META ${providers.meta?'CONFIGURED':'MISSING'} · SUBQUADRATIC ${providers.subquadratic?'CONFIGURED':'MISSING'}`;
  $('#start-live').disabled=!providers.meta||!providers.subquadratic;
  $('#start-subq').disabled=!providers.subquadratic;
  $('#run-dialog').showModal();
};
async function start(mode){
  $('#run-dialog').close();$('#notice').hidden=true;
  try{const r=await fetch('api/run',{method:'POST',headers:{'Content-Type':'application/json','X-CrossExam':'local-workspace'},body:JSON.stringify({mode})});const result=await r.json();if(!r.ok)throw Error(result.error);busy=true;$('#progress').hidden=false;$('#progress-text').textContent='Probing sandbox isolation…';await poll();}catch(e){toast(e.message);}
}
$('#start-local').onclick=()=>start('local');$('#start-subq').onclick=()=>start('subq');$('#start-live').onclick=()=>start('live');
$('#replay').onclick=async()=>{
  if(!report||replaying)return;
  replaying=true;$('#replay').disabled=true;$('#run').disabled=true;
  $('#notice').hidden=false;$('#notice').textContent='Recorded evidence playback. These are saved execution results, not a new live run.';
  const steps=[['overview',0,'Original tests pass. The independent contract check fails.'],['overview',1,'A second counterexample: repeated requests silently consume stock.'],['learning',null,'Validation evidence decides which suite changes are promoted.'],['learning',null,'A cheaper regression is rejected. The stronger suite stays active.'],['audit',null,'Only after learning ends do we open the final audit.'],['evidence',null,'Every decision is linked to source, suite hashes, and execution evidence.']];
  for(const [view,index,message]of steps){showView(view);if(index!==null)selectCase(index);toast(message);await new Promise(resolve=>setTimeout(resolve,4500));}
  replaying=false;$('#replay').disabled=false;$('#run').disabled=false;
};
window.CrossExam={showView,selectCase,getReport:()=>report};
showView(location.hash.slice(1).replace('view=','')||'overview');poll();setInterval(()=>{if(local)poll()},1200);
