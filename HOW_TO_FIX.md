# HOW TO FIX: Step-by-Step Guide

**Date**: 2026-03-20 | **Scope**: Fix all blocking issues in 2-3 days

---

## STATUS CHECK

### Codebase Size
- **Total lines**: 3,100
- **Core functions**: 11 public functions
- **Key files**: 8 Python modules in src/routing/

### Issues to Fix
1. ❌ **Merge conflicts** (CRITICAL) - Code won't compile
2. ❌ **Phase 1 bin assignment bug** (HIGH) - ~1% misrouting
3. ❌ **Phase 2 monitoring stubbed** (HIGH) - No monitoring in production
4. ⚠️ **Dead code** (LOW) - Experimental files not used

---

## PART 1: RESOLVE MERGE CONFLICTS (2-4 hours)

### Problem
Git merge left conflict markers in 3 files:
```
src/routing/framework.py       # 3 conflict blocks
src/routing/production_router.py # 3 conflict blocks
README.md                      # Visible conflict markers
requirements.txt               # Minor conflicts
```

### Solution: Resolve Conflicts Manually

#### Step 1: Check conflict status
```bash
cd "c:\Users\riddh\OneDrive\Desktop\SLM use cases"
git status
```

Expected output:
```
UU src/routing/framework.py
UU src/routing/production_router.py
UU README.md
UU requirements.txt
```

#### Step 2: Resolve framework.py (3 conflicts)

**Conflict 1** (lines 97-145):
```python
<<<<<<< HEAD
=======
    def difficulty_to_bin_probabilities(self, difficulty_score: float,
                                        num_bins: int = 5) -> Dict[int, float]:
        """Probabilistic bin assignment..."""
>>>>>>> 4ebe773
```

**Action**: **KEEP the Other branch version** (it has the probabilistic binning function)
```bash
# In src/routing/framework.py, DELETE the conflict markers and keep:
def difficulty_to_bin_probabilities(self, difficulty_score: float,
                                    num_bins: int = 5) -> Dict[int, float]:
    """..."""
    bin_position = difficulty_score * (num_bins - 1)
    lower_bin = int(bin_position)
    upper_bin = min(lower_bin + 1, num_bins - 1)
    fraction = bin_position - lower_bin

    bin_probs = {}
    for bin_id in range(num_bins):
        if bin_id == lower_bin:
            bin_probs[bin_id] = 1.0 - fraction
        elif bin_id == upper_bin and upper_bin != lower_bin:
            bin_probs[bin_id] = fraction
        else:
            bin_probs[bin_id] = 0.0
    return bin_probs
```

**Conflict 2** (lines 150-157):
```python
<<<<<<< HEAD
        Bin samples by difficulty metric
=======
        Bin samples by difficulty metric (DETERMINISTIC for grouping)

        Used during Phase 0 analysis to group samples for statistics.
>>>>>>> 4ebe773
```

**Action**: **KEEP the Other version** (more detailed docstring)

**Conflict 3** (lines 175-193):
```python
<<<<<<< HEAD
                # Clamp to [0, 1]
                difficulty_score = max(0.0, min(1.0, difficulty_score))

                # Map to bin
                bin_id = int(difficulty_score * (num_bins - 1))
                bin_id = min(bin_id, num_bins - 1)
=======
                # Get probabilistic bin assignment
                bin_probs = self.difficulty_to_bin_probabilities(difficulty_score, num_bins)

                # Assign to most likely bin (argmax)
                bin_id = max(bin_probs, key=bin_probs.get)

                # Store both deterministic bin and probabilistic assignment
                sample['_bin_id'] = bin_id
                sample['_bin_probs'] = bin_probs
                sample['_difficulty_score'] = difficulty_score
>>>>>>> 4ebe773
```

**Action**: **KEEP the Other version** (has probabilistic binning)
```python
# Get probabilistic bin assignment
bin_probs = self.difficulty_to_bin_probabilities(difficulty_score, num_bins)

# Assign to most likely bin (argmax)
bin_id = max(bin_probs, key=bin_probs.get)

# Store both deterministic bin and probabilistic assignment
sample['_bin_id'] = bin_id
sample['_bin_probs'] = bin_probs
sample['_difficulty_score'] = difficulty_score
```

---

#### Step 3: Resolve production_router.py (3 conflicts)

**Conflict 1** (lines 50-53):
```python
<<<<<<< HEAD
=======
    num_bins: int = 5
>>>>>>> 4ebe773
```

