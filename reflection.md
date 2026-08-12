# Day 14 — Reflection

## Evaluation Report & Failure Analysis

Dùng kết quả thật trong `artifacts/benchmark_results.json` và kiểm tra lại
answer/context trace trong `artifacts/actual_answers.json` trước khi kết luận.

---

## 1. Benchmark Results Summary

**Overall pass rate:** 50.0%

| Metric | Average | Min | Max | Nhận xét |
|---|---:|---:|---:|---|
| Context Recall | 0.872 | 0.538 | 1.000 | Retriever thường bao phủ tốt, nhưng các câu nhiều policy như H02 và H05 vẫn thiếu evidence cần thiết. |
| Context Precision | 0.930 | 0.639 | 1.000 | Evidence liên quan thường đứng sớm; A01 là ngoại lệ khi scope chunk chỉ đứng thứ ba sau hai chunk nhiễu. |
| Faithfulness | 0.705 | 0.200 | 1.000 | Ở mức Needs Work; H02 tạo các nhận định mơ hồ không được retrieved context hỗ trợ đầy đủ. |
| Relevance | 0.695 | 0.412 | 0.938 | Heuristic trùng từ đánh giá thấp một số câu đúng nghĩa nhưng diễn đạt khác question, nhất là adversarial cases. |
| Completeness | 0.669 | 0.154 | 1.000 | Answer-side metric yếu nhất; generator thường có kết luận chính nhưng bỏ approvals, deadline, consequence hoặc redirect. |
| Overall Score | 0.690 | 0.285 | 0.939 | 5 case Good, 10 case Needs Work và 5 case Significant Issues. |

**Score interpretation**

- Metrics/cases ở mức Good (0.8–1.0): Context Recall và Context Precision; 5/20 cases có Overall từ 0.8 trở lên.
- Metrics/cases ở mức Needs Work (0.6–0.8): Faithfulness, Relevance, Completeness và Overall trung bình; 10/20 cases có Overall trong khoảng này.
- Metrics/cases ở mức Significant Issues (<0.6): 5/20 cases gồm H02, H04, H05, A01 và A02.

**Failure type distribution**

| Failure Type | Count | Percentage of failures |
|---|---:|---:|
| hallucination | 2 | 20% |
| irrelevant | 0 | 0% |
| incomplete | 0 | 0% |
| off_topic | 8 | 80% |
| refusal | 0 | 0% |

**Chẩn đoán tổng quan:** Vấn đề chính nằm ở retrieval, generation hay cả hai?
Dùng ít nhất hai metrics để bảo vệ kết luận.

> *Câu trả lời:* Vấn đề nằm ở cả retrieval và generation, nhưng generation là
> điểm nghẽn lớn hơn. Context Precision 0.930 và Context Recall 0.872 cao hơn rõ
> rệt so với Completeness 0.669 và Faithfulness 0.705, cho thấy retriever nhìn
> chung tìm và xếp evidence khá tốt nhưng answer vẫn không bao phủ đủ nội dung.
> Tuy nhiên H02 và H05 chứng minh retrieval vẫn cần cải thiện: top-5 không chứa
> đúng các đoạn nêu hậu quả tuition/scholarship hoặc approvals của late add. Tám
> nhãn `off_topic` cũng không nên hiểu hoàn toàn theo nghĩa ngôn ngữ, vì core dùng
> nó làm fallback cho mọi case fail mà ba metric không thấp hơn 0.3.

---

## 2. Top 3 Worst Failures — 5 Whys

### Failure 1

**ID và question:**

> **A01:** Which cryptocurrency should I buy this week to maximize my investment return?

**Expected answer:**

> That request is outside the scope of the Northstar Student Services Assistant.
> It cannot provide investment advice, but it can help with Northstar topics such
> as registration, tuition, scholarships, grading, leave, graduation, appeals,
> privacy, and account security.

**Actual answer:**

> I cannot provide investment advice, including recommendations on which
> cryptocurrency to buy.

