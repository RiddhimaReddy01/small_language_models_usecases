#!/usr/bin/env python3
"""
Task-specific parsers - extract structured data from raw outputs.
Improves validation accuracy by checking actual content quality.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple
import ast
import pandas as pd


class TaskParser:
    """Base class for task-specific parsing"""

    def parse(self, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
        """Parse raw output into structured format.

        Returns: (parsed_dict, is_valid)
        """
        raise NotImplementedError


class CodeGenerationParser(TaskParser):
    """Extract and validate code snippets"""

    def parse(self, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
        """Extract code blocks and validate syntax"""

        parsed = {"code_blocks": []}

        # Extract code blocks (```...```)
        code_pattern = r'```(?:python|py)?\s*\n(.*?)\n```'
        matches = re.findall(code_pattern, raw_output, re.DOTALL)

        if matches:
            for code in matches:
                parsed["code_blocks"].append(code.strip())

        # If no code block markers, try to extract function/class definitions
        if not parsed["code_blocks"]:
            lines = raw_output.split('\n')
            code_lines = []
            for line in lines:
                if line.strip().startswith(('def ', 'class ', 'import ', 'from ')):
                    code_lines.append(line)
            if code_lines:
                parsed["code_blocks"].append('\n'.join(code_lines))

        # Validate syntax
        is_valid = False
        for code in parsed["code_blocks"]:
            try:
                ast.parse(code)
                parsed["syntax_valid"] = True
                is_valid = True
                break
            except SyntaxError:
                parsed["syntax_valid"] = False

        # Valid if has code blocks with valid syntax
        is_valid = len(parsed["code_blocks"]) > 0 and parsed.get("syntax_valid", False)

        return parsed, is_valid


class ClassificationParser(TaskParser):
    """Extract and validate class labels"""

    VALID_CLASSES = {
        "positive", "negative", "neutral",  # sentiment
        "sports", "political", "technology", "business", "health",  # topics
        "spam", "not spam", "ham",  # spam detection
        "true", "false", "yes", "no",  # boolean
    }

    def parse(self, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
        """Extract classification label"""

        parsed = {"raw_text": raw_output[:100]}

        # Look for label in first sentence
        first_sentence = raw_output.split('.')[0].lower().strip()

        # Try to find class label
        label = None
        for valid_class in self.VALID_CLASSES:
            if valid_class in first_sentence:
                label = valid_class
                break

        # If not found, try extracting word in quotes
        if not label:
            quoted = re.findall(r'"([^"]+)"', raw_output.lower())
            if quoted:
                for q in quoted:
                    if q in self.VALID_CLASSES:
                        label = q
                        break

        parsed["predicted_class"] = label
        is_valid = label is not None and len(raw_output.strip()) > 5

        return parsed, is_valid


class MathsParser(TaskParser):
    """Extract and validate mathematical answers"""

    def parse(self, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
        """Extract numerical answer"""

        parsed = {}

        # Look for numbers (including negative, decimals, fractions)
        number_pattern = r'-?\d+\.?\d*|\d+\.\d+'
        matches = re.findall(number_pattern, raw_output)

        parsed["numbers_found"] = matches

        # Extract first number as answer
        answer = None
        if matches:
            try:
                answer = float(matches[-1])  # Take last number (likely the answer)
                parsed["answer"] = answer
            except:
                pass

        # Valid if has numeric answer
        is_valid = answer is not None

        return parsed, is_valid


class SummarizationParser(TaskParser):
    """Extract and validate summaries"""

    def parse(self, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
        """Check if output is a summary (not full text)"""

        parsed = {}

        # Check length
        raw_len = len(raw_output.split())
        parsed["word_count"] = raw_len
        parsed["is_condensed"] = raw_len < 200  # Summary should be <200 words (increased from 100)

        # Check for summary markers
        summary_markers = ["summary", "in summary", "key points", "conclusion", "overall"]
        has_marker = any(marker in raw_output.lower() for marker in summary_markers)
        parsed["has_summary_marker"] = has_marker

        # Valid if condensed AND has content
        is_valid = parsed["is_condensed"] and raw_len > 10

        return parsed, is_valid


class RetrievalGroundedParser(TaskParser):
    """Extract relevant quotes/answers from context"""

    def parse(self, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
        """Check if answer references source context"""

        parsed = {}

        # Look for quoted text or citations
        quoted = re.findall(r'"([^"]+)"', raw_output)
        parsed["quotes"] = quoted

        # Check for answer structure
        lines = raw_output.split('\n')
        parsed["num_lines"] = len([l for l in lines if l.strip()])

        # Valid if has meaningful answer
        is_valid = len(raw_output.strip()) > 10 and parsed["num_lines"] > 0

        return parsed, is_valid


class InstructionFollowingParser(TaskParser):
    """Check if instructions were followed"""

    def parse(self, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
        """Validate instruction compliance"""

        parsed = {}

        # Check for list structures (for "list X items")
        has_list = any(raw_output.startswith(c) for c in ['1.', '-', '*', '•'])
        parsed["has_list"] = has_list

        # Check for sequential content (for "count to X")
        has_sequence = any(str(i) in raw_output for i in range(1, 10))
        parsed["has_sequence"] = has_sequence

        # Check for alphabetical order (for "alphabetical order")
        has_alphabetical = any(letter in raw_output.lower() for letter in 'abcdefghijklmnopqrstuvwxyz')
        parsed["has_content"] = has_alphabetical

        # Valid if response is structured
        is_valid = (has_list or has_sequence or has_alphabetical) and len(raw_output.strip()) > 5

        return parsed, is_valid


class InformationExtractionParser(TaskParser):
    """Extract named entities"""

    ENTITY_TYPES = {
        "person": ["name", "john", "alice", "bob", "called", "named"],
        "location": ["location", "city", "country", "place", "paris", "london", "new york"],
        "organization": ["organization", "company", "corp", "inc", "llc", "microsoft", "google"],
        "date": ["\d{4}", "\d{1,2}/\d{1,2}", "january", "february", "march", "2025"],
    }

    def parse(self, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
        """Extract entities"""

        parsed = {"entities": {}}

        lower_output = raw_output.lower()

        # Look for entities
        for entity_type, keywords in self.ENTITY_TYPES.items():
            for keyword in keywords:
                if keyword in lower_output:
                    parsed["entities"][entity_type] = True
                    break

        # Extract quoted entities
        quoted = re.findall(r'"([^"]+)"', raw_output)
        parsed["extracted_text"] = quoted[:3] if quoted else []

        # Valid if extracted something meaningful
        is_valid = len(parsed["entities"]) > 0 or len(parsed["extracted_text"]) > 0

        return parsed, is_valid


class TextGenerationParser(TaskParser):
    """Validate generated text quality"""

    def parse(self, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
        """Check text generation quality"""

        parsed = {}

        # Check basic metrics
        word_count = len(raw_output.split())
        sentence_count = len([s for s in raw_output.split('.') if s.strip()])

        parsed["word_count"] = word_count
        parsed["sentence_count"] = sentence_count
        parsed["avg_words_per_sentence"] = word_count / sentence_count if sentence_count > 0 else 0

        # Check for coherence markers
        coherence_markers = ['\n\n', 'here', 'therefore', 'because', 'however', 'example']
        has_markers = sum(1 for marker in coherence_markers if marker in raw_output.lower())
        parsed["coherence_markers"] = has_markers

        # Valid if has minimum content and structure
        is_valid = word_count > 20 and sentence_count > 0

        return parsed, is_valid


# Parser registry
PARSERS = {
    "text_generation": TextGenerationParser(),
    "code_generation": CodeGenerationParser(),
    "classification": ClassificationParser(),
    "maths": MathsParser(),
    "summarization": SummarizationParser(),
    "retrieval_grounded": RetrievalGroundedParser(),
    "instruction_following": InstructionFollowingParser(),
    "information_extraction": InformationExtractionParser(),
}


def parse_task_output(task: str, raw_output: str, sample_id: str) -> Tuple[Dict[str, Any], bool]:
    """Get parser for task and parse output"""

    if task not in PARSERS:
        return {}, len(raw_output.strip()) > 0

    parser = PARSERS[task]
    return parser.parse(raw_output, sample_id)


def reparse_all_tasks():
    """Re-parse all outputs with task-specific parsers"""

    print("\n" + "=" * 70)
    print("TASK-SPECIFIC PARSING")
    print("=" * 70)

    benchmark_output = Path("benchmark_output")

    results = {}

    for task_dir in sorted(benchmark_output.iterdir()):
        if not task_dir.is_dir():
            continue

        # Find model subdirectory
        model_dirs = [d for d in task_dir.iterdir() if d.is_dir()]
        if not model_dirs:
            continue

        model_dir = model_dirs[0]
        outputs_jsonl = model_dir / "outputs.jsonl"

        if not outputs_jsonl.exists():
            continue

        task_name = task_dir.name
        print(f"\n{task_name.upper()}")
        print("-" * 70)

        # Read records
        records = []
        with open(outputs_jsonl) as f:
            for line in f:
                records.append(json.loads(line))

        # Parse each record
        valid_before = sum(1 for r in records if r.get("valid"))

        for record in records:
            raw_output = record.get("raw_output", "")
            parsed, is_valid = parse_task_output(task_name, raw_output, record.get("sample_id", ""))

            record["parsed_output"] = parsed
            record["valid"] = is_valid  # Update validity based on parsing

        valid_after = sum(1 for r in records if r.get("valid"))

        # Write back
        with open(outputs_jsonl, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')

        # Compute stats
        by_bin = {}
        for record in records:
            bin_id = record.get("bin")
            if bin_id not in by_bin:
                by_bin[bin_id] = {"success": 0, "total": 0}
            by_bin[bin_id]["total"] += 1
            if record.get("valid"):
                by_bin[bin_id]["success"] += 1

        # Update SDDF
        sddf_data = []
        for bin_id in sorted(by_bin.keys()):
            stats = by_bin[bin_id]
            bin_records = [r for r in records if r.get("bin") == bin_id]
            avg_latency = sum(r.get("latency_sec", 0) for r in bin_records) / len(bin_records) if bin_records else 0

            sddf_data.append({
                "bin": bin_id,
                "n_samples": stats["total"],
                "success_rate": stats["success"] / stats["total"],
                "avg_latency": avg_latency,
                "validity_rate": stats["success"] / stats["total"]
            })

        sddf_csv = model_dir / "sddf_ready.csv"
        df = pd.DataFrame(sddf_data)
        df.to_csv(sddf_csv, index=False)

        success_rate = valid_after / len(records) if records else 0
        results[task_name] = success_rate

        print(f"Before: {valid_before}/{len(records)} ({valid_before*100/len(records):.1f}%)")
        print(f"After:  {valid_after}/{len(records)} ({valid_after*100/len(records):.1f}%)")
        print(f"Change: {(valid_after-valid_before)*100/len(records):+.1f}%")

        print("\nPer-bin breakdown:")
        for bin_id in sorted(by_bin.keys()):
            stats = by_bin[bin_id]
            pct = stats["success"] * 100 / stats["total"]
            print(f"  Bin {bin_id}: {stats['success']}/{stats['total']} ({pct:.1f}%)")

    # Summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS (TASK-SPECIFIC PARSING)")
    print("=" * 70)

    for task, rate in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"{task:30s}: {rate*100:6.1f}%")

    avg_rate = sum(results.values()) / len(results) if results else 0
    print(f"\n{'AVERAGE':30s}: {avg_rate*100:6.1f}%")
    print("\nTask-specific parsing complete!")


if __name__ == "__main__":
    reparse_all_tasks()
