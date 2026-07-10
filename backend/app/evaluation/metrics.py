"""
backend/app/evaluation/metrics.py
 
Definitions of the evaluation metrics used across the golden dataset run,
plus simple aggregation helpers. Each metric returns a 1-10 score with a
reason, produced by judge.py's LLM-as-judge call.
"""
 
METRIC_DEFINITIONS = {
    "faithfulness": "Does the answer only state things supported by the given context, without adding unsupported claims?",
    "grounding": "Is every factual claim in the answer traceable to the provided context (document, database, or image/OCR data)?",
    "relevance": "Does the answer actually address what the user asked, without going off-topic?",
    "completeness": "Does the answer cover the key points available in the context relevant to the question, without leaving out important information?",
    "hallucination_risk": "Inverse metric: 10 = no hallucination detected, 1 = answer is substantially fabricated or unsupported.",
}
 
 
def aggregate_scores(results: list[dict]) -> dict:
    """Given a list of per-question judge results, compute per-metric
    averages plus an overall average across all metrics and questions."""
    totals = {metric: [] for metric in METRIC_DEFINITIONS}
 
    for result in results:
        for metric in METRIC_DEFINITIONS:
            score = result.get(metric, {}).get("score")
            if isinstance(score, (int, float)):
                totals[metric].append(score)
 
    averages = {
        metric: (sum(scores) / len(scores) if scores else None)
        for metric, scores in totals.items()
    }
 
    all_scores = [s for scores in totals.values() for s in scores]
    overall_average = sum(all_scores) / len(all_scores) if all_scores else None
 
    return {
        "per_metric_average": averages,
        "overall_average": overall_average,
        "questions_evaluated": len(results),
    }
 
 
def summarize_by_agent(results: list[dict]) -> dict:
    """Group results by which agent path was executed (retriever, mcp,
    vision, ocr, report_analysis) and report average overall score per
    agent, to see which pipeline paths perform best/worst."""
    by_agent = {}
    for result in results:
        agent = result.get("agent_executed", "unknown")
        by_agent.setdefault(agent, []).append(result)
 
    summary = {}
    for agent, agent_results in by_agent.items():
        summary[agent] = aggregate_scores(agent_results)
 
    return summary
 