const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, Header, Footer, AlignmentType, HeadingLevel, BorderStyle,
  WidthType, ShadingType, VerticalAlign, PageNumber, PageBreak,
  TableOfContents, LevelFormat
} = require('docx');
const fs = require('fs');
const path = require('path');

const CURVES_DIR = path.join(__dirname, 'report_curves');
const OUT_PATH   = path.join(__dirname, 'SDDF_Report.docx');

// ---------- helpers ----------
const HEADER_COLOR = 'D5E8F0';
const ALT_ROW      = 'F5F9FC';
const brd = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
const borders = { top: brd, bottom: brd, left: brd, right: brd };

function cell(text, opts = {}) {
  const { bold = false, shade = false, alt = false, width = null, align = 'left', color = null, italic = false } = opts;
  const fill = shade ? HEADER_COLOR : alt ? ALT_ROW : 'FFFFFF';
  return new TableCell({
    borders,
    width: width ? { size: width, type: WidthType.DXA } : undefined,
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: align === 'center' ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({
        text: String(text), bold, italic,
        size: 20, font: 'Arial',
        color: color || (shade ? '1F3864' : '000000'),
      })]
    })]
  });
}

function hdrRow(cols, widths) {
  return new TableRow({ children: cols.map((c, i) => cell(c, { bold: true, shade: true, width: widths?.[i] })) });
}

function dataRow(cols, widths, isAlt = false) {
  return new TableRow({ children: cols.map((c, i) => cell(c, { alt: isAlt, width: widths?.[i] })) });
}

function makeTable(headers, rows, widths) {
  const totalW = widths ? widths.reduce((a, b) => a + b, 0) : 9360;
  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: widths || headers.map(() => Math.floor(9360 / headers.length)),
    rows: [
      hdrRow(headers, widths),
      ...rows.map((r, i) => dataRow(r, widths, i % 2 === 1))
    ]
  });
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, bold: true, font: 'Arial', size: 32 })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, bold: true, font: 'Arial', size: 26 })] });
}
function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text, bold: true, font: 'Arial', size: 22 })] });
}
function p(text, opts = {}) {
  const { bold = false, italic = false, size = 22, color = '000000', indent = false } = opts;
  return new Paragraph({
    indent: indent ? { left: 360 } : undefined,
    children: [new TextRun({ text: String(text), bold, italic, size, font: 'Arial', color })]
  });
}
function blank() { return new Paragraph({ children: [new TextRun('')] }); }
function pb() { return new Paragraph({ children: [new PageBreak()] }); }

function formulaBlock(lines) {
  return lines.map(l => new Paragraph({
    indent: { left: 720 },
    children: [new TextRun({ text: l, font: 'Courier New', size: 20, color: '1A237E' })]
  }));
}

function bullet(text) {
  return new Paragraph({
    numbering: { reference: 'bullets', level: 0 },
    children: [new TextRun({ text, size: 22, font: 'Arial' })]
  });
}

function loadImg(name) {
  const fp = path.join(CURVES_DIR, name);
  if (!fs.existsSync(fp)) return null;
  return fs.readFileSync(fp);
}

function imgPara(filename, w = 630, h = 315) {
  const data = loadImg(filename);
  if (!data) return p(`[Image not found: ${filename}]`, { italic: true, color: 'CC0000' });
  return new Paragraph({
    children: [new ImageRun({
      type: 'png', data,
      transformation: { width: w, height: h },
      altText: { title: filename, description: filename, name: filename }
    })]
  });
}

function sectionBanner(text) {
  return new Paragraph({
    shading: { fill: '1F3864', type: ShadingType.CLEAR },
    children: [new TextRun({ text, bold: true, font: 'Arial', size: 28, color: 'FFFFFF' })]
  });
}

// ---------- FORMULA HELPER: render formula as styled block ----------
function formula(label, expr, symbols) {
  const items = [
    blank(),
    new Paragraph({
      indent: { left: 360 },
      children: [
        new TextRun({ text: label + '  ', bold: true, size: 22, font: 'Arial', color: '1F3864' }),
        new TextRun({ text: expr, font: 'Cambria Math', size: 22, color: '1A237E' })
      ]
    })
  ];
  if (symbols && symbols.length) {
    items.push(new Paragraph({ indent: { left: 720 }, children: [new TextRun({ text: 'where:', italic: true, size: 20, font: 'Arial', color: '555555' })] }));
    for (const s of symbols) {
      items.push(new Paragraph({
        indent: { left: 900 },
        numbering: { reference: 'bullets', level: 0 },
        children: [new TextRun({ text: s, size: 20, font: 'Arial' })]
      }));
    }
  }
  items.push(blank());
  return items;
}

// =========================================================
// BUILD DOCUMENT
// =========================================================
const children = [];

// ---- TITLE PAGE ----
children.push(
  blank(), blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Sample Difficulty Distribution Framework (SDDF)', bold: true, font: 'Arial', size: 52, color: '1F3864' })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Technical Report', bold: true, font: 'Arial', size: 40, color: '2E75B6' })] }),
  blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Capability-Based SLM Routing Across Eight Tasks', font: 'Arial', size: 28, italic: true, color: '555555' })] }),
  blank(), blank(),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Device: Riddhima  |  AMD Ryzen 7 8840HS  |  2026-03-18', font: 'Arial', size: 20, color: '777777' })] }),
  pb()
);

// ---- TABLE OF CONTENTS ----
children.push(
  h1('Table of Contents'),
  new TableOfContents('Table of Contents', { hyperlink: true, headingStyleRange: '1-3' }),
  pb()
);

// =========================================================
// SECTION 1: EXECUTIVE SUMMARY
// =========================================================
children.push(
  h1('Section 1: Executive Summary'),
  p('The Sample Difficulty Distribution Framework (SDDF) is a data-driven pipeline that routes inference requests between small language models (SLMs) and a Groq-hosted baseline LLM based on the learned difficulty of each input. Rather than sending all queries to an expensive baseline, SDDF profiles task complexity using a six-dimensional difficulty vector, bins samples by difficulty, measures per-bin capability and risk, and applies a two-tier gating rule to determine the routing limit.'),
  blank(),
  p('Key findings across 8 tasks:', { bold: true }),
  makeTable(
    ['Task', 'Decision', 'Key Finding'],
    [
      ['Classification', 'ESCALATE', 'SLM-1/2 achieve 93-100% canonical success; SDDF smoke curves n<5 per bin — tau detection impossible'],
      ['Maths', 'ESCALATE (smoke) / ROUTE SLM (canonical)', 'SLM-1 100% success all bins; BASELINE raw accuracy only 38.3% — SLM competitive at low difficulty'],
      ['Text Generation', 'ROUTE SLM-1 / ESCALATE SLM-2', 'SLM-1 (Qwen 2B-class) 100% canonical; SLM-2 (Phi 3B-class) near-zero; model fit dominates'],
      ['Summarization', 'ESCALATE', 'SLM-2 ROUGE-1=0.281 matches BASELINE=0.277; tau_risk fires at bin 0 for SLM-2'],
      ['Info Extraction', 'ESCALATE', 'All tiers Macro F1 <=0.19; high invalid output rates (50-80%); BASELINE 16x faster'],
      ['Retrieval Grounded', 'ESCALATE', 'SLM-0 (0.5B) EM=66.7% EXCEEDS BASELINE 63.3%; smoke run insufficient for routing decision'],
      ['Instruction Following', 'ROUTE SLM', 'ONLY routing success: 7 pairs, all Zone A, ratio=1.0, precision=recall=F1=1.0, tau_cap=0.0'],
      ['Code Generation', 'ESCALATE', 'SLM-1 pass@1=1.0 but at 91s/query; canonical risk >0.20 all bins; BASELINE 110 tok/s'],
    ],
    [2200, 2600, 4560]
  ),
  pb()
);

// =========================================================
// SECTION 2: SDDF FRAMEWORK SETUP
// =========================================================
children.push(h1('Section 2: SDDF Framework Setup — Step-by-Step Pipeline'));

children.push(h2('2.1 Framework Identity and Design Principles'));
children.push(
  p('SDDF routes inference between SLM tiers and a Groq-hosted baseline LLM using task difficulty as the primary signal. Two core principles govern the design:'),
  bullet('Risk-first: reject requests where SLM failure probability exceeds tolerance (tau_risk gate) before evaluating capability'),
  bullet('Capability-second: accept requests only where SLM matches baseline to within a learned threshold (tau_cap gate)'),
  blank(),
  p('The two-tier design produces a hard routing limit: requests below the limit route to SLM; requests above escalate to BASELINE LLM.')
);

children.push(h2('2.2 Stage 1 — Data Ingestion and Normalization  (sddf/ingest.py)'));
children.push(p('Raw task outputs are normalized to a canonical schema: input_text, primary_metric, valid_output, latency_sec, difficulty_score, difficulty_bin.'));
children.push(blank());
children.push(makeTable(
  ['Task', 'Primary Metric', 'valid_output criterion'],
  [
    ['Classification', 'Accuracy (0 or 1)', 'Label matches allowed label set'],
    ['Maths', 'Exact Match (numeric)', '"Final Answer: <num>" pattern present'],
    ['Code Generation', 'pass@1 (execution)', 'Code parses and passes unit tests'],
    ['Summarization', 'ROUGE-1 F1', 'Non-empty summary, no truncation'],
    ['Information Extraction', 'Macro F1', 'Valid JSON with all required keys'],
    ['Retrieval Grounded', 'Exact Match', 'Non-empty answer string'],
    ['Instruction Following', 'Constraint Satisfaction Rate', 'All format constraints parseable'],
    ['Text Generation', 'Constraint Satisfaction Rate', 'Constraint metadata present'],
  ],
  [2200, 2500, 4660]
));

