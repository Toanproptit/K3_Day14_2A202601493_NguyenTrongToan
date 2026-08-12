"""
Day 14 — AI Evaluation & Benchmarking Pipeline
AICB-P1: AI Practical Competency Program, Phase 1

Key concepts from lecture:
    - Evaluation = Scientific Method for AI (Hypothesis → Experiment → Measure → Conclude → Iterate)
    - 4 nhóm metrics: Task Completion, Answer Quality, RAG-Specific, Business
    - RAG pipeline metrics: Context Recall → Context Precision → Faithfulness → Answer Relevancy
    - LLM-as-Judge: rubric scoring 1-5, detect bias (positional, verbosity, self-preference)
    - Golden dataset: stratified sampling (5 Easy + 7 Medium + 5 Hard + 3 Adversarial)
    - Failure taxonomy: hallucination, irrelevant, incomplete, off_topic, refusal
    - 5 Whys method for root cause analysis
    - CI/CD integration: eval as quality gate (score < threshold = block deploy)
    - Continuous Improvement Loop: Evaluate → Analyze → Improve → Augment → Repeat

Instructions:
    1. Fill in every required section marked with TODO.
    2. Do NOT change class/function signatures. The optional ``contexts``
       parameter in ``run_full_eval`` is part of the required interface.
    3. Copy this file to solution/solution.py when done.
    4. Run: pytest tests/ -v

The reranking helper is an optional bonus exercise and may remain unimplemented.
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Task 1 — Data Models (Golden Dataset + Evaluation Results)
# ---------------------------------------------------------------------------

@dataclass
class QAPair:
    """
    A question-answer pair for evaluation (part of the Golden Dataset).

    From lecture: Golden dataset cần có:
        - question: câu hỏi user
        - ground_truth (expected_answer): expert-written expected answer
        - context: source documents cần retrieve
        - metadata: difficulty (easy/medium/hard), category, source_docs

    Fields:
        question:        The question to answer.
        expected_answer: The reference/ground-truth answer (expert-written).
        context:            Source context (may be empty string if not applicable).
        metadata:           Optional metadata dict (difficulty, category, etc.).
        retrieved_contexts: List of retrieved chunks (ORDER = retriever rank).
                            Used by the retrieval-side metrics (Task 2b).
    """
    question: str
    expected_answer: str
    context: str = ""
    metadata: dict = field(default_factory=dict)
    retrieved_contexts: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    """
    Evaluation result for a single Q&A pair.

    From lecture - RAG metrics pipeline:
        Question → Retriever → Context → Generator → Answer
        Each step has a metric: Context Recall, Context Precision, Faithfulness, Answer Relevancy

    From lecture - Score interpretation:
        0.8-1.0: Good (Monitor, maintain)
        0.6-0.8: Needs work (Analyze failures, iterate)
        < 0.6: Significant issues (Deep investigation required)

    Fields:
        qa_pair:        The original QAPair.
        actual_answer:  What the agent actually returned.
        faithfulness:   Float 0-1, how grounded the answer is in context.
        relevance:      Float 0-1, how relevant the answer is to the question.
        completeness:   Float 0-1, how complete the answer is vs expected.
        passed:         True if all three scores >= 0.5.
        failure_type:   None if passed, otherwise one of:
                        "hallucination", "irrelevant", "incomplete", "off_topic".
        context_precision: Float 0-1 or None — quality of retrieval ranking.
        context_recall:    Float 0-1 or None — coverage of expected by context.
                        (Both stay None unless retrieved chunks are supplied;
                         they are NOT part of overall_score().)
    """
    # TODO: define fields
    
    qa_pair: QAPair
    actual_answer: str
    faithfulness: float
    relevance: float
    completeness: float
    passed: bool
    failure_type: str | None = None
    context_precision: float | None = None
    context_recall: float | None = None

    def overall_score(self) -> float:
        """Compute the average of faithfulness, relevance, and completeness.

        Returns:
            (faithfulness + relevance + completeness) / 3.0

        TODO: Return mean of the three metric scores
        """
        return (
            self.faithfulness
            + self.relevance
            + self.completeness
        ) / 3.0


# ---------------------------------------------------------------------------
# Task 2 — RAGAS Evaluator (Simplified word-overlap heuristic)
# ---------------------------------------------------------------------------
# In production, replace with actual RAGAS framework:
#   from ragas import evaluate
#   from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRecall, ContextPrecision
#
# Or DeepEval:
#   from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
#   assert_test(test_case, [faithfulness, hallucination])
#
# Or TruLens:
#   from trulens.core import Feedback
#   f_groundedness = Feedback(provider.groundedness_measure_with_cot_reasons)
# ---------------------------------------------------------------------------

# Common English stopwords are ignored so overlap reflects *content* words,
# not filler (otherwise "is"/"a"/"the" inflate every score).
STOPWORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "with", "as", "by", "and", "or",
    "it", "its", "this", "that", "these", "those", "from", "into", "than",
}


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokenization, ignoring punctuation and stopwords."""
    if not text:
        return set()
    tokens = re.findall(r"\b\w+\b", text.lower())
    return {t for t in tokens if t not in STOPWORDS}


