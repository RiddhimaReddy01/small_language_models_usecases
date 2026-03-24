# Code Generation Use Case - Evaluation Design

## 1. Task Definition

The task is **natural language to executable Python program generation**.

- **Input:** a textual programming problem
- **Output:** a Python function that satisfies the specification
- **Evaluation:** the generated code is executed against unit tests, and correctness is determined from the test results

This evaluation setting measures whether a model can convert a problem statement into valid, executable, and correct Python code.

## 2. Datasets

Two complementary benchmarks are used to capture both algorithmic reasoning and broader programming coverage.

| Dataset | Source | Total Problems | Language | Evaluation | Purpose |
|---|---|---:|---|---|---|
| `HumanEval` | OpenAI | 164 | Python | Unit tests | Measures algorithmic reasoning and clean function synthesis |
| `MBPP` | Google Research | 974 | Python | Unit tests | Covers broader basic-to-intermediate programming patterns |

## 3. Time-Bounded Sampling Strategy

Rather than enforcing a fixed number of tasks per model, the evaluation uses a **15-minute wall-clock budget per model**. A shared mixed sample is prepared from both datasets, and each model attempts as many tasks as possible within the time limit.

Recommended quick-run sample pool:

- up to `15` tasks from `HumanEval`
- up to `15` tasks from `MBPP`
- maximum candidate pool: `30` tasks per model

All models should use:

- the same sampled task IDs
- the same prompt template
- the same test harness
- the same stopping rule

This design is better suited to fast experiments because it captures both task-solving ability and practical throughput.

## 4. Models

### Local SLMs

| Model | Parameters | Deployment |
|---|---:|---|
| `Phi-3 Mini` | ~3.8B | local inference, 4-bit quantized |
| `Gemma 2B` | ~2B | local inference, 4-bit quantized |
| `Mistral 7B` | ~7B | local inference, 4-bit quantized |

### Baseline LLM

| Model | Purpose |
|---|---|
| `Gemini 1.5 Flash` | reference baseline and approximate performance ceiling |

## 5. Evaluation Protocol

### 5.1 Prompting

Use one standard prompt template for all models:

```text
Write a Python function that solves the following problem.

Problem:
{problem_description}

Requirements:
- Return only Python code
- Use the exact function name and parameters specified
- Do not include explanations
```

Optional robustness testing can be performed using prompt variants such as:

- `Solve this problem`
- `Write a Python function to solve`
- `Implement the function below`

### 5.2 Generation Settings

Keep generation parameters fixed across models as much as possible:

- low temperature for `pass@1`
- fixed `max_new_tokens`
- fixed `top_p` if used
- fixed random seed where supported

### 5.3 Execution

Generated code should be run in a controlled environment with:

- per-task timeout
- memory limit
- restricted system access where possible
- isolated execution for safety

### 5.4 Logging and Audit Trail

For each run, log:

- task ID
- dataset name
- full prompt
- model name
- generation settings
- generated code
- execution status
- test results
- latency
- memory usage

## 6. Table A: Capability Metrics

Table A reports correctness, robustness, compliance, calibration proxies, and safety over the tasks each model was able to attempt within the `15-minute` budget.

| Model | HumanEval Attempted | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Self-Consistency Score* | Format Compliance | Signature Compliance | Instruction Adherence | Deterministic Reproducibility* | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `Phi-3 Mini` |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `Gemma 2B` |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `Mistral 7B` |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `Gemini 1.5 Flash` |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

### Capability Metric Definitions

- **pass@1:** fraction of attempted tasks where the first generated program passes all unit tests
- **Syntax Error Rate:** proportion of outputs that are invalid Python
- **Runtime Failure Rate:** proportion of outputs that execute but crash during testing
- **Logical Failure Rate:** proportion of outputs that run successfully but fail one or more tests
- **Reliability Score:** `1 - total failure rate`, where failure includes syntax, runtime, and logical failure
- **Self-Consistency Score:** agreement across multiple generations for the same task; useful as a proxy for calibration
- **Format Compliance:** proportion of outputs that contain only code in the expected format
- **Signature Compliance:** proportion of outputs that use the exact required function name and parameter list
- **Instruction Adherence:** proportion of outputs that follow prompt constraints such as "return only code" and "no explanations"
- **Deterministic Reproducibility:** proportion of reruns that produce the same output under identical settings
- **Unsafe Code Rate:** proportion of generations containing dangerous operations such as shell execution, network access, or destructive file actions

Optional metrics are marked with `*` because they require extra generations or reruns.

## 7. Table B: Operational Metrics

Table B reports practical deployment metrics measured during the same `15-minute` evaluation run.

| Model | Time Budget | Tasks Completed in 15 min | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens | Cost / Request |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `Phi-3 Mini` | 15 min |  |  |  |  |  |  |  |
| `Gemma 2B` | 15 min |  |  |  |  |  |  |  |
| `Mistral 7B` | 15 min |  |  |  |  |  |  |  |
| `Gemini 1.5 Flash` | 15 min |  |  |  |  |  |  |  |

### Operational Metric Definitions

- **Tasks Completed in 15 min:** number of tasks fully processed, including generation and test execution, within the time budget
- **Avg Latency / Task:** average end-to-end time per task
- **P95 Latency:** 95th percentile latency to capture slow-tail behavior
- **Tokens/sec:** generation throughput
- **Peak RAM:** maximum memory usage observed during inference
- **Avg Output Tokens:** average number of generated tokens per task
- **Cost / Request:** average API or infrastructure cost per generation

## 8. Optional Additional Metrics

These metrics may be included as secondary analysis if references or extra instrumentation are available.

| Metric | Purpose |
|---|---|
| `CodeBLEU` | structural similarity to a reference implementation |
| `Edit Distance` | textual similarity to a reference solution |
| `Test Coverage` | completeness of the executed solution path |
| `Compilation Success` | syntactic validity or successful parsing |

## 9. Safety Screening

Before execution, generated code should be checked for unsafe behavior. Examples include:

- file deletion or arbitrary file modification
- shell or subprocess commands
- network calls
- unsafe imports such as `os`, `subprocess`, `socket`, or `shutil` when not required

Suggested metric:

`unsafe_code_rate = unsafe_generations / total_generations`

## 10. Report-Ready Methodology Paragraph

Each model was evaluated on a shared mixed sample drawn from `HumanEval` and `MBPP` under a fixed `15-minute` wall-clock budget. Instead of enforcing a fixed number of tasks per model, we measured how many tasks each model could attempt and complete within the allotted time. Capability metrics were computed over the attempted tasks and included correctness (`pass@1`), robustness (syntax, runtime, and logical failures), compliance with output and function-signature constraints, optional calibration proxies, and safety screening for unsafe code generation. Operational metrics captured latency, throughput, memory usage, and cost, enabling comparison of both code-generation quality and deployment practicality.

## 11. Interpretation

This design separates two distinct questions:

- **Can the model solve coding tasks correctly?** This is captured by Table A.
- **Can the model do so efficiently enough for practical use?** This is captured by Table B.

The time-bounded setup is especially useful for comparing local SLMs with a stronger API baseline because it reflects realistic deployment trade-offs between quality, speed, and resource consumption.