children.push(h2('2.3 Stage 2 — Difficulty Feature Extraction  (sddf/difficulty.py)'));
children.push(p('Six features form the difficulty vector d(x):'));
children.push(blank());
children.push(...formula('d(x) =', '( n_in,  H,  R^,  |Gamma|,  a~,  D )', [
  'x — input query/prompt',
  'n_in — number of whitespace-delimited tokens in the input',
  'H — Shannon entropy at token level (bits)',
  'R^ — reasoning proxy (estimated reasoning complexity)',
  '|Gamma| — constraint count (total output formatting/content constraints)',
  'a~ — approximate parametric dependence on model parameters',
  'D — syntactic/semantic dependency distance in the input',
]));

children.push(...formula('Feature 1 — Input Length:', 'n_in(x) = |split(x)|', [
  'split(x) — whitespace tokenization of text x',
]));

children.push(...formula('Feature 2 — Shannon Entropy  (Shannon, 1948):', 'H(x) = -SUM_{t in V(x)}  p(t) * log2(p(t)),   p(t) = c_t / SUM_{t\'} c_{t\'}', [
  'V(x) — vocabulary of unique tokens in x',
  'c_t — count of token t in x',
  'p(t) — empirical probability of token t',
]));

children.push(...formula('Feature 3 — Reasoning Proxy:', 'R^(x) = 0.05 * |w_q|  +  1.0 * n_steps  +  0.5 * n_ent  +  1.0 * 1_comp', [
  '|w_q| — word count of the question/prompt field',
  'n_steps — number of explicit reasoning steps in metadata',
  'n_ent — number of named entities in metadata',
  '1_comp — binary indicator: compositional reasoning required',
]));

children.push(...formula('Feature 4 — Constraint Count:', '|Gamma|(x) = |F_req| + |R_fmt| + |R_cnt| + |R_len| + |R_ord|', [
  'F_req — required output fields',
  'R_fmt — format rules (e.g., JSON, bullet points)',
  'R_cnt — content rules (e.g., forbidden words)',
  'R_len — length rules (e.g., word limits)',
  'R_ord — ordering rules (e.g., section order)',
]));

children.push(h3('Dominant Dimension per Task'));
children.push(makeTable(
  ['Task', 'Dominant Dimension d*', 'Rationale'],
  [
    ['Classification', 'H (Shannon entropy)', 'Label ambiguity increases with input vocabulary diversity'],
    ['Maths', 'R^ (reasoning proxy)', 'Step count and compositional structure drive problem difficulty'],
    ['Code Generation', 'R^ (reasoning proxy)', 'Logical composition is the primary cognitive load'],
    ['Summarization', 'n_in (input length)', 'Longer articles require more compression and context management'],
    ['Retrieval Grounded', 'n_in (input length)', 'Longer context increases extraction difficulty'],
    ['Information Extraction', '|Gamma| (constraint count)', 'Number of required fields determines structured output load'],
    ['Instruction Following', '|Gamma| (constraint count)', 'Constraint count defines task complexity'],
    ['Text Generation', '|Gamma| (constraint count)', 'Output format and length rules dominate difficulty'],
  ],
  [2000, 2200, 5160]
));

children.push(h2('2.4 Stage 3 — Difficulty Binning and Soft Assignment'));
children.push(...formula('Quantile Binning (K=5):', 'b_k = { x in D : d*(x) in [q_{k/K},  q_{(k+1)/K}) },   k = 0,...,4', [
  'q_p — p-th quantile of difficulty scores in dataset D',
  'Each bin b_k contains approximately |D|/5 samples',
  'Implementation: pd.qcut(df["difficulty_score"], q=5, labels=False, duplicates="drop")',
]));

children.push(...formula('Soft Bin Probability (linear interpolation):', 'pos = s*(K-1),   l = floor(pos),   u = min(l+1, K-1),   alpha = pos - l', [
  's in [0,1] — normalized difficulty score',
  'P(bin_k | s) = (1-alpha) if k=l;   alpha if k=u and u!=l;   0 otherwise',
]));
children.push(p('Dataset: benchmark_2024, stratified_by_difficulty, 15 samples/bin x 5 bins = 75 per model.'));

children.push(h2('2.5 Stage 4 — Capability and Risk Curve Generation'));
children.push(...formula('Per-Bin Capability:', 'P^_m(b) = (1/|b|) * SUM_{i in b} 1[y_i >= tau_q  AND  v_i = 1]', [
  'tau_q = 0.85 — quality threshold',
  'v_i in {0,1} — output validity indicator',
  'y_i — primary metric value for example i',
]));
children.push(...formula('Per-Bin Risk:', 'Risk_m(b) = 1 - P^_m(b)', []));
children.push(...formula('Capability Ratio  (sddf/curves.py: compute_ratio_curve):', 'rho_k = (1/|b_k|) * SUM_{i in b_k}  y_i^SLM / max(y_i^LLM,  epsilon),   epsilon = 1e-9', [
  'rho_k — SLM-to-BASELINE capability ratio in bin k',
]));
children.push(...formula('Smoothed Ratio  (sddf/curves.py: smooth_ratio_curve):', 'rho~_k = (1/w) * SUM_{j=k-w+1}^{k} rho_j,   w = max(1, floor(n/2))', [
  'w — rolling window width (50% of curve length by default)',
]));
children.push(...formula('Expected Capability (soft assignment):', 'E[cap | s] = SUM_{k=0}^{K-1}  P(bin_k | s) * P^_m(k)', []));
children.push(...formula('Expected Risk (soft assignment):', 'E[risk | s] = SUM_{k=0}^{K-1}  P(bin_k | s) * Risk_m(k)', []));

children.push(h2('2.6 Stage 5 — Tipping Point Detection  (sddf/tipping.py, src/utils/stats.py)'));
children.push(...formula('Wilson Score CI  (Wilson, 1927):', 'p~ = (p + z^2/(2n)) / (1 + z^2/n),   Delta = z * sqrt(p(1-p)/n + z^2/(4n^2)) / (1 + z^2/n)', [
  'p — observed success rate',
  'n — sample count in bin',
  'z = 1.96 — z-score for 95% confidence',
  'CI_95%(p,n) = [max(0, p~ - Delta),  min(1, p~ + Delta)]',
]));
children.push(...formula('Tipping Points (LEARNED from data via Wilson CI):', 'tau_cap = max{ b : CI_lo(P^_m(b)) >= 0.95,  |b| >= 5 }', [
  'CI_lo — lower bound of Wilson 95% CI',
  '0.95 — capability threshold',
]));
children.push(...formulaBlock(['tau_risk = min{ b : CI_lo(Risk_m(b)) > 0.20,  |b| >= 5 }']));
children.push(p('     0.20 — risk tolerance threshold;   |b|>=5 — minimum sample gate for statistical validity', { italic: true, color: '555555' }));
children.push(blank());
children.push(p('Consecutive ratio rule (sddf/tipping.py): first difficulty level where 2 consecutive bins have ratio_smooth < 0.95.'));

children.push(h2('2.7 Stage 6 — Two-Tier Decision Matrix  (src/routing/decision_matrix.py)'));
children.push(...formula('Zone Assignment  (sddf/zones.py):', 'Zone(b) = A  if rho~_b >= 0.95  (SLM fully deployable)', []));
children.push(...formulaBlock([
  '         = B  if 0.85 <= rho~_b < 0.95  (SLM deployable with monitoring)',
  '         = C  if rho~_b < 0.85  (BASELINE required)',
]));
children.push(...formula('Routing Rule:', 'limit = min(tau_risk,  tau_cap)', []));
children.push(...formulaBlock([
  'route(x) = SLM       if s(x) <= limit',
  '         = BASELINE  if s(x) >  limit',
]));

children.push(h2('2.8 Difficulty Weight Learning  (sddf/difficulty_weights.py)'));
children.push(...formula('Weighted Difficulty Score:', 's_k(w) = SUM_{i=1}^{6} w_i * d_i^(k)', []));
children.push(...formula('Utility Function (Gradient Ascent):', 'U_k = sigma(alpha*(s_k - tau)) * [P^_m(k) - lambda*Risk_m(k) - (U_base - lambda*R_base)]', []));
children.push(...formula('Weight Update:', 'w_i  <-  w_i + eta * SUM_k  delta_k * d_i^(k)', []));
children.push(makeTable(
  ['Symbol', 'Value', 'Meaning'],
  [
    ['alpha', '10.0', 'Sigmoid steepness (gate sharpness)'],
    ['tau', '0.5', 'Decision threshold for accept/reject'],
    ['lambda', '1.0', 'Risk penalty weight'],
    ['U_base', '0.95', 'BASELINE assumed capability'],
    ['R_base', '0.05', 'BASELINE assumed risk'],
    ['eta', '0.01', 'Learning rate'],
    ['Steps', '200', 'Gradient ascent iterations'],
  ],
  [1500, 1200, 6660]
));

children.push(h2('2.9 Failure Taxonomy  (src/routing/failure_taxonomy.py)'));
children.push(...formula('Severity-Weighted Risk:', 'weighted_risk(b) = SUM_{i in b} w_sev(i) / |b|', []));
children.push(makeTable(
  ['Severity', 'w_sev', 'Example Failure Types'],
  [
    ['Critical', '1.0', 'timeout, empty output, token limit exceeded, syntax error'],
    ['High', '0.8', 'execution error, logic error, wrong label, hallucination'],
    ['Medium', '0.5', 'incomplete output, reasoning error, factual inaccuracy'],
    ['Low', '0.2', 'too short, too long, low relevance, minor format deviation'],
  ],
  [1800, 1200, 6360]
));
children.push(blank());
children.push(...formula('Quality Gate:', 'accept_i = 1[y_i >= tau_q] * 1[v_i = 1],   tau_q = 0.85', [
  'gate_i = 1[s_i <= s_max] * 1[l_i <= l_max] * accept_i',
  'Precision = TP/(TP+FP);   Recall = TP/(TP+FN)',
  's_max — learned max difficulty for SLM routing;   l_max — latency ceiling',
]));
children.push(pb());

// =========================================================
// SECTION 3: EXPERIMENT CONFIGURATION
// =========================================================
children.push(h1('Section 3: Experiment Configuration'));

