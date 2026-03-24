import { useState } from "react";

// ═══════════════════════════════════════
// SHARED COMPONENTS
// ═══════════════════════════════════════
function DT({h,r,hl,c}){return<div style={{overflowX:"auto",marginBottom:12}}><table style={{width:"100%",borderCollapse:"collapse",fontSize:c?10.5:11.5}}><thead><tr>{h.map((x,i)=><th key={i} style={{textAlign:i===0?"left":"right",padding:c?"5px 6px":"7px 8px",borderBottom:"2px solid #ddd",color:"#555",fontWeight:600,fontSize:c?9.5:10.5,whiteSpace:"nowrap"}}>{x}</th>)}</tr></thead><tbody>{r.map((row,ri)=><tr key={ri} style={{background:hl!==undefined&&ri===hl?"rgba(99,153,34,0.08)":ri%2===0?"#fafaf8":"transparent"}}>{row.map((cell,ci)=><td key={ci} style={{padding:c?"4px 6px":"6px 8px",borderBottom:"1px solid #eee",textAlign:ci===0?"left":"right",fontFamily:ci>0?"monospace":"inherit",fontWeight:ci===0?500:400,whiteSpace:"nowrap"}}>{cell}</td>)}</tr>)}</tbody></table></div>}
function Sec({title,children}){return<div style={{marginBottom:36}}><h2 style={{fontSize:18,fontWeight:600,color:"#1B2A3E",margin:"0 0 12px",paddingBottom:6,borderBottom:"2px solid #1B2A3E"}}>{title}</h2>{children}</div>}
function Sub({title,children}){return<div style={{marginBottom:16}}><h3 style={{fontSize:14,fontWeight:600,color:"#333",margin:"0 0 8px"}}>{title}</h3>{children}</div>}
function P({children,style}){return<p style={{fontSize:13,color:"#444",lineHeight:1.7,marginBottom:10,...style}}>{children}</p>}
function W({children}){return<div style={{display:"flex",gap:6,padding:"8px 12px",background:"#FFF8E1",borderRadius:8,marginBottom:6,fontSize:12,lineHeight:1.5,borderLeft:"3px solid #EF9F27"}}><span style={{fontWeight:700,color:"#B85C00",flexShrink:0}}>⚠</span><span style={{color:"#6B5300"}}>{children}</span></div>}
function F({title,children}){return<div style={{padding:"10px 14px",background:"#f0f7e8",borderRadius:8,borderLeft:"3px solid #639922",marginBottom:10,fontSize:12,lineHeight:1.6}}><strong style={{color:"#3B6D11"}}>{title}</strong><br/>{children}</div>}
function Chip({l,v}){return<span style={{display:"inline-flex",alignItems:"center",gap:4,fontSize:11,padding:"3px 8px",borderRadius:6,background:"#f3f3f0",marginRight:4,marginBottom:4}}><span style={{color:"#777"}}>{l}</span><span style={{fontWeight:600,fontFamily:"monospace"}}>{v}</span></span>}

// ═══════════════════════════════════════
// CAPABILITY ZONES (full interactive)
// ═══════════════════════════════════════
const CZ=[{id:"green",num:"ZONE 1",t:"SLM-safe",co:"#639922",bg:"#EAF3DE",bc:"#3B6D11",desc:"SLM ≤3B matches or exceeds LLM. No fallback.",dims:[{n:"Reasoning depth",r:"Single-hop, pattern matching.",s:"≤ 3",p:30},{n:"Knowledge demand",r:"Narrow, all in-context.",s:"≤ 2",p:20},{n:"Context length",r:"Short ≤2K tokens.",s:"≤ 2",p:20},{n:"Conv. coherence",r:"Stateless, single-turn.",s:"≤ 1",p:10},{n:"Calibration",r:"Binary/categorical output.",s:"≤ 2",p:20},{n:"Output structure",r:"Fixed schemas.",s:"≤ 3",p:30}],ops:["Latency ≤50ms p95","Cost ≤$0.01/1K","Single GPU/CPU/mobile","Full data locality","Delta vs LLM ≤2%"]},{id:"amber",num:"ZONE 2",t:"Conditional SLM",co:"#BA7517",bg:"#FAEEDA",bc:"#854F0B",desc:"SLMs succeed with RAG, constrained decoding, CoT distillation, fine-tuning.",dims:[{n:"Reasoning depth",r:"2–3 hop with CoT scaffolding.",s:"≤ 5",p:50},{n:"Knowledge demand",r:"RAG-augmented, decomposable.",s:"≤ 5",p:50},{n:"Context length",r:"2K–8K, chunked viable.",s:"≤ 4",p:40},{n:"Conv. coherence",r:"2–4 turn, explicit state.",s:"≤ 4",p:40},{n:"Calibration",r:"Softmax + temperature.",s:"≤ 4",p:40},{n:"Output structure",r:"Semi-structured, grammar-guided.",s:"≤ 5",p:50}],ops:["Latency ≤200ms p95","Cost ≤$0.10/1K","A10/T4 + vector DB","Delta ≤5% with mitigations","Auto LLM fallback"]},{id:"red",num:"ZONE 3",t:"LLM-required",co:"#A32D2D",bg:"#FCEBEB",bc:"#791F1F",desc:"SLM structurally insufficient. Emergent capability gap.",dims:[{n:"Reasoning depth",r:"Multi-step planning, counterfactuals.",s:"≥ 6",p:100},{n:"Knowledge demand",r:"Open-domain, cross-domain synthesis.",s:"≥ 6",p:100},{n:"Context length",r:"Full-document >8K, cross-doc.",s:"≥ 5",p:100},{n:"Conv. coherence",r:"5+ turn, implicit coreference.",s:"≥ 5",p:100},{n:"Calibration",r:"Reliable uncertainty quantification.",s:"≥ 5",p:100},{n:"Output structure",r:"Unconstrained long-form, complex code.",s:"≥ 6",p:100}],ops:["Latency ≤2s","Cost ≤$5/1K","Multi-GPU / frontier API","Zero hallucination tolerance","Delta >10% unrecoverable"]},{id:"purple",num:"ZONE 4",t:"Hybrid routing",co:"#534AB7",bg:"#EEEDFE",bc:"#3C3489",desc:"Mixed subtasks: SLM high-volume simple, LLM escalated complex.",dims:[{n:"Reasoning depth",r:"SLM ≤3, LLM escalation on multi-hop.",s:"1–7",p:70},{n:"Knowledge demand",r:"SLM: in-domain+RAG. LLM: cross-domain.",s:"1–7",p:70},{n:"Context length",r:"SLM: ≤4K chunked. LLM: cross-chunk.",s:"1–8",p:80},{n:"Conv. coherence",r:"SLM: turns 1–3. LLM: implicit ref.",s:"1–7",p:70},{n:"Calibration",r:"SLM: softmax. LLM: entropy routing.",s:"1–7",p:70},{n:"Output structure",r:"SLM: constrained. LLM: free-form.",s:"1–8",p:80}],ops:["Routing ≤15ms","SLM:LLM 70:30–85:15","Blended ≤$0.50/1K","Router ≥90% accuracy","Graceful degradation"]}];

function CapZones(){const[v,setV]=useState("all");return<div>
<div style={{padding:"12px 14px",background:"#f5f5f2",borderRadius:8,marginBottom:14,fontSize:12,color:"#555",lineHeight:1.6}}><strong>Capability axis (1–10):</strong> Six failure-mode dimensions. Zone boundaries at non-linear SLM degradation thresholds.</div>
<div style={{display:"flex",gap:4,flexWrap:"wrap",marginBottom:14}}>{["all","green","amber","red","purple"].map(x=><button key={x} onClick={()=>setV(x)} style={{fontSize:11,padding:"5px 12px",borderRadius:6,background:v===x?"#fff":"#f0f0ec",color:v===x?"#1a1a1a":"#888",border:v===x?"1px solid #ccc":"1px solid transparent",cursor:"pointer",fontWeight:v===x?600:400}}>{x==="all"?"All":CZ.find(z=>z.id===x)?.t}</button>)}</div>
{CZ.filter(z=>v==="all"||z.id===v).map(z=><div key={z.id} style={{border:"1px solid #e0e0e0",borderRadius:10,marginBottom:16,overflow:"hidden"}}>
<div style={{padding:"12px 16px",borderBottom:`2px solid ${z.co}`,display:"flex",alignItems:"center",gap:10}}><span style={{fontSize:11,fontWeight:600,padding:"3px 10px",borderRadius:6,background:z.bg,color:z.bc}}>{z.num}</span><span style={{fontSize:15,fontWeight:600}}>{z.t}</span></div>
<div style={{padding:"12px 16px"}}><p style={{fontSize:12,color:"#666",lineHeight:1.6,marginBottom:12}}>{z.desc}</p>
<div style={{fontSize:11,fontWeight:600,color:"#888",textTransform:"uppercase",letterSpacing:0.4,marginBottom:8,paddingBottom:4,borderBottom:"1px solid #eee"}}>Capability limits</div>
{z.dims.map((d,i)=><div key={i} style={{display:"grid",gridTemplateColumns:"120px 1fr 70px",gap:8,padding:"6px 0",borderBottom:"1px solid #f0f0ec",fontSize:12}}>
<div style={{fontWeight:600}}>{d.n}</div><div style={{color:"#666",lineHeight:1.4}}>{d.r}<div style={{height:3,background:"#eee",borderRadius:2,marginTop:4}}><div style={{height:3,borderRadius:2,background:z.co,width:`${d.p}%`}}/></div></div><div style={{fontFamily:"monospace",fontSize:11,color:"#888",textAlign:"right"}}>{d.s}/10</div></div>)}
<div style={{marginTop:12,padding:"10px 14px",background:"#f5f5f2",borderRadius:8}}><div style={{fontSize:11,fontWeight:600,marginBottom:6}}>Operational limits</div>{z.ops.map((o,i)=><div key={i} style={{fontSize:11,color:"#666",lineHeight:1.6,paddingLeft:12,textIndent:-12}}>→ {o}</div>)}</div></div></div>)}</div>}

