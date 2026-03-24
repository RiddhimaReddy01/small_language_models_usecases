#!/usr/bin/env python3
"""
Centralized Configuration
All models, tasks, parameters, hardware settings, and prompts
"""

# ========== MODELS ==========
MODELS = {
    'tinyllama_1.1b': {
        'name': 'TinyLlama',
        'size': '1.1B',
        'cost': 1.0,
        'latency_ms': 500,
        'memory_gb': 2.0,
        'provider': 'local',
        'endpoint': 'localhost:8000',
        'type': 'SLM',
    },
    'qwen2.5_1.5b': {
        'name': 'Qwen',
        'size': '1.5B',
        'cost': 1.2,
        'latency_ms': 600,
        'memory_gb': 2.5,
        'provider': 'local',
        'endpoint': 'localhost:8001',
        'type': 'SLM',
    },
    'phi3_mini': {
        'name': 'Phi-3',
        'size': '3.8M',
        'cost': 0.8,
        'latency_ms': 400,
        'memory_gb': 1.5,
        'provider': 'local',
        'endpoint': 'localhost:8002',
        'type': 'SLM',
    },
    'llama_llama-3.3-70b-versatile': {
        'name': 'Llama-3.3',
        'size': '70B',
        'cost': 10.0,
        'latency_ms': 2000,
        'memory_gb': 140.0,
        'provider': 'api',
        'endpoint': 'https://api.together.ai',
        'type': 'LLM',
    },
}

# ========== TASKS ==========
TASKS = {
    'text_generation': {
        'name': 'Text Generation',
        'metric': 'ROUGE-L',
        'metric_type': 'continuous',  # For aggregation
        'baseline': 0.65,
        'hardware': ['cpu', 'gpu'],
        'supports_batch': True,
    },
    'code_generation': {
        'name': 'Code Generation',
        'metric': 'Pass@1',
        'metric_type': 'binary',
        'baseline': 0.70,
        'hardware': ['gpu'],
        'supports_batch': False,
    },
    'classification': {
        'name': 'Classification',
        'metric': 'F1',
        'metric_type': 'continuous',
        'baseline': 0.85,
        'hardware': ['cpu'],
        'supports_batch': True,
    },
    'maths': {
        'name': 'Math Reasoning',
        'metric': 'exact_match',
        'metric_type': 'binary',
        'baseline': 0.45,
        'hardware': ['cpu', 'gpu'],
        'supports_batch': True,
    },
    'summarization': {
        'name': 'Summarization',
        'metric': 'ROUGE-L',
        'metric_type': 'continuous',
        'baseline': 0.60,
        'hardware': ['gpu'],
        'supports_batch': True,
    },
    'retrieval_grounded': {
        'name': 'Retrieval Grounding',
        'metric': 'F1',
        'metric_type': 'continuous',
        'baseline': 0.75,
        'hardware': ['cpu'],
        'supports_batch': True,
    },
    'instruction_following': {
        'name': 'Instruction Following',
        'metric': 'exact_match',
        'metric_type': 'binary',
        'baseline': 0.80,
        'hardware': ['cpu', 'gpu'],
        'supports_batch': True,
    },
    'information_extraction': {
        'name': 'Information Extraction',
        'metric': 'F1',
        'metric_type': 'continuous',
        'baseline': 0.75,
        'hardware': ['cpu'],
        'supports_batch': True,
    },
}

# ========== SDDF PARAMETERS ==========
# Learned from optimization (sddf_weight_optimizer.py)
SDDF = {
    'weights': {
        'n_in': 0.1667,              # Input token count
        'H': 0.1667,                 # Shannon entropy
        'R': 0.1667,                 # Reasoning depth
        'constraint_count': 0.1667,  # Output constraints
        'alpha': 0.1667,             # Parametric dependence
        'D': 0.1667,                 # Dependency distance
    },
    'n_bins': 5,                     # Discrete bins for reporting
    'bin_std': 0.500001,             # Learned Gaussian spread (from optimization)
    'spike_threshold': 0.1,          # 10% curvature for spike detection
    'normalization': 'zscore',       # Component normalization
    'keep_continuous': True,         # ξ(x) ∈ [0,1] stays continuous
}

# ========== ROUTING PARAMETERS ==========
ROUTING = {
    'strategy': 'BALANCED',           # SAFE, BALANCED, COST_OPTIMIZED
    'cost_threshold': 5.0,            # Max acceptable cost multiplier
    'risk_threshold': 0.20,           # Max acceptable semantic failure risk
    'capability_threshold': 0.80,     # Min acceptable task accuracy
    'confidence_threshold': 0.70,     # Min acceptable routing confidence
    'enable_fallback': True,          # Fallback to LLM on uncertainty
}

# ========== INFERENCE SETTINGS ==========
INFERENCE = {
    'temperature': 0.7,
    'max_tokens': 2048,
    'top_p': 0.9,
    'top_k': 50,
    'repetition_penalty': 1.2,
    'timeout_seconds': 30,
}

# ========== HARDWARE SETTINGS ==========
HARDWARE = {
    'cpu': {
        'type': 'CPU',
        'cores': 8,
        'memory_gb': 32,
        'max_batch_size': 4,
        'cost_per_hour': 0.5,
    },
    'gpu': {
        'type': 'NVIDIA A100',
        'memory_gb': 80,
        'cores': 6912,
        'max_batch_size': 32,
        'cost_per_hour': 10.0,
    },
}