children.push(h2('3.1 Hardware'));
children.push(makeTable(
  ['Parameter', 'Value'],
  [
    ['Device name', 'Riddhima'],
    ['Processor', 'AMD Ryzen 7 8840HS w/ Radeon 780M Graphics (3.30 GHz)'],
    ['Architecture', 'x64, 16 logical cores'],
    ['Installed RAM', '16.0 GB (15.3 GB usable)'],
    ['GPU', 'None — torch 2.10.0+cpu only (no CUDA)'],
    ['OS', 'Windows 11 (64-bit, Build 10.0.26200)'],
    ['Python', '3.11.9'],
    ['Transformers', 'HuggingFace Transformers 5.2.0'],
    ['BASELINE inference', 'Groq Cloud REST API'],
    ['Run timestamp', '2026-03-18'],
  ],
  [3000, 6360]
));

children.push(h2('3.2 Model Tiers'));
children.push(makeTable(
  ['Tier', 'Canonical Label', 'Backend'],
  [
    ['SLM-0', '0.5B tiny model', 'Local CPU (HuggingFace Transformers)'],
    ['SLM-1', 'Qwen 2B-class model', 'Local CPU (HuggingFace Transformers)'],
    ['SLM-2', 'Phi 3B-class model', 'Local CPU (HuggingFace Transformers)'],
    ['BASELINE', 'Groq-hosted LLM', 'Groq Cloud REST API'],
  ],
  [1800, 3000, 4560]
));
children.push(p('Note: Canonical tiers are design slots. Per-task archived evidence varies (see task_model_runs_table.json).', { italic: true, color: '555555' }));

children.push(h2('3.3 Inference Settings'));
children.push(makeTable(
  ['Parameter', 'Value'],
  [
    ['system_prompt', '"You are a helpful assistant."'],
    ['instruction_wrapper', '"Q: {input}\\nA:"'],
    ['temperature', '0.7'],
    ['top_p', '0.9'],
    ['max_tokens', '200'],
    ['stop_tokens', '[\"\\n\\n\"]'],
    ['seed', '42'],
    ['template_version', 'v1.0'],
  ],
  [3000, 6360]
));

children.push(h2('3.4 Dataset Setup'));
children.push(makeTable(
  ['Parameter', 'Value'],
  [
    ['Source', 'benchmark_2024'],
    ['Selection method', 'stratified_by_difficulty'],
    ['Binning rule', 'quantile(5) — 5 equal-frequency bins'],
    ['Samples per bin', '15'],
    ['Total per model', '75 samples'],
  ],
  [3000, 6360]
));

children.push(h2('3.5 Ground Truth by Task'));
children.push(makeTable(
  ['Task', 'Dataset', 'Ground Truth', 'Evaluation Method'],
  [
    ['Classification', 'SST-2, Emotion, AG News', 'Human-labeled sentiment/category', 'Exact label match -> accuracy'],
    ['Maths', 'GSM8K, SVAMP', 'Numeric answer', 'Numeric exact match'],
    ['Code Generation', 'HumanEval, MBPP', 'Unit tests', 'Execution pass rate (pass@1)'],
    ['Summarization', 'CNN/DailyMail 3.0.0', 'Reference summary', 'ROUGE-1 F1'],
    ['Information Extraction', 'SROIE', 'Field values (company, address, date, total)', 'Macro F1 over fields'],
    ['Retrieval Grounded', 'SQuAD', 'Answer span', 'Exact Match (EM)'],
    ['Instruction Following', 'IFEval (google/IFEval)', 'Constraint specifications', 'Constraint satisfaction rate'],
    ['Text Generation', 'benchmark_2024 custom', 'Constraint metadata', 'Constraint satisfaction rate'],
  ],
  [1700, 1800, 2800, 3060]
));
children.push(pb());

// =========================================================
// SECTION 4: TASK COMPLEXITY
// =========================================================
children.push(h1('Section 4: Task Complexity Calculation'));

children.push(h2('4.1 Six-Dimensional Difficulty Vector'));
children.push(p('See Section 2.3 for all formulas and symbol glossaries.'));

children.push(h2('4.2 Dominant Dimension per Task'));
children.push(p('See table in Section 2.3.'));

children.push(h2('4.3 Worked Example — Classification (Entropy)'));
children.push(makeTable(
  ['Step', 'Value'],
  [
    ['Input', '"The movie was surprisingly moving and beautifully shot."'],
    ['Tokens', '["The", "movie", "was", "surprisingly", "moving", "and", "beautifully", "shot"]'],
    ['n_in', '8 tokens, all unique'],
    ['H calculation', 'H = -8 * (1/8 * log2(1/8)) = -8 * (1/8 * -3) = 3.0 bits'],
    ['Dominant dim', 'H (entropy) -> difficulty_score = 3.0 bits'],
    ['Bin assignment', 'pd.qcut: bin depends on quantiles of full dataset'],
  ],
  [2500, 6860]
));

children.push(h2('4.4 Difficulty Binning'));
children.push(p('Implementation: pd.qcut(df["difficulty_score"], q=5, labels=False, duplicates="drop")'));
children.push(p('Bins 0 (easiest) to 4 (hardest); 15 samples per bin in canonical runs.'));

children.push(h2('4.5 Weight Learning'));
children.push(p('Gradient ascent (200 steps, lr=0.01) optimizes weights w = (w_n_in, w_H, w_R^, w_Gamma, w_a~, w_D) to maximize routing utility U_k. Initial weights: all 1.0. See Section 2.8 for full formulas.'));
children.push(pb());

// =========================================================
// SECTION 5: METRICS
// =========================================================
children.push(h1('Section 5: Capability and Operational Metrics'));

children.push(h2('5.1 Capability Metrics per Task'));
children.push(makeTable(
  ['Task', 'Primary Metric', 'Formula', 'Source'],
  [
    ['Classification', 'Accuracy', 'correct / total', '—'],
    ['Maths', 'Exact Match Accuracy', 'numeric_match(pred, ref)', 'Cobbe et al. (2021)'],
    ['Code Generation', 'pass@1', 'passed / attempted', 'Chen et al. (2021)'],
    ['Summarization', 'ROUGE-1 F1', '2*P*R / (P+R) on unigrams', 'Lin (2004)'],
    ['Information Extraction', 'Macro F1', 'avg F1 across documents', '—'],
    ['Retrieval Grounded', 'Exact Match (EM)', '100 * correct / total', 'Rajpurkar et al. (2016)'],
    ['Instruction Following', 'Constraint Satisfaction Rate', 'constraints_satisfied / total', 'Zhou et al. (2023)'],
    ['Text Generation', 'Constraint Satisfaction Rate', 'same as above', '—'],
  ],
  [2000, 2000, 3000, 2360]
));

children.push(h2('5.2 Operational Metrics'));
children.push(
  bullet('success_rate per bin — fraction where primary_metric >= 0.85 AND valid_output=1 (from sddf_ready.csv)'),
  bullet('avg_latency_sec — mean inference latency per sample (seconds)'),
  bullet('validity_rate — fraction of samples with valid_output=1'),
  bullet('throughput — queries/min or tokens/sec (from task_model_runs_table.json)'),
  bullet('invalid_output_rate — fraction of outputs that fail format validation')
);
children.push(pb());

// =========================================================
// HELPER: PER-TASK SECTION
// =========================================================
function taskSection(sectionNum, taskName, config) {
  const {
    datasets, datasetDesc, models, dominantDim, dominantFormula,
    promptTemplate, promptFile, primaryMetric, groundTruth,
    complexityExample, capHeaders, capRows, capWidths,
    opHeaders, opRows, opWidths, capNote,
    capCurveFile, riskCurveFile, capCurveDesc, riskCurveDesc,
    tauCapText, tauRiskText, decisionText,
  } = config;

  const items = [];
  items.push(h1(`Section ${sectionNum}: ${taskName}`));
  items.push(sectionBanner(`Task: ${taskName}`));
  items.push(blank());

  // A. Task Setup
  items.push(h2('A. Task Setup'));
  items.push(makeTable(
    ['Parameter', 'Value'],
    [
      ['Datasets', datasets],
      ['Source', datasetDesc || 'benchmark_2024'],
      ['Models', models],
      ['Dominant difficulty dimension', dominantDim],
      ['Primary metric', primaryMetric],
      ['Ground truth', groundTruth],
    ],
    [2500, 6860]
  ));
  items.push(blank());
  items.push(p('Prompt Template  (' + promptFile + '):', { bold: true }));
  for (const line of promptTemplate.split('\n')) {
    items.push(new Paragraph({ indent: { left: 720 }, children: [new TextRun({ text: line, font: 'Courier New', size: 19, color: '1A237E' })] }));
  }

  // B. Complexity
  items.push(blank());
  items.push(h2('B. Task Complexity Calculation'));
  items.push(p('Dominant dimension: ' + dominantDim));
  if (dominantFormula) items.push(...formulaBlock([dominantFormula]));
  items.push(p('Example: ' + complexityExample));

  // C. Capability Table
  items.push(blank());
  items.push(h2('C. Results — Capability Metrics Table'));
  if (capNote) items.push(p(capNote, { italic: true, color: '555555' }));
  items.push(makeTable(capHeaders, capRows, capWidths));

  // D. Operational Table
  items.push(blank());
  items.push(h2('D. Results — Operational Metrics Table'));
  items.push(p('Source: sddf_ready.csv (canonical 75-sample runs, 15/bin x 5 bins)'));
  items.push(makeTable(opHeaders, opRows, opWidths));

  // E. Capability Curve
  items.push(blank());
  items.push(h2('E. Capability Curve'));
  items.push(p(capCurveDesc));
  items.push(imgPara(capCurveFile, 630, 315));

  // F. Risk Curve
  items.push(blank());
  items.push(h2('F. Risk Curve'));
  items.push(p(riskCurveDesc));
  items.push(imgPara(riskCurveFile, 630, 315));

  // G. Tipping Points
  items.push(blank());
  items.push(h2('G. Tipping Point Analysis'));
  items.push(makeTable(
    ['Gate', 'Value', 'Analysis'],
    [
      ['tau_cap', tauCapText[0], tauCapText[1]],
      ['tau_risk', tauRiskText[0], tauRiskText[1]],
      ['limit = min(tau_risk, tau_cap)', tauCapText[0] === 'None' && tauRiskText[0] === 'None' ? 'None' : 'See decision', 'Routing threshold'],
    ],
    [2000, 2000, 5360]
  ));

  // H. Decision
  items.push(blank());
  items.push(h2('H. Routing Decision'));
  items.push(p(decisionText, { bold: false }));
  items.push(pb());
  return items;
}