// ═══════════════════════════════════════
// OPERATIONAL ZONES (full interactive)
// ═══════════════════════════════════════
const OZ=[{id:"green",num:"OPS 1",t:"SLM-mandated",co:"#639922",bg:"#EAF3DE",bc:"#3B6D11",desc:"LLM infeasible. Hard constraints.",dims:[{n:"Latency",r:"≤50ms p99. Autocomplete, HFT.",s:"≥9",p:90},{n:"Cost",r:"Near-zero. >1M/day.",s:"≥9",p:90},{n:"Data locality",r:"Zero egress. HIPAA/GDPR.",s:"10",p:100},{n:"Throughput",r:">10K/sec sustained.",s:"≥8",p:80},{n:"Infra",r:"Mobile, edge, single CPU.",s:"≥9",p:90},{n:"Availability",r:"99.99%, offline.",s:"≥8",p:80}],rule:"ANY metric ≥8 with hard constraint."},{id:"amber",num:"OPS 2",t:"SLM-preferred",co:"#BA7517",bg:"#FAEEDA",bc:"#854F0B",desc:"LLM feasible but suboptimal. TCO decision.",dims:[{n:"Latency",r:"≤200ms p95.",s:"5–7",p:60},{n:"Cost",r:"100K–1M/day.",s:"5–7",p:60},{n:"Data locality",r:"Prefer local, not mandated.",s:"4–6",p:50},{n:"Throughput",r:"1K–10K/sec.",s:"4–6",p:50},{n:"Infra",r:"Single-GPU. API possible.",s:"4–6",p:50},{n:"Availability",r:"99.9% with failover.",s:"4–6",p:50}],rule:"≥3 metrics at 4–7. No hard constraints."},{id:"red",num:"OPS 3",t:"LLM-viable",co:"#A32D2D",bg:"#FCEBEB",bc:"#791F1F",desc:"No constraint favoring SLM. Capability decides.",dims:[{n:"Latency",r:"≤2s. Async/batch.",s:"≤3",p:20},{n:"Cost",r:"<10K/day or high value.",s:"≤3",p:20},{n:"Data locality",r:"No restriction.",s:"≤2",p:10},{n:"Throughput",r:"<1K/sec.",s:"≤3",p:20},{n:"Infra",r:"Cloud multi-GPU / API.",s:"≤2",p:10},{n:"Availability",r:"99.5% with retries.",s:"≤3",p:20}],rule:"All metrics ≤3."},{id:"purple",num:"OPS 4",t:"Hybrid-optimal",co:"#534AB7",bg:"#EEEDFE",bc:"#3C3489",desc:"Bimodal: high-volume SLM + low-volume LLM.",dims:[{n:"Latency",r:"70–85% ≤100ms, rest ≤1.5s.",s:"mixed",p:65},{n:"Cost",r:"Blended. SLM handles floor.",s:"mixed",p:65},{n:"Data locality",r:"SLM: local PII. LLM: anonymized.",s:"split",p:70},{n:"Throughput",r:">5K/sec aggregate.",s:"mixed",p:60},{n:"Infra",r:"SLM on-prem + LLM API.",s:"split",p:55},{n:"Availability",r:"SLM 99.99% + LLM 99.5%.",s:"split",p:70}],rule:"≥2 metrics bimodal. SLM savings > routing cost."}];

function OpsZones(){const[v,setV]=useState("all");return<div>
<div style={{padding:"12px 14px",background:"#f5f5f2",borderRadius:8,marginBottom:14,fontSize:12,color:"#555",lineHeight:1.6}}><strong>Operational axis (1–10):</strong> Scores deployment <em>requirements</em>. High = stricter = favors SLM. "Even if an LLM <em>could</em> do this, <em>should</em> it?"</div>
<div style={{display:"flex",gap:4,flexWrap:"wrap",marginBottom:14}}>{["all","green","amber","red","purple"].map(x=><button key={x} onClick={()=>setV(x)} style={{fontSize:11,padding:"5px 12px",borderRadius:6,background:v===x?"#fff":"#f0f0ec",color:v===x?"#1a1a1a":"#888",border:v===x?"1px solid #ccc":"1px solid transparent",cursor:"pointer",fontWeight:v===x?600:400}}>{x==="all"?"All":OZ.find(z=>z.id===x)?.t}</button>)}</div>
{OZ.filter(z=>v==="all"||z.id===v).map(z=><div key={z.id} style={{border:"1px solid #e0e0e0",borderRadius:10,marginBottom:16,overflow:"hidden"}}>
<div style={{padding:"12px 16px",borderBottom:`2px solid ${z.co}`,display:"flex",alignItems:"center",gap:10}}><span style={{fontSize:11,fontWeight:600,padding:"3px 10px",borderRadius:6,background:z.bg,color:z.bc}}>{z.num}</span><span style={{fontSize:15,fontWeight:600}}>{z.t}</span></div>
<div style={{padding:"12px 16px"}}><p style={{fontSize:12,color:"#666",lineHeight:1.6,marginBottom:12}}>{z.desc}</p>
<div style={{fontSize:11,fontWeight:600,color:"#888",textTransform:"uppercase",letterSpacing:0.4,marginBottom:8,paddingBottom:4,borderBottom:"1px solid #eee"}}>Operational metrics</div>
{z.dims.map((d,i)=><div key={i} style={{display:"grid",gridTemplateColumns:"110px 1fr 60px",gap:8,padding:"6px 0",borderBottom:"1px solid #f0f0ec",fontSize:12}}>
<div style={{fontWeight:600}}>{d.n}</div><div style={{color:"#666",lineHeight:1.4}}>{d.r}<div style={{height:3,background:"#eee",borderRadius:2,marginTop:4}}><div style={{height:3,borderRadius:2,background:z.co,width:`${d.p}%`}}/></div></div><div style={{fontFamily:"monospace",fontSize:11,color:"#888",textAlign:"right"}}>{d.s}</div></div>)}
<div style={{marginTop:12,padding:"10px 14px",borderRadius:8,borderLeft:`3px solid ${z.co}`,background:"#f9f9f6"}}><div style={{fontSize:11,fontWeight:600,marginBottom:2}}>Zone entry rule</div><div style={{fontSize:12,color:"#555",lineHeight:1.6}}>{z.rule}</div></div></div></div>)}</div>}

// ═══════════════════════════════════════
// DECISION MATRIX (full, clickable)
// ═══════════════════════════════════════
const MD={"C1×O1":{d:"Pure SLM",t:"Both align. Max savings.",tag:"NO CONFLICT",c:"s",a:["SLM ≤3B INT4/INT8 on-device","No retrieval, no fallback"],ri:["Near-zero. Monitor drift"]},"C2×O1":{d:"SLM+mitigations",t:"Ops forces SLM. RAG/CoT close gap.",tag:"ENGINEERING",c:"co",a:["SLM + vector index","Distilled CoT fine-tune"],ri:["3–5% delta. Maintenance surface"]},"C3×O1":{d:"Conflict→redesign",t:"Needs LLM but ops forbids.",tag:"HARD CONFLICT",c:"x",a:["Split: SLM preproc + async LLM","Or reduce scope to C2","Or degraded + human review"],ri:["HIGH. Fundamental compromise"]},"C4×O1":{d:"SLM degraded",t:"Hybrid wants LLM, ops blocks.",tag:"TRADE-OFF",c:"co",a:["SLM all traffic","Confidence-gated abstain"],ri:["UX degrades 15–30%"]},"C1×O2":{d:"SLM bonus",t:"Easy + ops favors SLM.",tag:"LOW EFFORT",c:"sl",a:["SLM ≤3B standard serve"],ri:["Overengineering risk"]},"C2×O2":{d:"SLM+mitigations",t:"Both favor SLM. Clear ROI.",tag:"SWEET SPOT",c:"co",a:["SLM 1–7B + RAG + LoRA","Target ≤5% delta, 80% cost cut"],ri:["Mitigation creep"]},"C3×O2":{d:"LLM+cost opt",t:"Needs LLM, wants cheaper.",tag:"COST PRESSURE",c:"h",a:["LLM + semantic cache","Prompt compression 30–50%"],ri:["Compression loses context"]},"C4×O2":{d:"Hybrid aggressive",t:"80–90% SLM. LLM tail only.",tag:"ROUTER",c:"h",a:["SLM on-prem + LLM API","Entropy-based router ≤10ms"],ri:["Router miscalibration"]},"C1×O3":{d:"Either works",t:"No constraint. Team choice.",tag:"INDIFFERENT",c:"sl",a:["<1K/day → LLM API",">10K/day → SLM"],ri:["Analysis paralysis"]},"C2×O3":{d:"LLM default",t:"Ops neutral. LLM easiest.",tag:"BUILD VS BUY",c:"co",a:["LLM API now, migrate later"],ri:["Vendor lock-in"]},"C3×O3":{d:"Pure LLM",t:"Both → LLM.",tag:"NO CONFLICT",c:"l",a:["Frontier API","Multi-provider fallback"],ri:["Cost at scale, outages"]},"C4×O3":{d:"Hybrid balanced",t:"Quality-first 60:40.",tag:"QUALITY",c:"h",a:["Conservative router","LLM-as-judge calibration"],ri:["Complexity may not justify"]},"C1×O4":{d:"SLM (no router)",t:"Too simple for routing.",tag:"OVER-ENG",c:"sl",a:["Single SLM, no LLM path"],ri:["Building unnecessary infra"]},"C2×O4":{d:"Hybrid natural",t:"SLM+RAG primary, LLM edges.",tag:"NATURAL",c:"h",a:["Shared retrieval layer","LLM on mitigation failures"],ri:["High arch complexity"]},"C3×O4":{d:"LLM+SLM preproc",t:"SLM filters, LLM reasons.",tag:"PIPELINE",c:"h",a:["SLM classify/extract/filter","LLM gets cleaner input, 40–60% fewer tokens"],ri:["SLM errors cascade"]},"C4×O4":{d:"Full hybrid",t:"Max investment. Router+monitoring.",tag:"MAX",c:"h",a:["Learned router, adaptive thresholds","Full observability stack"],ri:["Only at >100K/day"]}};
const CC={s:{bg:"#EAF3DE",t:"#3B6D11"},sl:{bg:"#F5F9EC",t:"#639922"},co:{bg:"#FAEEDA",t:"#854F0B"},h:{bg:"#EEEDFE",t:"#534AB7"},l:{bg:"#FCEBEB",t:"#791F1F"},x:{bg:"#FFF8E1",t:"#854F0B"}};

