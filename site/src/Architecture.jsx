import React from 'react';
import {motion,useReducedMotion} from 'motion/react';

export default function Architecture({report}){
  const reduced=useReducedMotion();
  const generator=report?.manifest.proposal_protocol.generator;
  const names={fetchai:'Fetch.ai ASI:One',meta:'Meta Muse Spark',openai:'OpenAI',gemini:'Gemini'};
  return <section className="architecture-section" id="architecture"><div className="section-shell">
    <span className="micro">ARCHITECTURE / MUSE AT THE CORE</span>
    <div className="architecture-heading"><h2>Models propose.<br/>Execution decides.</h2><p>Independent roles, connected by reproducible evidence.</p></div>
    <div className="architecture-flow">
      <motion.div className="architecture-primary" initial={reduced?false:{opacity:0,y:20}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{duration:.6}}>
        <span className="micro">01 / PRIMARY CODE-GENERATION INTEGRATION</span><h3>Meta<br/><strong>Muse Spark</strong></h3><p>Propose adversarial implementations.<br/>Challenge what passing tests really prove.</p><span className="architecture-status">Adapter implemented · API access currently returns HTTP 402</span>
      </motion.div>
      <div className="architecture-support">{[
        ['02','Google DeepMind / Gemini','Independent test author','Contract + counterexamples. Candidate code withheld.'],
        ['03','Fetch.ai / uAgents','Callable verification','Execute a patch. Return a signed, verifiable verdict.'],
        ['04','MongoDB','Evidence and frozen suites','Hash-verified artifacts, suite versions and receipts.']
      ].map(([n,provider,role,detail],i)=><motion.div key={n} className="architecture-role" initial={reduced?false:{opacity:0,x:15}} whileInView={{opacity:1,x:0}} viewport={{once:true}} transition={{duration:.5,delay:i*.1}}><span className="micro">{n}</span><div><span className="micro">{role}</span><h3>{provider}</h3><p>{detail}</p></div></motion.div>)}</div>
    </div>
    <div className="architecture-foundation"><span><strong>Subquadratic</strong> prioritizes risks</span><span><strong>OS sandbox + independent oracle</strong> judge behavior</span><span><strong>OpenUI</strong> exposes the evidence</span></div>
    <p className="architecture-run">Recorded campaign: {names[generator]||'loading'} generated the patch; {generator==='meta'?'Muse access verified in this run.':'Muse remains the primary architecture integration, pending API credits.'} <a href="#integrations">Inspect actual provider calls ↗</a></p>
  </div></section>;
}