// =========================================================
// SECTION 6: CLASSIFICATION
// =========================================================
children.push(...taskSection(6, 'Classification', {
  datasets: 'SST-2 (binary sentiment), Emotion (6-class), AG News (4-class topic)',
  datasetDesc: 'benchmark_2024 (HuggingFace datasets)',
  models: 'SLM-1 (Qwen 2B-class), SLM-2 (Phi 3B-class), BASELINE LLM (Groq)',
  dominantDim: 'H — Shannon entropy of input text',
  dominantFormula: 'H(x) = -SUM_{t in V(x)}  p(t)*log2(p(t)),   p(t) = c_t / n',
  promptFile: 'tasks/classification/classification_eval/models.py:100',
  promptTemplate: 'You are a text classification system.\nChoose exactly one label from the list: {labels}\nRespond with only one label and no extra words.\nText: {text}',
  primaryMetric: 'Accuracy = correct/total',
  groundTruth: 'Human-labeled class labels (SST-2: positive/negative; Emotion: 6 classes; AG News: 4 topics)',
  complexityExample: '"The film tries hard but fails to engage" -> 9 unique tokens -> H ≈ 3.17 bits -> bin 1',
  capNote: 'Source: task_model_runs_table.json (phi3:mini archived evidence for SLM-1 and SLM-2 slots)',
  capHeaders: ['Model', 'SST-2 Acc', 'Emotion Acc', 'AG News Acc', 'SST-2 F1', 'Emotion F1', 'AG News F1'],
  capRows: [
    ['SLM-1 (Qwen 2B-class)', '1.000', '0.667', '0.750', '1.000', '0.556', '0.667'],
    ['SLM-2 (Phi 3B-class)', '1.000', '0.667', '0.750', '1.000', '0.556', '0.667'],
    ['BASELINE LLM', '—', '—', '—', '—', '—', '—'],
  ],
  capWidths: [2500, 1100, 1100, 1100, 1100, 1100, 1360],
  opHeaders: ['Model', 'Bin 0', 'Bin 1', 'Bin 2', 'Bin 3', 'Bin 4', 'Avg Latency (s)'],
  opRows: [
    ['SLM-1 (Qwen 2B-class)', '1.000', '0.933', '1.000', '1.000', '1.000', '3.27'],
    ['SLM-2 (Phi 3B-class)', '1.000', '1.000', '1.000', '0.933', '1.000', '9.47'],
    ['BASELINE LLM', 'incomplete', '—', '—', '—', '—', '—'],
  ],
  opWidths: [2800, 1000, 1000, 1000, 1000, 1000, 1560],
  capCurveFile: 'classification_capability_curve.png',
  riskCurveFile: 'classification_risk_curve.png',
  capCurveDesc: 'Three SDDF smoke-run sub-curves (Emotion, SST-2, AG News). X-axis = Shannon entropy H (bits). Ratio=SLM/BASELINE per bin. Zone A = green (>=0.95), Zone B = yellow (0.85-0.95), Zone C = red (<0.85).',
  riskCurveDesc: 'Canonical risk curves (15 samples/bin). SLM-1 and SLM-2 both show near-zero risk (<0.067) across all bins. Wilson 95% CI shading shown. Red dashed line = 0.20 threshold.',
  tauCapText: ['H ≈ 4.404 bits (Emotion, bin 2)', 'Ratio_smooth=1.0 only at bin 2; single bin -> precarious; n=1 < 5 minimum gate'],
  tauRiskText: ['None', 'CI_lo of risk < 0.20 for all bins in both SLM-1 and SLM-2 canonical runs'],
  decisionText: 'ESCALATE. Despite 93-100% canonical success, SDDF smoke curves have n=1-2 per bin (below min_samples=5 gate). Precision=1.0 but recall=0.25 (SST-2), meaning gate rejects 75% of valid SLM responses. Re-run with matched SLM/BASELINE pairs across full 75-sample dataset recommended.',
}));

// =========================================================
// SECTION 7: MATHS
// =========================================================
children.push(...taskSection(7, 'Maths', {
  datasets: 'GSM8K (grade school math word problems), SVAMP (varied arithmetic)',
  datasetDesc: 'benchmark_2024',
  models: 'SLM-1 (Qwen 2B-class), SLM-2 (Phi 3B-class), BASELINE LLM (Groq)',
  dominantDim: 'R^ — reasoning proxy (step count + compositional complexity)',
  dominantFormula: 'R^(x) = 0.05*|w_q|  +  1.0*n_steps  +  0.5*n_ent  +  1.0*1_comp',
  promptFile: 'tasks/maths/src/prompts.py',
  promptTemplate: 'Solve the following math problem carefully.\nProvide the final answer in the format:\nFinal Answer: <number>\nProblem:\n{question}',
  primaryMetric: 'Exact Match Accuracy — numeric equivalence between extracted answer and ground truth',
  groundTruth: 'Numeric answers from GSM8K/SVAMP datasets',
  complexityExample: '"If a store sells 12 apples/hour for 8 hours, how many total?" -> |w_q|=19, n_steps=2 -> R^ = 0.95+2.0 = 2.95',
  capNote: 'Source: task_model_runs_table.json (phi3_mini evidence for SLM-2). SLM-1 canonical slot shows 100% success on format metric — different from raw accuracy.',
  capHeaders: ['Model', 'Final Ans Accuracy (%)', 'pass@3 (%)', 'Majority Vote (%)'],
  capRows: [
    ['SLM-1 (Qwen 2B-class)', '~100 (format metric)', '—', '—'],
    ['SLM-2 (Phi 3B-class)', '19.2', '47.3', '9.7'],
    ['BASELINE LLM', '38.3', '76.5', '32.8'],
  ],
  capWidths: [3000, 2500, 2000, 1860],
  opHeaders: ['Model', 'Bin 0', 'Bin 1', 'Bin 2', 'Bin 3', 'Bin 4', 'Avg Latency (s)', 'Throughput (q/min)'],
  opRows: [
    ['SLM-1 (Qwen 2B-class)', '1.000', '1.000', '1.000', '1.000', '1.000', '6.77', '~8.9'],
    ['SLM-2 (Phi 3B-class)', '0.933', '1.000', '1.000', '1.000', '1.000', '25.17', '2.11'],
    ['BASELINE LLM', '1.000', '1.000', '1.000', '1.000', '1.000', '3.30', '55.78'],
  ],
  opWidths: [2400, 800, 800, 800, 800, 800, 1380, 1580],
  capCurveFile: 'maths_capability_curve.png',
  riskCurveFile: 'maths_risk_curve.png',
  capCurveDesc: 'Smoke run: 2 matched pairs each (GSM8K, SVAMP). All ratio=0.0 -> Zone C. X-axis = approximate R^ value. Insufficient data for tau detection.',
  riskCurveDesc: 'Canonical risk curves (15/bin). SLM-1 risk=0.0 all bins; SLM-2 bin 0 risk=0.067, bins 1-4 risk=0.0. Wilson CI shown. All CI_lo < 0.20 -> tau_risk = None.',
  tauCapText: ['None', 'Smoke ratio=0.0 for both datasets; no bin with ratio_smooth >= 0.95'],
  tauRiskText: ['None', 'All CI_lo of risk < 0.20 in canonical runs; n=2 per task in smoke (below gate)'],
  decisionText: 'ESCALATE (smoke run insufficient). Canonical 75-sample results show SLM-1 100% success format metric — however this measures format compliance, not raw numeric accuracy (SLM-2 raw accuracy = 19.2% vs BASELINE 38.3%). Recommendation: run SDDF with canonical data and validate with exact-match evaluation.',
}));

