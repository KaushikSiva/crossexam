import React from 'react';
import {motion,useReducedMotion} from 'motion/react';
import VerificationScene from './VerificationScene.jsx';
import './hero.css';

// Visual thesis: a quiet monochrome studio, precise type and one silver gate.
// Content: name → the evaluation problem → enter the existing lab or watch.
// Motion: staggered type, pointer-responsive depth, restrained button feedback.
export default function Hero({onWatch}){
  const reduced=useReducedMotion();
  const entrance=(delay=0)=>({initial:reduced?false:{opacity:0,y:18},animate:{opacity:1,y:0},transition:{duration:.8,delay,ease:[.22,1,.36,1]}});
  return <div className="hero-shell hero-v2">
    <header className="hero-nav">
      <a className="hero-brand" href="#top" aria-label="CrossExam home"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M7 7l18 18M25 7L7 25" stroke="currentColor" strokeWidth="5"/><circle cx="16" cy="16" r="3" fill="#080808"/></svg>CrossExam</a>
      <nav aria-label="Main navigation"><a href="#how">How it works</a><a href="#improvement">Self-improvement</a><a href="#evidence">Evidence</a></nav>
      <a className="hero-source" href="https://github.com/KaushikSiva/crossexam" target="_blank" rel="noreferrer">GitHub <span aria-hidden="true">↗</span></a>
    </header>
    <section className="hero-stage" id="top" aria-labelledby="hero-title">
      <div className="hero-intro">
        <motion.div className="hero-eyebrow" {...entrance(.05)}><span aria-hidden="true"/>INDEPENDENT CODE VERIFICATION</motion.div>
        <motion.h1 id="hero-title" {...entrance(.12)}>CrossExam<span>.</span></motion.h1>
      </div>
      <VerificationScene/>
      <div className="hero-message">
        <motion.h2 {...entrance(.23)}>The code passed.<br/><span>Did the tests?</span></motion.h2>
        <motion.p {...entrance(.31)}>Find the bugs your tests accept.<br/>Make every improvement prove itself.</motion.p>
        <motion.div className="hero-actions" {...entrance(.39)}>
          <a className="hero-enter" href="./lab/">Open evaluation lab <span aria-hidden="true">↗</span></a>
          <button className="film-button hero-watch" onClick={onWatch} aria-label="Watch the one-minute film"><svg viewBox="0 0 28 28" aria-hidden="true"><circle cx="14" cy="14" r="13"/><path d="m11 9 8 5-8 5Z"/></svg>Watch the demo</button>
        </motion.div>
      </div>
      <div className="hero-foot"><span>OPEN SOURCE. EXECUTABLE EVIDENCE.</span><a href="#how">Explore the proof <span aria-hidden="true">↓</span></a></div>
    </section>
  </div>;
}
