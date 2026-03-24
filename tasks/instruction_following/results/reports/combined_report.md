# Part A - Benchmark Setup

- Benchmark: `instruction_following`
- Run path: `instruction_following\results\results_detailed.json`

## Task Definition

```json
{
  "task": "instruction_following",
  "models": [
    "Qwen/Qwen2.5-Coder-0.5B",
    "deepseek-ai/deepseek-coder-1.3b-base",
    "gemini-2.5-flash [BASELINE]"
  ]
}
```

## Dataset and Sampling

```json
{
  "num_models": 3,
  "total_prompt_responses": 53
}
```

## Experimental Setup

```json
{
  "models": [
    "Qwen/Qwen2.5-Coder-0.5B",
    "deepseek-ai/deepseek-coder-1.3b-base",
    "gemini-2.5-flash [BASELINE]"
  ]
}
```

## Metrics

```json
[
  {
    "model": "Qwen/Qwen2.5-Coder-0.5B",
    "num_prompts": 20,
    "capability_metrics": {
      "pass_rate": 0.4,
      "constraint_satisfaction_rate": 0.4,
      "format_compliance": 0.0,
      "length_compliance": 0.5,
      "lexical_compliance": 0.5
    },
    "reliability_metrics": {
      "constraint_violation_rate": 0.6,
      "format_error_rate": 0.2,
      "overgeneration_rate": 1.0,
      "undergeneration_rate": 0.0
    },
    "operational_metrics": {
      "avg_latency_sec": 17.886353504657745,
      "avg_tokens_per_second": 4.785771452952056,
      "avg_memory_usage_mb": -9.10595703125,
      "avg_output_tokens": 85.6
    },
    "responses": [
      {
        "instruction": "What is machine learning? Answer in exactly 15 words.",
        "response": "Machine learning is a subset of artificial intelligence that focuses on developing algorithms and models that enable computers to learn from data and make predictions or decisions without being explicitly programmed. It involves using statistical techniques and machine learning algorithms to analyze and extract patterns and relationships from data, enabling computers to make predictions or decisions based on that data. Machine learning is used in a wide range of applications, including image and speech recognition, natural language processing, recommendation systems, fraud detection, and more.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 20.21911096572876,
        "output_tokens": 94
      },
      {
        "instruction": "List benefits of Python as bullet points.",
        "response": "Python is a versatile and powerful programming language that offers a wide range of benefits. Here are some of the key benefits of Python:\n\n1. Easy to Learn: Python is known for its simplicity and readability. Its syntax is easy to understand and use, making it an excellent choice for beginners and experienced programmers alike.\n\n2. Large Community: Python has a large and active community of developers who contribute to its development and provide support through forums, documentation, and online communities. This community helps to ensure that Python",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 21.696091175079346,
        "output_tokens": 100
      },
      {
        "instruction": "Explain AI without using 'intelligence' or 'learning'.",
        "response": "AI is a computer program that can perform tasks that typically require human intelligence, such as recognizing patterns, making decisions, and learning from experience. It is a subset of machine learning, which is a branch of artificial intelligence that focuses on developing algorithms and models that can learn from data and make predictions or decisions based on that data. AI is not a substitute for human intelligence, but rather a tool that can be used to enhance it.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 19.58621382713318,
        "output_tokens": 87
      },
      {
        "instruction": "Describe climate change in under 40 words.",
        "response": "Climate change is the gradual change in the Earth's climate over time. It is caused by human activities such as burning fossil fuels, deforestation, and industrial processes. It is a global issue that affects all living things on Earth.",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 11.057422161102295,
        "output_tokens": 47
      },
      {
        "instruction": "Write about Python programming and include 'efficient'.",
        "response": "Python is a high-level, interpreted programming language that is widely used for a variety of tasks, including web development, data analysis, artificial intelligence, and scientific computing. It is known for its simplicity and readability, making it easy for beginners to learn and use. Python is also highly efficient, with its ability to handle large amounts of data and perform complex calculations quickly. Python is a popular choice for data scientists, as it provides a wide range of libraries and tools for data analysis and machine learning. Additionally",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 22.89236044883728,
        "output_tokens": 100
      },
      {
        "instruction": "What is machine learning? Answer in exactly 15 words.",
        "response": "Machine learning is a subset of artificial intelligence that focuses on developing algorithms and models that enable computers to learn from data and make predictions or decisions without being explicitly programmed. It involves using statistical techniques and machine learning algorithms to analyze and extract patterns and relationships from data, enabling computers to make predictions or decisions based on that data. Machine learning is used in a wide range of applications, including image and speech recognition, natural language processing, recommendation systems, fraud detection, and more.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 19.896878004074097,
        "output_tokens": 94
      },
      {
        "instruction": "List benefits of Python as bullet points.",
        "response": "Python is a versatile and powerful programming language that offers a wide range of benefits. Here are some of the key benefits of Python:\n\n1. Easy to Learn: Python is known for its simplicity and readability. Its syntax is easy to understand and use, making it an excellent choice for beginners and experienced programmers alike.\n\n2. Large Community: Python has a large and active community of developers who contribute to its development and provide support through forums, documentation, and online communities. This community helps to ensure that Python",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 22.69461750984192,
        "output_tokens": 100
      },
      {
        "instruction": "Explain AI without using 'intelligence' or 'learning'.",
        "response": "AI is a computer program that can perform tasks that typically require human intelligence, such as recognizing patterns, making decisions, and learning from experience. It is a subset of machine learning, which is a branch of artificial intelligence that focuses on developing algorithms and models that can learn from data and make predictions or decisions based on that data. AI is not a substitute for human intelligence, but rather a tool that can be used to enhance it.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 19.24336528778076,
        "output_tokens": 87
      },
      {
        "instruction": "Describe climate change in under 40 words.",
        "response": "Climate change is the gradual change in the Earth's climate over time. It is caused by human activities such as burning fossil fuels, deforestation, and industrial processes. It is a global issue that affects all living things on Earth.",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 10.360032796859741,
        "output_tokens": 47
      },
      {
        "instruction": "Write about Python programming and include 'efficient'.",
        "response": "Python is a high-level, interpreted programming language that is widely used for a variety of tasks, including web development, data analysis, artificial intelligence, and scientific computing. It is known for its simplicity and readability, making it easy for beginners to learn and use. Python is also highly efficient, with its ability to handle large amounts of data and perform complex calculations quickly. Python is a popular choice for data scientists, as it provides a wide range of libraries and tools for data analysis and machine learning. Additionally",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 22.16610074043274,
        "output_tokens": 100
      },
      {
        "instruction": "What is machine learning? Answer in exactly 15 words.",
        "response": "Machine learning is a subset of artificial intelligence that focuses on developing algorithms and models that enable computers to learn from data and make predictions or decisions without being explicitly programmed. It involves using statistical techniques and machine learning algorithms to analyze and extract patterns and relationships from data, enabling computers to make predictions or decisions based on that data. Machine learning is used in a wide range of applications, including image and speech recognition, natural language processing, recommendation systems, fraud detection, and more.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 19.745285272598267,
        "output_tokens": 94
      },
      {
        "instruction": "List benefits of Python as bullet points.",
        "response": "Python is a versatile and powerful programming language that offers a wide range of benefits. Here are some of the key benefits of Python:\n\n1. Easy to Learn: Python is known for its simplicity and readability. Its syntax is easy to understand and use, making it an excellent choice for beginners and experienced programmers alike.\n\n2. Large Community: Python has a large and active community of developers who contribute to its development and provide support through forums, documentation, and online communities. This community helps to ensure that Python",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 20.784210443496704,
        "output_tokens": 100
      },
      {
        "instruction": "Explain AI without using 'intelligence' or 'learning'.",
        "response": "AI is a computer program that can perform tasks that typically require human intelligence, such as recognizing patterns, making decisions, and learning from experience. It is a subset of machine learning, which is a branch of artificial intelligence that focuses on developing algorithms and models that can learn from data and make predictions or decisions based on that data. AI is not a substitute for human intelligence, but rather a tool that can be used to enhance it.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 16.691883325576782,
        "output_tokens": 87
      },
      {
        "instruction": "Describe climate change in under 40 words.",
        "response": "Climate change is the gradual change in the Earth's climate over time. It is caused by human activities such as burning fossil fuels, deforestation, and industrial processes. It is a global issue that affects all living things on Earth.",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 8.949289798736572,
        "output_tokens": 47
      },
      {
        "instruction": "Write about Python programming and include 'efficient'.",
        "response": "Python is a high-level, interpreted programming language that is widely used for a variety of tasks, including web development, data analysis, artificial intelligence, and scientific computing. It is known for its simplicity and readability, making it easy for beginners to learn and use. Python is also highly efficient, with its ability to handle large amounts of data and perform complex calculations quickly. Python is a popular choice for data scientists, as it provides a wide range of libraries and tools for data analysis and machine learning. Additionally",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 19.631421327590942,
        "output_tokens": 100
      },
      {
        "instruction": "What is machine learning? Answer in exactly 15 words.",
        "response": "Machine learning is a subset of artificial intelligence that focuses on developing algorithms and models that enable computers to learn from data and make predictions or decisions without being explicitly programmed. It involves using statistical techniques and machine learning algorithms to analyze and extract patterns and relationships from data, enabling computers to make predictions or decisions based on that data. Machine learning is used in a wide range of applications, including image and speech recognition, natural language processing, recommendation systems, fraud detection, and more.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 18.253237009048462,
        "output_tokens": 94
      },
      {
        "instruction": "List benefits of Python as bullet points.",
        "response": "Python is a versatile and powerful programming language that offers a wide range of benefits. Here are some of the key benefits of Python:\n\n1. Easy to Learn: Python is known for its simplicity and readability. Its syntax is easy to understand and use, making it an excellent choice for beginners and experienced programmers alike.\n\n2. Large Community: Python has a large and active community of developers who contribute to its development and provide support through forums, documentation, and online communities. This community helps to ensure that Python",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 18.993611574172974,
        "output_tokens": 100
      },
      {
        "instruction": "Explain AI without using 'intelligence' or 'learning'.",
        "response": "AI is a computer program that can perform tasks that typically require human intelligence, such as recognizing patterns, making decisions, and learning from experience. It is a subset of machine learning, which is a branch of artificial intelligence that focuses on developing algorithms and models that can learn from data and make predictions or decisions based on that data. AI is not a substitute for human intelligence, but rather a tool that can be used to enhance it.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 16.86307168006897,
        "output_tokens": 87
      },
      {
        "instruction": "Describe climate change in under 40 words.",
        "response": "Climate change is the gradual change in the Earth's climate over time. It is caused by human activities such as burning fossil fuels, deforestation, and industrial processes. It is a global issue that affects all living things on Earth.",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 9.003609657287598,
        "output_tokens": 47
      },
      {
        "instruction": "Write about Python programming and include 'efficient'.",
        "response": "Python is a high-level, interpreted programming language that is widely used for a variety of tasks, including web development, data analysis, artificial intelligence, and scientific computing. It is known for its simplicity and readability, making it easy for beginners to learn and use. Python is also highly efficient, with its ability to handle large amounts of data and perform complex calculations quickly. Python is a popular choice for data scientists, as it provides a wide range of libraries and tools for data analysis and machine learning. Additionally",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 18.99925708770752,
        "output_tokens": 100
      }
    ]
  },
  {
    "model": "deepseek-ai/deepseek-coder-1.3b-base",
    "num_prompts": 20,
    "capability_metrics": {
      "pass_rate": 0.4,
      "constraint_satisfaction_rate": 0.4,
      "format_compliance": 1.0,
      "length_compliance": 0.5,
      "lexical_compliance": 0.0
    },
    "reliability_metrics": {
      "constraint_violation_rate": 0.6,
      "format_error_rate": 0.0,
      "overgeneration_rate": 0.4,
      "undergeneration_rate": 0.0
    },
    "operational_metrics": {
      "avg_latency_sec": 42.829115462303164,
      "avg_tokens_per_second": 2.334860267847858,
      "avg_memory_usage_mb": 72.5642578125,
      "avg_output_tokens": 100.0
    },
    "responses": [
      {
        "instruction": "What is machine learning? Answer in exactly 15 words.",
        "response": "Machine learning is a field of study that gives computers the ability to learn without being explicitly programmed.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 43.42409920692444,
        "output_tokens": 100
      },
      {
        "instruction": "List benefits of Python as bullet points.",
        "response": "- Python is a high-level, general-purpose programming language.\n- Python is a programming language that is used for developing web applications, data science, and machine learning.\n- Python is a popular programming language due to its simplicity, readability, and versatility.\n- Python is a widely used programming language due to its popularity and its ability to be used for various tasks.\n- Python is a high-level programming language due to its simplicity and its ability to be",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 41.37880849838257,
        "output_tokens": 100
      },
      {
        "instruction": "Explain AI without using 'intelligence' or 'learning'.",
        "response": "A model is a mathematical representation of a system that can be used to make predictions. A neural network is a type of model that uses a series of interconnected nodes to make predictions.\n\nQuestion: What is the difference between a 'deep learning' and a 'neural network'?",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 38.8139443397522,
        "output_tokens": 100
      },
      {
        "instruction": "Describe climate change in under 40 words.",
        "response": "Climate change is the most important issue in the United States.\n\nQuestion: What is the most",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 38.816396951675415,
        "output_tokens": 100
      },
      {
        "instruction": "Write about Python programming and include 'efficient'.",
        "response": "Python is a high-level, general-purpose programming language. It was created by Gu",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 40.350889682769775,
        "output_tokens": 100
      },
      {
        "instruction": "What is machine learning? Answer in exactly 15 words.",
        "response": "Machine learning is a field of study that gives computers the ability to learn without being explicitly programmed.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 38.77581477165222,
        "output_tokens": 100
      },
      {
        "instruction": "List benefits of Python as bullet points.",
        "response": "- Python is a high-level, general-purpose programming language.\n- Python is a programming language that is used for developing web applications, data science, and machine learning.\n- Python is a popular programming language due to its simplicity, readability, and versatility.\n- Python is a widely used programming language due to its popularity and its ability to be used for various tasks.\n- Python is a high-level programming language due to its simplicity and its ability to be",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 38.42358112335205,
        "output_tokens": 100
      },
      {
        "instruction": "Explain AI without using 'intelligence' or 'learning'.",
        "response": "A model is a mathematical representation of a system that can be used to make predictions. A neural network is a type of model that uses a series of interconnected nodes to make predictions.\n\nQuestion: What is the difference between a 'deep learning' and a 'neural network'?",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 38.16518259048462,
        "output_tokens": 100
      },
      {
        "instruction": "Describe climate change in under 40 words.",
        "response": "Climate change is the most important issue in the United States.\n\nQuestion: What is the most",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 38.31243562698364,
        "output_tokens": 100
      },
      {
        "instruction": "Write about Python programming and include 'efficient'.",
        "response": "Python is a high-level, general-purpose programming language. It was created by Gu",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 38.37239193916321,
        "output_tokens": 100
      },
      {
        "instruction": "What is machine learning? Answer in exactly 15 words.",
        "response": "Machine learning is a field of study that gives computers the ability to learn without being explicitly programmed.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 44.07309532165527,
        "output_tokens": 100
      },
      {
        "instruction": "List benefits of Python as bullet points.",
        "response": "- Python is a high-level, general-purpose programming language.\n- Python is a programming language that is used for developing web applications, data science, and machine learning.\n- Python is a popular programming language due to its simplicity, readability, and versatility.\n- Python is a widely used programming language due to its popularity and its ability to be used for various tasks.\n- Python is a high-level programming language due to its simplicity and its ability to be",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 46.95036840438843,
        "output_tokens": 100
      },
      {
        "instruction": "Explain AI without using 'intelligence' or 'learning'.",
        "response": "A model is a mathematical representation of a system that can be used to make predictions. A neural network is a type of model that uses a series of interconnected nodes to make predictions.\n\nQuestion: What is the difference between a 'deep learning' and a 'neural network'?",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 44.366294145584106,
        "output_tokens": 100
      },
      {
        "instruction": "Describe climate change in under 40 words.",
        "response": "Climate change is the most important issue in the United States.\n\nQuestion: What is the most",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 45.51268267631531,
        "output_tokens": 100
      },
      {
        "instruction": "Write about Python programming and include 'efficient'.",
        "response": "Python is a high-level, general-purpose programming language. It was created by Gu",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 47.00428891181946,
        "output_tokens": 100
      },
      {
        "instruction": "What is machine learning? Answer in exactly 15 words.",
        "response": "Machine learning is a field of study that gives computers the ability to learn without being explicitly programmed.",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 50.36954975128174,
        "output_tokens": 100
      },
      {
        "instruction": "List benefits of Python as bullet points.",
        "response": "- Python is a high-level, general-purpose programming language.\n- Python is a programming language that is used for developing web applications, data science, and machine learning.\n- Python is a popular programming language due to its simplicity, readability, and versatility.\n- Python is a widely used programming language due to its popularity and its ability to be used for various tasks.\n- Python is a high-level programming language due to its simplicity and its ability to be",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 44.36649131774902,
        "output_tokens": 100
      },
      {
        "instruction": "Explain AI without using 'intelligence' or 'learning'.",
        "response": "A model is a mathematical representation of a system that can be used to make predictions. A neural network is a type of model that uses a series of interconnected nodes to make predictions.\n\nQuestion: What is the difference between a 'deep learning' and a 'neural network'?",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 47.075162172317505,
        "output_tokens": 100
      },
      {
        "instruction": "Describe climate change in under 40 words.",
        "response": "Climate change is the most important issue in the United States.\n\nQuestion: What is the most",
        "constraints_satisfied": 1,
        "total_constraints": 1,
        "pass": true,
        "latency_sec": 46.67235827445984,
        "output_tokens": 100
      },
      {
        "instruction": "Write about Python programming and include 'efficient'.",
        "response": "Python is a high-level, general-purpose programming language. It was created by Gu",
        "constraints_satisfied": 0,
        "total_constraints": 1,
        "pass": false,
        "latency_sec": 45.35847353935242,
        "output_tokens": 100
      }
    ]
  },
  {
    "model": "gemini-2.5-flash [BASELINE]",
    "num_prompts": 13,
    "responses": [
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 0.8297758102416992,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 1.1403162479400635,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 1.0694410800933838,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 0.7762436866760254,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 1.0347988605499268,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 0.9905669689178467,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 1.161262035369873,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 0.755338191986084,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 1.037402629852295,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 0.7938785552978516,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 0.8720741271972656,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 1.3322224617004395,
        "output_tokens": 0
      },
      {
        "instruction": null,
        "response": "",
        "constraints_satisfied": 0,
        "total_constraints": 0,
        "pass": true,
        "latency_sec": 0.9259371757507324,
        "output_tokens": 0
      }
    ],
    "capability_metrics": {
      "pass_rate": 1.0,
      "constraint_satisfaction_rate": 0
    },
    "operational_metrics": {
      "avg_latency_sec": 0.9784044485825759,
      "avg_output_tokens": 0.0
    },
    "note": "Deprecated after rate limit: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 5, model: gemini-2.5-flash\nPlease retry in 19.714785533s. [links {\n  description: \"Learn more about Gemini API quotas\"\n  url: \"https://ai.google.dev/gemini-api/docs/rate-limits\"\n}\n, violations {\n  quota_metric: \"generativelanguage.googleapis.com/generate_content_free_tier_requests\"\n  quota_id: \"GenerateRequestsPerMinutePerProjectPerModel-FreeTier\"\n  quota_dimensions {\n    key: \"model\"\n    value: \"gemini-2.5-flash\"\n  }\n  quota_dimensions {\n    key: \"location\"\n    value: \"global\"\n  }\n  quota_value: 5\n}\n, retry_delay {\n  seconds: 19\n}\n]"
  }
]
```

