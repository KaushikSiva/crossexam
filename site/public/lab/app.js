const $ = (selector) => document.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label = value => value.replaceAll('_', ' ');
const pct = score => score.total ? Math.round(1000 * score.detected / score.total) / 10 : 0;
let report = null, local = false, busy = false, replaying = false, selected = 0, currentView = 'overview', providers = {}, statsShown = false;
const titles = {overview:['The perfect-score problem.','Broken code your tests accept.'],learning:['The eval gets better.','Promoted only when validation improves.'],audit:['The unseen test.','Held-out variants, opened after learning.'],evidence:['Show your work.','Hashes, provider calls, and the full journal.']};

/* ---------- motion ---------- */
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const EASE = 'cubic-bezier(.22,1,.36,1)';
const rise = [{opacity:0,transform:'translateY(12px)'},{opacity:1,transform:'none'}];
function anim(el, keyframes, opts = {}) {
  if (reduced || !el?.animate) return null;
  return el.animate(keyframes, {duration:560, easing:EASE, fill:'backwards', ...opts});
}
function stagger(els, {delay = 0, step = 55, frames = rise, duration = 560, max = 24} = {}) {
  els.slice(0, max).forEach((el, i) => anim(el, frames, {delay: delay + i * step, duration}));
}
function countUp(root, delay = 0) {
  $$('[data-count]', root).forEach(el => {
    const to = +el.dataset.count, dec = Number.isInteger(to) ? 0 : 1;
    if (reduced) { el.textContent = to.toFixed(dec); return; }
    el.textContent = (0).toFixed(dec);
    const t0 = performance.now() + delay, dur = 1000;
    const tick = now => {
      const k = Math.max(0, Math.min(1, (now - t0) / dur)), e = 1 - Math.pow(1 - k, 3);
      el.textContent = (to * e).toFixed(dec);
      if (k < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}
function moveIndicator() {
  const active = $('.nav.active'), bar = $('.nav-indicator');
  if (!active || !bar) return;
  bar.style.width = active.offsetWidth + 'px';
  bar.style.height = active.offsetHeight + 'px';
  bar.style.transform = `translate(${active.offsetLeft}px,${active.offsetTop}px)`;
}
window.addEventListener('resize', moveIndicator);

function animateView(view) {
  if (!report) return;
  const root = $('#' + view);
  if (view === 'overview') { stagger($$('.case-button', root), {step:45}); animateCase(); }
  if (view === 'learning') {
    stagger($$('#curve .pt', root), {delay:250, step:220, frames:[{opacity:0,transform:'scale(0)'},{opacity:1,transform:'scale(1)'}], duration:420});
    stagger($$('#curve .value-label', root), {delay:380, step:220});
    $$('#curve .drop', root).forEach(el => anim(el, [{strokeDashoffset:120},{strokeDashoffset:0}], {delay:1250, duration:700}));
    $$('#curve .ghost', root).forEach(el => anim(el, [{opacity:0,transform:'translateY(-30px)'},{opacity:1,transform:'none'}], {delay:1700, duration:500, easing:'cubic-bezier(.5,1.6,.4,1)'}));
    anim($('.promotion-panel', root), rise, {delay:150});
    countUp($('#promotion-panel'), 200);
    stagger($$('.bar-fill', root), {delay:300, step:60, frames:[{transform:'scaleX(0)'},{transform:'scaleX(1)'}], duration:900});
    stagger($$('#version-table tbody tr', root), {delay:400, step:60});
  }
  if (view === 'audit') {
    $$('.exam-row', root).forEach((row, r) => {
      anim(row, rise, {delay:r * 250});
      stagger($$('.cell', row), {delay:300 + r * 450, step:70, frames:[{opacity:0,transform:'rotateY(90deg) scale(.6)'},{opacity:1,transform:'none'}], duration:450});
      countUp(row, 300 + r * 450);
    });
    stagger($$('#audit-table tbody tr', root), {delay:600, step:35});
  }
  if (view === 'evidence') {
    stagger($$('#provenance dt, #provenance dd', root), {step:30});
    stagger($$('.event', root), {delay:150, step:35, max:16});
  }
}
function animateCase() {
  const root = $('#case-detail');
  if (!root || reduced) return;
  anim($('.case-title', root), rise);
  const chips = $$('.verdict-strip span', root);
  anim(chips[0], rise, {delay:120});
  anim(chips[1], [{opacity:0,transform:'scale(1.5)'},{opacity:1,transform:'scale(1)'}], {delay:900 + 600 * Math.max(0, $$('.trace-step', root).length - 1), duration:380, easing:'cubic-bezier(.5,1.8,.4,1)'});
  $$('.trace-step', root).forEach((step, i) => {
    const at = 250 + i * 600;
    anim(step, [{opacity:0,transform:'translateX(-14px)'},{opacity:1,transform:'none'}], {delay:at});
    anim($('.exec', step), [{transform:'scaleX(0)'},{transform:'scaleX(1)'}], {delay:at + 150, duration:500, easing:'cubic-bezier(.65,0,.35,1)'});
    anim($('.trace-return', step), [{opacity:0},{opacity:1}], {delay:at + 550, duration:300});
    if (step.classList.contains('wrong')) {
      anim(step, [{transform:'none'},{transform:'translateX(-5px)'},{transform:'translateX(4px)'},{transform:'translateX(-2px)'},{transform:'none'}], {delay:at + 700, duration:380, easing:'ease-out', fill:'none'});
      $$('.bad-value', step).forEach(el => anim(el, [{background:'#171717',color:'#f7f7f7'},{background:'#e6e6e6',color:'#3d3d3d'}], {delay:at + 700, duration:1200, fill:'none'}));
    }
  });
  stagger($$('.diff span', root), {delay:500 + 600 * $$('.trace-step', root).length, step:70, frames:[{clipPath:'inset(0 100% 0 0)'},{clipPath:'inset(0 0 0 0)'}], duration:420});
}

/* ---------- navigation ---------- */
function showView(view) {
  if (!titles[view]) view = 'overview';
  currentView = view;
  $$('.view').forEach(el => el.classList.toggle('active', el.id === view));
  $$('.nav').forEach(el => el.classList.toggle('active', el.dataset.view === view));
  moveIndicator();
  $('#view-title').textContent = titles[view][0];
  $('#view-description').textContent = titles[view][1];
  anim($('#view-title'), [{opacity:0,transform:'translateY(8px)',filter:'blur(4px)'},{opacity:1,transform:'none',filter:'blur(0)'}], {duration:500});
  anim($('#view-description'), [{opacity:0},{opacity:1}], {delay:120, duration:500});
  if (location.hash !== '#view='+view) history.replaceState(null, '', '#view='+view);
  window.scrollTo({top:0,behavior:'instant'});
  if (view === 'learning' && report) renderLearning();
  animateView(view);
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

/* ---------- renderers ---------- */
function renderStats() {
  const before = report.audit_before, after = report.audit_after;
  const promoted = report.versions.filter(v => v.accepted && v.version > 0).length;
  const entries = [
    ['Final audit', `<span class="old">${before.detected}/${before.total}</span><span class="arrow">→</span><span data-count="${after.detected}">${after.detected}</span>/${after.total}`, 'Held-out code variants, same defect families'],
    ['Blind spots', `<span data-count="${report.counterexamples.length}">${report.counterexamples.length}</span>`, 'Faulty patches that pass the original suite'],
    ['False rejects', `<span data-count="${after.false_rejections}">${after.false_rejections}</span><span class="unit">/${after.controls}</span>`, 'Correct controls rejected'],
    ['Promoted', `<span data-count="${promoted}">${promoted}</span><span class="unit">/${report.versions.length-1}</span>`, `Active evaluation: v${report.active_version}`]
  ];
  $('#stats').innerHTML = entries.map(([name,value,note])=>`<div class="stat" title="${esc(note)}"><div class="stat-label">${name}</div><div class="stat-value">${value}</div></div>`).join('');
  if (!statsShown) { statsShown = true; stagger($$('.stat'), {step:80}); countUp($('#stats'), 150); }
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
    const differs = k => JSON.stringify(actual?.[k]) !== JSON.stringify(expected?.[k]);
    const tenant = actual?.tenant;
    const returned = tenant ? `tenant: <strong class="${wrong&&differs('tenant')?'bad-value':''}">${esc(tenant)}</strong>` : Object.entries(actual||{}).map(([k,v])=>`${esc(k)}: <strong class="${wrong&&differs(k)?'bad-value':''}">${esc(v)}</strong>`).join('<br>');
    const expectedKeys = Object.keys({...(expected||{}), ...(actual||{})}).filter(differs);
    const expectedText = expectedKeys.map(k => `${esc(k)}: ${esc(JSON.stringify(expected?.[k] ?? null))}`).join(' · ');
    return `<div class="trace-step ${wrong?'wrong':''}"><i class="exec"></i><div class="trace-label">REQ ${String(i+1).padStart(2,'0')} ${wrong?'<span>VIOLATION</span>':'<span class="ok">OK</span>'}</div><div class="trace-action">${esc(a.op).toUpperCase()}<br>tenant: <strong>${esc(a.tenant)}</strong><br>${a.key!==undefined?`key: <strong>${esc(a.key)}</strong><br>`:''}${a.qty!==undefined?`qty: ${esc(a.qty)} · ${esc(a.sku)}`:a.sku?`sku: ${esc(a.sku)}`:''}</div><div class="trace-return">↳ ${returned}${wrong?`<div class="expected">expected ${expectedText}</div>`:''}</div></div>`;
  }).join('');
  const diff=c.diff.split('\n').filter(line=>line.trim()&&!line.startsWith('@@')&&!line.startsWith('---')&&!line.startsWith('+++')).slice(0,8).map(line=>`<span class="${line.startsWith('+')?'added':line.startsWith('-')?'removed':'header'}">${esc(line)}</span>`).join('');
  $('#case-detail').innerHTML=`<div class="case-title"><h3>${esc(c.title)}</h3><div class="mono">${esc(c.origin).toUpperCase()}</div></div><div class="verdict-strip"><span>✓ EXISTING TESTS ${c.baseline_checks}/${c.baseline_checks}</span><span class="bad">× CONTRACT VIOLATED</span></div><div class="trace">${traces}</div><div class="code-label"><span>THE CHANGE</span><span>${w.actions.length}-STEP REPRO</span></div><pre class="diff">${diff}</pre>`;
  if (currentView === 'overview') animateCase();
}
function renderCases(){
  $('#case-list').innerHTML=report.counterexamples.map((c,i)=>`<button class="case-button ${i===selected?'active':''}" data-case="${i}"><div class="case-id"><span>${esc(c.id)} · ${esc(label(c.family).toUpperCase())}</span><em>FAIL</em></div><div class="case-name">${esc(c.title)}</div></button>`).join('');
  $$('.case-button').forEach(el=>el.onclick=()=>selectCase(+el.dataset.case));
  if(report.counterexamples.length)selectCase(selected);else $('#case-detail').innerHTML='<p class="empty">No proven blind spot in this run.</p>';
}

function curveSVG(){
  const versions=report.versions, W=650,H=270,L=43,R=26,T=27,B=42,iw=W-L-R,ih=H-T-B;
  const x=i=>L+i*iw/(versions.length-1), y=n=>T+(100-n)*ih/100;
  let active=versions[0].validation,points=[];
  versions.forEach((v,i)=>{if(v.accepted)active=v.validation;points.push([x(i),y(pct(active)),pct(active)]);});
  const grid=[0,25,50,75,100].map(n=>`<line x1="${L}" x2="${W-R}" y1="${y(n)}" y2="${y(n)}" stroke="#e1e1e1" stroke-dasharray="${n?'3 5':'0'}"/><text x="${L-12}" y="${y(n)+4}" text-anchor="end">${n}%</text>`).join('');
  const path=points.map((p,i)=>`${i?'L':'M'}${p[0]},${p[1]}`).join(' ');
  const fill=`${path} L${points.at(-1)[0]},${y(0)} L${L},${y(0)} Z`;
  const marks=points.map((p,i)=>`<circle class="pt" cx="${p[0]}" cy="${p[1]}" r="5" fill="#f7f7f7" stroke="#242424" stroke-width="2.5"><title>After v${i}: ${p[2]}%</title></circle><text class="value-label" x="${p[0]}" y="${p[1]-12}" text-anchor="middle">${p[2]}%</text><text x="${p[0]}" y="${H-17}" text-anchor="middle">v${i}${versions[i].accepted?'':' ×'}</text>`).join('');
  const rejected=versions.map((v,i)=>!v.accepted?`<line class="drop" x1="${x(i)}" x2="${x(i)}" y1="${points[i][1]+7}" y2="${y(pct(v.validation))-7}" stroke="#848484" stroke-dasharray="3 4"/><circle class="ghost" cx="${x(i)}" cy="${y(pct(v.validation))}" r="5" fill="#555555"><title>Rejected v${i}: ${pct(v.validation)}%</title></circle>`:'').join('');
  return `<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Validation detection across evaluation versions">${grid}<path class="curve-fill" d="${fill}" fill="#e0e0e0" opacity=".45"/><path class="curve-path" d="${path}" fill="none" stroke="#242424" stroke-width="3"/>${marks}${rejected}</svg>`;
}
function renderLearning(){
  $('#curve').innerHTML=curveSVG();
  const before=report.validation_before, after=report.validation_after;
  const rejected=report.versions.filter(v=>!v.accepted);
  $('#promotion-panel').innerHTML=`<div class="eyebrow">VALIDATION</div><div class="big"><span data-count="${pct(after)}">${pct(after)}</span><small>%</small></div><p>${after.detected}/${after.total} defects caught<br>${after.false_rejections}/${after.controls} false rejects</p>${rejected.length?`<div class="rollback"><strong>↶ ${rejected.map(v=>'v'+v.version).join(', ')} rejected</strong><br>v${report.active_version} stays active.</div>`:''}`;
  const families=[...new Set(after.rows.filter(r=>!r.correct).map(r=>r.family))];
  $('#family-chart').innerHTML=families.map(f=>{
    const b=before.rows.filter(r=>r.family===f),a=after.rows.filter(r=>r.family===f),bn=b.filter(r=>r.detected).length,an=a.filter(r=>r.detected).length;
    return `<div class="bar-row"><span>${esc(label(f))}</span><div class="bar-track"><div class="bar-new bar-fill" style="width:${an/a.length*100}%"></div><div class="bar-old" style="width:${bn/b.length*100}%"></div></div><span class="bar-number">${bn} → ${an}/${a.length}</span></div>`;
  }).join('');
  const max=Math.max(...report.versions.map(v=>v.suite.length));
  $('#cost-chart').innerHTML=report.versions.map(v=>`<div class="bar-row"><span>v${v.version} · ${v.suite.length}</span><div class="bar-track"><div class="bar-new bar-fill ${v.accepted?'':'reject'}" style="width:${v.suite.length/max*100}%"></div></div><span class="bar-number">${v.validation.seconds.toFixed(2)}s</span></div>`).join('');
  $('#version-table').innerHTML=`<div class="table-scroll"><table class="data-table"><thead><tr><th>Version</th><th>Proposal</th><th>Detection</th><th>False rejects</th><th>Decision</th><th>Suite</th></tr></thead><tbody>${report.versions.map(v=>`<tr><td class="mono">v${v.version}</td><td title="${esc(v.origin)}">${esc(v.rationale)}</td><td>${v.validation.detected}/${v.validation.total}</td><td>${v.validation.false_rejections}/${v.validation.controls}</td><td><span class="status ${v.accepted?'accepted':'rejected'}">${v.version===0?'BASELINE':v.accepted?'↑ PROMOTED':'↶ REJECTED'}</span></td><td class="mono" title="${esc(v.suite_sha256)}">${v.suite_sha256.slice(0,10)}</td></tr>`).join('')}</tbody></table></div>`;
}
function verdict(row){return row.correct?(row.detected?'FALSE REJECTION':'ACCEPTED'):(row.detected?'CAUGHT':'MISSED')}
function good(row){return row.correct?!row.detected:row.detected}
function renderAudit(){
  const b=report.audit_before,a=report.audit_after;
  const row=(name,score,cls)=>{const defects=score.rows.filter(r=>!r.correct),controls=score.rows.filter(r=>r.correct);
    return `<div class="exam-row ${cls}"><span class="mono">${name}</span><div class="cells">${defects.map(r=>`<i class="cell ${r.detected?'hit':'miss'}" title="${esc(r.id)} · ${esc(r.title)} · ${r.detected?'caught':'missed'}"></i>`).join('')}<b class="sep"></b>${controls.map(r=>`<i class="cell ctrl ${r.detected?'miss':'hit'}" title="${esc(r.id)} · ${esc(r.title)} · ${verdict(r).toLowerCase()}"></i>`).join('')}</div><div class="num"><span data-count="${score.detected}">${score.detected}</span><small>/${score.total}</small></div></div>`};
  $('#audit-visual').innerHTML=`<div class="exam-legend mono"><span><i class="cell hit"></i>caught</span><span><i class="cell miss"></i>missed</span><span><i class="cell ctrl hit"></i>control accepted</span></div>${row('ORIGINAL',b,'before')}${row('PROMOTED',a,'after')}`;
  $('#audit-table').innerHTML=`<div class="table-scroll"><table class="data-table"><thead><tr><th>Variant</th><th>Behavior</th><th>Original</th><th>Promoted</th></tr></thead><tbody>${a.rows.map(r=>{const old=b.rows.find(x=>x.id===r.id);return `<tr><td class="mono" title="${r.correct?'Correct implementation control':esc(label(r.family))}">${esc(r.id)}</td><td>${esc(r.title)}</td><td><span class="status ${good(old)?'accepted':'rejected'}">${verdict(old)}</span></td><td><span class="status ${good(r)?'accepted':'rejected'}">${verdict(r)}</span></td></tr>`}).join('')}</tbody></table></div>`;
  $('#limitations').innerHTML=report.limitations.map(l=>`<p>${esc(l)}</p>`).join('');
}
function renderEvidence(){
  const m=report.manifest;
  const entries=[['MODE',m.mode],['RUNTIME',m.runtime],['STARTED',m.created_at],['COMMIT',m.commit],['CONTRACT SHA-256',m.contract_sha256],['BENCHMARK SHA-256',m.corpus_sha256],['EVENT ROOT',report.event_root_sha256]];
  $('#provenance').innerHTML=entries.map(([k,v])=>`<dt>${k}</dt><dd class="${/SHA|ROOT|COMMIT/.test(k)?'hash':''}">${esc(v)}</dd>`).join('');
  $('#partner-calls').innerHTML=report.provider_calls.length?report.provider_calls.map(c=>`<div class="partner-row">${esc(c.provider==='meta'?'Meta':'Subquadratic')} · ${esc(c.purpose)}<div class="mono">${esc(c.model)} · ${esc(c.status)} · ${c.seconds}s · ${c.usage.input_tokens??c.usage.prompt_tokens??'—'} in</div></div>`).join(''):'<p class="empty">None — local fixture run.</p>';
  $('#event-count').textContent=`${report.events.length} EVENTS`;
  $('#journal').innerHTML=report.events.map(e=>`<div class="event"><span>${String(e.sequence).padStart(2,'0')}</span><div><strong>${esc(label(e.kind))}</strong><p>${esc(e.message)}</p></div></div>`).join('');
}
function render(){
  if(!report)return;
  const mode=report.manifest.mode;
  const modeLabel=mode==='live partners'?'Live partners':mode.startsWith('live Subquadratic')?'SubQ + fixtures':'Local fixtures';
  $('#mode').textContent=`${local?'Saved':'Recorded'} · ${modeLabel}`;
  $('#footer-mode').textContent=`${modeLabel} · ${report.elapsed_seconds}s · synthetic benchmark`;
  renderStats();renderCases();renderLearning();renderAudit();renderEvidence();
  if(!local){$('#run').innerHTML='Run locally <span>↗</span>';$('#run').onclick=()=>window.open('https://github.com/KaushikSiva/crossexam#quick-start','_blank','noopener');}
  animateView(currentView);
}
async function poll(){
  if(replaying)return;
  try{
    const response=await fetch('api/state');if(!response.ok)throw Error('Static report');
    const state=await response.json();local=true;providers=state.providers;
    const wasBusy=busy;busy=state.busy;
    $('#progress').hidden=!busy;
    $('#run').disabled=busy;$('#replay').disabled=busy;
    if(busy){const e=state.events.at(-1);$('#progress-text').textContent=e?.message||'Probing sandbox isolation…';$('#progress-count').textContent=`${state.events.length} EVENTS`;$('#mode').textContent='Running';}
    if(state.report&&(!report||state.report.event_root_sha256!==report.event_root_sha256)){report=state.report;statsShown=false;render();}
    if(wasBusy&&!busy){if(state.error){$('#notice').hidden=false;$('#notice').textContent=state.error;}else{render();toast('Campaign complete.');}}
    if(!report&&!busy){$('#notice').hidden=false;$('#notice').textContent='Start a campaign to populate the workspace.';}
  }catch(error){
    if(!report){try{const response=await fetch('report.json');if(!response.ok)throw Error('No report');report=await response.json();render();}catch{$('#notice').hidden=false;$('#notice').textContent='No saved report. Run python3 -m crossexam run, then start the server.';}}
  }
}
$('#run').onclick=()=>{
  $('#key-status').textContent=`META ${providers.meta?'✓':'MISSING'} · SUBQUADRATIC ${providers.subquadratic?'✓':'MISSING'}`;
  $('#start-live').disabled=!providers.meta||!providers.subquadratic;
  $('#start-subq').disabled=!providers.subquadratic;
  $('#run-dialog').showModal();
  stagger($$('#run-dialog .run-option'), {delay:80, step:70});
};
async function start(mode){
  $('#run-dialog').close();$('#notice').hidden=true;
  try{const r=await fetch('api/run',{method:'POST',headers:{'Content-Type':'application/json','X-CrossExam':'local-workspace'},body:JSON.stringify({mode})});const result=await r.json();if(!r.ok)throw Error(result.error);busy=true;$('#progress').hidden=false;$('#progress-text').textContent='Probing sandbox isolation…';await poll();}catch(e){toast(e.message);}
}
$('#start-local').onclick=()=>start('local');$('#start-subq').onclick=()=>start('subq');$('#start-live').onclick=()=>start('live');
$('#replay').onclick=async()=>{
  if(!report||replaying)return;
  replaying=true;$('#replay').disabled=true;$('#run').disabled=true;
  $('#notice').hidden=false;$('#notice').textContent='Playback of saved results — not a new run.';
  const steps=[['overview',0,'Tests pass. The contract check fails.'],['overview',1,'Retries silently consume stock.'],['learning',null,'Validation decides what gets promoted.'],['learning',null,'A cheaper regression is rejected.'],['audit',null,'Then the final audit opens.'],['evidence',null,'Every decision is hashed and journaled.']];
  for(const [view,index,message]of steps){showView(view);if(index!==null)selectCase(index);toast(message);await new Promise(resolve=>setTimeout(resolve,4500));}
  replaying=false;$('#replay').disabled=false;$('#run').disabled=false;$('#notice').hidden=true;
};
window.CrossExam={showView,selectCase,getReport:()=>report};
showView(location.hash.slice(1).replace('view=','')||'overview');poll();setInterval(()=>{if(local)poll()},1200);
