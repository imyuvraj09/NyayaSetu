# NyayaSetu Evaluation Dataset

## Overview
This dataset contains 30 carefully formulated legal questions designed to evaluate retrieval quality, keyword coverage, citation accuracy, and response grounding across the 7 Indian legal enactments indexed in NyayaSetu.

## Document Distribution
- **Constitution of India**: 5 questions (Q01–Q05)
- **Bharatiya Nyaya Sanhita, 2023**: 5 questions (Q06–Q10)
- **Bharatiya Nagarik Suraksha Sanhita, 2023**: 4 questions (Q11–Q14)
- **Bharatiya Sakshya Adhiniyam, 2023**: 4 questions (Q15–Q18)
- **Consumer Protection Act**: 4 questions (Q19–Q22)
- **Information Technology Act**: 4 questions (Q23–Q26)
- **Motor Vehicles Act**: 4 questions (Q27–Q30)

## Difficulty Distribution
- **Easy**: 10 questions
- **Medium**: 13 questions
- **Hard**: 7 questions

## Schema
Each test item includes:
- `id`: Unique identifier (e.g. `Q01`).
- `question`: Natural language inquiry about Indian statutory provisions.
- `expected_document`: Exact canonical title of the enactment expected to answer the query.
- `expected_keywords`: Key legal terms expected to appear in the retrieved statutory excerpts.
- `expected_sections`: Verified statutory section numbers from the enactment (empty if unverified).
- `difficulty`: Inquiry complexity level (`easy`, `medium`, `hard`).
- `category`: Legal domain classification.
