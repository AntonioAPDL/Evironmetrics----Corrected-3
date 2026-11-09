"""Small checks for active LaTeX structure and scientific concepts.

These checks guard omissions and broken wiring. They intentionally do not judge
writing quality or require a particular sentence; that requires a reading pass.
"""
from __future__ import annotations

import re
from pathlib import Path


def active_tex(text: str) -> str:
    """Remove LaTeX comments so retired material cannot satisfy a check."""
    return '\n'.join(re.sub(r'(?<!\\)%.*$', '', line) for line in text.splitlines())


def included_tex_paths(article_root: Path, entry: str = 'wileyNJD-APA.tex') -> list[Path]:
    """Return actual manuscript dependencies, excluding unused companion fragments."""
    root = Path(article_root).resolve()
    found: list[Path] = []
    seen: set[Path] = set()

    def visit(path: Path) -> None:
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ValueError('Manuscript include escapes article root')
        if path in seen:
            return
        if not path.is_file():
            raise FileNotFoundError(f'Missing manuscript include: {path.relative_to(root)}')
        seen.add(path)
        found.append(path)
        for name in re.findall(r'\\(?:input|include)\s*\{([^}]+)\}', active_tex(path.read_text())):
            child = root / name
            if not child.suffix:
                child = child.with_suffix('.tex')
            visit(child)

    visit(root / entry)
    return found


def manuscript_with_includes(article_root: Path) -> str:
    """Read the scientific text that is actually included in the current article."""
    return '\n'.join(path.read_text(encoding='utf-8')
                     for path in included_tex_paths(article_root))


def normalized_text(text: str) -> str:
    text = active_tex(text).replace('~', ' ')
    text = re.sub(r'\\(?:texttt|textbf|emph|mathrm|textrm)\{([^{}]*)\}', r'\1', text)
    return re.sub(r'\s+', ' ', text).lower()


def has_concepts(text: str, *patterns: str) -> bool:
    text = normalized_text(text)
    return all(re.search(pattern, text, re.I) is not None for pattern in patterns)


def has_label(text: str, label: str) -> bool:
    return re.search(r'\\label\s*\{' + re.escape(label) + r'\}', active_tex(text)) is not None


def in_order(text: str, *needles: str) -> bool:
    text = active_tex(text)
    positions = [text.find(needle) for needle in needles]
    return all(p >= 0 for p in positions) and positions == sorted(positions) and len(set(positions)) == len(positions)


def cited_url(article_text: str, bib_text: str, url: str) -> bool:
    """Accept direct URLs or a used bibliography entry resolving to the URL."""
    article = active_tex(article_text)
    if url in article:
        return True
    cited = {key.strip() for group in re.findall(r'\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}', article)
             for key in group.split(',')}
    entries = re.split(r'(?m)^\s*@', bib_text)
    for entry in entries:
        match = re.match(r'\w+\s*\{\s*([^,\s]+)', entry)
        if match and match.group(1) in cited and url in entry:
            return True
    return False


def structure_checks(article: str) -> list[tuple[str, bool, str]]:
    labels = ['sec:introduction', 'sec:data', 'sec:methodology', 'sec:evaluation', 'sec:forecastvalidation', 'sec5']
    checks = [('label:' + label, has_label(article, label), label) for label in labels]
    checks += [
        ('six_section_order', in_order(article, *(r'\label{' + label + '}' for label in labels)), 'introduction/data/method/evaluation/results/discussion'),
        ('scoring_before_results', in_order(article, r'\label{sec:evaluation}', r'\label{sec:forecastvalidation}'), 'evaluation precedes results'),
        ('illustration_before_interpretation', in_order(article, r'\label{subsec:synthillustration}', r'\label{sec:interpretation}'), 'forecast illustration precedes historical interpretation'),
        ('appendix_matrix', in_order(article, r'\appendix', r'\label{app:stateconstruction}'), 'full matrix construction in appendix'),
        ('appendix_augmentation', in_order(article, r'\appendix', r'\label{app:augmentation}'), 'likelihood augmentation in appendix'),
        ('forecast_evidence', has_concepts(article, r'five', r'rolling.origin|forecast origins?', r'CRPS', r'quantile', r'illustrat'), 'five origins, distributional/quantile scores, illustrative forecast'),
    ]
    return checks


SCIENTIFIC_CONCEPTS = {
    'variants': (r'Gaussian', r'asymmetric Laplace', r'univariate', r'multivariate', r'transfer', r'nine', r'exAL.M.T1'),
    'scores': (r'CRPS', r'negatively oriented|lower.{0,70}better|smaller.{0,70}better', r'quantile', r'check loss'),
    'synthesis': (r'quantile.specific', r'predictive distribution', r'interpolat', r'point mass'),
    'origin_design': (r'five', r'rolling.origin|forecast origins?', r'low.flow', r'high.flow|winter', r'version', r'archiv'),
    'verification': (r'USGS', r'verification', r'forecast (?:window|horizon)|forecast.window'),
    'archive_work': (r'archiv', r'version', r'spatial', r'covariate', r'overlap'),
    'physical_models': (r'conceptual', r'physically based', r'calibrat', r'practical|operational'),
    'likelihood': (r'extended asymmetric laplace', r'quantile', r'scale', r'skewness'),
    'climate_covariates': (r'ERA5.Land', r'PRISM', r'climate.index', r'GDPC|generalized dynamic principal component', r'Big Trees'),
    'data_roles': (r'USGS', r'target', r'retrospective', r'discrepanc', r'forecast product', r'covariate'),
    'transfer_inputs': (r'precipitation', r'soil moisture|soil.moisture', r'climate.index', r'transfer'),
    'latest_issue': (r'latest|most recent', r'issu', r'daily', r'member', r'GloFAS', r'NWS'),
    'historical_interpretation': (r'historical', r'interpret', r'quantile', r'contrasting|dry|wet'),
    'table_estimands': (r'posterior means', r'posterior medians', r'credible intervals', r'skewness', r'scale parameters'),
    'uncertainty_estimands': (r'fitted quantile|quantile.location', r'credible', r'predictive distribution', r'predictive interval|predictive envelope'),
    'runtime': (r'(?:about|approximately|roughly) two hours', r'64', r'503', r'parallel', r'stag', r'hardware', r'implementation'),
    'prior_weighting': (r'epsilon', r'anchor|reference', r'scale', r'covariance', r'carries|carried|carry'),
}


def scientific_checks(article: str, names: list[str] | None = None) -> list[tuple[str, bool, str]]:
    return [(name, has_concepts(article, *SCIENTIFIC_CONCEPTS[name]), ', '.join(SCIENTIFIC_CONCEPTS[name]))
            for name in (names if names is not None else SCIENTIFIC_CONCEPTS)]