class RAGASEvaluator:
    """
    Evaluates RAG pipeline outputs using RAGAS-inspired heuristics.

    All metrics use word overlap rather than LLM calls for simplicity.
    Replace with actual LLM-based evaluation in production.
    """

    def evaluate_faithfulness(self, answer: str, context: str) -> float:
        """
        Measure how grounded the answer is in the context.

        Heuristic:
            answer_tokens = _tokenize(answer)
            context_tokens = _tokenize(context)
            faithfulness = |answer_tokens ∩ context_tokens| / |answer_tokens|
            Clamp to [0.0, 1.0]. Return 1.0 if answer is empty.

        Returns:
            float in [0.0, 1.0] — 1.0 = fully grounded in context.
        """
        # TODO
        answer_tokens = _tokenize(answer)
        context_tokens = _tokenize(context)

        if not answer_tokens:
            return 1.0
        score = len(answer_tokens & context_tokens) / len(answer_tokens)
        return min(1.0, max(0.0, score))


    def evaluate_relevance(self, answer: str, question: str) -> float:
        """
        Measure how relevant the answer is to the question.

        Heuristic:
            relevance = |answer_tokens ∩ question_tokens| / |question_tokens|
            Clamp to [0.0, 1.0]. Return 1.0 if question is empty.

        Returns:
            float in [0.0, 1.0]
        """
        # TODO
        answer_tokens = _tokenize(answer)
        question_tokens = _tokenize(question)

        if not question_tokens:
            return 1.0

        score = len(answer_tokens & question_tokens) / len(question_tokens)
        return min(1.0, max(0.0, score))

    def evaluate_completeness(self, answer: str, expected: str) -> float:
        """
        Measure how well the answer covers the expected answer.

        Heuristic:
            completeness = |answer_tokens ∩ expected_tokens| / |expected_tokens|
            Clamp to [0.0, 1.0]. Return 1.0 if expected is empty.

        Returns:
            float in [0.0, 1.0]
        """
        # TODO
        answer_tokens = _tokenize(answer)
        expected_tokens = _tokenize(expected)

        if not expected_tokens:
            return 1.0

        score = len(answer_tokens & expected_tokens) / len(expected_tokens)
        return min(1.0, max(0.0, score))

    # -----------------------------------------------------------------------
    # Task 2b — Retrieval-side metrics (evaluate the GET-CONTEXT step)
    # -----------------------------------------------------------------------
    # From lecture (RAG pipeline): Context Recall → Context Precision →
    #   Faithfulness → Answer Relevancy. The two below score the RETRIEVER,
    #   operating on a LIST of chunks (order = retriever rank).
    # -----------------------------------------------------------------------

    def evaluate_context_recall(self, contexts: list[str], expected: str) -> float:
        """Context Recall — how much of the expected answer is covered by the
        UNION of retrieved chunks.

        Heuristic:
            union_tokens = ⋃ _tokenize(chunk) for chunk in contexts
            recall = |expected_tokens ∩ union_tokens| / |expected_tokens|
            Clamp to [0.0, 1.0]. Return 1.0 if expected is empty.

        Low recall => retriever missed evidence the answer needs.
        """
        # TODO
        expected_tokens = _tokenize(expected)

        if not expected_tokens:
            return 1.0

        union_tokens: set[str] = set()

        for chunk in contexts:
            union_tokens.update(_tokenize(chunk))

        score = len(expected_tokens & union_tokens) / len(expected_tokens)
        return min(1.0, max(0.0, score))

    def evaluate_context_precision(
        self,
        contexts: list[str],
        expected: str,
        relevance_threshold: float = 0.1,
    ) -> float:
        """Context Precision — RANK-AWARE Average Precision (AP@K), like RAGAS.
        Rewards retrievers that place RELEVANT chunks BEFORE noise.

        Steps:
            1. A chunk is "relevant" if it covers >= relevance_threshold of the
               expected tokens:  |chunk ∩ expected| / |expected| >= threshold
            2. Precision@k = (#relevant in top-k) / k
            3. AP@K = (1 / #relevant) * Σ_k [ Precision@k · relevant_k ]

        Return 1.0 if expected empty; 0.0 if no chunks or none relevant.
        Reordering relevant chunks earlier (reranking) raises this score.
        """
        # TODO
        expected_tokens = _tokenize(expected)

        if not expected_tokens:
            return 1.0

        if not contexts:
            return 0.0

        relevant_flags: list[bool] = []

        for chunk in contexts:
            chunk_tokens = _tokenize(chunk)
            coverage = (
                len(chunk_tokens & expected_tokens)
                / len(expected_tokens)
            )
            relevant_flags.append(coverage >= relevance_threshold)

        relevant_count = sum(relevant_flags)

        if relevant_count == 0:
            return 0.0

        relevant_so_far = 0
        precision_sum = 0.0

        for rank, is_relevant in enumerate(relevant_flags, start=1):
            if is_relevant:
                relevant_so_far += 1
                precision_at_k = relevant_so_far / rank
                precision_sum += precision_at_k

        score = precision_sum / relevant_count
        return min(1.0, max(0.0, score))

    def run_full_eval(
        self,
        answer: str,
        question: str,
        context: str,
        expected: str,
        contexts: list[str] | None = None,
    ) -> EvalResult:
        """
        Run the three answer-side evaluations and, when ``contexts`` is
        supplied, both retrieval-side evaluations.

        passed = True if all three scores >= 0.5.

        failure_type determination (first match wins):
            faithfulness < 0.3  → "hallucination"
            relevance < 0.3     → "irrelevant"
            completeness < 0.3  → "incomplete"
            otherwise if failed → "off_topic"

        Retrieval wiring:
            contexts is None → context_recall and context_precision stay None
            contexts provided → evaluate and store both retrieval metrics

        The two retrieval metrics diagnose the retriever and do not change the
        three-metric ``passed`` rule or ``overall_score()``.

        Returns:
            EvalResult with all fields populated.
        """
        # TODO
        faithfulness = self.evaluate_faithfulness(answer, context)
        relevance = self.evaluate_relevance(answer, question)
        completeness = self.evaluate_completeness(answer, expected)

        passed = all(
            score >= 0.5
            for score in (faithfulness, relevance, completeness)
        )

        failure_type: str | None = None

        if not passed:
            if faithfulness < 0.3:
                failure_type = "hallucination"
            elif relevance < 0.3:
                failure_type = "irrelevant"
            elif completeness < 0.3:
                failure_type = "incomplete"
            else:
                failure_type = "off_topic"

        context_recall: float | None = None
        context_precision: float | None = None

        if contexts is not None:
            context_recall = self.evaluate_context_recall(
                contexts,
                expected,
            )
            context_precision = self.evaluate_context_precision(
                contexts,
                expected,
            )

        qa_pair = QAPair(
            question=question,
            expected_answer=expected,
            context=context,
            retrieved_contexts=(
                list(contexts) if contexts is not None else []
            ),
        )

        return EvalResult(
            qa_pair=qa_pair,
            actual_answer=answer,
            faithfulness=faithfulness,
            relevance=relevance,
            completeness=completeness,
            passed=passed,
            failure_type=failure_type,
            context_precision=context_precision,
            context_recall=context_recall,
        )