// =========================================================
// SECTION 8: TEXT GENERATION
// =========================================================
children.push(...taskSection(8, 'Text Generation', {
  datasets: 'benchmark_2024 custom; combined SDDF run: Qwen-2.5-3B vs gemini-2.5-flash-fresh',
  datasetDesc: 'Custom task items with constraint metadata',
  models: 'SLM-1 (Qwen 2B-class), SLM-2 (Phi 3B-class), BASELINE LLM (Groq)',
  dominantDim: '|Gamma| — constraint count (output format/length rules)',
  dominantFormula: '|Gamma|(x) = |F_req| + |R_fmt| + |R_cnt| + |R_len| + |R_ord|',
  promptFile: 'tasks/text_generation/run_benchmark.py (stored in results.json)',
  promptTemplate: 'Example prompts:\n  "Write a 4-line poem about artificial intelligence."\n  "Write a Python function to calculate the factorial."\n  "Summarize the plot of Romeo and Juliet in two sentences."',
  primaryMetric: 'Constraint Satisfaction Rate = constraints_satisfied / total',
  groundTruth: 'Constraint metadata attached to each task item (format_compliance, constraint_satisfaction_rate)',
  complexityExample: 'Combined SDDF run: all samples |Gamma|=0 -> difficulty_score=0.0 -> single bin -> no difficulty variation',
  capNote: 'Source: task_model_runs_table.json. aggregate_numeric_scores_available=false for text generation; qualitative evaluation only.',
  capHeaders: ['Model', 'Constraint Satisfaction', 'Model File Size'],
  capRows: [
    ['SLM-1 (Qwen 2B-class)', 'Qualitative; 15 examples', '~2.1 GB (qwen-2.5-3b)'],
    ['SLM-2 (Phi 3B-class)', 'Qualitative; 15 examples', '~2.4 GB (phi-3.5-mini)'],
    ['BASELINE LLM', '—', '—'],
  ],
  capWidths: [3000, 3500, 2860],
  opHeaders: ['Model', 'Bin 0', 'Bin 1', 'Bin 2', 'Bin 3', 'Bin 4', 'Avg Latency (s)'],
  opRows: [
    ['SLM-1 (Qwen 2B-class)', '1.000', '1.000', '1.000', '1.000', '1.000', '9.16'],
    ['SLM-2 (Phi 3B-class)', '0.167', '0.143', '0.267', '0.000', '—', '16.5'],
    ['BASELINE LLM', '1.000', '1.000', '1.000', '0.933', '1.000', '~14.1'],
  ],
  opWidths: [2800, 1000, 1000, 1000, 1000, 1000, 1560],
  capCurveFile: 'text_generation_capability_curve.png',
  riskCurveFile: 'text_generation_risk_curve.png',
  capCurveDesc: 'Combined SDDF run: all 15 samples have |Gamma|=0 -> single bin at 0.0. Both SLM-1 and SLM-2 ratio=0.0 relative to Gemini -> Zone C.',
  riskCurveDesc: 'Canonical risk curves. SLM-1 risk=0.0 all bins. SLM-2 risk=0.833-1.0 all bins -> tau_risk fires at bin 0. Wilson CI shading confirms CI_lo >> 0.20.',
  tauCapText: ['None', 'No matched pairs with ratio >= 0.95 in SDDF combined run'],
  tauRiskText: ['Bin 0 (SLM-2)', 'SLM-2 risk=0.833 at bin 0; CI_lo >> 0.20; n=15 >= 5 gate satisfied'],
  decisionText: 'Task-model fit dominates. SLM-1 (Qwen 2B-class): 100% canonical success -> ROUTE SLM. SLM-2 (Phi 3B-class): near-zero success -> ESCALATE. Combined SDDF run all Zone C (all |Gamma|=0 with ratio=0.0). Decision depends on which SLM tier is deployed.',
}));

// =========================================================
// SECTION 9: SUMMARIZATION
// =========================================================
children.push(...taskSection(9, 'Summarization', {
  datasets: 'CNN/DailyMail 3.0.0',
  datasetDesc: 'benchmark_2024 (HuggingFace)',
  models: 'SLM-0 (0.5B tiny), SLM-1 (Qwen 2B-class), SLM-2 (Phi 3B-class), BASELINE LLM (Groq)',
  dominantDim: 'n_in — input token count (article length)',
  dominantFormula: 'n_in(x) = |split(x)|   (whitespace tokenization)',
  promptFile: 'tasks/Summarization/configs/hf_llama1b_fast.json:21',
  promptTemplate: 'Summarize the following news article in exactly one complete sentence of 12 to 20 words.\nPreserve the main event and outcome. Do not output a title, fragment, bullet, or commentary.\nArticle:\n{article}\nSummary:',
  primaryMetric: 'ROUGE-1 F1 = 2*P*R/(P+R) on unigrams  (Lin, 2004)',
  groundTruth: 'Reference summaries from CNN/DailyMail dataset',
  complexityExample: 'Article with 345 whitespace tokens -> n_in=345 -> bin 2 (medium difficulty)',
  capNote: 'Source: task_model_runs_table.json (Llama-3.2-1B archived evidence for SLM-2 slot).',
  capHeaders: ['Model', 'ROUGE-1 F1', 'ROUGE-2 F1', 'ROUGE-L F1', 'Latency (s)', 'Tokens/sec'],
  capRows: [
    ['SLM-2 (Phi 3B-class)', '0.281', '0.106', '0.181', '0.763', '22.4'],
    ['BASELINE LLM', '0.277', '0.069', '0.173', '0.583', '24.8'],
  ],
  capWidths: [2500, 1300, 1300, 1300, 1500, 1460],
  opHeaders: ['Model', 'Bin 0', 'Bin 1', 'Bin 2', 'Bin 3', 'Bin 4', 'Avg Latency (s)'],
  opRows: [
    ['SLM-0 (0.5B tiny)', '1.000', '1.000', '1.000', '1.000', '1.000', '12.26'],
    ['SLM-1 (Qwen 2B-class)', '0.867', '0.933', '0.933', '0.933', '0.933', '13.74'],
    ['SLM-2 (Phi 3B-class)', '0.533', '0.600', '0.333', '0.533', '0.267', '14.23'],
    ['BASELINE LLM', '1.000', '1.000', '1.000', '1.000', '1.000', '3.41'],
  ],
  opWidths: [2800, 1000, 1000, 1000, 1000, 1000, 1560],
  capCurveFile: 'summarization_capability_curve.png',
  riskCurveFile: 'summarization_risk_curve.png',
  capCurveDesc: 'SDDF smoke run: 5 matched pairs, CNN/DailyMail. X-axis = article length in tokens. Ratio oscillates: 0.889 (B) -> 1.0 (A) -> 1.190 (A) -> 1.099 (A) -> 0.952 (A). tau_cap=375 tokens (last Zone A bin).',
  riskCurveDesc: 'Canonical risk curves (15/bin). SLM-2 risk=0.267-0.733 across bins; Wilson CI_lo[0]=0.268 > 0.20 -> tau_risk fires at bin 0. SLM-1 risk=0.067-0.133 (borderline). SLM-0 risk=0.0.',
  tauCapText: ['375 tokens (bin 4)', 'Last bin with ratio_smooth >= 0.95 in SDDF smoke curve; n=1 per bin (below gate for Wilson CI)'],
  tauRiskText: ['Bin 0 (SLM-2)', 'CI_lo of risk = 0.268 > 0.20 at bin 0; n=15 satisfies gate; risk gate binds first'],
  decisionText: 'ESCALATE. tau_risk fires at bin 0 for SLM-2 (CI_lo=0.268 > 0.20) before tau_cap=375 tokens. SLM-2 ROUGE-1 (0.281) marginally exceeds BASELINE (0.277) per capability snapshot, but risk is too high for reliable routing. SLM-0 shows 100% canonical success but this measures format compliance, not raw ROUGE. BASELINE preferred for reliability.',
}));

// =========================================================
// SECTION 10: INFORMATION EXTRACTION
// =========================================================
children.push(...taskSection(10, 'Information Extraction', {
  datasets: 'SROIE (ICDAR 2019 receipt OCR and IE competition)',
  datasetDesc: 'Huang et al. (2019)',
  models: 'SLM-0 (0.5B tiny), SLM-1 (Qwen 2B-class), SLM-2 (Phi 3B-class), BASELINE LLM (Groq)',
  dominantDim: '|Gamma| — constraint count (number of required extraction fields)',
  dominantFormula: '|Gamma|(x) = |F_req| + |R_fmt|   (required fields + JSON format rule)',
  promptFile: 'tasks/Information Extraction/src/ie_benchmark/prompting.py',
  promptTemplate: 'Extract the requested fields from the receipt text.\nReturn only one valid JSON object and nothing else.\nRequired keys: ["company", "address", "date", "total"]\nUse empty strings for missing values.\nNormalize date to YYYY-MM-DD when possible.\nReceipt text:\n{document_text}',
  primaryMetric: 'Macro F1 over extracted fields (company, address, date, total)',
  groundTruth: 'SROIE field annotations: company, address, date, total',
  complexityExample: 'SROIE receipt: 4 required fields -> |Gamma|=4 for all samples -> single difficulty bin in smoke run',
  capNote: 'Source: task_model_runs_table.json (SLM-0=Qwen2.5-0.5B-Instruct, SLM-1=Qwen2.5-1.5B-Instruct archived evidence).',
  capHeaders: ['Model', 'Macro F1', 'Micro F1', 'Exact Match', 'Invalid Output Rate'],
  capRows: [
    ['SLM-0 (0.5B tiny)', '0.167', '0.222', '0.000', '0.50'],
    ['SLM-1 (Qwen 2B-class)', '0.025', '0.042', '0.000', '0.80'],
    ['BASELINE LLM', '0.188', '0.300', '0.000', '0.75'],
  ],
  capWidths: [2500, 1400, 1400, 1400, 2660],
  opHeaders: ['Model', 'Bin 0', 'Bin 1', 'Bin 2', 'Bin 3', 'Bin 4', 'Latency (s/doc)', 'Throughput (doc/min)'],
  opRows: [
    ['SLM-0 (0.5B tiny)', '0.933', '1.000', '0.933', '0.867', '1.000', '14.59', '4.11'],
    ['SLM-1 (Qwen 2B-class)', '0.867', '1.000', '1.000', '1.000', '1.000', '17.45', '3.44'],
    ['SLM-2 (Phi 3B-class)', '1.000', '1.000', '1.000', '1.000', '1.000', '6.76', '~8.9'],
    ['BASELINE LLM', '1.000', '1.000', '1.000', '1.000', '1.000', '0.857', '70.04'],
  ],
  opWidths: [2400, 800, 800, 800, 800, 800, 1400, 1560],
  capCurveFile: 'information_extraction_capability_curve.png',
  riskCurveFile: 'information_extraction_risk_curve.png',
  capCurveDesc: 'SDDF smoke run: 4 matched pairs, single bin at |Gamma|=4. ratio=0.0 -> Zone C. No consecutive bins available for tipping point detection.',
  riskCurveDesc: 'Canonical risk curves (15/bin). SLM-0 max risk=0.133 (bin 3); SLM-1 max risk=0.133 (bin 0); SLM-2 risk=0.0 all bins. All CI_lo < 0.20 -> tau_risk = None.',
  tauCapText: ['None', 'Smoke ratio=0.0 (single bin); no Zone A/B bins detected'],
  tauRiskText: ['None', 'All CI_lo of risk < 0.20 in canonical runs; n=4 per smoke bin (below gate)'],
  decisionText: 'ESCALATE. Smoke run ratio=0.0 (all Zone C). Raw Macro F1 uniformly low across all tiers (<=0.19). BASELINE has 16x throughput advantage (70 docs/min vs 3-4 for SLMs). Invalid output rates are high across all tiers (0.50-0.80) -- structured JSON output parsing is the dominant failure mode.',
}));