function Matrix(){const[det,setDet]=useState(null);
return<div>
<div style={{padding:"12px 14px",background:"#f5f5f2",borderRadius:8,marginBottom:14,fontSize:12,color:"#555",lineHeight:1.6}}><strong>16 cells:</strong> 4 capability zones × 4 operational zones. Click any cell for architecture + risk.</div>
<div style={{overflowX:"auto"}}><table style={{width:"100%",borderCollapse:"collapse",fontSize:11,minWidth:600}}>
<thead><tr><th style={{width:100,padding:6}}></th>{["C1\nSLM-safe","C2\nConditional","C3\nLLM-required","C4\nHybrid"].map((c,i)=><th key={i} style={{textAlign:"center",padding:"8px 4px",borderBottom:"2px solid #ddd",fontSize:11,fontWeight:600,color:"#555",whiteSpace:"pre-line",lineHeight:1.3}}>{c}</th>)}</tr></thead>
<tbody>{["O1: SLM-mandated","O2: SLM-preferred","O3: LLM-viable","O4: Hybrid-optimal"].map((row,ri)=><tr key={ri}><td style={{padding:"6px 4px",fontWeight:600,fontSize:10,color:"#555",borderRight:"2px solid #ddd"}}>{row}</td>
{["C1","C2","C3","C4"].map((c,ci)=>{const k=`${c}×O${ri+1}`;const m=MD[k];const cl=CC[m.c];return<td key={ci} onClick={()=>setDet(det===k?null:k)} style={{padding:8,background:cl.bg,border:"1px solid #e8e8e4",cursor:"pointer",verticalAlign:"top"}}>
<div style={{fontFamily:"monospace",fontSize:9,fontWeight:600,color:cl.t,marginBottom:3}}>{k}</div>
<div style={{fontSize:11.5,fontWeight:600,marginBottom:2}}>{m.d}</div>
<div style={{fontSize:10,color:"#777",lineHeight:1.4}}>{m.t}</div>
<div style={{display:"inline-block",fontSize:8,fontWeight:600,padding:"2px 5px",borderRadius:3,marginTop:4,background:cl.t+"22",color:cl.t}}>{m.tag}</div>
</td>})}</tr>)}</tbody></table></div>
<div style={{display:"flex",flexWrap:"wrap",gap:8,marginTop:10,fontSize:11,color:"#888"}}>{[["#EAF3DE","Pure SLM"],["#F5F9EC","SLM light"],["#FAEEDA","Conditional"],["#EEEDFE","Hybrid"],["#FCEBEB","Pure LLM"],["#FFF8E1","Conflict"]].map(([bg,l],i)=><span key={i} style={{display:"flex",alignItems:"center",gap:4}}><span style={{width:10,height:10,borderRadius:2,background:bg,border:"1px solid #ddd"}}/>{l}</span>)}</div>
{det&&MD[det]&&<div style={{marginTop:14,padding:"14px 16px",border:"1px solid #ddd",borderRadius:10}}>
<div style={{fontFamily:"monospace",fontSize:12,fontWeight:600,marginBottom:4}}>{det}: {MD[det].d}</div>
<div style={{fontSize:11,fontWeight:600,color:"#555",marginBottom:4}}>Architecture</div>
{MD[det].a.map((a,i)=><div key={i} style={{fontSize:12,color:"#666",lineHeight:1.6,paddingLeft:12,textIndent:-12}}>→ {a}</div>)}
<div style={{fontSize:11,fontWeight:600,color:"#555",marginTop:8,marginBottom:4}}>Risk</div>
{MD[det].ri.map((r,i)=><div key={i} style={{fontSize:12,color:"#666",lineHeight:1.6,paddingLeft:12,textIndent:-12}}>→ {r}</div>)}
</div>}</div>}

// ═══════════════════════════════════════
// TWO-AXIS SCI RUBRIC
// ═══════════════════════════════════════
function SCIRubric(){return<div>
<P>The Subtask Complexity Index uses a two-axis decomposition that separates structural task difficulty (unfixable) from engineering-addressable difficulty (fixable with tooling).</P>

<Sub title="Axis 1: Inherent Complexity (IC) = D1 + D2 + D3  [range 0–6]">
<P style={{fontSize:12,color:"#555"}}>Structural properties that no post-processing, constrained decoding, or pipeline can fix. If the model can't reason through it, engineering doesn't help.</P>
<DT h={["Dim","Name","0","1","2","Measures"]} r={[
  ["D1","Logical steps","1 step (direct map)","2–3 steps (sequential)","4+ steps (chain/recursion)","Min operations input→output"],
  ["D2","State tracking","Stateless","1 intermediate value","2+ intermediates or stack","Variables held across steps"],
  ["D3","Knowledge scope","All in prompt/context","Domain vocabulary needed","External API / cross-domain","Is answer derivable from input?"],
]}/>
</Sub>

<Sub title="Axis 2: Mitigable Complexity (MC) = D4 + D5  [range 0–4]">
<P style={{fontSize:12,color:"#555"}}>Causes of SLM failure that are recoverable through constrained decoding, post-processing rules, output validation, or template engines.</P>
<DT h={["Dim","Name","0","1","2","Measures"]} r={[
  ["D4","Output transformation","Copy / select span","Reformat / normalize","Generate novel content","Structural difference input→output"],
  ["D5","Constraint count","0–1 constraints","2 constraints","3+ simultaneous","Independent output requirements"],
]}/>
</Sub>

<Sub title="Deployment quadrants">
<DT h={["Quadrant","IC","MC","Meaning","Action"]} r={[
  ["SLM-ready","0–2","0–2","Simple task, simple output","Ship SLM as-is"],
  ["Engineer-fixable","0–2","3–4","Simple task, hard constraints","SLM + constrained decoding / post-processing"],
  ["Capability cliff","3+","any","Hard task, any output","LLM required — no engineering fix"],
  ["Double-hard","3+","3+","Hard task, hard constraints","LLM + output engineering still needed"],
]}/>
</Sub>

<div style={{display:"grid",gap:8,marginTop:8}}>
<div style={{padding:"10px 14px",background:"#f0f7e8",borderRadius:8,borderLeft:"3px solid #639922",fontSize:12,lineHeight:1.6}}>
<strong style={{color:"#3B6D11"}}>Example (PASSED):</strong> MBPP-505 "Move zeroes to end." D1:0 (single loop) D2:0 (no intermediates) D3:0 (all in prompt) → <strong>IC=0</strong>. D4:1 (reorder) D5:0 → <strong>MC=1</strong>. Quadrant: SLM-ready.
</div>
<div style={{padding:"10px 14px",background:"#FCEBEB",borderRadius:8,borderLeft:"3px solid #A32D2D",fontSize:12,lineHeight:1.6}}>
<strong style={{color:"#791F1F"}}>Example (FAILED):</strong> MBPP-374 "All permutations." D1:2 D2:2 D3:1 → <strong>IC=5</strong>. D4:2 D5:0 → <strong>MC=2</strong>. Quadrant: Capability cliff.
</div>
<div style={{padding:"10px 14px",background:"#FAEEDA",borderRadius:8,borderLeft:"3px solid #BA7517",fontSize:12,lineHeight:1.6}}>
<strong style={{color:"#854F0B"}}>Example (FAILED but fixable):</strong> "Summarize in exactly 1 sentence." D1:1 D2:0 D3:0 → <strong>IC=1</strong>. D4:1 D5:2 → <strong>MC=3</strong>. Quadrant: Engineer-fixable. Constrained decoding would solve this.
</div>
</div>
</div>}