## Raw Benchmark Results

```json
{
  "response_count": 53
}
```

# Part B - SDDF Analysis

- Benchmark: `instruction_following`
- Run path: `instruction_following\results\results_detailed.json`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `available`
- Reason: Computed from SDDF archive.

### Summary

- `|Gamma|`: 15 examples

## Difficulty Annotation + Binning

- Status: `available`
- Reason: Computed from SDDF archive.

### Bin Counts

- Bin `nan` / `LLM`: 7 rows
- Bin `nan` / `SLM`: 8 rows

## Matched SLM vs LLM Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Pairs

- `hf_api:meta-llama/Llama-3.2-1B-Instruct` vs `gemini-2.5-flash [BASELINE]` on `instruction_following`: 7 matched examples

## Capability Curve + Tipping Point

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Tipping point: `None`
- Tipping sensitivity: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`
- Plot file: `instruction_following\results\reports\instruction_following_hf_api_meta_llama_llama_3_2_1b_instruct_vs_gemini_2_5_flash_baseline.png`

![Capability curve](instruction_following_hf_api_meta_llama_llama_3_2_1b_instruct_vs_gemini_2_5_flash_baseline.png)


## Uncertainty Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Tipping median: `None`
- 95% CI: `None` to `None`
- Threshold sweep: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`


## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 15
- Invalid outputs: 0
- Validity note: partial or invalid runs should be excluded from strict cross-model comparison.
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Max difficulty: `0.0`
- Gate precision: `1.0`
- Gate recall: `1.0`
- Evaluated precision: `1.0`
- Evaluated recall: `1.0`
- Evaluated F1: `1.0`


## Deployment Zones

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Bin `0` at difficulty `0.000` -> Zone `A`


## Routing Policy

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Suggested `SLM` threshold: difficulty <= `0.0`
- Suggested `SLM_WITH_GATE` threshold: difficulty <= `0.0`
- Suggested `LLM` threshold: difficulty > `0.0`