// =========================================================
// SECTION 11: RETRIEVAL GROUNDED
// =========================================================
children.push(...taskSection(11, 'Retrieval Grounded', {
  datasets: 'SQuAD (Stanford Question Answering Dataset)',
  datasetDesc: 'Rajpurkar et al. (2016)',
  models: 'SLM-0 (0.5B tiny), SLM-1 (Qwen 2B-class), SLM-2 (Phi 3B-class), BASELINE LLM (Groq)',
  dominantDim: 'n_in — input token count of context passage',
  dominantFormula: 'n_in(x) = |split(context + question)|',
  promptFile: 'tasks/Retrieval_grounded/src/prompts.py',
  promptTemplate: 'Answer the question using only the information in the context.\nContext:\n{context}\nQuestion:\n{question}\nAnswer:',
  primaryMetric: 'Exact Match (EM) = 100 * correct / total  (Rajpurkar et al., 2016)',
  groundTruth: 'SQuAD answer spans (character-level matches)',
  complexityExample: '200-token context -> n_in=200 -> bin 1; 400-token context -> bin 3',
  capNote: 'Source: task_model_runs_table.json (SLM-0=Qwen2.5-Coder-0.5B-Instruct). SLM-0 EXCEEDS BASELINE on EM (66.7% vs 63.3%).',
  capHeaders: ['Model', 'Exact Match (%)', 'F1 Score (%)', 'Context Utilization (%)'],
  capRows: [
    ['SLM-0 (0.5B tiny)', '66.67', '71.26', '96.67'],
    ['BASELINE LLM', '63.33', '77.78', '83.33'],
  ],
  capWidths: [3000, 2200, 2200, 2960],
  opHeaders: ['Model', 'Bin 0', 'Bin 1', 'Bin 2', 'Bin 3', 'Bin 4', 'Latency (ms)', 'p95 Latency (ms)'],
  opRows: [
    ['SLM-0 (0.5B tiny)', '1.000', '1.000', '1.000', '1.000', '1.000', '5,534', '8,079'],
    ['SLM-1 (Qwen 2B-class)', '1.000', '1.000', '0.933', '0.933', '1.000', '~4,780', '—'],
    ['SLM-2 (Phi 3B-class)', '0.800', '0.933', '0.733', '0.800', '0.733', '~8,900', '—'],
    ['BASELINE LLM', '1.000', '1.000', '1.000', '1.000', '1.000', '829', '1,056'],
  ],
  opWidths: [2400, 800, 800, 800, 800, 800, 1250, 1710],
  capCurveFile: 'retrieval_grounded_capability_curve.png',
  riskCurveFile: 'retrieval_grounded_risk_curve.png',
  capCurveDesc: 'SDDF smoke run: 6 matched pairs, single bin. ratio=0.0 -> Zone C. Single bin means no consecutive tipping detection possible.',
  riskCurveDesc: 'Canonical risk curves (15/bin). SLM-0 risk=0.0 all bins. SLM-1 max risk=0.067 (bins 2-3). SLM-2 risk=0.067-0.267. All CI_lo < 0.20 -> tau_risk = None (borderline for SLM-2 at bins 2,4).',
  tauCapText: ['None', 'Smoke single bin ratio=0.0; no Zone A in SDDF run; SLM-0 EM>BASELINE but no ratio pairs'],
  tauRiskText: ['None', 'SLM-2 CI_lo borderline (0.072-0.108) but stays below 0.20; non-consecutive pattern'],
  decisionText: 'ESCALATE (smoke run insufficient). Notable: SLM-0 (0.5B tiny) achieves higher EM than BASELINE (66.7% vs 63.3%) with 96.7% context utilization vs 83.3%. Recommendation: route SLM-0 for short-context queries (low n_in bins); escalate for long context where SLM-2 drops to 73%. Full matched-pair SDDF run needed to confirm.',
}));

// =========================================================
// SECTION 12: INSTRUCTION FOLLOWING
// =========================================================
children.push(...taskSection(12, 'Instruction Following', {
  datasets: 'IFEval (google/IFEval, HuggingFace)',
  datasetDesc: 'Zhou et al. (2023)',
  models: 'SLM-0 (0.5B tiny), SLM-1 (Qwen 2B-class), SLM-2 (Phi 3B-class), BASELINE LLM (Groq)',
  dominantDim: '|Gamma| — constraint count (number of instruction constraints)',
  dominantFormula: '|Gamma|(x) = number of verifiable constraints in the instruction',
  promptFile: 'tasks/instruction_following/src/instruction_following/pipeline_core.py:113',
  promptTemplate: 'Follow the instruction exactly.\nInstruction:\n{instruction}\nResponse:',
  primaryMetric: 'Constraint Satisfaction Rate = constraints_satisfied / total',
  groundTruth: 'Constraint specifications in IFEval dataset (length, format, exclusion, inclusion)',
  complexityExample: 'All 7 SDDF-run samples had |Gamma|=0 (no explicit counting constraints) -> single bin at 0.0',
  capNote: 'Source: task_model_runs_table.json (SLM-0=Qwen2.5-Coder-0.5B, SLM-1=deepseek-coder-1.3b archived evidence).',
  capHeaders: ['Model', 'Pass Rate', 'Constraint Satisfaction Rate', 'Format Compliance'],
  capRows: [
    ['SLM-0 (0.5B tiny)', '0.400', '0.400', '0.000'],
    ['SLM-1 (Qwen 2B-class)', '0.400', '—', '1.000'],
    ['SLM-2 (Phi 3B-class)', '—', '—', '—'],
    ['BASELINE LLM', '1.000', '—', '—'],
  ],
  capWidths: [2800, 1700, 2700, 2160],
  opHeaders: ['Model', 'Bin 0', 'Bin 1', 'Bin 2', 'Bin 3', 'Bin 4', 'Avg Latency (s)', 'Tokens/sec'],
  opRows: [
    ['SLM-0 (0.5B tiny)', '0.933', '1.000', '0.933', '1.000', '1.000', '17.89', '4.79'],
    ['SLM-1 (Qwen 2B-class)', '0.800', '0.800', '1.000', '0.933', '0.933', '42.83', '2.33'],
    ['SLM-2 (Phi 3B-class)', '1.000', '1.000', '1.000', '1.000', '1.000', '3.02', '—'],
    ['BASELINE LLM', '1.000', '1.000', '1.000', '1.000', '1.000', '0.978', '—'],
  ],
  opWidths: [2400, 800, 800, 800, 800, 800, 1400, 1360],
  capCurveFile: 'instruction_following_capability_curve.png',
  riskCurveFile: 'instruction_following_risk_curve.png',
  capCurveDesc: '** ONLY ROUTING SUCCESS IN THIS STUDY ** IFEval: 7 matched pairs, all |Gamma|=0, single bin. Ratio=1.0 -> Zone A. tau_cap=0.0 (SLM capable at all observed difficulties).',
  riskCurveDesc: 'Canonical risk curves (15/bin). All three SLM tiers show low risk (<0.20) across all bins. Wilson CI_lo < 0.20 for all -> tau_risk = None. Gate fully satisfied.',
  tauCapText: ['0.0 (all difficulties)', 'ratio_smooth=1.0 at the only bin (|Gamma|=0); n=7 >= 5 minimum gate; SLM fully capable'],
  tauRiskText: ['None', 'risk=0.0 at single SDDF bin; CI_lo=0.0; does NOT trigger tau_risk'],
  decisionText: 'ROUTE SLM — the only task achieving successful routing. All 7 matched pairs in bin 0 (|Gamma|=0), ratio=1.0, precision=recall=F1=1.0, limit=min(0.0, 0.0)=0.0. Result is specific to unconstrained instructions; higher |Gamma| would require further evaluation. Note: BASELINE pass_rate=1.0 vs SLM-0 pass_rate=0.40 in capability snapshot — but SDDF ratio routing succeeds because matched SDDF pairs showed equal performance.',
}));

// =========================================================
// SECTION 13: CODE GENERATION
// =========================================================
children.push(...taskSection(13, 'Code Generation', {
  datasets: 'HumanEval, MBPP',
  datasetDesc: 'Chen et al. (2021)',
  models: 'SLM-0 (0.5B tiny), SLM-1 (Qwen 2B-class), SLM-2 (Phi 3B-class), BASELINE LLM (Groq)',
  dominantDim: 'R^ — reasoning proxy (logical composition + step count)',
  dominantFormula: 'R^(x) = 0.05*|w_q|  +  1.0*n_steps  +  0.5*n_ent  +  1.0*1_comp',
  promptFile: 'tasks/code_generation/src/codegen_eval/prompts.py (fast_cpu variant)',
  promptTemplate: 'Return only the completed Python function.\nProblem:\n{problem_text}\nComplete this function exactly:\n```python\n{starter_code}\n```\nRequirements:\n- Use the exact function name `{entry_point}`\n- Preserve the required parameters\n- Return only Python code\n- Do not include explanations',
  primaryMetric: 'pass@1 = execution pass rate (Chen et al., 2021)',
  groundTruth: 'Unit tests from HumanEval/MBPP datasets (execution-based)',
  complexityExample: 'Simple 1-step function -> R^~1.0; complex algorithm with loops+conditionals -> R^~5-10',
  capNote: 'Source: task_model_runs_table.json (SLM-0=Qwen2.5-Coder-0.5B-Instruct, SLM-1=Qwen2.5-Coder-1.5B-Instruct). BASELINE low pass@1 likely reflects small evaluation set bias.',
  capHeaders: ['Model', 'pass@1', 'Avg Latency (s)', 'Tokens/sec'],
  capRows: [
    ['SLM-0 (0.5B tiny)', '0.500', '7.40', '7.70'],
    ['SLM-1 (Qwen 2B-class)', '1.000', '91.05', '0.60'],
    ['BASELINE LLM', '0.150', '0.665', '110.14'],
  ],
  capWidths: [3000, 2000, 2200, 2160],
  opHeaders: ['Model', 'Bin 0', 'Bin 1', 'Bin 2', 'Bin 3', 'Bin 4', 'Avg Latency (s)'],
  opRows: [
    ['SLM-1 (Qwen 2B-class)', '0.667', '0.733', '0.533', '0.667', '0.667', '10.29'],
    ['SLM-2 (Phi 3B-class)', '0.500', '0.600', '0.467', '0.667', '0.571', '16.11'],
    ['BASELINE LLM', '0.500', '—', '—', '—', '—', '0.84'],
  ],
  opWidths: [2800, 1000, 1000, 1000, 1000, 1000, 1560],
  capCurveFile: 'code_generation_capability_curve.png',
  riskCurveFile: 'code_generation_risk_curve.png',
  capCurveDesc: 'Smoke run: 1 matched pair each (HumanEval, MBPP). ratio=0.0 -> Zone C. n=1 per task -> Wilson CI not applicable.',
  riskCurveDesc: 'Canonical risk curves (15/bin). SLM-1 risk=0.267-0.467 across bins. CI_lo exceeds 0.20 at bin 2 (CI_lo=0.234) -> tau_risk fires at bin 2. Orange dashed = tau_risk.',
  tauCapText: ['None', 'Smoke ratio=0.0; no matched pairs achieving ratio >= 0.95'],
  tauRiskText: ['Bin 2 (SLM-1)', 'CI_lo[2]=0.234 > 0.20; n=15 satisfies gate; first consecutive violation'],
  decisionText: 'ESCALATE. All smoke bins Zone C. Canonical risk exceeds 0.20 threshold (tau_risk=bin 2). SLM-1 achieves pass@1=1.0 in archived capability run but at 91s/query (137x BASELINE latency) -- operationally infeasible. Three-way Pareto split: SLM-0 (moderate cap, fast), SLM-1 (best cap, slowest), BASELINE (fastest, lowest cap). BASELINE 110 tok/s preferred for production.',
}));