# ---------------------------------------------------------------------------
# Reranking helper (used by Exercise 3.5 — boosting Context Precision)
# ---------------------------------------------------------------------------

def rerank_by_overlap(contexts: list[str], query: str) -> list[str]:
    """A minimal lexical reranker: sort chunks by word overlap with the query,
    most-overlapping first. Stand-in for a real cross-encoder reranker.

    Reordering relevant chunks toward the top increases the rank-aware
    Context Precision WITHOUT changing the retrieved set.

    Hint: sorted(contexts, key=lambda c: len(_tokenize(c) & _tokenize(query)),
                 reverse=True)
    """
    # TODO (Bonus — Exercise 3.5): implement the reranker
    raise NotImplementedError("Implement rerank_by_overlap")


# ---------------------------------------------------------------------------
# Task 3 — LLM Judge
# ---------------------------------------------------------------------------
# From lecture:
#   - Judge LLM nhận: question + agent answer + reference answer + rubric
#   - Judge trả về: Score 1-5 + Rationale
#   - Best practices: multiple judges, randomize order, calibrate against human
#   - Biases: positional, verbosity, self-preference
#   - Rubric template:
#       5 = Correct, complete, well-cited
#       4 = Mostly correct, minor gaps
#       3 = Partially correct, some errors
#       2 = Significant errors or missing info
#       1 = Wrong or irrelevant
# ---------------------------------------------------------------------------

