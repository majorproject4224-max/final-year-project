# Dataset design decision

The former synthetic student/pair datasets are retired and removed from the active tree. Their generation and metrics remain only in Git history.

The active source is the original Stack Overflow Developer Survey 2024. See [dataset provenance](../../dataset/README.md), [methodology](../ML_METHODOLOGY.md) and [measured results](../RESULTS.md).

The supervised target is a respondent's recorded desired programming languages. There are no observed friendship or project-success labels in this source. We therefore do not train or report a supervised compatibility classifier.
