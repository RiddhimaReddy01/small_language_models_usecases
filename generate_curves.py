"""
SDDF Report Curve Generator
Generates capability and risk curve PNGs for all 8 tasks.
Output: report_curves/ directory
"""
import os
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "report_curves")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Wilson CI ---
def wilson_ci(p, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = z * math.sqrt((p*(1-p)/n + z**2/(4*n**2))) / denom
    return max(0.0, center - margin), min(1.0, center + margin)

# Colors
C_SLM0 = '#4CAF50'   # green
C_SLM1 = '#2196F3'   # blue
C_SLM2 = '#FF9800'   # orange
C_BASE = '#9E9E9E'   # grey
C_CAP  = '#4CAF50'   # green for tau_cap
C_RISK = '#FF5722'   # deep orange for tau_risk
C_THRESH = '#F44336' # red for risk threshold line

ZONE_A = '#C8E6C9'   # green tint
ZONE_B = '#FFF9C4'   # yellow tint
ZONE_C = '#FFCDD2'   # red tint


def add_zone_fills_ratio(ax, x_vals):
    """Add Zone A/B/C fills to a ratio (capability) curve plot."""
    xmin, xmax = min(x_vals) - 0.3, max(x_vals) + 0.3
    ax.axhspan(0.95, 1.5, alpha=0.12, color='#4CAF50', zorder=0, label='Zone A (≥0.95)')
    ax.axhspan(0.85, 0.95, alpha=0.12, color='#FFC107', zorder=0, label='Zone B (0.85–0.95)')
    ax.axhspan(0.0, 0.85, alpha=0.12, color='#F44336', zorder=0, label='Zone C (<0.85)')
    ax.axhline(y=0.95, color='#4CAF50', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.axhline(y=0.85, color='#FFC107', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.axhline(y=1.0, color=C_BASE, linewidth=0.8, linestyle=':', alpha=0.4, label='BASELINE=1.0')


def save_cap_curve(task, x_vals, ratios, ratio_smooth, xlabel, tau_cap=None,
                   x_vals2=None, ratios2=None, label2=None, ratios_smooth2=None,
                   title_suffix="", n_vals=None):
    fig, ax = plt.subplots(figsize=(10, 5))
    add_zone_fills_ratio(ax, x_vals)

    ax.plot(x_vals, ratios, 'o-', color=C_SLM1, linewidth=2, markersize=7, label='Ratio (SLM/BASELINE)', zorder=3)
    ax.plot(x_vals, ratio_smooth, 's--', color='#1565C0', linewidth=1.5, markersize=5, alpha=0.8, label='Ratio smooth', zorder=3)

    if x_vals2 is not None and ratios2 is not None:
        lbl2 = label2 or 'Ratio 2'
        ax.plot(x_vals2, ratios2, 'D-', color=C_SLM2, linewidth=2, markersize=7, label=lbl2, zorder=3)
        if ratios_smooth2:
            ax.plot(x_vals2, ratios_smooth2, 'D--', color='#E65100', linewidth=1.5, markersize=5, alpha=0.8, label=f'{lbl2} smooth', zorder=3)

    if n_vals is not None:
        for xi, ri, ni in zip(x_vals, ratios, n_vals):
            ax.annotate(f'n={ni}', (xi, ri), textcoords='offset points', xytext=(0, 8),
                        ha='center', fontsize=8, color='#555')

    if tau_cap is not None:
        ax.axvline(x=tau_cap, color=C_CAP, linewidth=2, linestyle='--', zorder=4)
        ax.annotate(f'τ_cap={tau_cap}', xy=(tau_cap, 0.97),
                    xytext=(tau_cap + (max(x_vals) - min(x_vals)) * 0.03, 0.90),
                    fontsize=10, color=C_CAP, fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=C_CAP, lw=1.5))

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Capability Ratio ρ (SLM / BASELINE)', fontsize=12)
    ax.set_title(f'{task} — Capability Curve{title_suffix}', fontsize=14, fontweight='bold')
    ax.set_ylim(-0.05, 1.35)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, f'{task.lower().replace(" ", "_")}_capability_curve.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def save_risk_curve(task, bins, models_data, tau_risk=None, xlabel='Difficulty Bin',
                    title_suffix=""):
    """
    models_data: list of dicts with keys: label, color, success, n
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    # Risk threshold
    ax.axhline(y=0.20, color=C_THRESH, linewidth=2, linestyle='--', label='Risk threshold = 0.20', zorder=5)

    for m in models_data:
        lbl = m['label']
        col = m['color']
        success = m['success']
        n = m.get('n', [15]*len(bins))
        risk = [1 - s if s is not None else None for s in success]

        # compute Wilson CI on risk
        ci_lo, ci_hi = [], []
        valid_bins, valid_risk = [], []
        for b, r, ni in zip(bins, risk, n):
            if r is None:
                continue
            lo, hi = wilson_ci(r, ni)
            ci_lo.append(lo)
            ci_hi.append(hi)
            valid_bins.append(b)
            valid_risk.append(r)

        if not valid_bins:
            continue
        ax.fill_between(valid_bins, ci_lo, ci_hi, alpha=0.18, color=col)
        ax.plot(valid_bins, valid_risk, 'o-', color=col, linewidth=2.2, markersize=8,
                label=lbl, zorder=3)

    if tau_risk is not None:
        ax.axvline(x=tau_risk, color='#FF5722', linewidth=2, linestyle='--', zorder=6)
        y_pos = 0.65
        ax.annotate(f'τ_risk={tau_risk}', xy=(tau_risk, y_pos),
                    xytext=(tau_risk + (max(bins) - min(bins) + 0.5) * 0.04, y_pos + 0.07),
                    fontsize=10, color='#FF5722', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color='#FF5722', lw=1.5))

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Risk = 1 − Success Rate', fontsize=12)
    ax.set_title(f'{task} — Risk Curve{title_suffix}\n(with Wilson 95% CI shading, n=15/bin)',
                 fontsize=13, fontweight='bold')
    ax.set_ylim(-0.05, 1.1)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, f'{task.lower().replace(" ", "_")}_risk_curve.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ============================================================
# 1. CLASSIFICATION
# ============================================================
print("Generating Classification curves...")
# Capability: Emotion (3 sub-curves, use one plot with 3 lines)
# Emotion
em_x  = [2.375, 3.774, 4.404, 4.502, 4.852]
em_r  = [0.000, 0.000, 1.000, 0.000, 0.000]
em_rs = [0.000, 0.000, 1.000, 0.000, 0.000]
em_n  = [2, 1, 1, 1, 1]
# SST-2
sst_x  = [3.522, 4.122, 4.170, 4.664, 4.789]
sst_r  = [0.500, 1.000, 1.000, 1.000, 0.000]
sst_rs = [0.500, 1.000, 1.000, 1.000, 0.000]
# AG News
ag_x  = [4.222, 4.761, 4.965, 5.234]
ag_r  = [1.000, 1.000, 0.000, 1.000]

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax_i, (xv, rv, rsv, nv, title, tc, xlbl) in enumerate([
    (em_x, em_r, em_rs, em_n, 'Emotion', 4.404, 'Entropy (bits)'),
    (sst_x, sst_r, sst_rs, [2,1,1,1,1], 'SST-2', None, 'Entropy (bits)'),
    (ag_x, ag_r, ag_r, [1,1,1,1], 'AG News', None, 'Entropy (bits)'),
]):
    ax = axes[ax_i]
    ax.axhspan(0.95, 1.4, alpha=0.12, color='#4CAF50', zorder=0)
    ax.axhspan(0.85, 0.95, alpha=0.12, color='#FFC107', zorder=0)
    ax.axhspan(0.0, 0.85, alpha=0.12, color='#F44336', zorder=0)
    ax.axhline(y=0.95, color='#4CAF50', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.axhline(y=1.0, color='grey', linewidth=0.8, linestyle=':', alpha=0.4)
    ax.plot(xv, rv, 'o-', color=C_SLM1, linewidth=2, markersize=7, label='Ratio', zorder=3)
    ax.plot(xv, rsv, 's--', color='#1565C0', linewidth=1.5, markersize=5, alpha=0.8, label='Smooth', zorder=3)
    for xi, ri, ni in zip(xv, rv, nv):
        ax.annotate(f'n={ni}', (xi, ri), textcoords='offset points', xytext=(0,8),
                    ha='center', fontsize=8, color='#555')
    if tc is not None:
        ax.axvline(x=tc, color=C_CAP, linewidth=2, linestyle='--', zorder=4)
        ax.annotate(f'τ_cap={tc}', xy=(tc, 1.1), xytext=(tc-0.3, 1.22),
                    fontsize=9, color=C_CAP, fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=C_CAP, lw=1.2))
    ax.set_xlabel('Entropy H (bits)', fontsize=11)
    ax.set_ylabel('Ratio ρ', fontsize=11)
    ax.set_title(f'Classification — {title}', fontsize=12, fontweight='bold')
    ax.set_ylim(-0.1, 1.4)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
plt.suptitle('Classification Capability Curves (SDDF Smoke Run)', fontsize=14, fontweight='bold', y=1.02)
fig.tight_layout()
path = os.path.join(OUTPUT_DIR, 'classification_capability_curve.png')
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  Saved: {path}")

# Risk curve: Classification (canonical, 15/bin)
bins5 = [0, 1, 2, 3, 4]
save_risk_curve('Classification', bins5, [
    {'label': 'SLM-1 (Qwen 2B-class)', 'color': C_SLM1,
     'success': [1.0, 0.933, 1.0, 1.0, 1.0], 'n': [15]*5},
    {'label': 'SLM-2 (Phi 3B-class)', 'color': C_SLM2,
     'success': [1.0, 1.0, 1.0, 0.933, 1.0], 'n': [15]*5},
], tau_risk=None, title_suffix=' (canonical, 15/bin)\nτ_risk = None (CI_lo of risk < 0.20 for all bins)')

# ============================================================
# 2. MATHS
# ============================================================
print("Generating Maths curves...")
save_cap_curve('Maths',
    x_vals=[1.0, 2.0], ratios=[0.0, 0.0], ratio_smooth=[0.0, 0.0],
    xlabel='Reasoning Proxy R̂ (approx.)',
    tau_cap=None, n_vals=[2, 2],
    title_suffix='\n(Smoke run: 2 matched pairs; all Zone C)')

save_risk_curve('Maths', bins5, [
    {'label': 'SLM-1 (Qwen 2B-class)', 'color': C_SLM1,
     'success': [1.0, 1.0, 1.0, 1.0, 1.0], 'n': [15]*5},
    {'label': 'SLM-2 (Phi 3B-class)', 'color': C_SLM2,
     'success': [0.933, 1.0, 1.0, 1.0, 1.0], 'n': [15]*5},
], tau_risk=None, title_suffix=' (canonical)\nτ_risk = None (all CI_lo of risk < 0.20)')

# ============================================================
# 3. TEXT GENERATION
# ============================================================
print("Generating Text Generation curves...")
save_cap_curve('Text_Generation',
    x_vals=[0.0], ratios=[0.0], ratio_smooth=[0.0],
    xlabel='Constraint Count |Γ|',
    tau_cap=None, n_vals=[15],
    title_suffix='\n(Combined SDDF run: all |Γ|=0, ratio=0.0, Zone C for both SLMs)')

save_risk_curve('Text_Generation', bins5, [
    {'label': 'SLM-1 (Qwen 2B-class)', 'color': C_SLM1,
     'success': [1.0, 1.0, 1.0, 1.0, 1.0], 'n': [15]*5},
    {'label': 'SLM-2 (Phi 3B-class)', 'color': C_SLM2,
     'success': [0.167, 0.143, 0.267, 0.0, None], 'n': [15, 15, 15, 15, 0]},
], tau_risk=0.0, title_suffix=' (canonical)\nτ_risk = bin 0 for SLM-2 (risk=0.833 >> 0.20)')

# ============================================================
# 4. SUMMARIZATION
# ============================================================
print("Generating Summarization curves...")
sum_x  = [294, 309, 345, 348, 375]
sum_r  = [0.889, 1.000, 1.190, 1.099, 0.952]
sum_rs = [0.889, 1.000, 1.190, 1.099, 0.952]
save_cap_curve('Summarization',
    x_vals=sum_x, ratios=sum_r, ratio_smooth=sum_rs,
    xlabel='Article Length n_in (tokens)',
    tau_cap=375, n_vals=[1,1,1,1,1],
    title_suffix='\n(CNN/DailyMail, ROUGE-1, 5 matched pairs)')

save_risk_curve('Summarization', bins5, [
    {'label': 'SLM-0 (0.5B tiny)', 'color': C_SLM0,
     'success': [1.0, 1.0, 1.0, 1.0, 1.0], 'n': [15]*5},
    {'label': 'SLM-1 (Qwen 2B-class)', 'color': C_SLM1,
     'success': [0.867, 0.933, 0.933, 0.933, 0.933], 'n': [15]*5},
    {'label': 'SLM-2 (Phi 3B-class)', 'color': C_SLM2,
     'success': [0.533, 0.600, 0.333, 0.533, 0.267], 'n': [15]*5},
], tau_risk=0, title_suffix=' (canonical)\nτ_risk = bin 0 for SLM-2 (CI_lo=0.268 > 0.20)')

# ============================================================
# 5. INFORMATION EXTRACTION
# ============================================================
print("Generating Information Extraction curves...")
save_cap_curve('Information_Extraction',
    x_vals=[4.0], ratios=[0.0], ratio_smooth=[0.0],
    xlabel='Constraint Count |Γ| (# required fields)',
    tau_cap=None, n_vals=[4],
    title_suffix='\n(SROIE, 4 matched pairs; single bin |Γ|=4, Zone C)')

save_risk_curve('Information_Extraction', bins5, [
    {'label': 'SLM-0 (0.5B tiny)', 'color': C_SLM0,
     'success': [0.933, 1.0, 0.933, 0.867, 1.0], 'n': [15]*5},
    {'label': 'SLM-1 (Qwen 2B-class)', 'color': C_SLM1,
     'success': [0.867, 1.0, 1.0, 1.0, 1.0], 'n': [15]*5},
    {'label': 'SLM-2 (Phi 3B-class)', 'color': C_SLM2,
     'success': [1.0, 1.0, 1.0, 1.0, 1.0], 'n': [15]*5},
], tau_risk=None, title_suffix=' (canonical)\nτ_risk = None (all CI_lo of risk < 0.20)')

# ============================================================
# 6. RETRIEVAL GROUNDED
# ============================================================
print("Generating Retrieval Grounded curves...")
save_cap_curve('Retrieval_Grounded',
    x_vals=[1.0], ratios=[0.0], ratio_smooth=[0.0],
    xlabel='Context Length n_in (tokens)',
    tau_cap=None, n_vals=[6],
    title_suffix='\n(SQuAD, 6 matched pairs; single bin, Zone C)')

save_risk_curve('Retrieval_Grounded', bins5, [
    {'label': 'SLM-0 (0.5B tiny)', 'color': C_SLM0,
     'success': [1.0, 1.0, 1.0, 1.0, 1.0], 'n': [15]*5},
    {'label': 'SLM-1 (Qwen 2B-class)', 'color': C_SLM1,
     'success': [1.0, 1.0, 0.933, 0.933, 1.0], 'n': [15]*5},
    {'label': 'SLM-2 (Phi 3B-class)', 'color': C_SLM2,
     'success': [0.800, 0.933, 0.733, 0.800, 0.733], 'n': [15]*5},
], tau_risk=None, title_suffix=' (canonical)\nτ_risk = None for SLM-2 (CI_lo borderline but non-consecutive)')

# ============================================================
# 7. INSTRUCTION FOLLOWING
# ============================================================
print("Generating Instruction Following curves...")
fig, ax = plt.subplots(figsize=(8, 5))
ax.axhspan(0.95, 1.4, alpha=0.12, color='#4CAF50', zorder=0, label='Zone A (≥0.95)')
ax.axhspan(0.85, 0.95, alpha=0.12, color='#FFC107', zorder=0, label='Zone B (0.85–0.95)')
ax.axhspan(0.0, 0.85, alpha=0.12, color='#F44336', zorder=0, label='Zone C (<0.85)')
ax.axhline(y=0.95, color='#4CAF50', linewidth=0.8, linestyle='--', alpha=0.5)
ax.axhline(y=1.0, color='grey', linewidth=0.8, linestyle=':', alpha=0.4)
ax.plot([0.0], [1.0], 'o', color=C_SLM1, markersize=14, label='Ratio = 1.0 (n=7)', zorder=5)
ax.axvline(x=0.0, color=C_CAP, linewidth=2, linestyle='--', zorder=4)
ax.annotate('τ_cap = 0.0\n(ROUTE SLM)', xy=(0.0, 1.0), xytext=(0.2, 1.15),
            fontsize=10, color=C_CAP, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=C_CAP, lw=1.5))
ax.set_xlabel('Constraint Count |Γ|', fontsize=12)
ax.set_ylabel('Capability Ratio ρ (SLM / BASELINE)', fontsize=12)
ax.set_title('Instruction Following — Capability Curve\n(IFEval, 7 matched pairs, all Zone A — ONLY ROUTING SUCCESS)',
             fontsize=13, fontweight='bold')
ax.set_xlim(-0.5, 1.5)
ax.set_ylim(-0.1, 1.4)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
fig.tight_layout()
path = os.path.join(OUTPUT_DIR, 'instruction_following_capability_curve.png')
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  Saved: {path}")

save_risk_curve('Instruction_Following', bins5, [
    {'label': 'SLM-0 (0.5B tiny)', 'color': C_SLM0,
     'success': [0.933, 1.0, 0.933, 1.0, 1.0], 'n': [15]*5},
    {'label': 'SLM-1 (Qwen 2B-class)', 'color': C_SLM1,
     'success': [0.800, 0.800, 1.0, 0.933, 0.933], 'n': [15]*5},
    {'label': 'SLM-2 (Phi 3B-class)', 'color': C_SLM2,
     'success': [1.0, 1.0, 1.0, 1.0, 1.0], 'n': [15]*5},
], tau_risk=None, title_suffix=' (canonical)\nτ_risk = None (all CI_lo of risk < 0.20)')

# ============================================================
# 8. CODE GENERATION
# ============================================================
print("Generating Code Generation curves...")
save_cap_curve('Code_Generation',
    x_vals=[1.0, 2.0], ratios=[0.0, 0.0], ratio_smooth=[0.0, 0.0],
    xlabel='Reasoning Proxy R̂ (approx.)',
    tau_cap=None, n_vals=[1, 1],
    title_suffix='\n(HumanEval+MBPP, 1 matched pair each; all Zone C)')

save_risk_curve('Code_Generation', bins5, [
    {'label': 'SLM-1 (Qwen 2B-class)', 'color': C_SLM1,
     'success': [0.667, 0.733, 0.533, 0.667, 0.667], 'n': [15]*5},
    {'label': 'SLM-2 (Phi 3B-class)', 'color': C_SLM2,
     'success': [0.500, 0.600, 0.467, 0.667, 0.571], 'n': [15]*5},
], tau_risk=2, title_suffix=' (canonical)\nτ_risk = bin 2 for SLM-1 (CI_lo=0.234 > 0.20, first consecutive)')

print("\nAll curves saved to:", OUTPUT_DIR)
print("Files:")
for f in sorted(os.listdir(OUTPUT_DIR)):
    print(f"  {f}")