class LLMJudge:
    """
    Uses an LLM to score AI responses according to a rubric.
    """

    def __init__(self, judge_llm_fn: Callable[[str], str]) -> None:
        self.judge_llm_fn = judge_llm_fn

    def score_response(
        self,
        question: str,
        answer: str,
        rubric: dict[str, Any],
    ) -> dict[str, Any]:
        rubric_text = "\n".join(
            f"- {criterion}: {description}"
            for criterion, description in rubric.items()
        )

        prompt = f"""
    Evaluate the following AI answer.

    Question:
    {question}

    Answer:
    {answer}

    Rubric:
    {rubric_text}

    Return a JSON object mapping each rubric criterion to a score from 0 to 1.
    """.strip()

        raw_response = self.judge_llm_fn(prompt)

        default_scores = {
            criterion: 0.5
            for criterion in rubric
        }

        try:
            parsed = json.loads(raw_response)

            if not isinstance(parsed, dict):
                scores = default_scores
            else:
                scores = {}

                for criterion in rubric:
                    value = parsed.get(criterion, 0.5)

                    if isinstance(value, (int, float)):
                        scores[criterion] = min(
                            1.0,
                            max(0.0, float(value)),
                        )
                    else:
                        scores[criterion] = 0.5

        except (json.JSONDecodeError, TypeError, ValueError):
            scores = default_scores

        return {
            "scores": scores,
            "reasoning": raw_response,
        }
            

    def detect_bias(
        self,
        scores_batch: list[dict[str, Any]],
    ) -> dict[str, Any]:
        all_scores: list[float] = []
        response_averages: list[float] = []

        for result in scores_batch:
            scores = result.get("scores", {})

            if not isinstance(scores, dict):
                continue

            numeric_scores = [
                float(value)
                for value in scores.values()
                if isinstance(value, (int, float))
            ]

            if numeric_scores:
                all_scores.extend(numeric_scores)
                response_averages.append(
                    sum(numeric_scores) / len(numeric_scores)
                )

        if not all_scores:
            return {
                "positional_bias": False,
                "leniency_bias": False,
                "severity_bias": False,
            }

        average_score = sum(all_scores) / len(all_scores)

        positional_bias = False

        if len(response_averages) > 1:
            other_average = (
                sum(response_averages[1:])
                / len(response_averages[1:])
            )
            positional_bias = response_averages[0] > other_average

        return {
            "positional_bias": positional_bias,
            "leniency_bias": average_score > 0.8,
            "severity_bias": average_score < 0.3,
        }


# ---------------------------------------------------------------------------
# Task 4 — Benchmark Runner
# ---------------------------------------------------------------------------
# From lecture:
#   - CI/CD integration: Framework + CI/CD = quality gate tự động
#   - Agent với faithfulness < 0.7 → không được deploy
#   - Regression = metric drop > 0.05 vs baseline
#   - Triggers: mỗi code release, mỗi prompt change, trước demo/launch
# ---------------------------------------------------------------------------

