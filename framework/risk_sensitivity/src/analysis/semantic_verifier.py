#!/usr/bin/env python3
"""
Semantic Verifier - Task-Specific Ground Truth Verification

Implements Option B: Task-specific metrics for semantic correctness
- Code Generation: Execute code and verify correctness
- Maths: Verify numerical answers
- Classification: Check if predicted label is correct (requires reference)
- Text Generation: Compare with reference using metrics (requires reference)
"""

import json
import re
import ast
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class SemanticVerifier:
    """Verify semantic correctness using task-specific logic"""

    def __init__(self):
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

        self.models = [
            'qwen2.5_1.5b',
            'phi3_mini',
            'tinyllama_1.1b',
            'llama_llama-3.3-70b-versatile',
        ]

    def get_benchmark_dir(self, task_type: str) -> Path:
        """Navigate to benchmark directory"""
        base_dir = Path(__file__).parent.parent.parent.parent.parent

        if task_type == 'text_generation':
            return base_dir / "data/benchmark/benchmark_output_fixed"
        elif task_type in ['code_generation', 'summarization']:
            return base_dir / "data/benchmark/benchmark_output_fixed_all"
        else:
            return base_dir / "data/benchmark/benchmark_output"

    # ========== MATHS VERIFICATION ==========

    def verify_math_answer(self, prompt: str, extracted_answer: Optional[float]) -> Dict:
        """
        Verify mathematical answer by solving the problem independently

        Returns:
            {
                'can_verify': bool,
                'is_correct': bool or None,
                'expected_answer': float or None,
                'model_answer': float or None,
                'method': str,
            }
        """
        if extracted_answer is None:
            return {
                'can_verify': False,
                'is_correct': None,
                'expected_answer': None,
                'model_answer': None,
                'method': 'NO_ANSWER_EXTRACTED'
            }

        # Simple algebraic equations: ax + b = c
        match = re.search(r'(\d+\.?\d*)\s*x\s*\+\s*(\d+\.?\d*)\s*=\s*(\d+\.?\d*)', prompt)
        if match:
            a, b, c = float(match.group(1)), float(match.group(2)), float(match.group(3))
            expected = (c - b) / a
            is_correct = abs(extracted_answer - expected) < 0.01
            return {
                'can_verify': True,
                'is_correct': is_correct,
                'expected_answer': expected,
                'model_answer': extracted_answer,
                'method': 'LINEAR_EQUATION'
            }

        # Arithmetic expressions: evaluate them
        try:
            # Extract the arithmetic expression (simple cases)
            match = re.search(r'Calculate:\s*(.+?)(?:\s*\(|$)', prompt)
            if match:
                expr = match.group(1).strip()
                # Replace ^ with ** for exponentiation
                expr_eval = expr.replace('^', '**')
                # Replace ! with factorial (basic support)
                if '!' in expr_eval:
                    # Handle factorial: n! = n*(n-1)*...*1
                    for num in re.findall(r'(\d+)!', expr_eval):
                        fact = math.factorial(int(num))
                        expr_eval = expr_eval.replace(f'{num}!', str(fact))

                expected = eval(expr_eval)
                is_correct = abs(extracted_answer - expected) < 0.01
                return {
                    'can_verify': True,
                    'is_correct': is_correct,
                    'expected_answer': expected,
                    'model_answer': extracted_answer,
                    'method': 'ARITHMETIC_EVAL'
                }
        except:
            pass

        # Square root questions
        if 'square root' in prompt.lower():
            match = re.search(r'square root of (\d+\.?\d*)', prompt, re.IGNORECASE)
            if match:
                num = float(match.group(1))
                expected = math.sqrt(num)
                is_correct = abs(extracted_answer - expected) < 0.01
                return {
                    'can_verify': True,
                    'is_correct': is_correct,
                    'expected_answer': expected,
                    'model_answer': extracted_answer,
                    'method': 'SQUARE_ROOT'
                }

        # Couldn't verify - return that we can't
        return {
            'can_verify': False,
            'is_correct': None,
            'expected_answer': None,
            'model_answer': extracted_answer,
            'method': 'UNSUPPORTED_PROBLEM_TYPE'
        }

    # ========== CODE GENERATION VERIFICATION ==========

    def verify_code_syntax(self, code_blocks: List[str]) -> Dict:
        """
        Verify Python code syntax

        Returns:
            {
                'has_code': bool,
                'syntax_valid': bool,
                'errors': List[str],
                'testable': bool,
                'method': str,
            }
        """
        if not code_blocks:
            return {
                'has_code': False,
                'syntax_valid': False,
                'errors': ['No code blocks extracted'],
                'testable': False,
                'method': 'NO_CODE'
            }

        errors = []
        all_valid = True

        for i, code in enumerate(code_blocks):
            try:
                ast.parse(code)
            except SyntaxError as e:
                all_valid = False
                errors.append(f"Block {i}: {str(e)}")

        return {
            'has_code': True,
            'syntax_valid': all_valid,
            'errors': errors,
            'testable': all_valid and len(code_blocks) > 0,
            'method': 'PYTHON_AST_PARSE'
        }

    def verify_code_functionality(self, prompt: str, code_blocks: List[str]) -> Dict:
        """
        Verify code functionality with basic tests

        Limited by safety - only run simple test cases
        """
        if not code_blocks:
            return {'functional': False, 'reason': 'NO_CODE_BLOCKS'}

        syntax_check = self.verify_code_syntax(code_blocks)
        if not syntax_check['syntax_valid']:
            return {'functional': False, 'reason': 'SYNTAX_ERROR', 'errors': syntax_check['errors']}

        # Try to run simple tests for known functions
        code = code_blocks[0]

        # String reverse function
        if 'reverse' in prompt.lower() and 'string' in prompt.lower():
            try:
                namespace = {}
                exec(code, namespace)
                if 'reverse_string' in namespace:
                    func = namespace['reverse_string']
                    result = func("hello")
                    if result == "olleh":
                        return {'functional': True, 'test': 'REVERSE_STRING', 'passed': True}
                    else:
                        return {'functional': False, 'test': 'REVERSE_STRING', 'passed': False, 'expected': 'olleh', 'got': result}
            except Exception as e:
                return {'functional': False, 'reason': 'EXECUTION_ERROR', 'error': str(e)}

        # Factorial function
        if 'factorial' in prompt.lower():
            try:
                namespace = {}
                exec(code, namespace)
                if 'factorial' in namespace:
                    func = namespace['factorial']
                    result = func(5)
                    if result == 120:
                        return {'functional': True, 'test': 'FACTORIAL', 'passed': True}
                    else:
                        return {'functional': False, 'test': 'FACTORIAL', 'passed': False, 'expected': 120, 'got': result}
            except Exception as e:
                return {'functional': False, 'reason': 'EXECUTION_ERROR', 'error': str(e)}

        # Generic: code is syntactically valid but we can't verify functionality
        return {'functional': None, 'reason': 'UNSUPPORTED_PROBLEM', 'note': 'Code is syntactically valid but functionality cannot be tested'}

    # ========== GENERAL VERIFICATION ==========

    def verify_sample(self, task_type: str, sample: Dict) -> Dict:
        """
        Verify semantic correctness for a sample based on task type
        """
        prompt = sample.get('prompt', '')
        parsed_output = sample.get('parsed_output', {})

        verification = {
            'task': task_type,
            'prompt_preview': prompt[:60],
            'semantic_verifiable': False,
            'semantic_correct': None,
        }

        if task_type == 'maths':
            answer = parsed_output.get('answer')
            math_verify = self.verify_math_answer(prompt, answer)
            verification['semantic_verifiable'] = math_verify['can_verify']
            verification['semantic_correct'] = math_verify.get('is_correct')
            verification['details'] = math_verify

        elif task_type == 'code_generation':
            code_blocks = parsed_output.get('code_blocks', [])
            syntax_verify = self.verify_code_syntax(code_blocks)
            func_verify = self.verify_code_functionality(prompt, code_blocks)

            verification['semantic_verifiable'] = syntax_verify['syntax_valid']
            verification['syntax_valid'] = syntax_verify['syntax_valid']
            verification['functional'] = func_verify.get('functional')
            if func_verify.get('functional'):
                verification['semantic_correct'] = True
            elif func_verify.get('functional') is False:
                verification['semantic_correct'] = False
            # else: None if functional verification not applicable
            verification['details'] = func_verify

        else:
            # Other tasks: we don't have reference data
            verification['semantic_verifiable'] = False
            verification['reason'] = 'NO_REFERENCE_DATA'

        return verification

    def analyze_task_semantic_correctness(self, task_type: str, model: str, max_samples: int = 100) -> Dict:
        """Analyze semantic correctness for a task/model combination"""
        benchmark_dir = self.get_benchmark_dir(task_type)
        output_file = benchmark_dir / task_type / model / "outputs.jsonl"

        if not output_file.exists():
            return {'error': f'No outputs found: {output_file}'}

        verifications = []
        verifiable_count = 0
        correct_count = 0
        samples_analyzed = 0

        try:
            with open(output_file) as f:
                for i, line in enumerate(f):
                    if i >= max_samples:
                        break

                    try:
                        sample = json.loads(line)
                        verification = self.verify_sample(task_type, sample)
                        verifications.append(verification)

                        if verification['semantic_verifiable']:
                            verifiable_count += 1
                            if verification['semantic_correct']:
                                correct_count += 1

                        samples_analyzed += 1
                    except:
                        continue
        except Exception as e:
            return {'error': str(e)}

        semantic_accuracy = correct_count / verifiable_count if verifiable_count > 0 else None

        return {
            'task': task_type,
            'model': model,
            'total_samples': samples_analyzed,
            'verifiable_samples': verifiable_count,
            'correct_samples': correct_count,
            'semantic_accuracy': semantic_accuracy,  # Among verifiable samples
            'coverage': verifiable_count / samples_analyzed if samples_analyzed > 0 else 0.0,
            'verifications': verifications,
        }

    def analyze_all_tasks(self, max_samples: int = 100) -> Dict:
        """Analyze semantic correctness across all tasks and models"""
        results = {}

        for task in self.task_types:
            print(f"Verifying semantic correctness for {task}...")
            results[task] = {}

            for model in self.models:
                print(f"  - {model}...")
                results[task][model] = self.analyze_task_semantic_correctness(task, model, max_samples)

        return results

    def print_semantic_analysis(self, results: Dict) -> str:
        """Generate readable semantic verification report"""
        report = []
        report.append("\n" + "=" * 120)
        report.append("SEMANTIC CORRECTNESS VERIFICATION")
        report.append("=" * 120)

        for task_type, task_results in results.items():
            report.append(f"\n{task_type.upper()}")
            report.append("-" * 120)

            for model, analysis in task_results.items():
                if 'error' in analysis:
                    report.append(f"  {model}: {analysis['error']}")
                    continue

                report.append(f"\n  {model}:")
                report.append(f"    Total Samples: {analysis['total_samples']}")
                report.append(f"    Verifiable: {analysis['verifiable_samples']} / {analysis['total_samples']} ({analysis['coverage']*100:.1f}%)")

                if analysis['semantic_accuracy'] is not None:
                    report.append(f"    Semantic Accuracy: {analysis['correct_samples']} / {analysis['verifiable_samples']} ({analysis['semantic_accuracy']*100:.1f}%)")
                else:
                    report.append(f"    Semantic Accuracy: N/A (insufficient verifiable samples)")

        return "\n".join(report)


if __name__ == "__main__":
    verifier = SemanticVerifier()

    # Analyze semantic correctness for all tasks
    print("Starting semantic correctness verification...\n")
    results = verifier.analyze_all_tasks(max_samples=50)

    # Print report
    report = verifier.print_semantic_analysis(results)
    print(report)

    # Save results
    output_file = Path("semantic_verification_results.json")
    with open(output_file, 'w') as f:
        # Convert to serializable format (remove verification objects)
        serializable = {}
        for task, task_data in results.items():
            serializable[task] = {}
            for model, analysis in task_data.items():
                if 'verifications' in analysis:
                    # Keep summary stats, drop individual verifications
                    clean_analysis = {k: v for k, v in analysis.items() if k != 'verifications'}
                    serializable[task][model] = clean_analysis
                else:
                    serializable[task][model] = analysis

        json.dump(serializable, f, indent=2)

    print(f"\n\nResults saved to {output_file}")