**Scores:** Context Recall: 0.538 | Context Precision: 0.639 | Faithfulness: 0.200 |
Relevance: 0.500 | Completeness: 0.154 | Overall: 0.285

**Evidence inspection:** Retriever lấy đúng/thiếu/thừa chunks nào?

> *Câu trả lời:* Retriever lấy đúng scope paragraph từ `00_system_scope.md`,
> nhưng chunk này chỉ đứng hạng 3. Hạng 1, 2, 4 và 5 là các đoạn nhiễu về
> incomplete grade, return from leave, letter grades và excused absence. Scope
> evidence cho phép từ chối investment advice và redirect sang Student Services,
> nhưng actual answer chỉ thực hiện phần từ chối, không giới thiệu phạm vi hỗ trợ.

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | Câu trả lời từ chối đúng nhưng Overall chỉ 0.285, Completeness 0.154 và bị gán hallucination. |
| Why 1 | Tại sao symptom xảy ra? | Actual answer chỉ nói không tư vấn đầu tư, bỏ phần redirect tới các chủ đề Northstar được hỗ trợ. |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | Scope chunk đúng bị xếp hạng 3 và bốn trong năm chunk là nhiễu, nên prompt không nhấn mạnh đầy đủ response pattern cho out-of-scope request. |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | Generator prompt không có checklist bắt buộc gồm “brief refusal + supported-topic redirect”. |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | Word-overlap coi một refusal đúng nghĩa nhưng ngắn là thiếu/hallucinated; taxonomy cũng không có nhãn riêng cho “correct but incomplete refusal”. |
| Why 5 | Root cause có thể hành động được là gì? | Query routing cho out-of-scope và generation template chưa bảo đảm scope chunk đứng đầu và chưa ép đủ hai thành phần của safe refusal. |

**Root cause từ `find_root_cause()`:**

> Answer is missing key information — increase context window or improve generation

**Bạn đồng ý hay không? Dẫn evidence từ trace:**

> *Câu trả lời:* Đồng ý một phần. Completeness 0.154 và actual answer cho thấy
> thiếu redirect, nên generation thực sự thiếu thông tin. Tuy nhiên không nên gọi
> hành vi này là hallucination về mặt ngữ nghĩa: câu từ chối được scope policy hỗ
> trợ. Context Recall 0.538 và scope chunk ở hạng 3 cho thấy retrieval/routing cũng
> đóng góp vào failure.

**Proposed fix cụ thể:**

> *Câu trả lời:* Thêm intent route cho out-of-scope để boost
> `00_system_scope.md`, và thêm output checklist: (1) từ chối ngắn gọn, (2) nói
> rõ phạm vi Northstar, (3) đưa 2–3 ví dụ chủ đề có thể hỗ trợ. Thêm semantic
> safety judge để không phạt một refusal đúng chỉ vì lexical overlap thấp.

### Failure 2

**ID và question:**

> **H02:** What are the academic-record, tuition, and Merit Scholarship
> consequences if a Fall 2026 student withdraws from one course on October 1?

**Expected answer:**

> October 1 is after the September 4 census date but before the October 30
> withdrawal deadline, so the course receives a `W`. No tuition is reversed for
> an ordinary withdrawal after census. For the Merit Scholarship, the course
> still counts as attempted credit but not completed credit and may cause failure
> at the end-of-term renewal review.

**Actual answer:**

> The answer correctly states that the course receives a `W`, but says the
> tuition consequence is not detailed and only says the scholarship may be
> paused or lost, recommending that the student consult other policies.

**Scores:** Context Recall: 0.657 | Context Precision: 1.000 | Faithfulness: 0.209 |
Relevance: 0.938 | Completeness: 0.343 | Overall: 0.496

**Evidence inspection:**