class BenchmarkRunner:
    """
    Runs a full evaluation benchmark.
    """

    def run(
        self,
        qa_pairs: list[QAPair],
        agent_fn: Callable[[str], str],
        evaluator: RAGASEvaluator,
    ) -> list[EvalResult]:
        results: list[EvalResult] = []

        for pair in qa_pairs:
            actual_answer = agent_fn(pair.question)

            result = evaluator.run_full_eval(
                answer=actual_answer,
                question=pair.question,
                context=pair.context,
                expected=pair.expected_answer,
                contexts=pair.retrieved_contexts,
            )

            # run_full_eval tạo một QAPair mới, nhưng benchmark cần giữ
            # metadata và dữ liệu đầy đủ của pair gốc.
            result.qa_pair = pair
            results.append(result)

        return results

    def generate_report(
        self,
        results: list[EvalResult],
    ) -> dict[str, Any]:
        total = len(results)

        if total == 0:
            return {
                "total": 0,
                "passed": 0,
                "pass_rate": 0.0,
                "avg_faithfulness": 0.0,
                "avg_relevance": 0.0,
                "avg_completeness": 0.0,
                "avg_context_recall": None,
                "avg_context_precision": None,
                "failure_types": {},
            }
        passed_count = sum(result.passed for result in results)

        avg_faithfulness = (
            sum(result.faithfulness for result in results) / total
        )
        avg_relevance = (
            sum(result.relevance for result in results) / total
        )
        avg_completeness = (
            sum(result.completeness for result in results) / total
        )

        context_recalls = [
            result.context_recall
            for result in results
            if result.context_recall is not None
        ]

        context_precisions = [
            result.context_precision
            for result in results
            if result.context_precision is not None
        ]

        avg_context_recall = (
            sum(context_recalls) / len(context_recalls)
            if context_recalls
            else None
        )

        avg_context_precision = (
            sum(context_precisions) / len(context_precisions)
            if context_precisions
            else None
        )

        failure_types: dict[str, int] = {}

        for result in results:
            if result.failure_type is not None:
                failure_types[result.failure_type] = (
                    failure_types.get(result.failure_type, 0) + 1
                )

        return {
            "total": total,
            "passed": passed_count,
            "pass_rate": passed_count / total,
            "avg_faithfulness": avg_faithfulness,
            "avg_relevance": avg_relevance,
            "avg_completeness": avg_completeness,
            "avg_context_recall": avg_context_recall,
            "avg_context_precision": avg_context_precision,
            "failure_types": failure_types,
        }

    def run_regression(
        self,
        new_results: list,
        baseline_results: list,
    ) -> dict:
        def average(results: list, attribute: str) -> float:
            if not results:
                return 0.0

            return sum(
                getattr(result, attribute)
                for result in results
            ) / len(results)

        new_avg_faithfulness = average(
            new_results,
            "faithfulness",
        )
        new_avg_relevance = average(
            new_results,
            "relevance",
        )
        new_avg_completeness = average(
            new_results,
            "completeness",
        )

        baseline_avg_faithfulness = average(
            baseline_results,
            "faithfulness",
        )
        baseline_avg_relevance = average(
            baseline_results,
            "relevance",
        )
        baseline_avg_completeness = average(
            baseline_results,
            "completeness",
        )

        regressions: list[str] = []

        if baseline_avg_faithfulness - new_avg_faithfulness > 0.05:
            regressions.append("faithfulness")

        if baseline_avg_relevance - new_avg_relevance > 0.05:
            regressions.append("relevance")

        if baseline_avg_completeness - new_avg_completeness > 0.05:
            regressions.append("completeness")

        return {
            "new_avg_faithfulness": new_avg_faithfulness,
            "new_avg_relevance": new_avg_relevance,
            "new_avg_completeness": new_avg_completeness,
            "baseline_avg_faithfulness": baseline_avg_faithfulness,
            "baseline_avg_relevance": baseline_avg_relevance,
            "baseline_avg_completeness": baseline_avg_completeness,
            "regressions": regressions,
            "passed": len(regressions) == 0,
        }

    def identify_failures(
        self,
        results: list[EvalResult],
        threshold: float = 0.5,
    ) -> list[EvalResult]:
        return [
            result
            for result in results
            if (
                result.faithfulness < threshold
                or result.relevance < threshold
                or result.completeness < threshold
            )
        ]


