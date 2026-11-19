# References and project contribution

Official title: **ConnectAI: AI/ML-Based Social Connection Recommendation Platform**.

## Functional reference

[RohitGaira — connecT University Social Platform](https://github.com/RohitGaira/connecT-University-Social-Platform) provides the conceptual reference for profiles, connections, project teams, events and messaging. Its README describes its own Node/Express/MongoDB/Socket.io platform. ConnectAI uses its own React/Django/Channels implementation. We do not claim to have audited every version of the reference or that these platform features are novel.

## Research and technical references

1. **Stack Exchange, Inc. (2024). Stack Overflow Developer Survey.** [Original data](https://github.com/StackExchange/Survey/tree/main/packages/archive/2024), [methodology](https://survey.stackoverflow.co/2024/methodology), [technology questions](https://survey.stackoverflow.co/2024/technology). Source of actual technology-use and desired-technology responses, not a source of friendship labels.
2. **Kleinerman, A., Rosenfeld, A., & Kraus, S. (2018). Providing Explanations for Recommendations in Reciprocal Environments.** [Paper](https://arxiv.org/abs/1807.01227). Motivates explaining potential benefit to both sides. Its study is in a different domain and does not prove ConnectAI improves learning or collaboration.
3. **Palomares, I., Porcel, C., Pizzato, L., Guy, I., & Herrera-Viedma, E. (2020 preprint). Reciprocal Recommender Systems: Analysis of State-of-Art Literature, Challenges and Opportunities towards Social Recommendation.** [Paper](https://arxiv.org/abs/2007.16120). Background on two-sided people recommendation; our application does not reproduce the full surveyed algorithms.
4. **scikit-learn documentation: RandomForestClassifier.** [API/multi-output support](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html). Used for genuine supervised language-preference learning.
5. **scikit-learn documentation: K-Means.** [Algorithm and limitations](https://scikit-learn.org/stable/modules/clustering.html#k-means). Used for unsupervised profile grouping and silhouette/inertia analysis.
6. **scikit-learn documentation: Common pitfalls.** [Data leakage](https://scikit-learn.org/stable/common_pitfalls.html). Supports fitting transformations on training data only.

Accessed 19 November 2026. Dataset bytes are pinned separately by commit and checksum.

## What is the distinct contribution here?

| Existing/platform idea | ConnectAI revision | What is demonstrated |
|---|---|---|
| Find similar people by profile | Show reciprocal technology-learning opportunities | Explanations display both observed intersections |
| Recommendation percentages | Separate learned preference probability from a transparent discovery score | UI labels, component comparisons and limitations |
| A working social platform demo | Real original survey → field mapping → preprocessing → trained model → application | Reproducible source checksum and saved pipeline |
| Results on clean demonstration records | Evaluate naturally incomplete records and artificial masking separately | Audits, coverage/abstentions and measured F1/error |
| Show only one impressive score | Compare simple baselines and disclose where they win | Held-out table, confusion matrix, MSE/RMSE and learning curves |

The contribution is an explainable, data-grounded **learning-partner discovery workflow**, integrated into this social platform. It is not a claim of research novelty for K-Means, Random Forest or reciprocal recommendation. We have measured preference prediction, not real-world social benefit. A consented user study is the next step for that claim.

## Suggested explanation to your teacher

“ConnectAI now starts from original public developer-survey data. Our profile questions map directly to that data. The forest learns actual stated technology preferences, while K-Means discovers technology groups. We use them to help discover potential learning partners and show both sides of the exchange. We demonstrate missing-data handling and report the simple baselines, including the one that beats our forest on F1. We do not claim the survey measures friendship success.”
