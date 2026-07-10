"""
backend/run_evaluation.py
 
Runs the 50-question golden dataset against the live /chat endpoint,
scores each answer with judge.py's LLM-as-judge, aggregates results with
metrics.py, and writes a full evaluation report to
Project documents/Tracker/Evaluation_Report.md
 
Usage (from project root, backend must be running on port 8800):
    python backend/run_evaluation.py
"""
 
import json
import time
import requests
import os
import sys
 
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
 
from evaluation.judge import judge_answer
from evaluation.metrics import aggregate_scores, summarize_by_agent
 
BACKEND_URL = "http://localhost:8800"
DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
REPORT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "Project documents", "Tracker", "Evaluation_Report.md"
)
 
 
def run_question(item):
    question = item["question"]
    start = time.time()
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            data={"query": question},
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()
        answer = data.get("answer", "")
        sources = data.get("sources", [])
        response_time = round(time.time() - start, 2)
    except requests.exceptions.RequestException as e:
        return {
            "id": item["id"],
            "category": item["category"],
            "question": question,
            "answer": f"ERROR: {e}",
            "sources": [],
            "response_time": round(time.time() - start, 2),
            "error": True,
        }
 
    context = " | ".join(sources) if sources else "No sources returned."
    judge_result = judge_answer(question, context, answer)
 
    agent_executed = "unknown"
    if sources:
        if any("PostgreSQL" in s for s in sources):
            agent_executed = "mcp"
        else:
            agent_executed = "retriever"
 
    return {
        "id": item["id"],
        "category": item["category"],
        "question": question,
        "answer": answer,
        "sources": sources,
        "response_time": response_time,
        "agent_executed": agent_executed,
        "error": False,
        **judge_result,
    }
 
 
def main():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)
 
    # Skip questions requiring an image upload — not automatable via this
    # simple script; noted separately in the report.
    text_only = [q for q in dataset if not q.get("requires_image")]
    skipped = [q for q in dataset if q.get("requires_image")]
 
    results = []
    for item in text_only:
        print(f"Running Q{item['id']}: {item['question'][:60]}...")
        result = run_question(item)
        results.append(result)
 
    overall = aggregate_scores(results)
    by_agent = summarize_by_agent(results)
 
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# MediAssist AI — Golden Dataset Evaluation Report\n\n")
        f.write(f"Total questions in dataset: {len(dataset)}\n\n")
        f.write(f"Questions requiring image upload (skipped, run manually): {len(skipped)}\n")
        for q in skipped:
            f.write(f"- Q{q['id']}: {q['question']}\n")
        f.write(f"\nQuestions evaluated automatically: {len(results)}\n\n")
 
        f.write("## Overall scores (average across all evaluated questions)\n\n")
        f.write("| Metric | Average score (1-10) |\n|---|---|\n")
        for metric, avg in overall["per_metric_average"].items():
            avg_str = f"{avg:.2f}" if avg is not None else "N/A"
            f.write(f"| {metric} | {avg_str} |\n")
        overall_avg_str = f"{overall['overall_average']:.2f}" if overall["overall_average"] else "N/A"
        f.write(f"\n**Overall average across all metrics: {overall_avg_str}**\n\n")
 
        f.write("## Scores by agent path\n\n")
        for agent, scores in by_agent.items():
            f.write(f"### {agent}\n")
            avg_str = f"{scores['overall_average']:.2f}" if scores["overall_average"] else "N/A"
            f.write(f"- Questions: {scores['questions_evaluated']}\n")
            f.write(f"- Overall average: {avg_str}\n\n")
 
        avg_response_time = sum(r["response_time"] for r in results) / len(results) if results else 0
        f.write(f"## Average response time: {avg_response_time:.2f}s\n\n")
 
        f.write("## Per-question detail\n\n")
        for r in results:
            f.write(f"### Q{r['id']} [{r['category']}]: {r['question']}\n\n")
            f.write(f"**Answer:** {r['answer']}\n\n")
            f.write(f"**Sources:** {', '.join(r['sources']) if r['sources'] else 'none'}\n\n")
            f.write(f"**Response time:** {r['response_time']}s | **Agent path:** {r.get('agent_executed', 'n/a')}\n\n")
            if not r.get("error"):
                for metric in ["faithfulness", "grounding", "relevance", "completeness", "hallucination_risk"]:
                    m = r.get(metric, {})
                    f.write(f"- {metric}: {m.get('score', 'N/A')} — {m.get('reason', '')}\n")
            else:
                f.write("**Error occurred, not scored.**\n")
            f.write("\n---\n\n")
 
    print(f"\nDone. Report written to: {REPORT_PATH}")
    print(f"Overall average score: {overall_avg_str}")
 
 
if __name__ == "__main__":
    main()
 