import React, {createContext, useContext, useMemo, useState} from 'react';
import {defineComponent, createLibrary, Renderer, createParser} from '@openuidev/react-lang';
import {z} from 'zod/v4';

const EvidenceContext=createContext(null);
const Heading=defineComponent({name:'BriefHeading',description:'A heading selected from the report-backed evidence views.',props:z.object({kind:z.enum(['learning','audit','failure'])}),component:({props})=>{
  const labels={learning:['The evaluation learns.','Validation decides which proposal earns promotion.'],audit:['The final exam.','Different code variants, opened after learning stops.'],failure:['Two requests. One broken boundary.','A reproducible tenant-isolation counterexample.']};
  return <div className="brief-heading"><span className="micro">RECORDED EVIDENCE</span><h3>{labels[props.kind][0]}</h3><p>{labels[props.kind][1]}</p></div>;
}});
const Metric=defineComponent({name:'MeasuredMetric',description:'A metric loaded directly from the signed-off report. Never accept a model-supplied numerical value.',props:z.object({kind:z.enum(['audit','controls','promotions','validation'])}),component:({props})=>{
  const r=useContext(EvidenceContext);const metrics={audit:['Final audit',`${r.audit_before.detected}/${r.audit_before.total} → ${r.audit_after.detected}/${r.audit_after.total}`],controls:['Correct controls rejected',`${r.audit_after.false_rejections}/${r.audit_after.controls}`],promotions:['Improvements promoted',String(r.versions.filter(v=>v.accepted&&v.version>0).length)],validation:['Validation detection',`${r.validation_after.detected}/${r.validation_after.total}`]};
  return <div className="brief-metric"><span>{metrics[props.kind][0]}</span><strong>{metrics[props.kind][1]}</strong></div>;
}});
const Curve=defineComponent({name:'MeasuredCurve',description:'The measured validation curve, including rejected proposals.',props:z.object({dataset:z.literal('validation')}),component:()=>{
  const r=useContext(EvidenceContext);let active=r.versions[0].validation;
  const points=r.versions.map((v,i)=>{if(v.accepted)active=v.validation;return[35+i*520/(r.versions.length-1),195-160*active.detected/active.total,active.detected,active.total]});
  return <div className="brief-curve"><svg viewBox="0 0 600 240" role="img" aria-label="Measured validation improvement"><path d="M35 35H565M35 115H565M35 195H565" stroke="#d9ded0" strokeDasharray="4 6"/><polyline points={points.map(p=>p.slice(0,2).join(',')).join(' ')} fill="none" stroke="#5f7e30" strokeWidth="3"/>{points.map((p,i)=><g key={i}><circle cx={p[0]} cy={p[1]} r="5" fill="#f7f8f0" stroke="#5f7e30" strokeWidth="2"/><text x={p[0]} y={p[1]-14} textAnchor="middle">{p[2]}/{p[3]}</text><text x={p[0]} y="225" textAnchor="middle">v{i}{r.versions[i].accepted?'':' ×'}</text></g>)}</svg><span className="micro">VALIDATION SET · ACTIVE SUITE RETAINED AFTER REJECTION</span></div>;
}});
const Audit=defineComponent({name:'AuditResults',description:'Every final audit result, including misses and correct controls, from the saved report.',props:z.object({show:z.enum(['defects','controls'])}),component:({props})=>{
  const r=useContext(EvidenceContext);const rows=r.audit_after.rows.filter(row=>props.show==='controls'?row.correct:!row.correct);
  return <div className="brief-audit">{rows.map(row=><div key={row.id}><span className="micro">{row.id}</span><span>{row.title}</span><strong className={row.correct?!row.detected?'ok':'bad':row.detected?'ok':'bad'}>{row.correct?row.detected?'FALSE REJECTION':'ACCEPTED':row.detected?'CAUGHT':'MISSED'}</strong></div>)}</div>;
}});
const Finding=defineComponent({name:'Counterexample',description:'Render an existing counterexample by its report ID. Unknown IDs produce no invented evidence.',props:z.object({id:z.string()}),component:({props})=>{
  const r=useContext(EvidenceContext);const c=r.counterexamples.find(c=>c.id===props.id);if(!c)return <p>Counterexample not present in this run.</p>;
  return <div className="brief-finding"><div className="brief-verdict"><span>EXISTING SUITE {c.baseline_checks}/{c.baseline_checks} PASS</span><strong>CONTRACT FAIL</strong></div><pre>{JSON.stringify(c.witness.actions,null,2)}</pre><p>Actual second tenant: <strong>{c.witness.actual.at(-1)?.tenant}</strong> · Expected: <strong>{c.witness.expected.at(-1)?.tenant}</strong></p></div>;
}});
const Note=defineComponent({name:'EvidenceNote',description:'A fixed methodology note; explanatory copy cannot invent metrics.',props:z.object({kind:z.enum(['scope','promotion','independence'])}),component:({props})=>{
  const text={scope:'Small synthetic benchmark. Held-out implementations share defect families with discovery. These are not real-world accuracy estimates.',promotion:'A proposal must catch more validation defects, preserve existing coverage, and reject no correct controls. The final audit is excluded from learning.',independence:'The test author sees the contract and observed failures, but not the implementation or attacker transcript. A separate executable oracle supplies expected outcomes.'};
  return <p className="brief-note">{text[props.kind]}</p>;
}});
const Panel=defineComponent({name:'EvidencePanel',description:'Compose an evidence brief using registered, report-bound components.',props:z.object({children:z.array(z.union([Heading.ref,Metric.ref,Curve.ref,Audit.ref,Finding.ref,Note.ref]))}),component:({props,renderNode})=><div className="openui-brief">{renderNode(props.children)}</div>});
export const library=createLibrary({id:'crossexam-evidence',root:'EvidencePanel',components:[Panel,Heading,Metric,Curve,Audit,Finding,Note]});
const programs={
 learning:'root = EvidencePanel([heading, score, controls, curve, note])\nheading = BriefHeading("learning")\nscore = MeasuredMetric("validation")\ncontrols = MeasuredMetric("controls")\ncurve = MeasuredCurve("validation")\nnote = EvidenceNote("promotion")',
 audit:'root = EvidencePanel([heading, score, controls, results, note])\nheading = BriefHeading("audit")\nscore = MeasuredMetric("audit")\ncontrols = MeasuredMetric("controls")\nresults = AuditResults("defects")\nnote = EvidenceNote("scope")',
 failure:'root = EvidencePanel([heading, finding, note])\nheading = BriefHeading("failure")\nfinding = Counterexample("D01")\nnote = EvidenceNote("independence")'
};