**Action**: **KEEP the Other version** (need num_bins field)
```python
@dataclass
class AnalysisResult:
    task: str
    model: str
    capability_curve: Dict[int, float]
    risk_curve: Dict[int, float]
    tau_cap: Optional[int]
    tau_risk: Optional[int]
    zone: str
    empirical_tau_c: float = 0.80
    empirical_tau_r: float = 0.20
    num_bins: int = 5  # KEEP THIS
    timestamp: str = ""
```

**Conflict 2** (lines 181-195):
```python
<<<<<<< HEAD
        # Step 13: Assign to bin
        bin_id = min(int(difficulty * 4), 4)

        # Step 14: Get curves for bin
        analysis = self.get_analysis(task, preferred_model)
=======
        # Step 13: Get curves and configuration
        analysis = self.get_analysis(task, preferred_model)
        num_bins = analysis.num_bins if analysis else 5

        # Step 14: Assign to bin
        bin_id = min(int(difficulty * num_bins), num_bins - 1)
>>>>>>> 4ebe773
```

**Action**: **KEEP Other version, BUT FIX the formula!**
```python
# Step 13: Get analysis and configuration
analysis = self.get_analysis(task, preferred_model)
num_bins = analysis.num_bins if analysis else 5

# Step 14: Assign to bin (FIXED FORMULA)
bin_id = min(int(difficulty * (num_bins - 1)), num_bins - 1)
```

**Why**: The formula should be `* (num_bins - 1)`, not `* num_bins` (see bin assignment test)

**Conflict 3** (lines 280-286):
```python
<<<<<<< HEAD
            # Try SLM first, escalate if verification fails
            # For now, return SLM (verification happens later)
            return model
=======
            return "SLM_with_verification"
>>>>>>> 4ebe773
```

**Action**: **KEEP the Other version**
```python
elif zone == "Q2":
    # Zone 2: SLM + Verify + Escalate
    return "SLM_with_verification"
```

---

#### Step 4: Resolve README.md

**Action**: Remove conflict markers, keep description of current system (HEAD version is more polished)

#### Step 5: Resolve requirements.txt

**Action**: Keep union of both versions (matplotlib from Other branch is good)

#### Step 6: Test compilation
```bash
python -c "from src.routing import ProductionRouter, GeneralizedRoutingFramework; print('SUCCESS')"
```

Expected output: `SUCCESS`

---

## PART 2: FIX BIN ASSIGNMENT FORMULA (1-2 hours)

### Problem
**File**: `src/routing/production_router.py`, line 193 (after merge resolution)

**Current (buggy)**:
```python
bin_id = min(int(difficulty * num_bins), num_bins - 1)
```

**Fixed**:
```python
bin_id = min(int(difficulty * (num_bins - 1)), num_bins - 1)
```

### Action

**Edit**: `src/routing/production_router.py` line 193
```python
# BEFORE:
bin_id = min(int(difficulty * num_bins), num_bins - 1)

# AFTER:
bin_id = min(int(difficulty * (num_bins - 1)), num_bins - 1)
```

### Verify Fix
```bash
python3 << 'EOF'
# Test that Phase 0 and Phase 1 produce same bins
num_bins = 5
test_difficulties = [0.0, 0.25, 0.5, 0.75, 0.99, 1.0]

print("Difficulty | Phase0 | Phase1 | Match")
print("-" * 40)

for diff in test_difficulties:
    # Phase 0
    phase0 = int(diff * (num_bins - 1))
    phase0 = min(phase0, num_bins - 1)

    # Phase 1 FIXED
    phase1 = min(int(diff * (num_bins - 1)), num_bins - 1)

    match = "OK" if phase0 == phase1 else "FAIL"
    print(f"{diff:<11.2f} {phase0:<7} {phase1:<7} {match}")
EOF
```

Expected: All "OK"

---

## PART 3: IMPLEMENT PHASE 2 MONITORING (8-16 hours)

### Current Problem
```python
def log_result(self, task: str, model: str, bin_id: int, success: bool):
    """Log an actual result for monitoring (Phase 2)"""
    # This would be called after actual inference completes
    # Store in time-series database in production
    pass  # ❌ NOT IMPLEMENTED
```

### Solution: Add Monitoring Logger

#### Step 1: Create monitoring module

**File**: `src/routing/monitoring.py`

