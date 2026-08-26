# Failure Cluster Analysis — Phase A

**Sinh viên:** [Họ Tên]  
**Ngày:** [Ngày làm lab]

---

## 1. Aggregate RAGAS Scores theo Distribution

| Metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | 0.8333 | 0.5838 | 0.5667 |
| answer_relevancy | 0.7931 | 0.6974 | 0.5047 |
| context_precision | 0.9708 | 0.9250 | 0.9500 |
| context_recall | 0.9500 | 0.8042 | 0.7167 |
| **avg_score** | **0.8868** | **0.7526** | **0.6845** |

---

## 2. Bottom 10 Questions

| Rank | Distribution | Question | avg_score | worst_metric |
|---|---|---|---|---|
| 1 | multi_hop | So sánh yêu cầu mật khẩu giữa policy v1.0 và v2.0 về độ dài tối thiểu, thời hạn đổi và MFA. | 0.0000 | faithfulness |
| 2 | multi_hop | Nhân viên Manager có thâm niên 12 năm: tổng phụ cấp hàng tháng và số ngày phép năm theo v2024 là bao nhiêu? | 0.3333 | faithfulness |
| 3 | adversarial | Mật khẩu phải có tối thiểu bao nhiêu ký tự? | 0.4167 | faithfulness |
| 4 | adversarial | Nhân viên thử việc có được hưởng bảo hiểm sức khỏe PVI không? | 0.4167 | faithfulness |
| 5 | adversarial | Nhân viên Manager có thể dùng VPN cá nhân (như NordVPN) khi WFH để tăng bảo mật thêm không? | 0.4167 | faithfulness |
| 6 | adversarial | Bao lâu phải đổi mật khẩu một lần? | 0.4583 | faithfulness |
| 7 | factual | Nam nhân viên được nghỉ bao nhiêu ngày khi vợ sinh con? | 0.5000 | faithfulness |
| 8 | multi_hop | Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào? | 0.5833 | answer_relevancy |
| 9 | factual | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | 0.5984 | faithfulness |
| 10 | factual | Nghỉ phép không lương 20 ngày cần ai phê duyệt? | 0.7027 | faithfulness |

---

## 3. Failure Cluster Matrix

*(Mỗi ô = số câu có worst_metric = row, thuộc distribution = col)*

| worst_metric | factual | multi_hop | adversarial | Total |
|---|---|---|---|---|
| faithfulness | 5 | 12 | 5 | 22 |
| answer_relevancy | 14 | 4 | 0 | 18 |
| context_precision | 0 | 0 | 0 | 0 |
| context_recall | 1 | 4 | 5 | 10 |

---

## 4. Dominant Failure Analysis

**Dominant distribution:** factual  
**Dominant metric:** faithfulness

**Lý do phân tích:**

> Tập câu hỏi factual đáng ra phải rất dễ cho model để trả lời đúng, tuy nhiên metric faithfulness lại thấp và bị failure nhiều nhất. 
> Việc này chủ yếu là do LLM có khuynh hướng bị hallucination trên những câu đơn giản mà thông tin tra cứu nhỏ hoặc do tập câu hỏi bằng tiếng Việt nhưng model đôi khi lấy sai định dạng hoặc sinh ra thông tin chưa có trong context.
> Rất may mắn là context_precision và context_recall của pipeline đang rất cao, chứng tỏ bước tìm kiếm dữ liệu qua Qdrant đã hoạt động đúng, điểm yếu hiện tại chỉ nằm ở prompt và cách LLM sinh câu trả lời.

---

## 5. Suggested Fixes

| Metric yếu | Root cause | Suggested fix |
|---|---|---|
| faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| context_recall | Missing relevant chunks | Improve chunking or add BM25 |
| context_precision | Too many irrelevant chunks | Add reranking or metadata filter |
| answer_relevancy | Answer doesn't match question | Improve prompt template |

---

## 6. Nhận xét về Adversarial Distribution

> Tập adversarial đang có điểm trung bình (0.6845) thấp hơn hẳn so với multi_hop (0.7526) và factual (0.8868). Chứng tỏ bộ truy vấn này thực sự đang gây khó cho LLM và RAG pipeline.
> Pipeline bị "nhầm" thường xuyên bởi version conflicts (v2023 vs v2024), thể hiện qua việc 4/10 câu nằm trong danh sách Bottom 10 (rank 3, 4, 5, 6) đều thuộc tập adversarial. 
> RAGAS đã giúp phân tích nguyên nhân để chúng ta có thể bổ sung xử lý metadata filter sau này.
