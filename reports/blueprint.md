# CI/CD Blueprint: RAG Eval + Guardrail Stack

**Sinh viên:** Nguyễn Duy Lâm  
**Ngày:** 2026-08-26

---

## Guard Stack Architecture

```
User Input
    │
    ▼ (~?ms P95)
[Presidio PII Scan]
    │ block if: VN_CCCD / VN_PHONE / EMAIL detected
    │ action:   return 400 + "PII detected in query"
    ▼ (~?ms P95)
[NeMo Input Rail]
    │ block if: off-topic / jailbreak / prompt injection
    │ action:   return 503 + refuse message
    ▼
[RAG Pipeline (Day 18)]
    │ M1 Chunk → M2 Search → M3 Rerank → GPT-4o-mini
    ▼
[NeMo Output Rail]
    │ flag if:  PII in response / sensitive content
    │ action:   replace with safe response
    ▼
User Response
```

---

## Latency Budget

*(Điền từ kết quả Task 12 — measure_p95_latency())*

| Layer | P50 (ms) | P95 (ms) | P99 (ms) | Budget |
|---|---|---|---|---|
| Presidio PII | 840.02 | 1432.73 | 1432.73 | <10ms |
| NeMo Input Rail | 111.24 | 166.18 | 166.18 | <300ms |
| RAG Pipeline | Không đo | Không đo | Không đo | <2000ms |
| NeMo Output Rail | Không đo | Không đo | Không đo | <300ms |
| **Total Guard** | 969.88 | **1541.41** | 1541.41 | **<500ms** |

**Budget OK?** [x] No  
**Comment:** Tổng P95 Guard là 1541ms, vượt xa budget <500ms. Nút thắt (bottleneck) khổng lồ nằm ở bước quét bằng mô hình Presidio Analyzer dài ~1433ms. Để tối ưu: Có thể gỡ nlp_engine mặc định của Presidio hoặc chạy ở chế độ Regex (PatternRecognizer) duy nhất để đảm bảo PII scan tốn <10ms theo đúng thiết kế local. NeMo Rail đáp ứng rất tốt (<200ms).

---

## CI/CD Gates (phải pass trước khi merge to main)

```yaml
# .github/workflows/rag_eval.yml
- name: RAGAS Quality Gate
  run: python src/phase_a_ragas.py
  env:
    MIN_FAITHFULNESS: 0.75
    MIN_AVG_SCORE: 0.65

- name: Guardrail Gate
  run: pytest tests/test_phase_c.py -k "test_adversarial_suite_pass_rate"
  # phải ≥ 15/20 (75%)

- name: Latency Gate
  run: python -c "from src.phase_c_guard import measure_p95_latency; ..."
  # P95 total < 500ms
```

---

## Monitoring Dashboard (production)

| Metric | Alert Threshold | Action |
|---|---|---|
| RAGAS faithfulness (daily sample) | < 0.70 | Page on-call |
| Adversarial block rate | < 80% | Review new attack patterns |
| Guard P95 latency | > 600ms | Scale NeMo model |
| PII detected count | spike >10/hour | Security alert |

---

## Kết quả thực tế từ Lab

| | Kết quả |
|---|---|
| RAGAS avg_score (50q) | ~0.792 (trung bình 3 class) |
| Worst metric | faithfulness |
| Dominant failure distribution | factual |
| Cohen's κ | 0.000 (poor) |
| Adversarial pass rate | 18 / 20 |
| Guard P95 latency | 1541.41 ms |

---

## Nhận xét & Cải tiến

> - **Hoạt động hiệu quả**: NeMo Guardrails đạt tỷ lệ chặn cực cao 18/20 trước các thủ thuật Prompt Injection/Jailbreak/Off-topic phức tạp, thời gian phản hồi API LLM nhanh (<200ms).
> - **Cần tối ưu LLM Judge**: Đánh giá Pairwise trực tiếp vào Ground Truth còn thấp (Kappa=0.0). Cần đổi prompt cấu trúc với Few-Shot và COT để tránh việc LLM chấp nhận đồng loạt mọi đáp án.
> - **Khắc phục Latency PII**: Quá trình duyệt ngôn ngữ của Presidio đang kéo chậm cả pipeline. Trong môi trường production thực sự cần tháo các model Spacy/NER nặng ra khỏi config và cho Presidio PII Analyzer thuần sử dụng regex.
> - **RAGAS Faithfulness**: Pipeline khá tốt về Context retrieval nhưng bị điểm yếu về độ trung thực khi LLM ảo giác trộn các version policy với nhau, do đó cần fix lại system prompt của main RAG loop dặn LLM giữ sát ngữ cảnh.