```python
"""Phase 2: Production Monitoring"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import asdict

class MonitoringLogger:
    """Log routing decisions for daily degradation checks"""

    def __init__(self, log_dir: Path = Path("logs")):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

    def log_decision(self, task: str, model: str, bin_id: int,
                    success: bool, difficulty: float) -> None:
        """Log a routing decision"""
        date = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"routing_{date}.jsonl"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "model": model,
            "bin_id": bin_id,
            "success": success,
            "difficulty": difficulty
        }

        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"WARNING: Failed to log decision: {e}")

    def get_daily_stats(self, task: str, model: str, date: str) -> Dict:
        """Get statistics for a task/model/date"""
        log_file = self.log_dir / f"routing_{date}.jsonl"

        if not log_file.exists():
            return {"samples": 0, "success_rate": 0}

        entries = []
        with open(log_file) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry['task'] == task and entry['model'] == model:
                        entries.append(entry)

        if not entries:
            return {"samples": 0, "success_rate": 0}

        success_count = sum(1 for e in entries if e['success'])
        success_rate = success_count / len(entries)

        return {
            "samples": len(entries),
            "success_rate": success_rate,
            "by_bin": self._group_by_bin(entries)
        }

    def _group_by_bin(self, entries: List[Dict]) -> Dict[int, Dict]:
        """Group entries by bin_id"""
        by_bin = {}
        for entry in entries:
            bin_id = entry['bin_id']
            if bin_id not in by_bin:
                by_bin[bin_id] = {"total": 0, "success": 0}

            by_bin[bin_id]["total"] += 1
            if entry['success']:
                by_bin[bin_id]["success"] += 1

        # Convert to success rates
        return {
            bin_id: by_bin[bin_id]["success"] / by_bin[bin_id]["total"]
            for bin_id in by_bin
        }
```

#### Step 2: Update ProductionRouter to use MonitoringLogger

**File**: `src/routing/production_router.py`

**Add import**:
```python
from .monitoring import MonitoringLogger
```

**Update __init__**:
```python
def __init__(self):
    """Initialize empty router"""
    self.analyses = {}
    self.routing_logs = []
    self.monitoring_metrics = []
    self.logger = MonitoringLogger()  # ADD THIS
```

**Fix log_result**:
```python
def log_result(self, task: str, model: str, bin_id: int,
               success: bool, difficulty: float = 0.5) -> None:
    """Log an actual result for monitoring (Phase 2)"""
    self.logger.log_decision(task, model, bin_id, success, difficulty)
```

**Update route() to call log_result**:
```python
def route(self, input_text: str, task: str, difficulty_metric: Callable,
          preferred_model: str = "qwen") -> Tuple[str, RoutingDecisionRecord]:
    # ... existing routing logic ...

    # After getting the routing decision:
    routed_model, decision = ...

    # LOG FOR PHASE 2 (new)
    # Note: success will be tracked separately after inference
    self.log_result(
        task=task,
        model=routed_model,
        bin_id=decision.bin_id,
        success=True,  # Will be updated after actual inference
        difficulty=decision.difficulty
    )

    return routed_model, decision
```

#### Step 3: Test Phase 2

```bash
python3 << 'EOF'
from src.routing.monitoring import MonitoringLogger
from datetime import datetime
from pathlib import Path

# Create logger
logger = MonitoringLogger(Path("test_logs"))

# Log some decisions
logger.log_decision("test_task", "qwen", bin_id=2, success=True, difficulty=0.5)
logger.log_decision("test_task", "qwen", bin_id=2, success=False, difficulty=0.5)
logger.log_decision("test_task", "qwen", bin_id=3, success=True, difficulty=0.75)

# Get stats
today = datetime.now().strftime("%Y-%m-%d")
stats = logger.get_daily_stats("test_task", "qwen", today)
print(f"Stats: {stats}")
# Expected: {"samples": 3, "success_rate": 0.67, "by_bin": {2: 0.5, 3: 1.0}}

print("Phase 2 monitoring works!")
EOF
```

---

## PART 4: CLEAN UP DEAD CODE (1-2 hours) - OPTIONAL

### Files to Audit

These files might be experimental:

```
src/routing/calculate_comprehensive_metrics.py  (17K) - Check if used
src/routing/fix_text_generation_validation.py   (5.6K) - Probably old
src/routing/fix_validation_bugs.py              (7.8K) - Probably old
```

### Check if Used

```bash
cd "C:\Users\riddh\OneDrive\Desktop\SLM use cases"

# Check imports
grep -r "calculate_comprehensive_metrics" src/ tests/
grep -r "fix_text_generation_validation" src/ tests/
grep -r "fix_validation_bugs" src/ tests/

# Check if any entry points reference them
grep -r "from.*calculate_comprehensive" .
grep -r "import.*fix_text_generation" .
```

### Decision

If these files are **not imported anywhere**, they're dead code:
- ✅ KEEP if: Used by tests or other code
- ❌ DELETE if: Not referenced anywhere

