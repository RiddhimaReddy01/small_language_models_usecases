# Metric Calculation: Math & Logic Guide

**Location**: `metric_calculators.py`
**Purpose**: Calculate actual task-specific accuracy metrics from model outputs
**Used by**: `sddf_capability_analyzer.extract_task_accuracy()`

---

## Overall Logic Flow

```
Model Output (raw_output)
         ↓
[Task-Specific Extraction]  ← Extract relevant information
         ↓
[Comparison with Ground Truth]  ← Compare to expected result
         ↓
[Calculate Metric]  ← Apply task-specific formula
         ↓
Accuracy Score ∈ [0, 1]
```

---

## 1. CODE GENERATION: Pass@1

### What It Measures
**Does the generated code execute without errors?**

### Mathematical Definition
```
Pass@1 = {
    1.0  if code_compiles(raw_output)
    0.0  otherwise
}
```

### Logical Flow
```
1. Extract Python code from raw_output
   - Look for ```python code block
   - Or check if 'def ' exists

2. Try to compile code
   compile(code, '<string>', 'exec')

3. Check result
   - Compilation succeeds → 1.0 ✓
   - SyntaxError → 0.0 ✗
   - Exception → 0.0 ✗
```

### Example
```python
# Sample
raw_output = """
Here's a solution:
```python
def reverse_string(s):
    return s[::-1]
```
"""

# Extraction → "def reverse_string(s):\n    return s[::-1]"
# Compilation → Success
# Result: 1.0 ✓
```

### Code
```python
def calculate_pass_at_1(sample):
    code = extract_code_block(sample['raw_output'])
    try:
        compile(code, '<string>', 'exec')
        return 1.0  # Passes
    except SyntaxError:
        return 0.0  # Fails
```

---

## 2. TEXT GENERATION: ROUGE-L

### What It Measures
**How much overlap is there between generated and reference text?**

### Mathematical Definition
**ROUGE-L = LCS(reference, generated) / len(reference)**

Where:
- **LCS**: Longest Common Subsequence
- **Numerator**: Length of longest matching sequence
- **Denominator**: Length of reference text

### Intuition
- Measures how much of the reference appears in generated (in order)
- NOT word-for-word, but sequence preservation
- Value: 0.0 (no overlap) to 1.0 (perfect match)

### Example Calculation
```
Reference:  "The quick brown fox"
Generated:  "The fast brown fox"

LCS (longest matching sequence):
"The" → match ✓
" " → match ✓
"brown" → match ✓
" " → match ✓
"fox" → match ✓
LCS = "The brown fox" (length 13)

ROUGE-L = 13 / 19 ≈ 0.68

Interpretation: 68% of reference appears in generated
```

### Why Not Just Word-Match?
```
Method 1: Exact Word Match
Generated: "The fast brown fox"
Reference: "The quick brown fox"
Words matching: The, brown, fox = 3/4 = 0.75

Method 2: ROUGE-L (sequence match)
The sequence "The _ brown fox" appears = 0.68
(More realistic: generated has different adjective)
```

### Code
```python
def calculate_rouge_l(sample):
    reference = sample.get('ground_truth')
    generated = sample.get('raw_output')

    matcher = SequenceMatcher(None, reference, generated)
    lcs_length = sum(block.size for block in matcher.get_matching_blocks())

    rouge_l = lcs_length / len(reference)
    return min(rouge_l, 1.0)
```

---

## 3. CLASSIFICATION: F1 Score

### What It Measures
**How accurate is the predicted class? (Balances precision and recall)**

### Mathematical Definition

**Precision = TP / (TP + FP)**
- "Of all predictions we made, how many were correct?"

**Recall = TP / (TP + FN)**
- "Of all actual positives, how many did we find?"

**F1 = 2 × (Precision × Recall) / (Precision + Recall)**
- Harmonic mean of precision and recall
- Balances both metrics equally

### Confusion Matrix Logic
```
                  Predicted
                  Positive | Negative
Actual │ Positive    TP    │   FN
       │ Negative    FP    │   TN

TP (True Positive):   Predicted positive, actually positive ✓
FP (False Positive):  Predicted positive, actually negative ✗
FN (False Negative):  Predicted negative, actually positive ✗
TN (True Negative):   Predicted negative, actually negative ✓
```

### Example 1: Correct Prediction
```
Task: Sentiment classification
Predicted: "positive"
Actual: "positive"

