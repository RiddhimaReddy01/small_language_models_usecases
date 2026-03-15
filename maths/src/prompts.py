TEMPLATE = (
    "Solve the following math problem carefully.\n\n"
    "Provide the final answer in the format:\n\n"
    "Final Answer: <number>\n\n"
    "Problem:\n{question}"
)


def perturb_paraphrase(question: str) -> str:
    return "Please solve: " + question


def perturb_typo(question: str) -> str:
    if len(question) > 10:
        midpoint = len(question) // 2
        return question[:midpoint] + question[midpoint + 1 :]
    return question


def build_prompt(question: str) -> str:
    return TEMPLATE.format(question=question)


def build_perturbed_question(question: str, variant: str) -> str:
    if variant == "paraphrase":
        return perturb_paraphrase(question)
    if variant == "typo":
        return perturb_typo(question)
    raise ValueError(f"Unknown perturbation variant: {variant}")