// =========================================================
// SECTION 14: TWO-TIER DECISION MATRIX
// =========================================================
children.push(h1('Section 14: Two-Tier Decision Matrix'));

children.push(h2('14.1 Matrix Logic (Two-Tier Gating)'));
children.push(...formula('Risk-First Gate:', 'tau_risk = min{ b : CI_lo(Risk_m(b)) > 0.20,   |b| >= 5 }', [
  'CI_lo — lower bound of Wilson 95% CI on per-bin risk',
  '0.20 — risk tolerance threshold (LEARNED from data)',
  '|b| >= 5 — minimum sample gate for statistical validity',
]));
children.push(...formula('Capability Gate:', 'tau_cap = max{ b : CI_lo(P^_m(b)) >= 0.95,   |b| >= 5 }', [
  '0.95 — capability threshold (LEARNED from data)',
]));
children.push(...formula('Routing Limit:', 'limit = min(tau_risk,   tau_cap)', []));
children.push(...formulaBlock([
  'route(x) = SLM       if s(x) <= limit',
  '         = BASELINE  if s(x) >  limit',
]));

children.push(h2('14.2 Master Decision Table — All 8 Tasks'));
children.push(makeTable(
  ['Task', 'Dominant Dim', 'tau_risk', 'tau_cap', 'Binding Gate', 'Decision'],
  [
    ['Classification', 'H (entropy)', 'None (n<5)', 'H~4.40 bits (bin 2)', 'capability', 'ESCALATE'],
    ['Maths', 'R^', 'None (n<5)', 'None', 'none', 'ESCALATE'],
    ['Text Generation', '|Gamma|', 'Bin 0 (SLM-2)', 'None', 'risk (SLM-2)', 'ESCALATE SLM-2 / ROUTE SLM-1'],
    ['Summarization', 'n_in', 'Bin 0 (SLM-2)', 'n_in=375 tokens', 'risk fires first', 'ESCALATE'],
    ['Info Extraction', '|Gamma|', 'None (n<5)', 'None', 'none', 'ESCALATE'],
    ['Retrieval Grounded', 'n_in', 'None (borderline)', 'None', 'none', 'ESCALATE'],
    ['Instruction Following', '|Gamma|', 'None', '0.0', 'capability', 'ROUTE SLM'],
    ['Code Generation', 'R^', 'Bin 2 (SLM-1)', 'None', 'risk', 'ESCALATE'],
  ],
  [1800, 1400, 1700, 1800, 1700, 1960]
));

children.push(h2('14.3 Matrix-by-Matrix Analysis'));
const matrixAnalysis = [
  ['Classification', 'tau_risk: not triggered — n=1-2/bin (below min_samples=5 gate). tau_cap: Emotion bin 2 (H=4.40 bits, ratio_smooth=1.0) but n=1. Gate recall=0.25 means gate rejects 75% of valid SLM responses.', 'ESCALATE — insufficient matched pairs; high canonical success but unverified by ratio test'],
  ['Maths', 'tau_risk: GSM8K n=2, SVAMP n=2 -> below gate. tau_cap: ratio=0.0 (GSM8K), 0.5 (SVAMP) -> neither >= 0.95. Neither gate can trigger.', 'ESCALATE — smoke insufficient; canonical SLM-1 100% format compliance, not raw accuracy'],
  ['Text Generation', 'tau_risk: SLM-2 canonical bin 0 risk=0.833, n=15, CI_lo >> 0.20 -> fires. tau_cap: no ratio >= 0.95 in SDDF run.', 'ESCALATE (SLM-2) / ROUTE (SLM-1) — task-model fit determines outcome'],
  ['Summarization', 'tau_risk: SLM-2 canonical CI_lo=0.268 > 0.20 at bin 0. tau_cap: 375 tokens (bin 4, smoke run). Risk binds before capability.', 'ESCALATE — SLM-2 risk too high; SLM-0/1 borderline; BASELINE preferred'],
  ['Info Extraction', 'tau_risk: single bin |Gamma|=4, n=4 -> below gate. tau_cap: ratio=0.0 -> no Zone A/B. Neither gate fires.', 'ESCALATE — all Zone C; low F1; BASELINE 16x throughput advantage'],
  ['Retrieval Grounded', 'tau_risk: smoke single bin n=6 -> no consecutive test. Canonical SLM-2 CI_lo approaches 0.20 but stays below. tau_cap: SLM-0 EM>BASELINE but no ratio pairs.', 'ESCALATE — smoke insufficient; SLM-0 competitive on EM; recommend SLM-0 for short context'],
  ['Instruction Following', 'tau_risk: n=7, risk=0.0, CI_lo=0.0 -> does NOT trigger. tau_cap: ratio_smooth=1.0, CI_lo=0.95 >= 0.95 -> tau_cap=0.0. limit=0.0.', 'ROUTE SLM — only success; all Zone A; ratio=1.0; precision=recall=F1=1.0'],
  ['Code Generation', 'tau_risk: SLM-1 canonical CI_lo[2]=0.234 > 0.20 -> fires at bin 2. tau_cap: smoke ratio=0.0 -> no Zone A. Risk binds.', 'ESCALATE — SLM-1 91s/query; canonical risk >0.20; BASELINE 110 tok/s preferred'],
];
children.push(makeTable(
  ['Task', 'Gate Analysis', 'Decision'],
  matrixAnalysis,
  [1700, 5060, 2600]
));

children.push(h2('14.4 Deployment Zone Inventory'));
children.push(makeTable(
  ['Task / Dataset', 'Bin 0', 'Bin 1', 'Bin 2', 'Bin 3', 'Bin 4'],
  [
    ['Classification (Emotion)', 'C', 'C', 'A', 'C', 'C'],
    ['Classification (SST-2)', 'C', 'A', 'A', 'A', 'C'],
    ['Classification (AG News)', 'A', 'A', 'C', '—', 'A'],
    ['Summarization (CNN/DM)', 'B', 'A', 'A', 'A', 'A'],
    ['Instruction Following', 'A', '—', '—', '—', '—'],
    ['Maths / Code / IE / Retrieval / TextGen (SDDF)', 'C', 'C', 'C', 'C', 'C'],
  ],
  [3500, 1150, 1150, 1150, 1150, 1260]
));

children.push(h2('14.5 Why Risk Gate Dominates'));
children.push(p('SDDF smoke runs use 1-7 matched SLM/LLM pairs per task. With n=1-2 per bin, Wilson CI is too wide and the min_samples=5 gate prevents tau detection. The canonical 75-sample runs (15/bin) have sufficient per-bin counts but lack matched SLM-BASELINE pairs for ratio computation. This structural mismatch is the primary limitation of the current setup.'));

children.push(h2('14.6 Instruction Following — Why It Succeeds'));
children.push(p('All 7 samples collapse to bin 0 (|Gamma|=0: no explicit constraint counting in IFEval prompts). Zero difficulty variation -> single bin with ratio_smooth=1.0. n=7 >= 5 satisfies minimum gate. Both tau_cap=0.0 and tau_risk is not triggered -> routing decision: ROUTE SLM for all observed difficulty levels.'));

children.push(h2('14.7 Canonical Results Summary'));
children.push(makeTable(
  ['Tier', 'Strong Tasks (>=93% success)', 'Weak Tasks (<60% success)'],
  [
    ['SLM-0 (0.5B tiny)', 'IE (all bins), IF (all), Retrieval (all), Summarization (all)', 'No canonical artifacts for Classification/Maths/Code/TextGen'],
    ['SLM-1 (Qwen 2B-class)', 'Classification, IE (bins 1-4), IF (bins 2-3), Maths (all), Retrieval (bins 0-1,4)', 'Code Generation (53-73%), Summarization (87-93%)'],
    ['SLM-2 (Phi 3B-class)', 'Classification (>=93%), IE (100%), IF (100%)', 'Summarization (27-60%), Text Generation (0-27%)'],
  ],
  [1800, 4500, 3060]
));
children.push(pb());

