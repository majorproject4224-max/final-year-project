# Ten-minute demonstration and viva guide

Use a disposable demo database or two accounts on the approved deployment. Never use real private data just to make the demo look populated.

## Demonstration

1. **Purpose (one minute):** explain how students with complementary interests find collaborators and recruiting projects.
2. **Registration/profile:** register, add skills/interests/availability, save and show normalization (Python/python and ML/machine learning).
3. **Recommendations:** show students/projects, the synthetic-data notice and concrete explanations. Change a profile skill and request fresh recommendations.
4. **Project workflow:** create a project, apply from a second browser/account, accept as owner, observe team capacity/membership.
5. **Teammate ranking:** open the owner's project and show recommendations based on its requirements; invite a student and respond from My space.
6. **Connections and chat:** accept a connection, send between two browsers, show live delivery/read receipt and reload to show persisted history.
7. **Events and feedback:** create/join an event; move the shared project through In Progress to Completed and submit teammate feedback.
8. **ML evidence:** open the four data tables, generator, train script and actual metrics. Show k selection, entity-disjoint splitting and both classifiers.
9. **Close with limitations:** all bundled labels are synthetic, model scores are uncalibrated and hosting is a small free-tier demonstration.

Use separate browser profiles or an incognito window for the second student. Each tab has its own sessionStorage tokens.

## Likely questions

**Why both K-Means and Random Forest?** K-Means discovers similar skill/interest profiles and narrows candidates; Random Forest learns pair-level compatibility labels and ranks candidates.

**Is the recommendation just a rule?** Inference uses trained classifiers. The development labels came from a documented deterministic rubric, so current evaluation measures learning that rubric. Real compatibility claims need consented real outcomes.

**Why not random pair-row splitting?** The same student could appear in both sides, inflating evaluation. The project partitions student identities first; project identities are also separated for student–project matching.

**Why seven clusters?** It had the highest measured silhouette among tested k=2…10. The synthetic profile generator also influences that result; it is not proof of seven natural groups at our college.

**What if Redis stops?** Live events may be interrupted. Permanent history remains in MongoDB. The client reconnects and catches up. Rate limiting also uses Redis, so an outage can temporarily block API operations.

**What if two students get the last team slot?** A transaction with a conditional membership update allows only one approval; the other receives a conflict.

**Why MongoDB rather than MySQL?** MongoDB is a project requirement and fits profile/tag documents, but it requires different modeling and explicit transaction/index choices. It is not merely a syntax swap.

**How do you replace synthetic labels?** Obtain consent, define a real outcome/time window, export reviewed completed-project feedback with provenance, separate entities/time, evaluate offline and publish a reviewed model. Clicks alone are not reliable labels.

**What has not been built?** No email verification/recovery, moderation console, photo storage, group chat, real online-presence tracking or automatic retraining. These are future work, not hidden finished features.