TP = 1, FP = 0, FN = 0
Precision = 1/(1+0) = 1.0  (100% of our predictions were right)
Recall = 1/(1+0) = 1.0     (We found all positives)
F1 = 2 × (1.0 × 1.0) / (1.0 + 1.0) = 1.0 ✓ (Perfect!)
```

### Example 2: Wrong Prediction
```
Predicted: "negative"
Actual: "positive"

TP = 0, FP = 0, FN = 1
Precision = 0/(0+0) = undefined → 0
Recall = 0/(0+1) = 0.0    (Didn't find the positive)
F1 = 0 ✗ (Complete failure)
```

### Code
```python
def calculate_f1_score(sample):
    predicted = sample['parsed_output']['predicted_class'].lower()
    actual = sample['ground_truth'].lower()

    # For binary classification: exact match
    if predicted == actual:
        return 1.0
    else:
        return 0.0
```

---

## 4. MATHEMATICS: Exact Match

### What It Measures
**Does the answer exactly match the ground truth (after normalization)?**

### Mathematical Definition
```
Exact Match = {
    1.0  if normalize(predicted) == normalize(ground_truth)
    0.0  otherwise
}
```

### Normalization Steps
1. **Remove articles**: "a", "an", "the"
2. **Remove punctuation**: . , ! ? ' " ; :
3. **Lowercase**: "Apple" → "apple"
4. **Collapse whitespace**: "hello  world" → "hello world"

### Example
```
Question: "What is the capital of France?"
Generated: "The capital of France is Paris."
Ground truth: "Paris."

Step 1: Remove articles
Generated: "capital of France is Paris"
Ground truth: "Paris"

Step 2: Remove punctuation
Generated: "capital of france is paris"
Ground truth: "paris"

Step 3: Lowercase (already done)

Step 4: Collapse whitespace
Generated: "capital of france is paris"
Ground truth: "paris"

Match? NO → 0.0 ✗

BUT if ground truth was "capital of France is Paris":
After normalization both become "capital of france is paris"
Match? YES → 1.0 ✓
```

### Code
```python
def calculate_exact_match(sample):
    predicted = normalize_answer(sample['raw_output'])
    truth = normalize_answer(sample['ground_truth'])

    return 1.0 if predicted == truth else 0.0

def normalize_answer(s):
    s = re.sub(r'\b(a|an|the)\b', ' ', s)  # Remove articles
    s = re.sub(r'[^\w\s]', ' ', s)          # Remove punctuation
    s = ' '.join(s.split())                  # Collapse whitespace
    return s.lower()                         # Lowercase
```

---

## 5. SUMMARIZATION: ROUGE-L (Same as Text Generation)

Uses **ROUGE-L = LCS / reference_length**

### Why ROUGE-L for Summaries?
- Summaries should preserve key information from source
- ROUGE-L measures if generated summary contains source sequences
- Example: Source has "quick brown fox", summary should contain these terms

---

## 6. RETRIEVAL GROUNDED: F1 (Token-Level)

### What It Measures
**How much token overlap is there between predicted and reference answer?**

### Mathematical Definition

**Token Precision = overlapping_tokens / predicted_tokens**
- "Of tokens we predicted, how many were in reference?"

**Token Recall = overlapping_tokens / reference_tokens**
- "Of tokens in reference, how many did we predict?"

**F1 = 2 × (Precision × Recall) / (Precision + Recall)**

### Example: Question Answering
```
Question: "What is the capital of France?"
Generated: "The capital of France is Paris, a beautiful city."
Ground truth: "Paris"

Tokenize:
Predicted tokens: ["the", "capital", "of", "france", "is", "paris", "a", "beautiful", "city"]
Reference tokens: ["paris"]

Overlapping tokens: ["paris"] (count = 1)

Precision = 1/9 ≈ 0.11   (1 of 9 tokens match reference)
Recall = 1/1 = 1.0       (Found the answer token)
F1 = 2 × (0.11 × 1.0) / (0.11 + 1.0) ≈ 0.20

Interpretation: Found the answer but generated lot of extra words
```

### Code
```python
def calculate_f1_retrieval(sample):
    pred_tokens = set(sample['raw_output'].lower().split())
    ref_tokens = set(sample['ground_truth'].lower().split())

    overlap = len(pred_tokens & ref_tokens)
    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)

    f1 = 2 * (precision * recall) / (precision + recall)
    return f1
