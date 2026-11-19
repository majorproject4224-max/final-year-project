# ConnectAI: AI/ML-Based Social Connection Recommendation Platform

B.Tech Computer Science and Engineering project. Author, institution, department, guide and submission details should be completed by the project team.

## Problem and proposed system

People who want to learn or build together may not know who has relevant experience or complementary learning goals. ConnectAI combines structured profiles, connections, project applications, community activities and messaging with explainable discovery.

The platform supports students and other community members. Its evaluated ML scope is technology learning preferences; it does not predict friendship success or suitability for unrelated activities.

## Reference and contribution

The [connecT university social platform](https://github.com/RohitGaira/connecT-University-Social-Platform) provides a functional reference for profiles, connections, teams, projects, events and messaging. ConnectAI uses React, Django REST Framework, MongoDB and Django Channels, with an independently documented ML pipeline.

The project's distinctive implementation is reciprocal technology learning discovery: both “what I want to learn that you use” and “what you want to learn that I use” are shown from actual profile comparisons. Source-linked fields, data completeness and measured model evidence make recommendations inspectable. Reciprocal recommendation is established research; we do not claim to invent it. See [REFERENCES.md](REFERENCES.md).

## Architecture and database

React calls protected Django REST APIs. MongoDB stores account/profile, connection, project/application, event/registration, conversation/message and feedback documents. JWT authenticates requests. Channels provides WebSocket delivery through Redis after messages are persisted in MongoDB.

Recommendation requests load a saved model bundle. Training runs offline. A diagram and database relationship details are in [ARCHITECTURE.md](ARCHITECTURE.md). Account names and contact details are operational data and are not model features.

## Real dataset and preprocessing

The original Stack Overflow Developer Survey 2024 contains 65,437 anonymous responses. Downloads are pinned by revision and SHA-256. Inputs are languages, databases, web frameworks and platforms used, plus coding years. Recorded desired programming languages are supervised targets. Profile ML controls map these source attributes directly.

The data contains naturally missing values. Missing technology lists remain empty, coding years use a training-only median and a missing flag, and missing targets are excluded. Case, aliases and duplicates are normalized. Equivalent input profiles remain in one partition, preventing exact-profile overlap. The eligible cohort has 55,752 rows. [Dataset card](../dataset/README.md) and [methodology](ML_METHODOLOGY.md) document each step.

## Models and discovery

K-Means groups L2-normalized technology vectors. Validation silhouette selects k=2 among seven tested values. Weak separation is reported rather than presented as meaningful fixed social categories.

A multi-output Random Forest predicts 16 desired-language indicators. Training/validation select tree count, depth, minimum leaf size and decision threshold. The held-out test set is used only after those choices. No synthetic compatibility labels, registered accounts or presentation fixtures enter training.

People ranking combines observed forward/reverse learning overlaps, shared technologies and predicted preference affinity. Its weights are transparent design choices. Project recommendations use observed requirement coverage, and community activities use explicit interests/location. These latter systems are not advertised as supervised ML.

## Evaluation and results

The forest has test micro-F1 0.6963, per-label accuracy 84.26%, probability MSE 0.11535 and RMSE 0.33963. Its exact-profile accuracy is 17.61%. A simple continue-current-languages baseline has slightly higher F1 (0.7048), while the forest has lower probability error. This mixed result does not establish universal superiority.

K-Means test silhouette is 0.0633, indicating strongly overlapping groups. All figures, correct/wrong counts, confusion matrix, learning curves, selected parameter comparisons and missing-input experiments are generated from saved real outputs in [RESULTS.md](RESULTS.md).

## Verification and measurement

[TESTING.md](TESTING.md) describes reproducible cloud checks for preprocessing, inference, API permissions, invalid values, empty-profile abstention, collaboration and chat. Actual browser screenshots accompany the README.

The survey records self-reported technology use and interest. The supervised outcome is desired language use; the reported metrics measure that prediction task. Social discovery uses documented ranking weights and observed reciprocal interests. Clustering results describe overlapping technology groups. Controlled missing-input experiments are reported separately from the original dataset's natural missing values, and all test metrics identify the fixed evaluation split.

## Implemented delivery

The working application includes accounts and profiles, explainable people recommendations, connection acceptance, project applications and teams, community activities, and private real-time chat with file sharing. Model training, preprocessing artifacts, evaluation figures, the cleaned CSV/Excel export and cloud verification evidence are included in the repository. Five fictional Indian-name profiles support presentations and are excluded from ML training. The application runs in GitHub Codespaces; deployment is reserved for the project owner's explicit instruction.