export default function EvidenceUI({report}){
  const[view,setView]=useState('learning'),[source,setSource]=useState(false);
  const program=programs[view];
  const valid=useMemo(()=>{const p=createParser(library.toJSONSchema(),library.root).parse(program);return !p.meta.errors.length&&!p.meta.unresolved.length&&!p.meta.incomplete},[program]);
  return <div className="evidence-composer"><aside><span className="micro">CHOOSE YOUR QUESTION</span>{[['learning','Did it actually improve?'],['audit','Does it generalize?'],['failure','Show me the failure.']].map(([id,title],i)=><button key={id} className={view===id?'selected':''} onClick={()=>setView(id)}><span>0{i+1}</span>{title}<i>↗</i></button>)}<div className="openui-mark"><span>Rendered with</span><a href="https://github.com/thesysdev/openui" target="_blank" rel="noreferrer">OpenUI ↗</a><p>Registered components read numbers directly from the report. This is a saved evidence brief, not a new model call.</p></div><button className="source-toggle" onClick={()=>setSource(!source)}>{source?'Hide':'View'} OpenUI program <span>{source?'−':'+'}</span></button></aside><div className="evidence-output" key={view}>{valid?<EvidenceContext.Provider value={report}><Renderer response={program} library={library} isStreaming={false} publishObservability={false}/></EvidenceContext.Provider>:<p>Could not validate the evidence program.</p>}{source&&<pre className="program-source">{program}</pre>}</div></div>;
}