# ---------------------------------------------------------------------------
# Task 5 — Failure Analyzer
# ---------------------------------------------------------------------------
# From lecture:
#   Failure Taxonomy:
#     - hallucination: bịa thông tin → faithfulness guardrail yếu
#     - irrelevant: không giải quyết câu hỏi → prompt ambiguous
#     - incomplete: bỏ sót thông tin → context window nhỏ, retrieval thiếu
#     - off_topic: trả lời chủ đề khác → intent detection sai
#     - refusal: từ chối khi nên trả lời → guardrails quá chặt
#
#   5 Whys Method: hỏi "Tại sao?" liên tục cho đến root cause
#   Failure Clustering: fix 1 root cause giải quyết nhiều failures cùng lúc
#   Continuous Improvement: Evaluate → Analyze → Improve → Augment → Repeat
# ---------------------------------------------------------------------------

class FailureAnalyzer:
    """
    Analyzes failed evaluation results to identify patterns and suggest fixes.
    """

    def categorize_failures(
        self,
        failures: list[EvalResult],
    ) -> dict[str, int]:
        categories: dict[str, int] = {}

        for failure in failures:
            failure_type = failure.failure_type or "unknown"
            categories[failure_type] = categories.get(failure_type, 0) + 1

        return categories

    def find_root_cause(self, failure: EvalResult) -> str:
        faithfulness = failure.faithfulness
        relevance = failure.relevance
        completeness = failure.completeness

        if (
            faithfulness < relevance
            and faithfulness < completeness
        ):
            return (
                "Context is missing or irrelevant — improve retrieval"
            )

        if (
            relevance < faithfulness
            and relevance < completeness
        ):
            return (
                "Answer does not address the question — "
                "improve prompt clarity"
            )

        if (
            completeness < faithfulness
            and completeness < relevance
        ):
            return (
                "Answer is missing key information — "
                "increase context window or improve generation"
            )

        return "Multiple issues detected — review full pipeline"

    def generate_improvement_log(
        self,
        failures: list,
        suggestions: list[str],
    ) -> str:
        lines = [
            "| Failure ID | Type | Root Cause | Suggested Fix | Status |",
            "|------------|------|------------|---------------|--------|",
        ]

        for index, failure in enumerate(failures, start=1):
            failure_id = f"F{index:03d}"
            failure_type = failure.failure_type or "unknown"
            root_cause = self.find_root_cause(failure)

            if index <= len(suggestions):
                suggested_fix = suggestions[index - 1]
            else:
                suggested_fix = "Review and assign corrective action"

            # Tránh ký tự | trong nội dung phá vỡ bảng Markdown.
            failure_type = failure_type.replace("|", "\\|")
            root_cause = root_cause.replace("|", "\\|")
            suggested_fix = suggested_fix.replace("|", "\\|")

            lines.append(
                f"| {failure_id} | {failure_type} | "
                f"{root_cause} | {suggested_fix} | Open |"
            )

        return "\n".join(lines)
    def generate_improvement_suggestions(
        self,
        failures: list[EvalResult],
    ) -> list[str]:
        if not failures:
            return []

        categories = self.categorize_failures(failures)

        suggestion_map = {
            "hallucination": (
                "Implement a hallucination checker and require every "
                "answer claim to be supported by retrieved context"
            ),
            "irrelevant": (
                "Improve intent detection and prompt instructions so "
                "answers directly address the user's question"
            ),
            "incomplete": (
                "Increase retrieval coverage and add prompt instructions "
                "to include all required conditions and steps"
            ),
            "off_topic": (
                "Improve query routing and add domain-scope checks before "
                "generating an answer"
            ),
            "refusal": (
                "Review refusal guardrails and add examples of valid "
                "student-service questions"
            ),
            "unknown": (
                "Review unclassified failures manually and extend the "
                "failure taxonomy"
            ),
        }

        suggestions: list[str] = []

        sorted_categories = sorted(
            categories.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        for failure_type, _count in sorted_categories:
            normalized_type = failure_type.lower()

            suggestion = suggestion_map.get(
                normalized_type,
                suggestion_map["unknown"],
            )

            if suggestion not in suggestions:
                suggestions.append(suggestion)

        fallback_suggestions = [
            (
                "Add the failed cases to the regression test dataset "
                "to prevent the same errors from returning"
            ),
            (
                "Inspect the lowest-scoring metric for each failure and "
                "assign an owner for corrective action"
            ),
            (
                "Re-run the benchmark after each retrieval, prompt, or "
                "model change"
            ),
        ]

        for suggestion in fallback_suggestions:
            if len(suggestions) >= 3:
                break
            suggestions.append(suggestion)

        return suggestions


# ---------------------------------------------------------------------------
# Entry point for manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Sample golden dataset (mini version — use 20 pairs in actual lab)
    # From lecture: stratified sampling = 5 Easy + 7 Medium + 5 Hard + 3 Adversarial
    qa_pairs = [
        # Easy — factual lookup
        QAPair(
            question="What is RAG?",
            expected_answer="RAG stands for Retrieval-Augmented Generation, which combines retrieval with text generation.",
            context="RAG is a technique that retrieves relevant documents and uses them to ground LLM generation.",
            metadata={"difficulty": "easy", "category": "definition"},
        ),
        QAPair(
            question="What is the capital of France?",
            expected_answer="Paris is the capital of France.",
            context="France is a country in Western Europe. Its capital city is Paris.",
            metadata={"difficulty": "easy", "category": "factual"},
        ),
        # Medium — multi-step reasoning
        QAPair(
            question="Explain backpropagation and why it matters for training",
            expected_answer="Backpropagation is an algorithm for training neural networks by computing gradients efficiently, enabling deep learning models to learn from errors.",
            context="Neural networks learn through gradient descent. Backpropagation efficiently computes these gradients layer by layer.",
            metadata={"difficulty": "medium", "category": "explanation"},
        ),
        # Hard — ambiguous
        QAPair(
            question="Should I use RAG or fine-tuning for my chatbot?",
            expected_answer="It depends on the use case: RAG is better for frequently updated knowledge, fine-tuning for consistent style/behavior. Consider cost, latency, and data freshness.",
            context="RAG retrieves external documents at inference time. Fine-tuning modifies model weights during training.",
            metadata={"difficulty": "hard", "category": "comparison"},
        ),
        # Adversarial — out-of-scope
        QAPair(
            question="What is the meaning of life?",
            expected_answer="This question is outside the scope of this system. I can help with AI and technology questions.",
            context="This is an AI assistant specialized in technology topics.",
            metadata={"difficulty": "adversarial", "category": "out_of_scope"},
        ),
    ]

    evaluator = RAGASEvaluator()
    runner = BenchmarkRunner()

    def mock_agent(question: str) -> str:
        """Simple mock agent for testing. Replace with your actual agent."""
        return f"Based on my knowledge: {question[:30]}... The answer involves key concepts."

    # Run benchmark
    results = runner.run(qa_pairs, mock_agent, evaluator)
    report = runner.generate_report(results)
    print("=== Benchmark Report ===")
    for k, v in report.items():
        print(f"  {k}: {v}")

    # Identify and analyze failures
    failures = runner.identify_failures(results, threshold=0.5)
    print(f"\n=== Failures ({len(failures)}) ===")
    analyzer = FailureAnalyzer()

    # Categorize (from lecture: cluster before fix)
    categories = analyzer.categorize_failures(failures)
    print("Failure Categories:", categories)

    # Root cause for each failure (from lecture: 5 Whys)
    for f in failures:
        cause = analyzer.find_root_cause(f)
        print(f"  Root cause: {cause}")

    # Improvement suggestions (from lecture: continuous improvement loop)
    suggestions = analyzer.generate_improvement_suggestions(failures)
    print("\nImprovement Suggestions:")
    for s in suggestions:
        print(f"  - {s}")

    # Generate improvement log (Markdown table)
    log = analyzer.generate_improvement_log(failures, suggestions)
    print("\n=== Improvement Log ===")
    print(log)
