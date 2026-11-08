import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';

const config=JSON.parse(await fs.readFile('recordings/timing.json','utf8'));
if(config.durations.length!==7)throw Error('Expected seven scenes, including the Muse architecture.');
await fs.mkdir('recordings/raw',{recursive:true});
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:1600,height:900},deviceScaleFactor:1,recordVideo:{dir:'recordings/raw',size:{width:1600,height:900}}});
const page=await context.newPage();
const banner=await fs.readFile('docs/assets/banner.svg','utf8');
const title=`<!doctype html><html><body style="margin:0;background:#111;display:flex;align-items:center;justify-content:center;height:100vh">${banner.replace('height="800"','height="800" style="width:100%;height:auto"')}</body></html>`;
const site=process.env.CROSSEXAM_SITE_URL||'http://127.0.0.1:5179/';
await page.goto(site,{waitUntil:'networkidle'});
await page.waitForSelector('.verification-scene.is-ready');
await page.addStyleTag({content:'html{scroll-behavior:auto!important}[aria-label="Open OpenUI Inspect"]{display:none!important}'});
// Preload the real evidence viewer from the same immutable report as the landing.
await page.evaluate(src=>{
  const frame=document.createElement('iframe');frame.id='recording-workspace';frame.src=src;
  frame.style.cssText='position:fixed;inset:0;width:100%;height:100%;border:0;z-index:10000;visibility:hidden';
  document.body.append(frame);
},new URL('lab/index.html',site).href);
const frame=await (await page.$('#recording-workspace')).contentFrame();
await frame.waitForSelector('.case-button',{state:'attached'});
await frame.waitForFunction(()=>Boolean(window.CrossExam?.getReport()));
await frame.evaluate(()=>{document.body.classList.add('recording');const r=window.CrossExam.getReport();const generated=r.counterexamples.findIndex(c=>c.id==='M01');window.CrossExam.selectCase(generated>=0?generated:0);});
await page.waitForTimeout(1200);
// A unique synchronization frame is removed from the final film by mux_demo.py.
// It gives the capture an actual visual time origin, independent of encoder flush.
await page.evaluate(()=>{const marker=document.createElement('div');marker.id='capture-sync';marker.style.cssText='position:fixed;inset:0;background:rgb(17,251,34);z-index:99999';document.body.append(marker)});
await page.waitForTimeout(600);
await page.evaluate(()=>document.querySelector('#capture-sync').remove());
const started=Date.now();let deadline=0;
async function hold(duration){deadline+=duration*1000;await page.waitForTimeout(Math.max(0,started+deadline-Date.now()));}
async function workspace(visible){await page.evaluate(v=>document.querySelector('#recording-workspace').style.visibility=v?'visible':'hidden',visible)}
async function section(id){await page.locator(id).evaluate(e=>window.scrollTo(0,e.getBoundingClientRect().top+window.scrollY))}
await hold(config.durations[0]);
await workspace(true);
await hold(config.durations[1]);
await section('#architecture');await workspace(false);
await hold(config.durations[2]);
await section('#improvement');await workspace(false);
await hold(config.durations[3]*.65);
await page.locator('.version-selector button').last().click();
await hold(config.durations[3]*.35);
await frame.evaluate(()=>window.CrossExam.showView('audit'));await workspace(true);
await hold(config.durations[4]);
await section('#agent-service');await workspace(false);
await page.getByRole('button',{name:'Faulty generated patch',exact:true}).click();
await hold(config.durations[5]*.6);
await page.getByRole('button',{name:'Correct implementation',exact:true}).click();
await hold(config.durations[5]*.4);
await page.setContent(title);await hold(config.durations[6]+1);
const contentDuration=(Date.now()-started)/1000;
const video=page.video();await context.close();
await video.saveAs('recordings/raw/crossexam-capture.webm');
await fs.writeFile('recordings/capture-timing.json',JSON.stringify({contentDuration,syncMarker:true,sceneDurations:config.durations,
  timingSha256:createHash('sha256').update(await fs.readFile('recordings/timing.json')).digest('hex'),
  captureSha256:createHash('sha256').update(await fs.readFile('recordings/raw/crossexam-capture.webm')).digest('hex')},null,2));
await browser.close();
console.log('Recorded synchronized browser scenes to recordings/raw/crossexam-capture.webm');