**Safe approach**: Keep them but document as experimental:
```python
"""
EXPERIMENTAL/DEPRECATED FILES
These files were used during development but may not be active:
- calculate_comprehensive_metrics.py
- fix_text_generation_validation.py
- fix_validation_bugs.py

Check imports before modifying or deleting.
"""
```

---

## PART 5: TESTING CHECKLIST (2-4 hours)

### Test 1: Code Compilation
```bash
python -c "from src.routing import *; print('OK')"
```

### Test 2: Bin Assignment
```bash
# Run the bin assignment test from earlier
# Verify all difficulties map to correct bins
```

### Test 3: Phase 0 Analysis
```bash
python3 << 'EOF'
from src.routing import GeneralizedRoutingFramework, TaskSpec

framework = GeneralizedRoutingFramework()
task = TaskSpec(
    name="test",
    validation_fn=lambda x: len(x) > 0,
    difficulty_metric=lambda x: min(len(x) / 1000, 1.0),
    num_bins=5
)

outputs = {
    'test_model': [
        {'raw_input': 'short', 'raw_output': 'output'},
        {'raw_input': 'x' * 500, 'raw_output': 'output'},
    ]
}

decisions = framework.analyze_task(task, outputs)
print(f"Analysis OK: {len(decisions)} models analyzed")
EOF
```

### Test 4: Phase 1 Routing
```bash
python3 << 'EOF'
from src.routing import ProductionRouter, AnalysisResult

router = ProductionRouter()
router.add_analysis_result(AnalysisResult(
    task="test",
    model="test_model",
    capability_curve={0: 0.8, 1: 0.8, 2: 0.8, 3: 0.6, 4: 0.5},
    risk_curve={0: 0.2, 1: 0.2, 2: 0.2, 3: 0.4, 4: 0.5},
    tau_cap=2,
    tau_risk=3,
    zone="Q3",
    num_bins=5
))

model, decision = router.route(
    input_text="test input",
    task="test",
    difficulty_metric=lambda x: min(len(x) / 1000, 1.0),
    preferred_model="test_model"
)

print(f"Routing OK: routed to {model}")
EOF
```

### Test 5: Phase 2 Monitoring
```bash
# See PART 3 - Test Phase 2 section above
```

---

## IMPLEMENTATION ORDER

### Day 1 (4-6 hours): Fix Merge Conflicts
1. Resolve framework.py (keep Other branch features)
2. Resolve production_router.py (keep Other branch + fix formula)
3. Resolve README.md
4. Resolve requirements.txt
5. Test compilation
6. Commit: "Resolve merge conflicts"

### Day 2 (8-12 hours): Implement Phase 2
1. Create monitoring.py
2. Update ProductionRouter to use MonitoringLogger
3. Add log_result implementation
4. Update route() to call log_result
5. Test Phase 2
6. Commit: "Implement Phase 2 monitoring"

### Day 3 (2-4 hours): Testing & Cleanup
1. Run all 5 tests
2. Fix any issues found
3. Clean up dead code (optional)
4. Final compilation test
5. Commit: "Add tests and cleanup"

---

## VERIFICATION CHECKLIST

- [ ] Merge conflicts resolved (all 3 files)
- [ ] Code compiles without errors
- [ ] Bin assignment formula fixed
- [ ] Phase 2 monitoring implemented
- [ ] Test 1 passes (compilation)
- [ ] Test 2 passes (bin assignment)
- [ ] Test 3 passes (Phase 0 analysis)
- [ ] Test 4 passes (Phase 1 routing)
- [ ] Test 5 passes (Phase 2 monitoring)
- [ ] No new merge conflicts
- [ ] Git commit messages clear

---

## ESTIMATED TIMELINE

| Task | Hours | Days |
|------|-------|------|
| Resolve merge conflicts | 3 | Day 1 (morning) |
| Fix bin assignment | 1 | Day 1 (afternoon) |
| Implement Phase 2 | 10 | Day 2 |
| Testing & cleanup | 3 | Day 3 |
| **TOTAL** | **17** | **2.5 days** |

---

## SUCCESS CRITERIA

✅ Code compiles without errors
✅ All 5 tests pass
✅ Phase 1 routing works (phase 0 → phase 1 consistent)
✅ Phase 2 monitoring persists logs to disk
✅ No merge conflict markers in any file
✅ Bin assignment formula matches across phases

---

**Generated**: 2026-03-20
**Status**: Ready to implement
**Effort**: 17 hours (2.5 days of focused work)