// ═══════════════════════════════════════
// 2D SCATTER CAPABILITY LIMITS
// ═══════════════════════════════════════
const LIM=[
  {num:"TC-01",t:"Classification",items:[
    {l:"Binary sentiment",ic:0,mc:1,s:"pass",e:"gemma2:2b 100% SST-2"},
    {l:"4-class topic",ic:0,mc:1,s:"pass",e:"Correct Sports/Business/World"},
    {l:"Simple emotion",ic:1,mc:1,s:"pass",e:"Direct lexical cues"},
    {l:"Ambiguous emotion",ic:2,mc:1,s:"fail",e:"qwen→anger for ALL emotions"},
    {l:"Sarcasm detection",ic:2,mc:2,s:"fail",e:"Polarity flip on irony"},
    {l:"Adjacent emotions",ic:3,mc:1,s:"fail",e:"surprise vs curiosity boundary"},
  ],boundary:"IC ≤ 1: SLM-safe. IC ≥ 2: pragmatic inference needed → fails.",lims:[["Best acc","0.806"],["Break","IC=2"]]},
  {num:"TC-02",t:"Text Generation",items:[
    {l:"Open-ended email/desc",ic:0,mc:1,s:"pass",e:"100% success, correct tone"},
    {l:"Professional tone",ic:0,mc:2,s:"pass",e:"Appropriate register"},
    {l:"Code snippet",ic:1,mc:1,s:"pass",e:"Correct Python"},
    {l:"Exact length ('4 lines')",ic:0,mc:4,s:"fail",e:"Constr sat 0.000–0.133"},
    {l:"Format+length+keyword",ic:0,mc:4,s:"fail",e:"No model satisfies"},
    {l:"Exactly 3 bullet points",ic:0,mc:3,s:"fail",e:"Wrong count generated"},
  ],boundary:"IC is low for all subtasks — generation quality is fine. MC ≥ 3: constraint adherence breaks. This is purely an engineer-fixable zone.",lims:[["Best constr","0.133"],["Break","MC=3"]]},
  {num:"TC-03",t:"Information Extraction",items:[
    {l:"Field copy (company, total)",ic:0,mc:1,s:"pass",e:"SmolLM2 copies correctly"},
    {l:"Fixed JSON schema",ic:0,mc:2,s:"pass",e:"100% schema validity"},
    {l:"Clean OCR extraction",ic:0,mc:2,s:"pass",e:"Micro F1 0.500"},
    {l:"Date normalization",ic:2,mc:2,s:"fail",e:"0.000 EM — all fail"},
    {l:"Address concatenation",ic:2,mc:3,s:"fail",e:"Multi-line join+cleanup"},
    {l:"Noisy OCR",ic:2,mc:2,s:"warn",e:"Not tested"},
  ],boundary:"IC ≤ 1 + MC ≤ 2: SLM works. Date normalization (IC=2, requiring parse+reformat) is the cliff. Schema adherence (MC) is not the bottleneck — SmolLM2 gets 100%.",lims:[["Best F1","0.500"],["EM","0.000"],["Break","IC=2"]]},
  {num:"TC-04",t:"Summarization",items:[
    {l:"News compression (tuned)",ic:1,mc:1,s:"pass",e:"DistilBART R-1 0.434"},
    {l:"Extractive single-topic",ic:1,mc:1,s:"pass",e:"Sem-sim 0.765"},
    {l:"Length compliance",ic:0,mc:3,s:"fail",e:"100% violation"},
    {l:"Generic (no tuning)",ic:1,mc:1,s:"fail",e:"t5-small R-1 0.117, 70% halluc"},
    {l:"Hallucination <10%",ic:2,mc:2,s:"fail",e:"Best: 30% halluc"},
    {l:"Key fact preservation",ic:3,mc:1,s:"fail",e:"83% info loss"},
  ],boundary:"IC ≤ 1 + domain-tuned: works. Length (MC=3): engineer-fixable. Hallucination (IC=2) and fact preservation (IC=3): inherent. Generic models fail even at IC=1 — domain tuning is prerequisite.",lims:[["R-1 tuned","0.434"],["R-1 generic","0.117"],["Break","IC=2 or no tuning"]]},
  {num:"TC-05",t:"Code Generation",items:[
    {l:"Move zeroes (single loop)",ic:0,mc:1,s:"pass",e:"MBPP-505 PASSED"},
    {l:"Triangle check (boolean)",ic:0,mc:1,s:"pass",e:"MBPP-334 PASSED"},
    {l:"isinstance in tuple",ic:3,mc:1,s:"fail",e:"MBPP-143 FAILED"},
    {l:"Nested loops (2D array)",ic:3,mc:2,s:"fail",e:"MBPP-380 FAILED"},
    {l:"cmath API usage",ic:3,mc:2,s:"fail",e:"MBPP-124 FAILED"},
    {l:"Stack algorithm (brackets)",ic:5,mc:1,s:"fail",e:"HumanEval/61 FAILED 6+ runs"},
    {l:"Recursion (permutations)",ic:5,mc:2,s:"fail",e:"MBPP-374 FAILED all runs"},
    {l:"HumanEval (0/5)",ic:5,mc:2,s:"fail",e:"All 5 FAILED"},
  ],boundary:"IC ≤ 0: passes (single-loop, single-condition). IC ≥ 3: fails without exception. The sharpest cliff in all test cases — no IC=1 or IC=2 tasks were even tested because MBPP/HumanEval jump directly from trivial to algorithmic.",lims:[["Passed","2/20"],["Break","IC=3"]]},
  {num:"TC-06",t:"Instruction Following",items:[
    {l:"Topic adherence",ic:0,mc:1,s:"pass",e:"On-topic generated"},
    {l:"Keyword inclusion",ic:0,mc:2,s:"pass",e:"Lexical 0.500"},
    {l:"Bullet format",ic:0,mc:2,s:"pass",e:"DeepSeek format 1.000"},
    {l:"Exact word count",ic:0,mc:4,s:"fail",e:"85–100 tokens output"},
    {l:"Word avoidance",ic:1,mc:3,s:"fail",e:"DeepSeek lexical 0.000"},
    {l:"All constraints simultaneous",ic:0,mc:4,s:"fail",e:"Pass rate 0.400"},
  ],boundary:"IC is ≤ 1 for all instruction tasks — the reasoning is trivial. MC ≥ 3: breaks. Like text generation, this is purely a constraint-adherence problem living on the MC axis. Constrained decoding is the fix.",lims:[["Pass rate","0.400"],["Break","MC=3"]]},
  {num:"TC-07",t:"Mathematical Reasoning",items:[
    {l:"1-step arithmetic",ic:0,mc:1,s:"pass",e:"'Half of 48' pattern-matched"},
    {l:"Unit conversion",ic:1,mc:1,s:"pass",e:"Single conversion"},
    {l:"2-step word problem",ic:3,mc:1,s:"fail",e:"Accuracy 20–30%"},
    {l:"3-step chain",ic:5,mc:1,s:"fail",e:"Hold 3 intermediates"},
    {l:"Dependent variables",ic:5,mc:1,s:"fail",e:"Three dependent calcs"},
    {l:"Rate/time conditional",ic:6,mc:1,s:"fail",e:"10% accuracy"},
  ],boundary:"IC ≤ 1: passes. IC ≥ 3: fails. MC is low across all maths subtasks (output is just a number). This is a pure IC-axis problem — reasoning depth is the only dimension that matters.",lims:[["Best acc","30.0%"],["Conf error","23–30%"],["Break","IC=3"]]},
  {num:"TC-08",t:"Retrieval-Grounded QA",items:[
    {l:"Verbatim span extraction",ic:0,mc:1,s:"pass",e:"96.67% context utilization"},
    {l:"Short factual answer",ic:0,mc:2,s:"pass",e:"66.67% EM, 3.33% halluc"},
    {l:"Clear question→answer",ic:1,mc:1,s:"pass",e:"86.67% length accuracy"},
    {l:"Paraphrasing needed",ic:2,mc:2,s:"fail",e:"Partial rate 13–30%"},
    {l:"'No answer' detection",ic:3,mc:1,s:"warn",e:"Not tested"},
    {l:"Multi-hop reasoning",ic:5,mc:2,s:"warn",e:"DeepSeek 53% halluc on simple"},
  ],boundary:"IC ≤ 1: excellent (copy from context). IC = 2: degrades (paraphrasing). IC ≥ 3: failure expected. MC is low — the output format is simple. This is RAG's sweet spot: keep IC low by providing all knowledge in-context.",lims:[["Best EM","66.67%"],["Halluc","3.33%"],["Break","IC=2"]]},
];