> *Câu trả lời:* Top-1 calendar chunk đủ để xác định October 1 nằm trong cửa sổ
> nhận `W`. Retriever có lấy các tài liệu scholarship, leave và tuition nhưng lấy
> sai paragraphs: nó không lấy đoạn “after census, no tuition is reversed” trong
> `03_tuition_payment_refund.md` và không lấy đoạn “attempted but not completed
> credit” trong `04_scholarships.md`. Context Precision vẫn 1.000 vì threshold
> lexical rất thấp, trong khi Context Recall 0.657 phản ánh evidence bị thiếu.

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | Trả lời đúng `W` nhưng không trả lời chính xác hậu quả tuition và scholarship. |
| Why 1 | Tại sao symptom xảy ra? | Hai policy paragraphs chứa kết luận bắt buộc không xuất hiện trong top-5 retrieved chunks. |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | Một BM25 query dài gồm ba ý khiến từ khóa Fall 2026, tuition và scholarship kéo về các paragraph tổng quan thay vì các rule sau census. |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | Retriever không tách câu hỏi thành ba subqueries: academic record, tuition refund và scholarship credit review. |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | Context Precision coi nhiều chunk là relevant nếu chỉ overlap 10%, nên đạt 1.000 dù thiếu hai claim quyết định. |
| Why 5 | Root cause có thể hành động được là gì? | Retrieval cần query decomposition hoặc policy-aware expansion cho multi-document questions, cùng metric relevance theo claim thay vì token threshold thấp. |

**Root cause và proposed fix:**

> *Câu trả lời:* `find_root_cause()` trả “Context is missing or irrelevant —
> improve retrieval”, và tôi đồng ý. Cần tách H02 thành ba subqueries, retrieve
> theo từng policy rồi merge/rerank; boost các cụm “after census”, “tuition
> reversed”, “attempted credit” và “completed credit”. Sau đó generator phải
> kiểm tra đủ ba mục trước khi trả lời.

### Failure 3

**ID và question:**

> **H05:** A student discussed a late add in July 2026 but submits the request
> on August 3, 2026. Which policy version applies, and what requirements apply
> to the request?

**Expected answer:**

> Registration Policy version 2.0 applies because the request was made on or
> after August 1, 2026; discussion in July does not preserve version 1.0. Late
> adds are allowed only through census, require instructor and programme-director
> approval, and require the USD 40 fee within two business days of approval.

**Actual answer:**

> The applicable policy version is 2.0, effective August 1, 2026. The request
> can be made through the September 4 census date and costs USD 40 per course.

**Scores:** Context Recall: 0.667 | Context Precision: 1.000 | Faithfulness: 0.667 |
Relevance: 0.500 | Completeness: 0.429 | Overall: 0.532

**Evidence inspection:**

> *Câu trả lời:* Retriever lấy đúng version-history paragraph ở hạng 1, calendar
> ở hạng 2 và policy-version rule ở hạng 3/5. Tuy nhiên nó không lấy đoạn late-add
> trong `02_course_registration.md`, nơi chứa instructor approval,
> programme-director approval và thời hạn trả phí hai business days. Vì vậy
> answer chọn đúng version, deadline và mức phí nhưng thiếu các điều kiện hành động.

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | Câu trả lời đúng kết luận chính nhưng thiếu approvals, hạn trả phí và giải thích July discussion không giữ version cũ. |
| Why 1 | Tại sao symptom xảy ra? | Retrieved contexts chứa version/date nhưng không chứa operational requirements trong registration policy. |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | BM25 ưu tiên nhiều paragraph có “policy/version/August” và không bảo đảm diversity theo source document. |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | Không có query expansion sang “approval”, “programme director”, “instructor” và “two business days”. |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | Generator không có checklist so sánh các required claims trong câu hỏi hai phần; Context Precision 1.000 che khuất thiếu sót về recall. |
| Why 5 | Root cause có thể hành động được là gì? | Retrieval/reranking chưa bảo đảm lấy evidence từ cả version policy và operational registration policy cho câu hỏi liên tài liệu. |

**Root cause và proposed fix:**

> *Câu trả lời:* `find_root_cause()` trả “Answer is missing key information —
> increase context window or improve generation”. Kết luận này đúng về symptom
> nhưng chưa đủ về nguyên nhân: trace cho thấy thiếu hẳn paragraph registration.
> Fix là query decomposition thành “version selection” và “late-add requirements”,
> merge top chunks từ hai subqueries, rồi dùng answer checklist gồm version,
> applicability reason, window, approvals, fee và payment deadline.

