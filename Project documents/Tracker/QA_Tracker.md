# QA Tracker

## Purpose

This tracker documents sample interactions used to evaluate the behavior of MediAssist AI during development. It highlights the system's ability to answer domain-relevant questions, handle unsupported queries gracefully, and expose limitations such as retrieval gaps or backend errors.

## Test Scope

The sample questions below were used to test:
- retrieval quality over uploaded documents
- answer grounding and hallucination avoidance
- fallback behavior for unsupported or out-of-scope questions
- resilience during backend or service issues

## Sample Evaluation Log

| No. | Question | Observed Response | Notes |
|---|---|---|---|
| 1 | What is this PDF about? | The system identified the document as a healthcare report related to Type 2 Diabetes. | Good initial document understanding. |
| 2 | What other information did you get from it? | The system extracted general information from the report and referenced the health sources used. | Demonstrates document-based retrieval capability. |
| 3 | What is Type 2 Diabetes? | The system provided a correct summary of the condition. | Relevant and grounded response. |
| 4 | What are the common symptoms of diabetes? | The system listed common symptoms such as thirst, fatigue, blurred vision, and slow healing. | Good factual response. |
| 5 | What are non-payable items during discharge? | The system responded that the information was not present in the provided context. | Correct abstention behavior. |
| 6 | How is diabetes diagnosed? | The system encountered a backend error during processing. | Exposed a reliability issue that needed follow-up. |
| 7 | What is the hospital's policy on emergency admissions? | The system responded that no relevant information was available. | Shows safe handling of missing context. |
| 8 | What is the hospital's policy on patient data compliance? | The system responded that the required information was not available. | Appropriate abstention. |
| 9 | What is the admission process for a new patient? | The system responded that the information was not available in the current context. | Good non-hallucination behavior. |
| 10 | What is the capital of France? | The system correctly refused to answer outside the supported domain. | Important guardrail behavior. |

## Key Findings

- The system performs well on supported document-based questions.
- It avoids hallucinating when the answer is not present in the retrieved context.
- Some failures were observed when the backend was unavailable, indicating the need for stronger error handling and reliability improvements.
- Retrieval quality can be improved for more precise and domain-specific results.

## Conclusion

This tracker demonstrates that the system was tested not only for correctness but also for safe behavior, transparency, and robustness. It serves as evidence of evaluation work completed during the project lifecycle.
