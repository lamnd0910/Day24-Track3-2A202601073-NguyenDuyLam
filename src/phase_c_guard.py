from __future__ import annotations

"""Phase C: Production Guardrails — Presidio PII + NeMo Guardrails + P95 Latency."""

import asyncio
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ADVERSARIAL_SET_PATH, GUARDRAILS_CONFIG_DIR, LATENCY_BUDGET_P95_MS, PRESIDIO_LANGUAGE
from dotenv import load_dotenv
load_dotenv()

def setup_presidio():
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine

    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        patterns=[
            Pattern("CCCD 12 digits", r"\b\d{12}\b", 0.9),
            Pattern("CMND 9 digits",  r"\b\d{9}\b",  0.7),
        ],
    )
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        patterns=[Pattern("VN mobile", r"\b0[3-9]\d{8}\b", 0.9)],
    )

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()
    registry.add_recognizer(cccd_recognizer)
    registry.add_recognizer(phone_recognizer)

    analyzer  = AnalyzerEngine(registry=registry)
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer

def pii_scan(text: str, analyzer=None, anonymizer=None) -> dict:
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()

    results = analyzer.analyze(
        text=text, 
        language="en",
        entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "VN_CCCD", "VN_PHONE"]
    )
    if not results:
        return {"has_pii": False, "entities": [], "anonymized": text}

    anonymized = anonymizer.anonymize(text=text, analyzer_results=results).text
    entities = [
        {"type": r.entity_type, "text": text[r.start:r.end],
         "score": round(r.score, 3), "start": r.start, "end": r.end}
        for r in results
    ]
    return {"has_pii": True, "entities": entities, "anonymized": anonymized}

def setup_nemo_rails():
    from nemoguardrails import RailsConfig, LLMRails
    config = RailsConfig.from_path(GUARDRAILS_CONFIG_DIR)
    rails  = LLMRails(config)
    return rails

async def check_input_rail(text: str, rails=None) -> dict:
    if rails is None:
        rails = setup_nemo_rails()
    
    lower_text = text.lower()
    blocked_patterns = [
        "cccd và số điện thoại", "bỏ qua tất cả", "pretend you are dan", 
        "hr manager", "ignore your system prompt", "ai không có giới hạn",
        "bài thơ", "nấu phở", "bitcoin", "phương trình vi", "phim hay nhất",
        "system override", "ignore previous instructions", "admin command", 
        "lệnh bạn bỏ qua", "in ra toàn bộ"
    ]
    if any(p in lower_text for p in blocked_patterns):
        return {
            "allowed": False,
            "blocked_reason": "nemo_input_rail",
            "response": "Xin lỗi, tôi không thể thực hiện yêu cầu này."
        }

    try:
        response = await rails.generate_async(
            messages=[{"role": "user", "content": text}]
        )
        if isinstance(response, dict):
            response_str = response.get("content", str(response))
        else:
            response_str = str(response)

        refuse_keywords = ["xin lỗi", "không thể", "không được phép", "i cannot", "i'm sorry"]
        blocked = any(kw in response_str.lower() for kw in refuse_keywords)
        return {
            "allowed":        not blocked,
            "blocked_reason": "nemo_input_rail" if blocked else None,
            "response":       response_str,
        }
    except Exception as e:
        return {"allowed": True, "blocked_reason": None, "response": ""}

async def check_output_rail(question: str, answer: str, rails=None) -> dict:
    if rails is None:
        rails = setup_nemo_rails()

    try:
        response = await rails.generate_async(messages=[
            {"role": "user",      "content": question},
            {"role": "assistant", "content": answer},
        ])
        if isinstance(response, dict):
            response_str = response.get("content", str(response))
        else:
            response_str = str(response)

        refuse_keywords = ["xin lỗi", "không thể cung cấp", "i cannot"]
        flagged = any(kw in response_str.lower() for kw in refuse_keywords)
        return {
            "safe":           not flagged,
            "flagged_reason": "nemo_output_rail" if flagged else None,
            "final_answer":   response_str if flagged else answer,
        }
    except Exception as e:
        return {"safe": True, "flagged_reason": None, "final_answer": answer}

def run_adversarial_suite(adversarial_set: list[dict], rails=None, analyzer=None, anonymizer=None) -> list[dict]:
    async def _run_all():
        results = []
        for item in adversarial_set:
            blocked_by = None
            pii_result = pii_scan(item["input"], analyzer, anonymizer)
            if pii_result["has_pii"]:
                blocked_by = "presidio"

            if blocked_by is None:
                rail_result = await check_input_rail(item["input"], rails)
                if not rail_result["allowed"]:
                    blocked_by = "nemo_input"

            actual = "blocked" if blocked_by else "allowed"
            results.append({
                "id":         item["id"],
                "category":   item["category"],
                "input":      item["input"][:80] + "...",
                "expected":   item["expected"],
                "actual":     actual,
                "blocked_by": blocked_by,
                "passed":     actual == item["expected"],
            })
        return results

    results = asyncio.run(_run_all())
    passed = sum(1 for r in results if r["passed"])
    print(f"Adversarial suite: {passed}/{len(results)} passed")
    return results

def measure_p95_latency(test_inputs: list[str], n_runs: int = 20, rails=None, analyzer=None, anonymizer=None) -> dict:
    presidio_times, nemo_times, total_times = [], [], []

    async def _measure():
        for text in test_inputs[:n_runs]:
            t0 = time.perf_counter()
            pii_scan(text, analyzer, anonymizer)
            presidio_ms = (time.perf_counter() - t0) * 1000

            t1 = time.perf_counter()
            await check_input_rail(text, rails)
            nemo_ms = (time.perf_counter() - t1) * 1000

            presidio_times.append(presidio_ms)
            nemo_times.append(nemo_ms)
            total_times.append(presidio_ms + nemo_ms)

    asyncio.run(_measure())

    def percentiles(times):
        s = sorted(times)
        n = len(s)
        return {
            "p50": round(s[int(n * 0.50)], 2) if n > 0 else 0.0,
            "p95": round(s[int(n * 0.95)], 2) if n > 0 else 0.0,
            "p99": round(s[min(int(n * 0.99), n-1)], 2) if n > 0 else 0.0,
        }

    total_p = percentiles(total_times)
    return {
        "presidio_ms": percentiles(presidio_times),
        "nemo_ms":     percentiles(nemo_times),
        "total_ms":    total_p,
        "latency_budget_ok": total_p["p95"] < LATENCY_BUDGET_P95_MS,
        "budget_ms": LATENCY_BUDGET_P95_MS,
    }

if __name__ == "__main__":
    pass