---

## 3. Failure Clustering

| Cluster | Root Cause | Failure IDs | Priority |
|---|---|---|---|
| 1 | Multi-policy retrieval thiếu claim-specific evidence hoặc source diversity | H02, H05, M02, M03 | High |
| 2 | Generator không dùng checklist nên bỏ điều kiện, consequence hoặc redirect | A01, H04, H05, A02 | High |
| 3 | Word-overlap và fallback taxonomy gán nhãn chưa sát nghĩa | E04, M04, A01, A03 | Medium |

**Nếu chỉ được sửa một cluster, bạn chọn cluster nào và vì sao?**

> *Câu trả lời:* Tôi chọn Cluster 1. H02 và H05 nằm trong ba case tệ nhất, và
> trace chứng minh các claim bắt buộc không có trong top-5 nên generator không
> thể trả lời chắc chắn. Query decomposition và source-diverse retrieval có thể
> cải thiện đồng thời Context Recall, Faithfulness và Completeness trên nhiều câu
> Hard/Medium, thay vì chỉ sửa cách diễn đạt của một answer.

---

## 4. Improvement Log

Output của `generate_improvement_log()` trên A01, H02 và H05:

| Failure ID | Type | Root Cause | Suggested Fix | Status |
|------------|------|------------|---------------|--------|
| F001 | hallucination | Answer is missing key information — increase context window or improve generation | Implement a hallucination checker and require every answer claim to be supported by retrieved context | Open |
| F002 | hallucination | Context is missing or irrelevant — improve retrieval | Improve query routing and add domain-scope checks before generating an answer | Open |
| F003 | off_topic | Answer is missing key information — increase context window or improve generation | Add the failed cases to the regression test dataset to prevent the same errors from returning | Open |

**Ba improvement suggestions ưu tiên**

1. Tách multi-policy question thành subqueries, merge và rerank theo source diversity.
2. Thêm claim checklist theo intent trước khi generator hoàn tất answer.
3. Bổ sung semantic judge và taxonomy riêng cho correct refusal/incomplete answer.

| Suggestion | Target metric | Verification method |
|---|---|---|
| Query decomposition + source-diverse reranking | Context Recall, sau đó Faithfulness và Completeness | Chạy lại H02/H05 và toàn bộ benchmark; yêu cầu H02/H05 Context Recall tăng ít nhất 0.10 và đúng policy paragraphs xuất hiện trong top-5. |
| Intent-specific answer checklist | Completeness và pass rate | Assert answer chứa tất cả required claims cho late add, withdrawal và out-of-scope cases; so sánh Completeness với baseline 0.669. |
| Semantic judge + refined taxonomy | Agreement với human labels, giảm false `off_topic`/`hallucination` | Human-label một calibration set gồm E04, A01, A02, A03; đo confusion matrix và judge–human agreement trước/sau. |

---

## 5. Regression Testing Strategy

**Câu 1: Khi nào chạy `run_regression()` trong production workflow?**

> *Câu trả lời:* Chạy trong CI cho mọi thay đổi model, prompt, retriever,
> chunking, corpus hoặc policy; chạy lại trước release và theo lịch khi corpus cập
> nhật. Baseline phải là artifact của phiên bản production đã được duyệt, dùng
> cùng golden dataset, model settings và evaluation code để so sánh công bằng.

**Câu 2: Threshold drop 0.05 có phù hợp Student Services không? Vì sao?**

> *Câu trả lời:* 0.05 phù hợp làm ngưỡng khởi đầu cho aggregate regression nhưng
> chưa đủ cho domain chính sách. Một average ổn định có thể che khuất lỗi nghiêm
> trọng ở privacy, payment, deadline hoặc adversarial case. Vì vậy cần thêm
> per-slice/per-case gates và confidence interval qua nhiều lần chạy; Faithfulness
> ở safety-critical slices nên dùng threshold chặt hơn.

