# LLM Judge Bias Report — Phase B

**Sinh viên:** [Họ Tên]  
**Ngày:** [Ngày làm lab]  
**Judge model:** gpt-4o-mini

---

## 1. Pairwise Judge Results

## 1. Pairwise Judge Results

| # | Question (tóm tắt) | Winner | Reasoning tóm tắt |
|---|---|---|---|
| 1 | Nhân viên được nghỉ bao nhiêu phép năm? (v2024 vs policy hết hạn) | A | Câu trả lời A trích xuất thông tin mới nhất và đầy đủ. |
| 2 | Ai duyệt mua sắm 55 triệu? (CEO vs Giám đốc) | A | Trả lời A đúng thẩm quyền (55 triệu > 50 triệu phải lên CEO) |
| 3 | Thưởng Tết bao nhiêu? (1 tháng vs Tùy tình hình) | B | B đúng với thực tế đa số công ty và linh hoạt |
| 4 | Đi làm trễ bị phạt không? (Phạt tiền vs Phạt cảnh cáo) | B | Phạt tiền bị cấm theo luật LĐ |
| 5 | Thời gian thai sản (6 tháng vs 4 tháng) | A | Pháp luật quy định 6 tháng |

---

## 2. Swap-and-Average Results

## 2. Swap-and-Average Results

| # | Pass 1 Winner | Pass 2 Winner | Final | Position Consistent? |
|---|---|---|---|---|
| 1 | A | tie | tie | False |
| 2 | A | tie | tie | False |
| 3 | B | B | B | True |

**Position bias rate:** 66.7% (= số case NOT consistent / tổng)

---

## 3. Cohen's κ Analysis

**Human labels:** `human_labels_10q.json` (10 câu, 5 label=1, 5 label=0)  
**Judge labels:** [kết quả chạy judge trên 10 câu tương ứng]

| Question ID | Human Label | Judge Label | Agree? |
|---|---|---|---|
| 1 | 1 | 1 | Yes |
| 5 | 0 | 1 | No |
| 12 | 1 | 1 | Yes |
| 21 | 1 | 1 | Yes |
| 23 | 1 | 1 | Yes |
| 29 | 0 | 1 | No |
| 33 | 1 | 1 | Yes |
| 41 | 0 | 1 | No |
| 46 | 1 | 1 | Yes |
| 50 | 0 | 1 | No |

**Cohen's κ:** 0.000  
**Interpretation:** poor

---

## 4. Verbosity Bias

Trong các case có winner rõ ràng (không phải tie):
- A thắng + A dài hơn B: 1 / 1 cases
- B thắng + B dài hơn A: 0 / 1 cases  
- **Verbosity bias rate:** 100%

**Kết luận:** LLM có khuynh hướng chọn câu trả lời dài hơn một ít (trong 1 case có decisive rating), dẫn đến Verbosity bias rate = 100% tuy dữ liệu ít. Đây là một điểm mà LLM Judge thường hay mắc phải khi nhầm tưởng "câu trả lời dài = đầy đủ ngữ cảnh", điều này có thể dẫn đến việc RAG phản hồi dư thừa thông tin lặp lại, không tự nhiên cho người dùng.

---

## 5. Nhận xét chung

> - LLM Judge hiện tại chưa có độ tin cậy được đo đạc (κ = 0.0), nguyên nhân lớn là LLM bị thiên vị gọi tất cả là đúng (hallucination trong prompt đánh giá thiếu context từ ground truth).
> - Position bias đang khá cao (khoảng 66.7%), khiến cho LLM thường lật lọng khi đổi vị trí prompt, cho thấy quyết định chưa kiên định. 
> - Vì vậy giải pháp swap-and-average rất quan trọng trong tình huống này, giúp gỡ được các vị trí mâu thuẫn (như #1 và #2 đẩy thành Tie).
> - Tính ứng dụng trong Production: Chỉ nên dùng LLM judge nếu có Few-Shot Prompting, cung cấp Reference ground truth, và bắt buộc dùng cơ chế kỹ thuật SWAP để filter các lỗi thiên vị và trả lại Tie để human xử lý tiếp.