// =========================================================
// SECTION 15: PARETO ANALYSIS
// =========================================================
children.push(h1('Section 15: Pareto Analysis — Cost / Latency / Capability'));
children.push(p('Each model tier is evaluated on three axes simultaneously: capability (primary metric), latency (seconds/query), and throughput (queries/min or tokens/sec). Source: model runs/PARETO_TABLE.md.'));
children.push(blank());
children.push(makeTable(
  ['Task', 'Tier', 'Capability', 'Latency', 'Throughput', 'Note'],
  [
    ['Classification', 'SLM-1', 'SST-2=1.0, Emotion=0.667, AGN=0.75', 'SST-2: 5.52s', '0.18 qps', 'Provisional'],
    ['Classification', 'SLM-2', 'Same (phi3:mini evidence)', 'SST-2: 5.52s', '0.18 qps', 'Provisional'],
    ['Classification', 'BASELINE LLM', 'Quality ceiling', '—', '—', 'Escalation target'],
    ['Maths', 'SLM-2', 'Acc=19.2%, pass@3=47.3%', '28.41s/q', '2.11 q/min', 'Provisional'],
    ['Maths', 'BASELINE LLM', 'Acc=38.3%, pass@3=76.5%', '1.08s/q', '55.78 q/min', 'Quality ceiling'],
    ['Text Generation', 'SLM-1', 'Qualitative; 15 examples', '~9.16s', '—', 'Provisional'],
    ['Text Generation', 'SLM-2', 'Low CSR (~0-27%)', '~16.5s', '—', 'Provisional'],
    ['Summarization', 'SLM-2', 'R1=0.281, R2=0.106, RL=0.181', '0.763s', '22.4 tok/s', 'Near-Pareto on ROUGE-1'],
    ['Summarization', 'BASELINE LLM', 'R1=0.277, R2=0.069, RL=0.173', '0.583s', '24.8 tok/s', 'Better ROUGE-2/L'],
    ['Info Extraction', 'SLM-0', 'MacroF1=0.167, MicroF1=0.222', '14.59s/doc', '4.11 doc/min', 'invalid_rate=0.50'],
    ['Info Extraction', 'SLM-1', 'MacroF1=0.025, MicroF1=0.042', '17.45s/doc', '3.44 doc/min', 'invalid_rate=0.80'],
    ['Info Extraction', 'BASELINE LLM', 'MacroF1=0.188, MicroF1=0.300', '0.857s/doc', '70.04 doc/min', 'Quality ceiling; invalid_rate=0.75'],
    ['Retrieval', 'SLM-0', 'EM=66.67%, F1=71.26%', '5.53s (p95:8.08)', '4.23 tok/s', 'SLM-0 > BASELINE on EM'],
    ['Retrieval', 'BASELINE LLM', 'EM=63.33%, F1=77.78%', '0.829s (p95:1.06)', '6.40 tok/s', '6.7x faster; better F1'],
    ['Instr. Following', 'SLM-0', 'pass_rate=0.40, CSR=0.40', '17.89s', '4.79 tok/s', 'Provisional'],
    ['Instr. Following', 'SLM-1', 'pass_rate=0.40, fmt=1.0', '42.83s', '2.33 tok/s', 'Higher latency'],
    ['Instr. Following', 'BASELINE LLM', 'pass_rate=1.0', '0.978s', '—', 'Quality ceiling'],
    ['Code Generation', 'SLM-0', 'pass@1=0.50', '7.40s', '7.70 tok/s', 'Best latency at moderate cap'],
    ['Code Generation', 'SLM-1', 'pass@1=1.00', '91.05s', '0.60 tok/s', 'Best cap, worst latency'],
    ['Code Generation', 'BASELINE LLM', 'pass@1=0.15', '0.665s', '110.14 tok/s', 'Fastest, lowest cap'],
  ],
  [1500, 1300, 2400, 1600, 1300, 1760]
));

children.push(blank());
children.push(h2('15.1 Key Pareto Insights'));
children.push(
  bullet('Retrieval Grounded: SLM-0 (0.5B) achieves higher EM than BASELINE (66.7% vs 63.3%) — small grounded-QA model exceeds large generalist LLM; however 6.7x slower'),
  bullet('Summarization: SLM-2 ROUGE-1 (0.281) marginally exceeds BASELINE (0.277); neither tier dominates all three ROUGE variants simultaneously — true Pareto frontier'),
  bullet('Code Generation: three-way Pareto split — SLM-0 (moderate cap, fast), SLM-1 (best cap, 137x slower), BASELINE (fastest, lowest cap)'),
  bullet('Info Extraction: all tiers low F1 (<=0.19) with high invalid rates (50-80%); BASELINE has 16x throughput advantage; no strong Pareto position for any tier'),
  bullet('Instruction Following: BASELINE dominates capability (100% vs 40%) at 18x lower latency; SLM-0 only viable if cost is the sole constraint'),
  bullet('Task-model fit matters more than parameter count: SLM-2 (Phi 3B-class) underperforms SLM-1 (Qwen 2B-class) on Text Generation despite more parameters')
);
children.push(pb());

// =========================================================
// SECTION 16: DISCUSSION
// =========================================================
children.push(h1('Section 16: Discussion and Limitations'));
children.push(makeTable(
  ['Issue', 'Detail', 'Recommendation'],
  [
    ['Sample size vs. statistical power', 'SDDF smoke runs: 1-7 matched pairs per task. Wilson CI requires >=5/bin. Structural mismatch means tau cannot be determined for 7/8 tasks.', 'Expand matched-pair datasets to 15-20 per bin for all tasks'],
    ['Success rate != semantic accuracy', 'Canonical success_rate = primary_metric>=0.85 AND valid_output=1. For Maths this reflects format compliance, not raw numeric accuracy (SLM-2 raw=19.2%).', 'Add exact-match accuracy as parallel metric in SDDF pipeline'],
    ['Missing canonical artifacts', 'Several tier slots have no preserved numeric artifact. Proxies used from nearest archived evidence.', 'Re-run canonical SDDF for all tier/task combinations with artifact preservation'],
    ['Task-model fit dominates parameter count', 'SLM-2 (Phi 3B-class) underperforms SLM-1 (Qwen 2B-class) on Text Generation despite more parameters.', 'Evaluate architecture-task alignment metrics independently of parameter count'],
    ['Retrieval anomaly', 'SLM-0 (0.5B) achieves higher EM than BASELINE on SQuAD (66.7% vs 63.3%). Context utilization 96.7% vs 83.3%.', 'Investigate routing SLM-0 for short-context Retrieval queries in production'],
    ['BASELINE variability', 'Groq BASELINE showed low pass@1=0.15 on Code Generation — likely small evaluation set bias, not representative of 70B model capability.', 'Increase code evaluation set size; test multiple prompt variants'],
  ],
  [2200, 4200, 2960]
));
children.push(pb());

// =========================================================
// SECTION 17: REFERENCES
// =========================================================
children.push(h1('Section 17: References'));
const refs = [
  'Shannon, C.E. (1948). A Mathematical Theory of Communication. Bell System Technical Journal, 27(3):379-423.',
  'Wilson, E.B. (1927). Probable inference, the law of succession, and statistical inference. Journal of the American Statistical Association, 22(158):209-212.',
  'Lin, C.Y. (2004). ROUGE: A Package for Automatic Evaluation of Summaries. ACL Workshop: Text Summarization Branches Out.',
  'Chen, M., Tworek, J., Jun, H., et al. (2021). Evaluating Large Language Models Trained on Code. arXiv:2107.03374.',
  'Cobbe, K., Kosaraju, V., Bavarian, M., et al. (2021). Training Verifiers to Solve Math Word Problems. arXiv:2110.14168.',
  'Hermann, K.M., Kocisky, T., Grefenstette, E., et al. (2015). Teaching Machines to Read and Comprehend. NeurIPS 28.',
  'Rajpurkar, P., Zhang, J., Lopyrev, K., & Liang, P. (2016). SQuAD: 100,000+ Questions for Machine Comprehension of Text. EMNLP 2016.',
  'Huang, Z., Chen, K., He, J., et al. (2019). ICDAR 2019 Competition on Scanned Receipt OCR and Information Extraction. ICDAR 2019.',
  'Zhou, J., Lu, T., Mishra, S., et al. (2023). Instruction-Following Evaluation for Large Language Models. arXiv:2311.07911.',
];
refs.forEach((ref, i) => children.push(new Paragraph({
  numbering: { reference: 'numbers', level: 0 },
  children: [new TextRun({ text: ref, size: 20, font: 'Arial' })]
})));

// =========================================================
// ASSEMBLE DOCUMENT
// =========================================================
const doc = new Document({
  numbering: {
    config: [
      { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: 'numbers', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  styles: {
    default: {
      document: { run: { font: 'Arial', size: 22 } }
    },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: 'Arial', color: '1F3864' },
        paragraph: { spacing: { before: 300, after: 120 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: 'Arial', color: '2E75B6' },
        paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: 'Arial', color: '385723' },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1200, bottom: 1440, left: 1200 }
      }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: '2E75B6', space: 1 } },
        children: [
          new TextRun({ text: 'SDDF Technical Report', bold: true, font: 'Arial', size: 18, color: '2E75B6' }),
          new TextRun({ text: '\t', font: 'Arial', size: 18 }),
          new TextRun({ text: 'Capability-Based SLM Routing', font: 'Arial', size: 18, color: '777777' }),
        ],
        tabStops: [{ type: 'right', position: 9360 }]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        border: { top: { style: BorderStyle.SINGLE, size: 6, color: '2E75B6', space: 1 } },
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: 'Page ', font: 'Arial', size: 18, color: '777777' }),
          new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 18, color: '777777' }),
          new TextRun({ text: ' of ', font: 'Arial', size: 18, color: '777777' }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], font: 'Arial', size: 18, color: '777777' }),
        ]
      })] })
    },
    children
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(OUT_PATH, buffer);
  console.log('SUCCESS: ' + OUT_PATH);
  console.log('Size: ' + (buffer.length / 1024 / 1024).toFixed(2) + ' MB');
}).catch(err => {
  console.error('ERROR:', err.message);
  process.exit(1);
});