# ========== PROMPTS (Examples per task) ==========
PROMPTS = {
    'code_generation': {
        'template': 'Write a Python function that {description}\n\nRequirements:\n{requirements}',
        'examples': [
            {
                'description': 'checks if a number is prime',
                'requirements': '- Handle edge cases (0, 1, negative)\n- Use efficient algorithm\n- Include docstring',
            },
            {
                'description': 'reverses a list in place',
                'requirements': '- Modify original list\n- O(1) space complexity\n- Handle empty lists',
            },
        ],
    },
    'text_generation': {
        'template': 'Write an article about {topic}\n\nStyle: {style}\nLength: {length} words',
        'examples': [
            {
                'topic': 'machine learning in healthcare',
                'style': 'technical but accessible',
                'length': '500-800',
            },
        ],
    },
    'classification': {
        'template': 'Classify the following text as {categories}:\n\n"{text}"',
        'examples': [
            {
                'categories': 'positive, negative, neutral',
                'text': 'The product works well but is overpriced',
            },
        ],
    },
    'maths': {
        'template': 'Solve this math problem step by step:\n\n{problem}',
        'examples': [
            {
                'problem': 'If x^2 + 2x + 1 = 0, find x',
            },
        ],
    },
    'summarization': {
        'template': 'Summarize the following text in {length} sentences:\n\n{text}',
        'examples': [
            {
                'length': '2-3',
                'text': 'Machine learning is transforming how we approach data analysis...',
            },
        ],
    },
    'retrieval_grounded': {
        'template': 'Answer the question using ONLY the provided context:\n\nContext: {context}\n\nQuestion: {question}',
        'examples': [
            {
                'context': 'The Earth orbits the Sun. One orbit takes 365.25 days.',
                'question': 'How long does it take Earth to orbit the Sun?',
            },
        ],
    },
    'instruction_following': {
        'template': 'Follow these instructions exactly:\n\n{instructions}\n\nInput: {input_text}',
        'examples': [
            {
                'instructions': '1. Capitalize first letter\n2. Add period at end\n3. Replace "a" with "x"',
                'input_text': 'hello world',
            },
        ],
    },
    'information_extraction': {
        'template': 'Extract the following fields from the text:\n\n{fields}\n\nText: {text}',
        'examples': [
            {
                'fields': 'name, email, phone, company',
                'text': 'John Smith works at Acme Corp. Email: john@acme.com, Phone: 555-0123',
            },
        ],
    },
}

# ========== ANALYSIS PARAMETERS ==========
ANALYSIS = {
    'max_samples_per_task_model': 1000,  # Cap samples for efficiency
    'min_samples_per_bin': 20,           # Min samples for stable estimates
    'percentile_clip': (1, 99),          # Clip outliers before analysis
    'visualization_dpi': 300,            # Output figure quality
    'output_format': 'json',             # json, csv, parquet
}

# ========== TIER DEFINITIONS (for decision matrix) ==========
# Auto-generated from risk curves, but can be overridden
TIER_DEFINITIONS = {
    'Budget-SLM': {
        'models': ['phi3_mini', 'tinyllama_1.1b', 'qwen2.5_1.5b'],
        'max_cost': 1.2,
        'max_risk': 0.20,
        'description': 'Fast, cheap, low-risk tasks',
    },
    'Balanced-Hybrid': {
        'models': ['tinyllama_1.1b', 'qwen2.5_1.5b'],
        'max_cost': 2.0,
        'max_risk': 0.50,
        'description': 'Medium complexity, acceptable degradation risk',
    },
    'Premium-LLM': {
        'models': ['llama_llama-3.3-70b-versatile'],
        'max_cost': 10.0,
        'max_risk': 1.0,
        'description': 'High complexity, critical tasks requiring best quality',
    },
}

# ========== PATHS (relative to project root) ==========
PATHS = {
    'benchmark_output': 'benchmark_output',
    'benchmark_output_fixed': 'benchmark_output_fixed',
    'benchmark_output_fixed_all': 'benchmark_output_fixed_all',
    'results': 'risk_sensitivity/results_from_existing.json',
    'learned_weights': 'risk_sensitivity/learned_sddf_weights.json',
    'decision_matrix': 'risk_sensitivity/decision_matrix.json',
    'plots_risk': 'risk_sensitivity/plots/risk',
    'plots_capability': 'risk_sensitivity/plots/capability',
}

# ========== METRIC EXTRACTION FUNCTIONS ==========
# Map task type to how to extract actual metric from output
METRIC_EXTRACTORS = {
    'code_generation': {
        'metric': 'Pass@1',
        'extractor': 'extract_pass_at_1',  # Function name
        'description': 'Code passes at least one test case',
    },
    'text_generation': {
        'metric': 'ROUGE-L',
        'extractor': 'extract_rouge_l',
        'description': 'Longest common subsequence overlap with reference',
    },
    'classification': {
        'metric': 'F1',
        'extractor': 'extract_f1_score',
        'description': 'Harmonic mean of precision and recall',
    },
    'maths': {
        'metric': 'exact_match',
        'extractor': 'extract_exact_match',
        'description': 'Answer exactly matches ground truth',
    },
    'summarization': {
        'metric': 'ROUGE-L',
        'extractor': 'extract_rouge_l',
        'description': 'Longest common subsequence overlap',
    },
    'retrieval_grounded': {
        'metric': 'F1',
        'extractor': 'extract_f1_score',
        'description': 'Token-level F1 with ground truth answer',
    },
    'instruction_following': {
        'metric': 'exact_match',
        'extractor': 'extract_exact_match',
        'description': 'Output exactly matches expected result',
    },
    'information_extraction': {
        'metric': 'F1',
        'extractor': 'extract_f1_score',
        'description': 'Token-level F1 for each field',
    },
}