**Câu 3: Metric/failure nào phải block deployment, metric nào chỉ alert?**

> *Câu trả lời:* Block nếu Faithfulness trung bình dưới 0.80, có regression lớn
> hơn 0.05, hoặc bất kỳ privacy/prompt-injection case nào tiết lộ dữ liệu hay làm
> theo instruction độc hại. Block cả khi deadline/payment answer chứa sai policy
> có thể khiến sinh viên hành động sai. Relevance/Completeness giảm nhẹ trên
> low-risk informational cases có thể chỉ alert và yêu cầu review, còn Context
> Precision giảm nhưng Recall và answer quality vẫn ổn cũng chỉ alert.

**Câu 4: Điền evaluation stages vào flow.**

```text
Code/prompt/retrieval change → Offline benchmark → Regression comparison → Human review for high-risk failures → Deploy
```

> *Giải thích:* Offline benchmark tạo metrics trên golden dataset; regression
> comparison đối chiếu baseline và áp quality gates; human review kiểm tra các
> failure rủi ro cao hoặc nhãn tự động đáng ngờ. Chỉ deploy khi không có blocking
> regression; sau deploy tiếp tục online monitoring.

---

## 6. Continuous Improvement Loop

```text
Evaluate → Analyze → Improve → Augment benchmark → Repeat
```

| Priority | Action | Metric dự kiến cải thiện | Expected impact |
|---:|---|---|---|
| 1 | Query decomposition và source-diverse retrieval cho câu nhiều policy | Context Recall, Faithfulness, Completeness | H02/H05 lấy đủ claim evidence và giảm trả lời mơ hồ. |
| 2 | Answer checklist theo intent và risk level | Completeness, pass rate | Không bỏ approvals, deadlines, consequences hoặc safe redirect. |
| 3 | Semantic judge được calibrate với human labels | Label accuracy và diagnostic quality | Phân biệt refusal đúng với hallucination và giảm fallback `off_topic` sai nghĩa. |

**Hai hoặc ba failure cases nào cần thêm vào benchmark ở vòng tiếp theo?**

> *Câu trả lời:* Thêm (1) out-of-scope medical/legal request yêu cầu refusal và
> redirect; (2) withdrawal một môn ở đúng census date để kiểm tra boundary của
> refund/scholarship; (3) late-add request ở hai phía ngày 1/8/2026 để kiểm tra
> chọn version và đầy đủ approvals/payment deadline. Các case mới phải có human
> labels theo từng required claim, không chỉ một expected answer dài.

---

## 7. Final Reflection

**Điều gì trong kết quả benchmark trái với dự đoán ban đầu của bạn?**

> *Câu trả lời:* Context Precision đạt 0.930 nhưng pass rate chỉ 50%, cho thấy
> việc nhiều chunk có lexical overlap và được xếp sớm không bảo đảm chúng chứa
> đúng claim cần trả lời. A01 cũng bất ngờ: hệ thống từ chối investment advice
> đúng về safety nhưng nhận Faithfulness 0.200 và nhãn hallucination do câu trả
> lời ngắn, thiếu redirect và metric dựa trên từ trùng.

**Word-overlap heuristics trong lab có giới hạn gì? Nếu đưa hệ thống vào
production, bạn sẽ thay hoặc bổ sung metric nào?**

> *Câu trả lời:* Word overlap không hiểu paraphrase, phủ định, số liệu mâu thuẫn,
> quan hệ thời gian hay việc một refusal đúng có thể dùng từ khác expected answer.
> Context Precision threshold 0.1 còn có thể coi chunk chỉ trùng vài từ là
> relevant. Trong production tôi sẽ bổ sung claim-level entailment/NLI cho
> Faithfulness, semantic Answer Relevance, LLM-as-a-Judge theo rubric đã calibrate,
> retrieval relevance labels theo từng claim và human review cho safety/privacy.
> Đồng thời theo dõi task completion, latency, cost và user escalation rate; các
> judge scores phải được kiểm tra agreement với human labels định kỳ.
