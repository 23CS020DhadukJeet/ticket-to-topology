"""Ticket generator with banned-term guardrail and deterministic business fallback.

Per BUILD_GUIDE Phase 5:
Inputs: business_context, symptom_class, flows.
Output: 2-3 sentences, voice of a non-technical branch manager.
Guard: banned terms (OSPF, EIGRP, router, route-map, redistribution, prefix-list,
Cisco, BGP, ASBR, ...) -> one retry -> fallback template built from business_context.
Tone by class: outage urgent, redundancy failover drill, suboptimal slowness, latent audit.
"""

import re
import time

from t2t.ai.prompts import load_prompt
from t2t.ai.providers import LLMProvider
from t2t.ai.sink import AICallRecord, AICallSink, NullAICallSink
from t2t.errors import AIUnavailable
from t2t.faults.loader import FaultModel

PROMPT_VERSION = "ticket_v1"

BANNED_TERMS = [
    "ospf",
    "eigrp",
    "bgp",
    "rip",
    "router",
    "routers",
    "route-map",
    "route-maps",
    "routemap",
    "routemaps",
    "redistribute",
    "redistribution",
    "prefix-list",
    "prefix-lists",
    "prefixlist",
    "prefixlists",
    "cisco",
    "asbr",
    "asbrs",
    "abr",
    "abrs",
    "autonomous system",
    "administrative distance",
    "seed metric",
    "subnets",
    "subnet",
    "passive-interface",
    "md5",
]


def find_banned_terms(text: str) -> list[str]:
    """Find any technical or routing jargon terms in the generated ticket."""
    found: list[str] = []
    text_lower = text.lower()
    for term in BANNED_TERMS:
        # Match as whole word or phrase
        pattern = rf"\b{re.escape(term)}\b"
        if re.search(pattern, text_lower):
            found.append(term)
    return found


def _sanitize_business_text(text: str) -> str:
    """Sanitize business context for fallback templates to eliminate jargon."""
    sanitized = text
    replacements = [
        (r"\bASBRs\b", "gateways"),
        (r"\bABRs\b", "gateways"),
        (r"\bASBR\b", "gateway"),
        (r"\bABR\b", "gateway"),
        (r"\brouters\b", "systems"),
        (r"\brouter\b", "system"),
        (r"\bOSPF\b", "core network"),
        (r"\bEIGRP\b", "branch network"),
        (r"\bredistribution\b", "data transfer"),
        (r"\bprefix-lists\b", "filter policies"),
        (r"\bprefix-list\b", "filter policy"),
        (r"\broute-maps\b", "routing rules"),
        (r"\broute-map\b", "routing rule"),
        (r"\bsubnets\b", "network segments"),
        (r"\bsubnet\b", "network segment"),
    ]
    for pat, rep in replacements:
        sanitized = re.sub(pat, rep, sanitized, flags=re.IGNORECASE)
    return sanitized.strip()


def get_deterministic_ticket_fallback(
    business_context: str,
    symptom_class: str,
) -> str:
    """Produce a deterministic non-technical incident ticket when AI is unavailable or fails."""
    clean_context = _sanitize_business_text(business_context)

    templates = {
        "outage": (
            "URGENT: All communication with partner and branch services is completely down. "
            "Users report that critical business applications cannot reach the destination. "
            f"{clean_context}"
        ),
        "redundancy": (
            "NOTICE: During scheduled maintenance failover testing, secondary backup connectivity "
            "failed to activate properly. Primary operations remain active but the site is running "
            f"without redundancy. {clean_context}"
        ),
        "suboptimal": (
            "PERFORMANCE ISSUE: Users are reporting noticeable slowness and high latency when "
            "accessing core applications. Transactions take longer than normal. "
            f"{clean_context}"
        ),
        "latent": (
            "COMPLIANCE ALERT: A routine operational infrastructure audit flagged "
            "policy discrepancies that introduce network instability risks during "
            f"future changes. {clean_context}"
        ),
    }

    return templates.get(symptom_class, templates["latent"])


def generate_ticket(
    fault: FaultModel,
    provider: LLMProvider,
    sink: AICallSink | None = None,
) -> str:
    """Generate a non-technical incident ticket for a fault using LLM with guardrails."""
    call_sink = sink or NullAICallSink()
    system_prompt = load_prompt(PROMPT_VERSION)

    flows_summary = "; ".join(f"{f.src} -> {f.dst} ({f.note})" for f in fault.flows)
    user_prompt = (
        f"Incident Details:\n"
        f"- Symptom Class: {fault.symptom_class}\n"
        f"- Affected Business Flows: {flows_summary}\n"
        f"- Business Context: {fault.business_context}\n\n"
        f"Write a 2-3 sentence incident report in non-technical branch manager language."
    )

    t_start = time.perf_counter()
    raw_response = ""
    ok = False

    try:
        raw_response = provider.complete(system_prompt, user_prompt)
        banned = find_banned_terms(raw_response)

        if not banned:
            ok = True
            return raw_response.strip()

        # Guard triggered: 1 retry asking LLM to eliminate technical jargon
        retry_prompt = (
            f"Your previous draft contained prohibited technical terms: {', '.join(banned)}.\n"
            f"Rewrite the ticket in 2-3 sentences using ONLY non-technical business language. "
            f"Never mention protocol names or router technical terms.\n"
            f"Context: {fault.business_context}"
        )
        raw_response = provider.complete(system_prompt, retry_prompt)
        banned_retry = find_banned_terms(raw_response)

        if not banned_retry:
            ok = True
            return raw_response.strip()

    except AIUnavailable:
        pass
    except Exception as err:
        call_sink.log_call(
            AICallRecord(
                purpose="generate_ticket",
                provider=type(provider).__name__,
                model=getattr(provider, "model", "none")
                if isinstance(getattr(provider, "model", None), str)
                else "none",
                prompt_version=PROMPT_VERSION,
                latency_ms=int((time.perf_counter() - t_start) * 1000),
                ok=False,
                error=str(err),
            )
        )
        return get_deterministic_ticket_fallback(fault.business_context, fault.symptom_class)

    latency_ms = int((time.perf_counter() - t_start) * 1000)
    call_sink.log_call(
        AICallRecord(
            purpose="generate_ticket",
            provider=type(provider).__name__,
            model=getattr(provider, "model", "none")
            if isinstance(getattr(provider, "model", None), str)
            else "none",
            prompt_version=PROMPT_VERSION,
            latency_ms=latency_ms,
            ok=ok,
        )
    )

    # Fallback to deterministic template if banned terms persisted
    return get_deterministic_ticket_fallback(fault.business_context, fault.symptom_class)