function LimitScatter({tc}){
  const W=320,H=240,pad={t:30,r:20,b:40,l:50};
  const iw=W-pad.l-pad.r, ih=H-pad.t-pad.b;
  const maxIC=6, maxMC=4;
  const sx=(v)=>pad.l+(v/maxIC)*iw, sy=(v)=>pad.t+ih-(v/maxMC)*ih;

  return<div style={{border:"1px solid #e0e0e0",borderRadius:10,marginBottom:20,overflow:"hidden"}}>
    <div style={{padding:"10px 16px",background:"#fafaf8",borderBottom:"1px solid #eee",display:"flex",alignItems:"center",gap:10}}>
      <span style={{fontFamily:"monospace",fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:4,background:"#e8e8e4"}}>{tc.num}</span>
      <span style={{fontWeight:600,fontSize:13}}>{tc.t}</span>
    </div>
    <div style={{padding:"12px 16px",display:"flex",gap:16,flexWrap:"wrap",alignItems:"flex-start"}}>
      {/* Scatter plot */}
      <svg viewBox={`0 0 ${W} ${H}`} style={{width:320,height:240,flexShrink:0}}>
        {/* Quadrant shading */}
        <rect x={pad.l} y={sy(maxMC)} width={sx(2)-pad.l} height={sy(0)-sy(2)} fill="rgba(99,153,34,0.06)" rx="4"/>
        <rect x={pad.l} y={sy(maxMC)} width={sx(2)-pad.l} height={sy(2)-sy(maxMC)} fill="rgba(186,117,23,0.06)" rx="4"/>
        <rect x={sx(2)} y={sy(maxMC)} width={sx(maxIC)-sx(2)} height={ih} fill="rgba(163,45,45,0.04)" rx="4"/>
        {/* Quadrant labels */}
        <text x={pad.l+4} y={sy(0)-4} fontSize="8" fill="#639922" fontWeight="600">SLM-ready</text>
        <text x={pad.l+4} y={sy(2.5)} fontSize="8" fill="#BA7517" fontWeight="600">Engineer-fixable</text>
        <text x={sx(3)} y={sy(0)-4} fontSize="8" fill="#A32D2D" fontWeight="600">Capability cliff</text>
        {/* IC=2 boundary */}
        <line x1={sx(2)} y1={pad.t} x2={sx(2)} y2={pad.t+ih} stroke="#534AB7" strokeWidth="1.5" strokeDasharray="4,3"/>
        {/* MC=2 boundary */}
        <line x1={pad.l} y1={sy(2)} x2={pad.l+iw} y2={sy(2)} stroke="#534AB7" strokeWidth="1" strokeDasharray="4,3" opacity="0.5"/>
        {/* Grid */}
        {[0,1,2,3,4,5,6].map(v=><line key={`gx${v}`} x1={sx(v)} y1={pad.t} x2={sx(v)} y2={pad.t+ih} stroke="#eee" strokeWidth="0.5"/>)}
        {[0,1,2,3,4].map(v=><line key={`gy${v}`} x1={pad.l} y1={sy(v)} x2={pad.l+iw} y2={sy(v)} stroke="#eee" strokeWidth="0.5"/>)}
        {/* Axes */}
        <line x1={pad.l} y1={pad.t+ih} x2={pad.l+iw} y2={pad.t+ih} stroke="#ccc" strokeWidth="1"/>
        <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t+ih} stroke="#ccc" strokeWidth="1"/>
        {[0,1,2,3,4,5,6].map(v=><text key={`lx${v}`} x={sx(v)} y={pad.t+ih+14} fontSize="9" fill="#999" textAnchor="middle">{v}</text>)}
        {[0,1,2,3,4].map(v=><text key={`ly${v}`} x={pad.l-6} y={sy(v)+3} fontSize="9" fill="#999" textAnchor="end">{v}</text>)}
        <text x={pad.l+iw/2} y={H-4} fontSize="10" fill="#666" textAnchor="middle" fontWeight="500">Inherent Complexity (IC) →</text>
        <text x={12} y={pad.t+ih/2} fontSize="10" fill="#666" textAnchor="middle" fontWeight="500" transform={`rotate(-90,12,${pad.t+ih/2})`}>Mitigable (MC) ↑</text>
        {/* Dots */}
        {tc.items.map((it,i)=>{
          const col=it.s==="pass"?"#639922":it.s==="fail"?"#A32D2D":"#BA7517";
          return<g key={i}>
            <circle cx={sx(it.ic)} cy={sy(it.mc)} r="8" fill={col} opacity="0.9"/>
            <text x={sx(it.ic)} y={sy(it.mc)+3.5} fontSize="8" fill="#fff" textAnchor="middle" fontWeight="700">{it.s==="pass"?"✓":it.s==="fail"?"✗":"?"}</text>
            <title>{`${it.l}\nIC=${it.ic} MC=${it.mc}\n${it.e}`}</title>
          </g>;
        })}
      </svg>
      {/* Legend + items */}
      <div style={{flex:1,minWidth:200}}>
        {tc.items.map((it,i)=>{
          const col=it.s==="pass"?"#3B6D11":it.s==="fail"?"#791F1F":"#854F0B";
          return<div key={i} style={{display:"flex",gap:6,marginBottom:4,fontSize:11,lineHeight:1.4}}>
            <span style={{color:col,fontWeight:600,flexShrink:0,width:12,textAlign:"center"}}>{it.s==="pass"?"✓":it.s==="fail"?"✗":"?"}</span>
            <span style={{color:col,fontWeight:500}}>{it.l}</span>
            <span style={{color:"#bbb",fontFamily:"monospace",fontSize:10,marginLeft:"auto",flexShrink:0}}>IC={it.ic} MC={it.mc}</span>
          </div>;
        })}
        <div style={{marginTop:8,padding:"8px 10px",borderRadius:6,borderLeft:"3px solid #1B2A3E",background:"#f5f5f2",fontSize:11,lineHeight:1.5}}>
          <strong>Boundary:</strong> {tc.boundary}
        </div>
        <div style={{display:"flex",flexWrap:"wrap",gap:4,marginTop:6}}>
          {tc.lims.map(([l,v],i)=><span key={i} style={{fontSize:10,padding:"2px 6px",borderRadius:4,background:"#f3f3f0"}}><span style={{color:"#999"}}>{l}: </span><span style={{fontWeight:600,fontFamily:"monospace"}}>{v}</span></span>)}
        </div>
      </div>
    </div>
  </div>;
}

// ═══════════════════════════════════════
// TEST CASE (expandable)
// ═══════════════════════════════════════
function TC({num,t,desc,ch,cr,chl,oh,or,ohl,cs,os}){const[open,setOpen]=useState(false);
return<div style={{border:"1px solid #e0e0e0",borderRadius:10,marginBottom:12,overflow:"hidden"}}>
<div onClick={()=>setOpen(!open)} style={{padding:"10px 14px",display:"flex",alignItems:"center",gap:8,cursor:"pointer",background:"#fafaf8"}}>
<span style={{fontFamily:"monospace",fontSize:10,fontWeight:600,padding:"2px 6px",borderRadius:4,background:"#e8e8e4"}}>{num}</span>
<span style={{flex:1,fontWeight:600,fontSize:13}}>{t}</span>
<span style={{color:"#999",fontSize:11}}>{open?"▼":"▶"}</span></div>
{open&&<div style={{padding:"10px 14px"}}><P>{desc}</P>
<Sub title="Capability"><DT h={ch} r={cr} hl={chl} c/></Sub>
<Sub title="Operational"><DT h={oh} r={or} hl={ohl} c/></Sub>
<div style={{marginBottom:6}}><span style={{fontSize:10,fontWeight:600,color:"#777",marginRight:4}}>Cap:</span>{cs.map((s,i)=><Chip key={i} l={s[0]} v={s[1]}/>)}</div>
<div><span style={{fontSize:10,fontWeight:600,color:"#777",marginRight:4}}>Ops:</span>{os.map((s,i)=><Chip key={i} l={s[0]} v={s[1]}/>)}</div>
</div>}</div>}

// ═══════════════════════════════════════
// PAPER
// ═══════════════════════════════════════
function DecisionTree(){const steps=[{id:"gate1",step:1,title:"Check operational hard constraints",desc:"Before capability scoring, test whether the environment forbids LLM use.",checks:["Data locality: do regulatory or contractual rules prohibit external API calls?","Latency: does the use case require 50 ms or less at p95?","Infrastructure: is deployment on-device, edge, or air-gapped?","Cost: is inference volume above 1M calls/day with a tight monthly budget?","Availability: must the system function offline or during connectivity loss?"],yes:"LLM is excluded. Continue in an SLM-only operating mode.",no:"LLM remains feasible. Continue to operational preference."},{id:"gate2",step:2,title:"Assess operational preference",desc:"If no hard block exists, determine whether economics still favor an SLM-first design.",checks:["Count operational dimensions in the 4-7 range.","If 3 or more dimensions fall in that range, SLM is preferred on total cost of ownership.","If all dimensions are 3 or below, operations are neutral and capability can dominate."],yes:"SLM is preferred economically. Continue to capability screening.",no:"No operational preference. Continue with all model classes open."},{id:"gate3",step:3,title:"Score the hardest subtask on capability dimensions",desc:"Use the maximum-demand subtask, not the average across the workload.",checks:["Reasoning depth: number of logical steps from input to output.","Knowledge demand: whether required knowledge is fully in prompt/context.","Context length: how much input must be jointly processed.","Conversational coherence: how many dependent turns must stay aligned.","Calibration: whether the task needs abstention or confidence quality.","Output structure: how constrained or open-ended the response must be."],yes:"If any dimension is 6 or higher, the task is in LLM-required territory.",no:"If all dimensions are 5 or below, continue to SCI scoring."},{id:"gate4",step:4,title:"Score SCI on representative subtasks",desc:"Separate inherent task difficulty from fixable output difficulty.",checks:["D1 Logical steps: 1 step = 0, 2-3 = 1, 4+ = 2.","D2 State tracking: none = 0, one intermediate = 1, 2+ = 2.","D3 Knowledge scope: all in input = 0, domain vocabulary = 1, external knowledge/API = 2.","D4 Output transformation: copy/select = 0, reformat = 1, novel generation = 2.","D5 Constraint simultaneity: 0-1 constraints = 0, 2 = 1, 3+ = 2.","Compute IC = D1 + D2 + D3 and MC = D4 + D5."],yes:"If any subtask has IC 3 or higher, SLM failure is structural.",no:"If max IC is 2 or below, SLM is viable and MC determines engineering needs."},{id:"gate5",step:5,title:"Map MC to mitigation strategy",desc:"Use output difficulty to decide whether tooling is required around the SLM.",checks:["MC 0-2: deploy SLM as-is.","MC 3-4: add constrained decoding, validators, or post-processing.","Constraint-heavy failures need output control; normalization-heavy failures need deterministic cleanup."],yes:"Deploy SLM with engineering mitigations.",no:"Deploy a pure SLM path."},{id:"gate6",step:6,title:"Run a validation experiment",desc:"Confirm the predicted zone with paired evaluation across candidate models.",checks:["Use the same evaluation items across all models.","Minimum 100 samples per subtask type for directional confidence; 500+ preferred.","Measure both quality metrics and operational metrics.","Classify failures into IC-driven, MC-driven, or infrastructure-driven."],yes:"Validation confirms the design. Proceed to deployment.",no:"Unexpected failures mean the task should be rescored or redesigned."}];return<div>{steps.map(s=><div key={s.id} style={{border:"1px solid #e0e0e0",borderRadius:10,marginBottom:14,overflow:"hidden"}}><div style={{padding:"12px 16px",background:"#fafaf8",borderBottom:"1px solid #eee",display:"flex",alignItems:"center",gap:10}}><span style={{fontSize:18,fontWeight:700,color:"#1B2A3E",width:30,height:30,borderRadius:"50%",background:"#e8e8e4",display:"flex",alignItems:"center",justifyContent:"center"}}>{s.step}</span><div><div style={{fontSize:14,fontWeight:600,color:"#1B2A3E"}}>{s.title}</div><div style={{fontSize:12,color:"#777"}}>{s.desc}</div></div></div><div style={{padding:"12px 16px"}}><div style={{fontSize:12,fontWeight:600,color:"#555",marginBottom:8}}>Checks to perform</div>{s.checks.map((c,i)=><div key={i} style={{fontSize:12,color:"#555",lineHeight:1.7,paddingLeft:14,textIndent:-14,marginBottom:3}}>â†’ {c}</div>)}<div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginTop:12}}><div style={{padding:"8px 12px",borderRadius:8,background:"#FCEBEB",borderLeft:"3px solid #A32D2D",fontSize:11,lineHeight:1.5}}><strong style={{color:"#791F1F"}}>If YES:</strong><br/><span style={{color:"#555"}}>{s.yes}</span></div><div style={{padding:"8px 12px",borderRadius:8,background:"#f0f7e8",borderLeft:"3px solid #639922",fontSize:11,lineHeight:1.5}}><strong style={{color:"#3B6D11"}}>If NO:</strong><br/><span style={{color:"#555"}}>{s.no}</span></div></div></div></div>)}</div>}

