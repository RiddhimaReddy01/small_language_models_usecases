#!/usr/bin/env python3
"""
SDDF Complexity Calculator

Compute task complexity using SDDF difficulty vector:
d(x) = (n_in, H, R̂, |Γ|, α, D)

where:
- n_in: Input token count (Pre-inference routing)
- H: Shannon entropy (Information density)
- R̂: Estimated reasoning depth (Post-hoc analysis)
- |Γ|: Output constraint count (Structural complexity)
- α: Parametric dependence (Knowledge demand)
- D: Dependency distance (Syntactic complexity)
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import math
import statistics
import re


class SDDFComplexityCalculator:
    """Calculate SDDF difficulty vector for each sample"""

    def __init__(self, sddf_components: str = 'learned', normalization: str = 'zscore'):
        """
        Args:
            sddf_components: Which components to use
                'learned': Use learned weights from optimization (default)
                'all_6': Use all six components [n_in, H, R, |Γ|, α, D] with equal weights
                'top_3': Use top three [R, |Γ|, α] with equal weights
            normalization: How to normalize complexity values
                'zscore': Standard (z-score) normalization (not currently used)
        """
        self.sddf_components = sddf_components
        self.normalization = normalization
        self.learned_weights = self._load_learned_weights()
        self.task_types = [
            "text_generation",
            "code_generation",
            "classification",
            "maths",
            "summarization",
            "retrieval_grounded",
            "instruction_following",
            "information_extraction"
        ]

    def _load_learned_weights(self) -> dict:
        """
        Load learned weights from optimization output

        ISSUE 15 FIX: Use centralized config for path
        """
        try:
            from .config import PATHS
            weights_file = PATHS['learned_weights']
        except ImportError:
            # Fallback if config import fails
            base_dir = Path(__file__).parent.parent.parent
            weights_file = base_dir / "data/config/learned_sddf_weights.json"

        if weights_file.exists():
            try:
                with open(weights_file) as f:
                    data = json.load(f)
                    return data.get('weights', {})
            except Exception:
                pass

        # Fallback: equal weights if file not found
        return {
            'n_in': 1/6,
            'H': 1/6,
            'R_hat': 1/6,
            'Gamma': 1/6,
            'alpha': 1/6,
            'D': 1/6,
        }

    def get_benchmark_dir(self, task_type: str) -> Path:
        """
        Get correct benchmark directory for task

        ISSUE 15 FIX: Use centralized config instead of hard-coded path calculation
        """
        try:
            from .config import PATHS
        except ImportError:
            # Fallback if config import fails
            base_dir = Path(__file__).parent.parent.parent.parent.parent
            if task_type == 'text_generation':
                return base_dir / "data/benchmark/benchmark_output_fixed"
            elif task_type in ['code_generation', 'summarization']:
                return base_dir / "data/benchmark/benchmark_output_fixed_all"
            else:
                return base_dir / "data/benchmark/benchmark_output"

        # Use centralized config
        if task_type == 'text_generation':
            return PATHS['benchmark_fixed']
        elif task_type in ['code_generation', 'summarization']:
            return PATHS['benchmark_fixed_all']
        else:
            return PATHS['benchmark_output']

    def load_outputs(self, task_type: str, model: str) -> List[Dict]:
        """Load JSONL output file"""
        benchmark_dir = self.get_benchmark_dir(task_type)
        output_file = benchmark_dir / task_type / model / "outputs.jsonl"

        if not output_file.exists():
            return []

        outputs = []
        parse_errors = 0

        try:
            with open(output_file) as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            outputs.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            parse_errors += 1
                            # Silent skip but track count
                            continue
        except IOError as e:
            # File read error - still return what we have
            pass

        return outputs

    # ========== SDDF COMPONENT 1: n_in (Input Token Count) ==========

    def calculate_n_in(self, sample: Dict) -> float:
        """
        Calculate input token count
        Approximation: 1 token ≈ 4 characters
        """
        raw_input = sample.get('raw_input') or sample.get('prompt', '')
        token_count = len(raw_input) / 4.0
        return min(token_count / 1000.0, 1.0)  # Normalize to [0, 1]

    # ========== SDDF COMPONENT 2: H (Shannon Entropy) ==========

    def calculate_shannon_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy of input text
        H = -Σ P(char) * log2(P(char))
        High entropy = diverse/complex text
        """
        if not text:
            return 0.0

        # Character frequency
        char_freq = defaultdict(int)
        for char in text.lower():
            char_freq[char] += 1

        # Calculate entropy
        entropy = 0.0
        text_len = len(text)
        for count in char_freq.values():
            p = count / text_len
            if p > 0:
                entropy -= p * math.log2(p)

        # Normalize to [0, 1]
        max_entropy = math.log2(min(len(char_freq), 256))
        if max_entropy > 0:
            return entropy / max_entropy
        return 0.0

    def calculate_H(self, sample: Dict) -> float:
        """Shannon entropy of input"""
        raw_input = sample.get('raw_input') or sample.get('prompt', '')
        return self.calculate_shannon_entropy(raw_input)

    # ========== SDDF COMPONENT 3: R̂ (Estimated Reasoning Depth) ==========

    def calculate_estimated_reasoning_depth(self, sample: Dict, task_type: str) -> float:
        """
        Estimate reasoning depth from sample characteristics

        Heuristics:
        - Code gen: More complex if has nested logic
        - Math: More complex if longer input (more steps)
        - QA: More complex if requires multi-hop reasoning
        """
        raw_input = sample.get('raw_input') or sample.get('prompt', '')
        raw_output = sample.get('raw_output', '')

        if task_type == 'code_generation':
            # Estimate from code structure complexity
            complexity = 0.0
            # Count brackets/nesting depth
            max_depth = 0
            current_depth = 0
            for char in raw_output:
                if char in '{([':
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char in '})]':
                    current_depth -= 1
            complexity = min(max_depth / 5.0, 1.0)  # Normalize

        elif task_type in ['maths', 'instruction_following']:
            # Estimate from input length (longer = more steps)
            complexity = min(len(raw_input) / 2000.0, 1.0)

        elif task_type in ['retrieval_grounded', 'summarization']:
            # Estimate from input + output complexity
            complexity = min((len(raw_input) + len(raw_output)) / 3000.0, 1.0)

        else:
            # Default: based on input length
            complexity = min(len(raw_input) / 1000.0, 1.0)

        return complexity

    def calculate_R(self, sample: Dict, task_type: str) -> float:
        """Estimated reasoning depth"""
        return self.calculate_estimated_reasoning_depth(sample, task_type)

    # ========== HELPER FUNCTIONS FOR ISSUE #1 & #2 FIXES ==========

    def extract_numbers_from_problem(self, prompt: str) -> List[str]:
        """
        ISSUE #1 FIX: Extract ONLY numbers from the problem statement
        Do NOT extract from solution/working steps

        Returns unique number strings from the problem text
        """
        # Find all numeric values (integers and decimals)
        numbers = re.findall(r'\d+(?:\.\d+)?', prompt)

        # Return unique values, preserving order
        seen = set()
        unique_numbers = []
        for num in numbers:
            if num not in seen:
                seen.add(num)
                unique_numbers.append(num)

        return unique_numbers

    def compute_parametric_complexity_refined(self, prompt: str) -> float:
        """
        ISSUE #2 FIX: Compute refined alpha from problem statement only

        Measures parametric complexity:
        - Number of distinct constants (0.3 weight)
        - Number of distinct unknowns/variables (0.3 weight)
        - Complexity of operations involved (0.4 weight)

        Returns value in [0, 1]
        """
        # Extract unique numbers from problem only
        numbers = self.extract_numbers_from_problem(prompt)
        num_parameters = len(numbers)

        # Count unknowns (variables like x, y, a, b, etc.)
        # But exclude single letters in words
        unknowns = set()
        for match in re.finditer(r'\b[a-z]\b', prompt.lower()):
            if match.group(0) not in {'a', 'i'}:  # Skip common articles
                unknowns.add(match.group(0))

        num_unknowns = len(unknowns)

        # Count operations (indicates complexity of relationships)
        operations = {
            'multiply': prompt.count('*'),
            'divide': prompt.count('/'),
            'power': prompt.count('^') + prompt.count('**'),
            'sqrt': prompt.count('sqrt') + prompt.count('√'),
            'parentheses': prompt.count('('),
        }
        num_operations = sum(operations.values())

        # Composite score: normalize by typical maximums
        # Typical ranges: 0-5 parameters, 0-3 unknowns, 0-10 operations
        alpha = (
            (min(num_parameters, 5) / 5.0) * 0.3 +
            (min(num_unknowns, 3) / 3.0) * 0.3 +
            (min(num_operations, 10) / 10.0) * 0.4
        )

        return min(max(alpha, 0.0), 1.0)

    # ========== SDDF COMPONENT 4: |Γ| (Output Constraint Count) ==========

    def calculate_output_constraint_count(self, sample: Dict, task_type: str) -> float:
        """
        Calculate output constraint count |Γ| from actual output structure

        ISSUE 12 FIX: Extract from parsed_output instead of task-constant
        Higher |Γ| means more structural requirements = more ways to fail

        Sample-specific variance:
        - Code: Count actual code blocks (1-3 = 0.33-1.0)
        - Math: Count intermediate values (3-15 = 0.2-1.0)
        - Others: Infer from output structure
        """
        parsed_output = sample.get('parsed_output', {})

        if task_type == 'code_generation':
            # Number of code blocks = number of functions/classes to implement
            code_blocks = parsed_output.get('code_blocks', [])
            num_functions = len(code_blocks)
            # Typical range: 1-3 functions per task
            # 0 blocks -> 0.0, 1 block -> 0.33, 2 blocks -> 0.67, 3+ -> 1.0
            return min(num_functions / 3.0, 1.0)

        elif task_type == 'maths':
            # ISSUE #1 FIX: Use unique numbers from problem statement only
            # Extract from prompt (problem), not raw_output (solution)
            prompt = sample.get('prompt', '')
            problem_numbers = self.extract_numbers_from_problem(prompt)
            num_unique_values = len(problem_numbers)

            # Typical range: 1-5 unique parameters per problem
            # 1 value -> 0.2, 3 values -> 0.6, 5+ -> 1.0
            return min(num_unique_values / 5.0, 1.0)

        elif task_type == 'classification':
            # Binary constraint: one label only
            return 0.2

        elif task_type in ['summarization', 'text_generation']:
            # Format constraint (length, structure)
            return 0.3

        elif task_type == 'retrieval_grounded':
            # Answer field constraint
            return 0.2

        elif task_type == 'instruction_following':
            # Multiple instruction constraints
            return 0.4

        elif task_type == 'information_extraction':
            # Multiple fields to extract
            return 0.5

        else:
            # Fallback: safe middle value
            return 0.3

    def calculate_constraint_count(self, sample: Dict, task_type: str) -> float:
        """Output constraint count |Γ|"""
        return self.calculate_output_constraint_count(sample, task_type)

    # ========== SDDF COMPONENT 5: α (Parametric Dependence) ==========

    def calculate_parametric_dependence(self, sample: Dict, task_type: str) -> float:
        """
        Estimate knowledge demand beyond the context

        ISSUE 12 FIX: Extract from actual output instead of task-constant
        High α: Requires external knowledge (libraries, APIs)
        Low α: Can be solved from context alone

        Sample-specific variance:
        - Code: Count external imports (0-5 = 0-1.0)
        - Math: Check for special constants (0 or 0.2-0.4)
        - Others: Infer from output complexity
        """
        raw_output = sample.get('raw_output', '').lower()
        raw_input = sample.get('raw_input') or sample.get('prompt', '')

        if task_type == 'code_generation':
            # External dependencies = libraries/APIs needed
            external_indicators = [
                'import ', 'from ', 'numpy', 'pandas', 'scipy',
                'requests', 'torch', 'tensorflow', 'sklearn'
            ]
            num_external = sum(1 for ind in external_indicators if ind in raw_output)
            # 0-5 external libraries possible
            # 0 imports -> 0.0, 1 import -> 0.2, 2 -> 0.4, etc.
            return min(num_external / 5.0, 1.0)

        elif task_type == 'maths':
            # ISSUE #2 FIX: Refined alpha based on problem parameters
            # Extract parametric complexity from problem statement only
            prompt = sample.get('prompt', '')
            return self.compute_parametric_complexity_refined(prompt)

        elif task_type == 'retrieval_grounded':
            # Should be low alpha (QA from context only)
            # If answer references external knowledge, higher alpha
            return 0.3 if len(raw_output) > 100 else 0.1

        elif task_type == 'classification':
            # Label depends on training knowledge
            return 0.5

        elif task_type == 'summarization':
            # Summary uses mostly input, some knowledge
            return 0.2

        elif task_type == 'instruction_following':
            # Depends on instruction complexity
            return min(len(raw_input) / 1000.0, 0.8)

        elif task_type == 'text_generation':
            # May require domain knowledge based on length/complexity
            return min(len(raw_output) / 1000.0, 0.7)

        else:
            return 0.4

    def calculate_alpha(self, sample: Dict, task_type: str) -> float:
        """Parametric dependence"""
        return self.calculate_parametric_dependence(sample, task_type)

    # ========== SDDF COMPONENT 6: D (Dependency Distance) ==========

    def calculate_dependency_distance(self, text: str) -> float:
        """
        Estimate syntactic complexity via dependency distance

        Heuristic: Average word distance to nearest clause boundary
        High D: Complex sentence structure
        Low D: Simple sentence structure
        """
        if not text:
            return 0.0

        # Split into sentences
        sentences = text.split('.')
        distances = []

        for sentence in sentences:
            words = sentence.strip().split()
            if len(words) > 1:
                # Average distance between words
                avg_distance = len(words) / 2.0
                distances.append(avg_distance)

        if distances:
            avg_dep_distance = statistics.mean(distances)
            # Normalize: assume max ~20 word distance
            return min(avg_dep_distance / 20.0, 1.0)

        return 0.0

    def calculate_D(self, sample: Dict) -> float:
        """Dependency distance"""
        raw_input = sample.get('raw_input') or sample.get('prompt', '')
        return self.calculate_dependency_distance(raw_input)

    # ========== INTEGRATE ALL COMPONENTS ==========

    def calculate_sddf_vector(self, sample: Dict, task_type: str) -> Dict[str, float]:
        """
        Calculate complete SDDF difficulty vector
        d(x) = (n_in, H, R̂, |Γ|, α, D)
        """
        return {
            'n_in': self.calculate_n_in(sample),
            'H': self.calculate_H(sample),
            'R': self.calculate_R(sample, task_type),
            'constraint_count': self.calculate_constraint_count(sample, task_type),
            'alpha': self.calculate_alpha(sample, task_type),
            'D': self.calculate_D(sample),
        }

    def apply_nonlinear_scaling(self, value: float, exponent: float = 0.5) -> float:
        """
        Apply power function scaling to spread low values across full range
        value^exponent where exponent < 1 amplifies low values

        Example with exponent 0.5 (square root):
        - 0.04 → 0.2
        - 0.09 → 0.3
        - 0.25 → 0.5
        - 0.64 → 0.8
        """
        if value <= 0:
            return 0.0
        return min(value ** exponent, 1.0)

    def calculate_composite_complexity(self, sddf_vector: Dict[str, float]) -> float:
        """
        Calculate single composite complexity score ξ(x) ∈ [0,1] from SDDF vector
        Uses learned weights from optimization by default
        Applies non-linear scaling to spread across bins [0, n_bins-1]
        """
        if self.sddf_components == 'learned':
            # Use learned weights from optimization
            w = self.learned_weights
            weighted_sum = (
                w.get('n_in', 1/6) * sddf_vector['n_in'] +
                w.get('H', 1/6) * sddf_vector['H'] +
                w.get('R_hat', w.get('R', 1/6)) * sddf_vector['R'] +
                w.get('Gamma', w.get('constraint_count', 1/6)) * sddf_vector['constraint_count'] +
                w.get('alpha', 1/6) * sddf_vector['alpha'] +
                w.get('D', 1/6) * sddf_vector['D']
            )
            linear_complexity = weighted_sum

        elif self.sddf_components == 'all_6':
            # Equal weights for all six components
            components = [
                sddf_vector['n_in'],
                sddf_vector['H'],
                sddf_vector['R'],
                sddf_vector['constraint_count'],
                sddf_vector['alpha'],
                sddf_vector['D'],
            ]
            linear_complexity = statistics.mean(components)

        elif self.sddf_components == 'top_3':
            # Top 3: R (reasoning), |Γ| (constraints), α (knowledge)
            components = [
                sddf_vector['R'],
                sddf_vector['constraint_count'],
                sddf_vector['alpha'],
            ]
            linear_complexity = statistics.mean(components)

        else:
            # Default to learned
            return self.calculate_composite_complexity(sddf_vector)

        # Apply non-linear scaling (cube root: exponent 0.33)
        # Spreads low values across full [0,1] range
        # Example: 0.1 → 0.464, 0.3 → 0.670, 0.5 → 0.794
        scaled_complexity = self.apply_nonlinear_scaling(linear_complexity, exponent=0.33)

        return scaled_complexity

    def analyze_task(self, task_type: str, model: str, max_samples: int = 100) -> List[Dict]:
        """
        Analyze single task/model combination
        Returns list of samples with SDDF vectors and complexity scores
        """
        outputs = self.load_outputs(task_type, model)

        if not outputs:
            return []

        results = []
        for i, sample in enumerate(outputs[:max_samples]):
            try:
                sddf_vector = self.calculate_sddf_vector(sample, task_type)
                composite_complexity = self.calculate_composite_complexity(sddf_vector)

                results.append({
                    'task_type': task_type,
                    'model': model,
                    'sample_id': i,
                    'sddf_vector': sddf_vector,
                    'composite_complexity': composite_complexity,
                    'raw_input': sample.get('raw_input') or sample.get('prompt', ''),
                    'raw_output': sample.get('raw_output', ''),
                    'bin': sample.get('bin'),
                    'validation_checks': sample.get('validation_checks', {}),
                })
            except:
                continue

        return results


if __name__ == "__main__":
    calculator = SDDFComplexityCalculator()

    # Example: Calculate SDDF for text generation
    results = calculator.analyze_task('text_generation', 'qwen2.5_1.5b', max_samples=50)

    print(f"\nCalculated SDDF vectors for {len(results)} samples")
    if results:
        sample = results[0]
        print(f"\nExample SDDF Vector (first sample):")
        print(f"  n_in (input tokens): {sample['sddf_vector']['n_in']:.3f}")
        print(f"  H (entropy): {sample['sddf_vector']['H']:.3f}")
        print(f"  R̂ (reasoning depth): {sample['sddf_vector']['R']:.3f}")
        print(f"  |Γ| (constraints): {sample['sddf_vector']['constraint_count']:.3f}")
        print(f"  α (dependence): {sample['sddf_vector']['alpha']:.3f}")
        print(f"  D (dependency distance): {sample['sddf_vector']['D']:.3f}")
        print(f"  Composite Complexity: {sample['composite_complexity']:.3f}")
