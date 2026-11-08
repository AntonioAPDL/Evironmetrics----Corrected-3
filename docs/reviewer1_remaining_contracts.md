# Continuity of earlier reviewer items

The November 2026 comment-1 revision changes exposition and figure style while
retaining all existing publication results. Earlier response text is historical
and remains unchanged.

The current article keeps the common state-space model, likelihood/source/transfer
variant labels, separate source roles, five forecast origins, 28-day and eight-day
comparisons, distributional and quantile scores, and distinct fitted-summary and
predictive intervals. Generated table estimands, selected run identities, source
hashes, and numerical contents retain their existing validators.

Current scientific-content checks are in `scripts/manuscript_text_contract.py`;
the workflow imports those pure utilities through `current_article_contract.py`.
They check active LaTeX concepts, references and section order. Old exact sentence
requirements are retained only for the prior-round response. A changed sentence
is not evidence that the corresponding scientific requirement was removed.

The six-section structure supersedes the earlier wording that forecast validation
and historical interpretation must be separate top-level sections: they are now
separate labeled subsections of Results, with the forecast illustration first.