function RoutingProcedure(){return<div><P>For mixed-difficulty workloads, hybrid deployment depends on a fast router that detects when a request crosses the SLM capability cliff and should be escalated to an LLM.</P><Sub title="Router architecture"><DT h={["Component","Specification","Rationale"]} r={[["Router model","Lightweight classifier on extracted features","A separate classifier adds less latency than an LLM router."],["Input features","Token count, multi-step markers, entity count, constraint count, normalization cues","These map directly to SCI dimensions D1-D5."],["Training data","Validation examples labeled SLM-pass or SLM-fail","The evaluation protocol produces the supervision set."],["Decision threshold","Route to LLM when predicted SLM-fail probability exceeds 0.6","Bias toward avoiding high-confidence SLM failures."],["Fallback behavior","If confidence is uncertain, use SLM plus selective LLM shadow verification","Catches drift without sending all traffic to the LLM."]]}/></Sub><Sub title="Priority-ordered routing signals"><DT h={["Priority","Signal","Maps to","Action","Why"]} r={[["1","Multi-step reasoning required","D1 >= 2","Route to LLM","Wrong reasoning cannot be repaired downstream."],["2","Intermediate state must be retained","D2 >= 2","Route to LLM","State loss causes confident but incorrect outputs."],["3","Knowledge absent from context","D3 >= 1","Route to LLM","Missing knowledge produces fabricated answers or APIs."],["4","Three or more simultaneous output constraints","D5 >= 2","Route to SLM with constrained decoding","This is MC-driven, not a capability failure."],["5","Normalization or format transformation required","D4 >= 1","Route to SLM with post-processing","Deterministic cleanup is cheaper than escalation."],["6","None of the above","Low IC / low MC","Route to SLM","Default to the cheaper path when the task is simple."]]}/><W>The ordering matters: IC-driven signals must be checked before MC-driven signals, otherwise the system will preserve format while still returning the wrong answer.</W></Sub><Sub title="Monitoring the router"><DT h={["Metric","How to measure","Alert threshold","Action"]} r={[["SLM agreement rate","Shadow-score 5-10% of SLM-routed traffic with an LLM","Below 85%","Lower the threshold or retrain the router."],["LLM utilization ratio","Percent of requests routed to LLM over a rolling week","Above 40%","Review features or reassess workload drift."],["Failure mode distribution","Audit 100 random SLM outputs per week","IC-driven failures > 10%","IC tasks are leaking through the router."],["Latency budget compliance","Track p95 including router overhead and mitigations","Exceeds target","Optimize router or simplify mitigations."],["Blended cost per request","Weighted average of SLM and LLM costs","Exceeds target by 20%","Shift more eligible traffic back to SLM."]]}/></Sub></div>}

function EvaluationProtocol(){return<div><P>Deployment decisions should be backed by a minimum reproducible evaluation workflow, not only by intuition from the matrix.</P><DT h={["Phase","What to do","Minimum sample size","Output","Why it matters"]} r={[["1. Task decomposition","Break the workload into subtask types and score SCI for each","All subtask types","Subtask inventory with IC/MC scores","This determines which decision path is even plausible."],["2. Candidate selection","Choose 2-3 SLMs and 1 LLM baseline","-","Comparable shortlist","Paired testing is required for trustworthy comparison."],["3. Benchmark run","Evaluate all models on the same samples and log quality plus ops metrics","100 per subtask type; 500+ preferred","Metric tables per model","Low sample counts hide real differences or invent fake ones."],["4. Failure classification","Label every bad output as IC-driven, MC-driven, or infrastructure-driven","All failures","Failure mode distribution","This tells you whether to buy more model or build more tooling."],["5. Statistical check","Run McNemar-style paired comparisons where applicable","Requires paired predictions","Significance evidence","Helps separate signal from noise."],["6. Decision","Map observed evidence back to the SDDF matrix","-","Documented zone assignment","The final recommendation should trace back to evidence."],["7. Monitoring plan","Define production thresholds, drift checks, and retraining triggers","-","Ops monitoring spec","Model quality and workload mix change over time."]]}/><F title="Minimum evidence standard">Do not ship a model-selection decision based on fewer than 100 evaluation samples per subtask type. Smaller runs can surface directional hints, but not dependable deployment guidance.</F></div>}

function DecisionRules(){return<div><P>The combined paper yields a small set of reusable rules that teams can test on new workloads.</P><DT h={["Rule","Condition","Prediction","Confidence","Basis"]} r={[["Rule 1","All capability dimensions <= 3 and hardest-subtask IC <= 1","SLM will match or beat the LLM baseline on the primary metric","High","Confirmed in classification, extraction, and retrieval-style tasks."],["Rule 2","Any capability dimension >= 6 or any subtask IC >= 3","SLM quality drops materially and cannot be rescued by output engineering","High","Observed in code generation and mathematical reasoning."],["Rule 3","MC >= 3 while IC <= 2","Constrained decoding or post-processing can close much of the gap","Medium","Strongly supported by failure patterns, though mitigations were not directly benchmarked."],["Rule 4","Domain-tuned SLM vs generic SLM at IC = 1","Task-specific tuning outperforms raw scale alone","High","Seen in summarization where tuning beats a smaller generic baseline by a wide margin."],["Rule 5","Two SLMs of different size on tasks with IC <= 2","Instruction tuning quality matters more than parameter count","Medium","Several tasks show scale inversions between 0.5B, 1.5B, and other local models."],["Rule 6","Hard operational constraint plus IC >= 3","No satisfactory deployment exists without redesign","Theoretical but structural","This is the irreconcilable conflict cell of the framework."]]}/><W>Rule 3 is the least directly validated rule in the paper because the recommended mitigations were inferred from the failure taxonomy rather than fully tested end to end.</W></div>}

const COST_ASSUMPTIONS=["All cost figures are estimated rather than directly logged billing records.","Local-model costs approximate marginal runtime cost per 1,000 inferences, combining electricity, hardware amortization, and execution overhead.","API costs are lightweight flash-tier proxies normalized to per-1,000-inference equivalents.","The cost analysis should be interpreted as Pareto guidance and order-of-magnitude comparison, not as invoice-grade accounting."];

