from __future__ import annotations


def build_prompt(document_text: str, target_fields: list[str]) -> str:
    fields_block = ", ".join(f'"{field}"' for field in target_fields)
    return (
        "Extract the requested fields from the receipt text.\n"
        "Return only one valid JSON object and nothing else.\n"
        f"Required keys: [{fields_block}]\n"
        "Use empty strings for missing values.\n"
        "Normalize date to YYYY-MM-DD when possible.\n\n"
        "JSON format example:\n"
        '{"company":"","address":"","date":"","total":""}\n\n'
        "Receipt text:\n"
        f"{document_text}\n"
    )


def build_gemini_prompt(document_text: str, target_fields: list[str]) -> str:
    fields_block = ", ".join(target_fields)
    return (
        "Task: extract receipt fields from OCR text.\n"
        f"Fields: {fields_block}\n"
        "Output rules:\n"
        "1. Return exactly one JSON object.\n"
        "2. Do not use markdown, code fences, commentary, or explanations.\n"
        "3. Always include all four keys: company, address, date, total.\n"
        "4. If a field is missing, use an empty string.\n"
        "5. Normalize date to YYYY-MM-DD when possible.\n"
        "6. Copy values from the receipt text; do not invent values.\n\n"
        'Return this exact schema:\n{"company":"","address":"","date":"","total":""}\n\n'
        "Receipt OCR text:\n"
        f"{document_text}\n"
    )
