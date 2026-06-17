"""
LLM client using GreenNode MaaS (OpenAI-compatible API).
Model: google/gemma-4-31b-it
"""
import logging
import os

from openai import OpenAI

MAAS_BASE_URL = "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"
MAAS_MODEL = "google/gemma-4-31b-it"


def call_llm(prompt: str, timeout: int = 180) -> str:
    """Call GreenNode MaaS and return the text response."""
    api_key = os.getenv("AI_PLATFORM_API_KEY")
    if not api_key:
        raise RuntimeError("AI_PLATFORM_API_KEY is not set in environment")

    client = OpenAI(
        base_url=os.getenv("LLM_BASE_URL", MAAS_BASE_URL),
        api_key=api_key,
    )
    model = os.getenv("LLM_MODEL", MAAS_MODEL)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=1,
        top_p=0.7,
        presence_penalty=0,
        timeout=timeout,
    )
    return response.choices[0].message.content.strip()
