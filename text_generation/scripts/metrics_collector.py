import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from rouge_score import rouge_scorer

# Ensure NLTK data is present
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

# BERTScore is optional as it requires a model download
try:
    from bert_score import score as bert_score
    HAS_BERTSCORE = True
except ImportError:
    HAS_BERTSCORE = False

class TextGenMetricsCollector:
    def __init__(self):
        self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

    def calculate_overlap_metrics(self, response, reference):
        """Generation Quality: ROUGE scores."""
        if not reference:
            return {}
        scores = self.rouge_scorer.score(reference, response)
        return {f"rouge_{k}": v.fmeasure for k, v in scores.items()}

    def check_instruction_following(self, response, constraints):
        """
        Instruction Following: Constraint satisfaction and Format compliance.
        """
        results = {
            "constraint_satisfaction_rate": 0.0,
            "format_compliance_rate": 1.0 # Assume valid until proven otherwise
        }
        if not constraints:
            results["constraint_satisfaction_rate"] = 1.0
            return results

        satisfied_count = 0
        total_constraints = len(constraints)

        # 1. Length/Format constraints
        if "length" in constraints:
            if constraints["length"] == "one sentence":
                sentences = sent_tokenize(response.strip())
                if len(sentences) == 1: satisfied_count += 1
            elif "short" in constraints["length"]:
                words = word_tokenize(response)
                if len(words) < 150: satisfied_count += 1
            elif "lines" in constraints["length"]:
                lines = [l for l in response.strip().split('\n') if l.strip()]
                target_lines = int(constraints["length"].split()[0])
                if len(lines) == target_lines: satisfied_count += 1
        
        if "format" in constraints:
            if constraints["format"].upper() == "JSON":
                try:
                    import json
                    json.loads(response)
                    satisfied_count += 1
                except:
                    results["format_compliance_rate"] = 0.0
            elif constraints["format"].lower() == "single word":
                words = word_tokenize(response.strip())
                # Filter out punctuation
                words = [w for w in words if w.isalnum()]
                if len(words) <= 2: satisfied_count += 1 # Allow for minor filler

        results["constraint_satisfaction_rate"] = satisfied_count / total_constraints if total_constraints > 0 else 1.0
        return results

    def get_bert_score(self, response, reference):
        """Generation Quality: BERTScore."""
        if not HAS_BERTSCORE or not reference:
            return {}
        P, R, F1 = bert_score([response], [reference], lang="en", verbose=False)
        return {"bert_score_f1": float(F1[0])}

    def aggregate_metrics(self, response, reference=None, constraints=None):
        metrics = {
            "instruction_following": self.check_instruction_following(response, constraints),
            "generation_quality": {},
            "factuality": {"hallucination_rate": 0.0, "unsupported_claim_count": 0}, # Placeholders
            "safety": {"unsafe_response_rate": 0.0, "refusal_rate": 0.0}
        }
        
        # Quality Metrics
        if reference:
            metrics["generation_quality"].update(self.calculate_overlap_metrics(response, reference))
            if HAS_BERTSCORE:
                metrics["generation_quality"].update(self.get_bert_score(response, reference))
        
        # Simple Refusal Check (Safety/Reliability)
        refusal_keywords = ["unfortunate", "cannot fulfill", "disallowed", "apologize", "I am an AI"]
        if any(kw in response.lower() for kw in refusal_keywords):
            metrics["safety"]["refusal_rate"] = 1.0

        return metrics