```

---

## 7. INSTRUCTION FOLLOWING: Constraint Satisfaction

### What It Measures
**What percentage of instructions were followed?**

### Mathematical Definition
```
Constraint Satisfaction = satisfied_constraints / total_constraints
```

### Example: Email Writing
```
Instructions:
1. Start with "Dear"
2. Include exactly 3 paragraphs
3. End with "Sincerely"

Generated:
"Dear John,

Paragraph 1...

Paragraph 2...

Paragraph 3...

Sincerely, Jane"

Check:
1. Starts with "Dear"? YES ✓
2. Has 3 paragraphs? YES ✓
3. Ends with "Sincerely"? YES ✓

Satisfaction = 3/3 = 1.0 (100%)
```

### Code
```python
def calculate_constraint_satisfaction(sample):
    constraints = sample.get('constraints', [])
    satisfied = sum(
        1 for c in constraints if check_constraint(sample['raw_output'], c)
    )
    return satisfied / len(constraints)
```

---

## 8. INFORMATION EXTRACTION: Field Accuracy

### What It Measures
**What percentage of fields were extracted correctly?**

### Mathematical Definition
```
Field Accuracy = correct_fields / total_fields
```

### Example: Contact Extraction
```
Text: "John Smith works at Acme Corp. john@example.com, 555-0123"

Fields to extract: [name, email, phone, company]
Ground truth: {
    "name": "John Smith",
    "email": "john@example.com",
    "phone": "555-0123",
    "company": "Acme Corp"
}

Extracted: {
    "name": "John Smith",        ✓ Match!
    "email": "john@example.com", ✓ Match!
    "phone": "555-0123",         ✓ Match!
    "company": "Acme"            ✗ Mismatch! (missing "Corp")
}

Accuracy = 3/4 = 0.75 (75%)
```

### Code
```python
def calculate_field_accuracy(sample):
    extracted = sample['parsed_output']
    ground_truth = sample['ground_truth_fields']

    correct = sum(
        1 for field, value in ground_truth.items()
        if normalize_answer(str(extracted.get(field, '')))
           == normalize_answer(str(value))
    )
    return correct / len(ground_truth)
```

---

## Integration in Capability Analysis

### Step-by-Step Process

**1. Load Sample**
```python
sample = {
    'raw_output': "...",
    'ground_truth': "...",
    'parsed_output': {...},
    ...
}
```

**2. Call Metric Calculator**
```python
task_type = "code_generation"
accuracy = extract_task_accuracy(sample, task_type)
```

**3. Calculate Metric (Option B: On Demand)**
```python
accuracy = calculate_metric(sample, task_type)
# If sample.get('raw_output') exists, calculates actual metric
```

**4. Aggregate by Bin**
```python
# Group samples by difficulty bin
for bin_idx in range(n_bins):
    samples_in_bin = [s for s in samples if bin_id(s) == bin_idx]
    accuracies = [extract_task_accuracy(s, task_type) for s in samples_in_bin]

    # Compute mean accuracy for this bin
    capability[bin_idx] = mean(accuracies)
```

**5. Detect Degradation (Inflection Point)**
```python
# Find where accuracy drops sharply
tau_capability = find_degradation_point(capability_curve)
# This is where model performance breaks down
```

---

## Summary: Metric Selection Guide

| Task | Metric | Type | Range | Meaning |
|------|--------|------|-------|---------|
| Code Gen | Pass@1 | Binary | 0-1 | Code executes? |
| Text Gen | ROUGE-L | Continuous | 0-1 | Sequence overlap |
| Classification | F1 | Continuous | 0-1 | Prediction accuracy |
| Math | Exact Match | Binary | 0-1 | Answer exact? |
| Summarization | ROUGE-L | Continuous | 0-1 | Summary overlap |
| Retrieval | F1 (token) | Continuous | 0-1 | Token match |
| Instructions | Satisfaction | Continuous | 0-1 | % followed |
| Extraction | Field Accuracy | Continuous | 0-1 | % fields correct |

---

## Fallback Strategy

**If metric calculation fails:**
1. ✓ Try to calculate from raw output (metric_calculators.py)
2. ✓ Try to extract from pre-calculated 'metrics' field (if available)
3. ✓ Fall back to validation-based binary (1.0 = valid, 0.0 = invalid)

**Note**: Fallback is **NOT task-specific accuracy**, just "output is valid or not"
