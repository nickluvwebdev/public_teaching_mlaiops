"""Bounded Vertex text call; record provider usage fields verbatim."""

import time
from cloudlayer.gcp_monitoring import session
from src.triage import prepare, validate, response_schema


def generate(cfg, prompt, options):
    if not cfg.llm_model:
        raise ValueError("Set LLM_MODEL to an available, price-verified model before live calls")
    cap = int(options.get("max_output_tokens", 96))
    if not 64 <= cap <= 256:
        raise ValueError("Lab token cap must be 64 through 256")
    url = (
        f"https://aiplatform.googleapis.com/v1/projects/{cfg.project_id}/locations/global/"
        f"publishers/google/models/{cfg.llm_model}:generateContent"
    )
    prepared = prepare(prompt)
    if options.get("concise", True):
        prepared = prepared.replace("under 40 words", "under 20 words")
        if "parts" in prompt.lower():
            prepared += "\nFor the parts request, explicitly say 'parts are not supplied'."
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prepared}]}],
        "generationConfig": {
            "maxOutputTokens": cap,
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": response_schema(prompt),
        },
    }
    tick = time.perf_counter()
    r = session().post(url, json=payload, timeout=60)
    r.raise_for_status()
    body = r.json()
    usage = body["usageMetadata"]
    text = "".join(
        x.get("text", "")
        for x in body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    )
    try:
        validate(text)
        control_error = None
    except (ValueError, TypeError) as exc:
        control_error = str(exc)
    return {
        "control_error": control_error,
        "provider_response_id": body.get("responseId"),
        "response": text,
        "input_tokens": usage["promptTokenCount"],
        "output_tokens": usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0),
        "cached_input_tokens": usage.get("cachedContentTokenCount", 0),
        "usage_source": "provider_usageMetadata",
        "provider_usage": usage,
        "model_version": body.get("modelVersion", cfg.llm_model),
        "max_output_tokens": cap,
        "latency_ms": (time.perf_counter() - tick) * 1000,
    }