function CostAnalysisSection(){return<div><P>This section incorporates the use-case Pareto analysis from the companion cost report. Rather than collapsing all benchmarks into a single comparison, it treats each workload as its own cost-accuracy-latency frontier and asks which deployment options remain efficient once all three dimensions are considered together.</P><div style={{marginBottom:14,padding:"12px 14px",background:"#f5f5f2",borderRadius:8}}>{COST_ASSUMPTIONS.map((item,i)=><div key={i} style={{fontSize:12,color:"#555",lineHeight:1.7,paddingLeft:14,textIndent:-14}}>-> {item}</div>)}</div><DT h={["Use case","Primary metric","Frontier local point(s)","Frontier API point","Cost takeaway"]} r={[["Classification","Accuracy","gemma2:2b for quality; qwen2.5:1.5b for fast local trade-off","gemini-2.5-flash-lite","SLMs remain efficient when locality or cost matters; API only wins on raw speed."],["Text generation","Constraint satisfaction","qwen-2.5-3b","gemini baseline","This is a real trade-off: local is cheaper, API is better on observed quality-speed."],["Information extraction","Micro F1","SmolLM2-1.7B","Gemini 2.5 Flash","Local wins on extraction quality and schema robustness; API wins on throughput."],["Summarization","ROUGE-1","distilbart-cnn-12-6 for quality; t5-small for speed","gemini-2.5-flash","Frontier splits three ways, showing that summary quality, speed, and cost are materially separable."],["Code generation","pass@1","DeepSeek Coder 1.3B and Qwen2.5 Coder 1.5B are nominal frontier points","Gemini 2.5 Flash Lite","Interpret cautiously: completed-task counts are unstable, but the task still looks API-favored operationally."],["Instruction following","Pass rate","Qwen2.5-Coder-0.5B","gemini-2.5-flash","Local remains viable, but the reported API result is numerically dominant and should be treated as provisional."],["Mathematical reasoning","Final answer accuracy","gemma_2b for practical local trade-off; orca_mini_7b for local accuracy","gemini_2_5_flash_real","This use case clearly shifts the frontier toward API deployment."],["Retrieval-grounded QA","Exact match","Qwen2.5-0.5B-Instruct","gemini-3.1-flash-lite-preview","RAG-QA preserves a strong local frontier point, but API remains the throughput leader."]]} c/><F title="Cost-analysis synthesis">Across the eight workloads, SLMs stay Pareto-efficient on narrow, structured, or retrieval-bounded tasks, while mathematical reasoning and credible code generation move the efficient frontier toward API models. The main implication is not that one model family always wins, but that SDDF's capability and operational zones should be paired with per-use-case frontier analysis before committing to a production architecture.</F></div>}

export default function Paper(){return<div style={{maxWidth:840,margin:"0 auto",fontFamily:"system-ui,-apple-system,sans-serif",color:"#1a1a1a",lineHeight:1.6}}>

<div style={{textAlign:"center",padding:"40px 0 30px",borderBottom:"3px solid #1B2A3E",marginBottom:30}}>
<h1 style={{fontSize:24,fontWeight:700,color:"#1B2A3E",margin:"0 0 6px"}}>SLM Deployment Decision Framework (SDDF)</h1>
<p style={{fontSize:15,color:"#555",margin:"0 0 4px"}}>Empirical Results Paper</p>
<p style={{fontSize:12,color:"#888",margin:"0 0 16px"}}>Capability and Operational Zone Validation Across Eight NLP Task Families</p>
<p style={{fontSize:13,fontWeight:600}}>Riddhima Reddy</p>
<p style={{fontSize:12,color:"#777"}}>M.S. Business Analytics & AI, UT Dallas — March 2026</p>
</div>

<Sec title="Abstract">
<P>This paper presents the SLM Deployment Decision Framework (SDDF) with empirical validation across eight NLP task families. The framework introduces: (1) a dual-axis scoring system with six capability and six operational dimensions, (2) a 4×4 decision matrix mapping to 16 deployment strategies, and (3) a two-axis Subtask Complexity Index (SCI) that decomposes task difficulty into Inherent Complexity (IC: reasoning, state, knowledge — unfixable) and Mitigable Complexity (MC: output transformation, constraint count — fixable with engineering). The IC/MC decomposition reveals that tasks cluster into four deployment quadrants: SLM-ready (low IC, low MC), Engineer-fixable (low IC, high MC), Capability cliff (high IC), and Double-hard (high both). The breaking point across all eight task families falls at IC ≥ 2–3, while MC-driven failures are systematically addressable through constrained decoding and post-processing.</P>
</Sec>

<Sec title="1. Capability zone definitions"><CapZones/></Sec>
<Sec title="2. Operational zone definitions"><OpsZones/></Sec>
<Sec title="3. Decision matrix (Capability × Operational)"><Matrix/></Sec>
<Sec title="4. Subtask Complexity Index (SCI): two-axis rubric"><SCIRubric/></Sec>

<Sec title="5. Experimental setup">
<DT h={["Component","Specification"]} r={[["OS","Windows-11-10.0.26200-SP0"],["Python","3.12.7"],["CPU","AMD64 Fam 25 Mod 117 (Ryzen 7 8840HS)"],["GPU","Radeon 780M (NOT used)"],["Backends","Ollama, HF Transformers, llama_cpp, Gemini API"],["Seed","42"]]}/>
<W>All local models CPU-only. Latency 10–50x higher than GPU.</W>
<W>Gemini API versions varied. Cross-experiment comparisons directional.</W>
</Sec>

<Sec title="6. Test case results (expandable)">
<P>Click to expand full tables.</P>
<TC num="TC-01" t="Classification" desc="SST-2, Emotion, AG News. n=16." ch={["Model","Acc","MacF1","WF1","Prec","Rec","Valid"]} cr={[["gemma2:2b","0.806","0.730","0.759","0.708","0.774","0.944"],["phi3:mini","0.750","0.684","0.684","0.667","0.750","1.000"],["qwen2.5:1.5b","0.639","0.574","0.574","0.553","0.639","1.000"],["gemini-lite","0.389","0.371","0.387","0.387","0.373","0.583"]]} chl={0} oh={["Model","N","Time","Thru","Lat","P95","CPU%","Mem","Parse"]} or={[["gemma2:2b","16","23.4","0.72","1.47","2.70","88","−118","0.06"],["phi3:mini","16","29.7","0.55","1.93","3.14","41","469","0.00"],["qwen:1.5b","16","12.6","1.28","0.83","1.07","90","160","0.00"],["gemini","16","4.2","4.88","0.24","0.39","59","9","0.42"]]} ohl={2} cs={[["Reas","1"],["Know","1"],["Ctx","1"],["Coh","1"],["Cal","1"],["Str","2"]]} os={[["Lat","5"],["Cost","8"],["Priv","3"],["Thr","4"],["Inf","8"],["Up","4"]]}/>
<TC num="TC-02" t="Text Generation" desc="15 prompts. Q4_K_M. Temp 0.7." ch={["Model","N","Succ","Constr","Fmt","R-1","R-2","R-L","BERT","Ref"]} cr={[["phi-3.5","15","1.00","0.000","1.00","0.00","0.00","0.00","0.00","0.07"],["qwen-3b","15","1.00","0.133","1.00","0.00","0.00","0.00","0.00","0.07"],["gemini","15","1.00","0.167","1.00","0.00","0.00","0.00","0.00","0.07"]]} chl={2} oh={["Model","Ok","Fail","TTFT","Total","Tok","TPS","RAM","Load","$"]} or={[["phi-3.5","15","0","0.84","45.6","403","9.1","3036","3.2","0"],["qwen-3b","15","0","0.51","22.1","242","10.9","2486","6.2","0"],["gemini","15","0","1.18","5.9","155","39.0","0","0.0","0.0002"]]} ohl={2} cs={[["Reas","3"],["Know","3"],["Ctx","2"],["Coh","1"],["Cal","2"],["Str","5"]]} os={[["Lat","5"],["Cost","7"],["Priv","3"],["Thr","4"],["Inf","6"],["Up","4"]]}/>
<TC num="TC-03" t="Information Extraction" desc="SROIE, n=4. JSON schema." ch={["Model","MacF1","MicF1","EM","Schema","Halluc","F1c"]} cr={[["Qwen-0.5B","0.167","0.222","0.000","0.500","0.000","0.222"],["Qwen-1.5B","0.025","0.042","0.000","0.200","0.375","0.042"],["SmolLM2","0.479","0.500","0.000","1.000","0.167","0.500"],["Gemini","0.188","0.300","0.000","0.250","0.250","0.300"]]} chl={2} oh={["Model","Lat/d","Thru","GPU","InTok","OutTok"]} or={[["Qwen-0.5B","14.6","4.1","","373","96"],["Qwen-1.5B","17.5","3.4","","383","64"],["SmolLM2","36.1","1.7","","488","53"],["Gemini","0.86","70.0","","495","16"]]} ohl={3} cs={[["Reas","2"],["Know","2"],["Ctx","2"],["Coh","1"],["Cal","2"],["Str","5"]]} os={[["Lat","6"],["Cost","8"],["Priv","8"],["Thr","5"],["Inf","8"],["Up","6"]]}/>
<TC num="TC-04" t="Summarization" desc="CNN/DM, n=30. Temp 0.0." ch={["Run","Model","N","R-1","R-2","R-L","Sim","Comp","Hal","LenV","Loss"]} cr={[["Def","distilbart","30","0.434","0.204","0.313","0.765","0.198","0.30","1.00","0.83"],["Fast","t5-sm","30","0.117","0.059","0.081","0.268","0.051","0.70","0.30","0.93"],["Gem","flash","11","0.123","0.018","0.088","0.376","0.028","0.45","0.27","1.00"]]} chl={0} oh={["Run","Model","N","Lat","Thru","Mem","InTok","Wall"]} or={[["Def","distilbart","30","13.2s","5.0t/s","1171M","314","~396s"],["Fast","t5-sm","30","0.71s","15.4t/s","682M","318","~21s"],["Gem","flash","11","0.90s","9.5t/s","API","329","—"]]} ohl={1} cs={[["Reas","3"],["Know","2"],["Ctx","3"],["Coh","1"],["Cal","3"],["Str","3"]]} os={[["Lat","5"],["Cost","6"],["Priv","4"],["Thr","5"],["Inf","6"],["Up","5"]]}/>
<TC num="TC-05" t="Code Generation" desc="MBPP, 4-min. Temp 0.2." ch={["Model","N","p@1","Syn","RT","Logic","Fmt","Sig","Instr"]} cr={[["Qwen-0.5B","20","0.100","0.25","0.25","0.40","0.75","0.75","0.75"],["DeepSeek","6","0.167","0.67","0.00","0.17","0.00","0.33","0.00"],["Qwen-1.5B","3","0.667","0.33","0.00","0.00","0.67","0.67","0.67"],["Gemini","20","0.150","0.10","0.45","0.30","0.55","0.55","0.55"]]} oh={["Model","Bgt","Done","Lat","P95","TPS","RAM","OutT"]} or={[["Qwen-0.5B","4m","20","6.1","9.6","7.0","0.01","41"],["DeepSeek","4m","6","45.8","50.0","1.3","0.01","59"],["Qwen-1.5B","4m","3","95.0","125","0.58","0.01","54"],["Gemini","4m","13","0.67","0.87","110","0.01","60"]]} ohl={3} cs={[["Reas","6"],["Know","4"],["Ctx","3"],["Coh","1"],["Cal","4"],["Str","7"]]} os={[["Lat","5"],["Cost","6"],["Priv","3"],["Thr","4"],["Inf","6"],["Up","4"]]}/>
<TC num="TC-06" t="Instruction Following" desc="5 prompts × 4. Temp 0.0." ch={["Model","N","Pass","Constr","Fmt","Len","Lex"]} cr={[["Qwen-0.5B","20","0.40","0.40","0.00","0.50","0.50"],["DeepSeek","20","0.40","0.40","1.00","0.50","0.00"],["gemini","13","1.00","0.00","—","—","—"]]} chl={2} oh={["Model","Lat","TPS","Mem","OutT","Note"]} or={[["Qwen","17.9","4.8","−9","86","overgen"],["DeepSeek","42.8","2.3","73","100","slow"],["gemini","0.98","—","—","0","rate-lim"]]} ohl={2} cs={[["Reas","2"],["Know","1"],["Ctx","1"],["Coh","1"],["Cal","2"],["Str","5"]]} os={[["Lat","5"],["Cost","6"],["Priv","3"],["Thr","4"],["Inf","6"],["Up","4"]]}/>
<TC num="TC-07" t="Mathematical Reasoning" desc="GSM8K+SVAMP, 20–130/model." ch={["Model","Acc%","P@3","MajV","Var","Hal%","Rob%","ConfE%"]} cr={[["orca_7b","30","65.7","21.6","22.1","35","70","23.3"],["gemma_2b","20.8","50.3","11.1","16.6","39.6","30","26.4"],["phi3","19.2","47.3","9.7","15.7","40.4","32","26.9"],["mistral_7b","10","27.1","2.8","9.1","45","10","30"],["gemini","38.3","76.5","32.8","24.0","30.8","85","20.6"]]} chl={4} oh={["Model","Con%","Stab%","Rep%","Fmt%","Trc%","Err%","ECE","Lat","Thr","RAM","N"]} or={[["orca","30","30","30","95","90","75","0","97.9","0.61","8G","20"],["gemma","100","33","33","95","90","75","0","10.2","5.86","4G","130"],["phi3","100","17","17","95","90","75","0","28.4","2.11","8G","130"],["mistral","100","0","0","95","90","75","0","20.4","2.94","12G","110"],["gemini","38","38","38","98","95","75","0","1.08","55.8","0","60"]]} ohl={4} cs={[["Reas","7"],["Know","3"],["Ctx","2"],["Coh","1"],["Cal","5"],["Str","3"]]} os={[["Lat","3"],["Cost","3"],["Priv","2"],["Thr","3"],["Inf","3"],["Up","3"]]}/>
<TC num="TC-08" t="Retrieval-Grounded QA" desc="SQuAD, n=30. Max 80 tok." ch={["Model","N","EM","F1","CtxU","LenA","Hal","Uns","Part"]} cr={[["Qwen-0.5B","30","66.67","71.26","96.67","86.67","3.33","3.33","13.33"],["DeepSeek","30","36.67","48.05","46.67","50.00","53.33","53.33","30.00"],["gemini","30","63.33","77.78","83.33","90.00","16.67","16.67","26.67"]]} chl={0} oh={["Model","Lat ms","P50","P95","TPS","OutT","InT","Mem","Wall"]} or={[["Qwen-0.5B","5534","6442","8079","4.2","702","197","0","166"],["DeepSeek","17565","16642","41459","1.4","731","222","0","529"],["gemini","829","829","1056","6.4","159","191","0","—"]]} ohl={2} cs={[["Reas","2"],["Know","2"],["Ctx","3"],["Coh","1"],["Cal","3"],["Str","2"]]} os={[["Lat","6"],["Cost","8"],["Priv","8"],["Thr","5"],["Inf","8"],["Up","6"]]}/>
</Sec>

<Sec title="7. SLM capability limits (IC × MC scatter)">
<P>Each test case plotted on two axes: Inherent Complexity (x, unfixable) vs Mitigable Complexity (y, fixable). Green region = SLM-ready. Amber region = engineer-fixable. Red region = capability cliff. Hover dots for SCI decomposition. The purple dashed line at IC=2 marks the empirical breaking point.</P>
<div style={{display:"flex",flexWrap:"wrap",gap:12,marginBottom:16,fontSize:11,color:"#888"}}>
  <span style={{display:"flex",alignItems:"center",gap:4}}><span style={{width:12,height:12,borderRadius:"50%",background:"#639922"}}/>Pass</span>
  <span style={{display:"flex",alignItems:"center",gap:4}}><span style={{width:12,height:12,borderRadius:"50%",background:"#A32D2D"}}/>Fail</span>
  <span style={{display:"flex",alignItems:"center",gap:4}}><span style={{width:12,height:12,borderRadius:"50%",background:"#BA7517"}}/>Extrapolated</span>
  <span style={{display:"flex",alignItems:"center",gap:4}}><span style={{width:18,height:0,borderTop:"2px dashed #534AB7"}}/>IC break</span>
</div>
{LIM.map(tc=><LimitScatter key={tc.num} tc={tc}/>)}
</Sec>

<Sec title="8. Cross-task patterns">
{[["IC is the dominant axis","The breaking point IC ≥ 2–3 holds across all 8 task families. Maths (IC break=3), Code (IC break=3), QA (IC break=2), Classification (IC break=2). D1 (logical steps) and D2 (state tracking) account for >80% of the IC variance in failed subtasks."],
["MC failures are systematically fixable","Text generation and instruction following failures cluster at MC ≥ 3 with IC ≤ 1. These are not capability problems — they're constraint-adherence problems. Constrained decoding, post-processing validation, or output templates would shift them into the SLM-ready quadrant without changing the model."],
["The IC/MC split predicts mitigation ROI","Tasks in the 'Engineer-fixable' quadrant (low IC, high MC) have the highest return on engineering investment. Tasks on the 'Capability cliff' (high IC) have zero ROI on output engineering — the model simply can't do the reasoning."],
["Domain tuning shifts IC, not MC","DistilBART (tuned) succeeds at IC=1 where t5-small (generic) fails at the same IC=1. Domain tuning effectively lowers the model's IC threshold by embedding task-specific reasoning patterns. But it doesn't help with MC — DistilBART still has 100% length violation."]].map(([t,b],i)=><div key={i} style={{padding:"10px 14px",background:"#f0f7e8",borderRadius:8,borderLeft:"3px solid #639922",marginBottom:8,fontSize:12,lineHeight:1.6}}><strong style={{color:"#3B6D11"}}>Pattern {i+1}: {t}</strong><br/>{b}</div>)}
</Sec>

<Sec title="9. Operational protocol: six-step deployment procedure">
<P>This section integrates the companion operational protocol into the empirical paper so the framework moves from descriptive findings to an executable decision workflow.</P>
<DecisionTree/>
</Sec>

<Sec title="10. Hybrid routing procedure">
<RoutingProcedure/>
</Sec>

<Sec title="11. Minimum viable evaluation protocol">
<EvaluationProtocol/>
</Sec>

<Sec title="12. Generalized decision rules">
<DecisionRules/>
</Sec>

<Sec title="13. Cost analysis and Pareto frontier synthesis">
<CostAnalysisSection/>
</Sec>

<Sec title="14. Contradictions and limitations">
<W>Gemini underperformance on classification (0.389). Possible: prompt sensitivity, flash-lite variant, n=16.</W>
<W>Qwen-1.5B worse than 0.5B on IE. Scaling inversion. Possible: instruction-tuning quality, n=4.</W>
<W>Uniform maths operational metrics suggest hardcoded defaults.</W>
<W>Zone 4 (Hybrid) not experimentally validated.</W>
<W>SCI scores author-assigned. Inter-rater reliability not tested.</W>
<W>Sample sizes 4–130. Need ≥500 for statistical confidence.</W>
</Sec>

<Sec title="Appendix A: Metric glossary + SCI">
<DT c h={["Metric","Definition","High=","Used"]} r={[["Accuracy","Match gold","Better","01,07"],["F1 (macro/micro/W)","Per-class/pooled/weighted","Quality","01,03"],["Exact Match","Verbatim","Precise","03,08"],["pass@1","Code passes tests","Correct","05"],["ROUGE-1/2/L","N-gram overlap","Alignment","04"],["Semantic Sim","Embedding cosine","Meaning","04"],["Constraint Sat","All met","Following","02,06"],["Schema Valid","JSON parseable","Structure","03"],["Hallucination","Unsupported info","Bad","03,04,07,08"],["Conf Error","Wrong+confident","Dangerous","07"],["Latency","Wall-clock/inference","Slower","All"],["Throughput","Inferences/sec","Capacity","All"],["Peak RAM","Max memory","Resources","02,04,05"]]}/>
<Sub title="SCI dimensions">
<DT c h={["","Name","0","1","2","Axis"]} r={[["D1","Logical steps","1","2–3","4+","IC"],["D2","State tracking","None","1 var","2+/stack","IC"],["D3","Knowledge","In prompt","Domain","External","IC"],["D4","Output transform","Copy","Reformat","Novel","MC"],["D5","Constraints","0–1","2","3+","MC"]]}/>
</Sub>
</Sec>

<Sec title="Appendix B: Sources">
<DT c h={["Source","URL"]} r={[["Repository","github.com/RiddhimaReddy01/small_language_models_usecases"],["SST-2","huggingface.co/datasets/stanfordnlp/sst2"],["Emotion","huggingface.co/datasets/dair-ai/emotion"],["AG News","huggingface.co/datasets/fancyzhx/ag_news"],["CNN/DailyMail","huggingface.co/datasets/abisee/cnn_dailymail"],["SROIE","rrc.cvc.uab.es/?ch=13"],["MBPP","huggingface.co/datasets/google-research-datasets/mbpp"],["SQuAD","huggingface.co/datasets/rajpurkar/squad"],["GSM8K","huggingface.co/datasets/openai/gsm8k"],["SVAMP","huggingface.co/datasets/ChilleD/SVAMP"],["Gemini","ai.google.dev"],["Ollama","ollama.com"]]}/>
</Sec>

</div>}
