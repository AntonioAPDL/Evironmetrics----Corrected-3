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


DOCUMENT_ENTRIES = {'main': 'wileyNJD-APA.tex'}
INCLUDE_RE = re.compile(r'\\(?:input|include)\s*\{([^}]+)\}')
APPENDIX_BOUNDARY_RE = re.compile(r'\\(begin|end)\s*\{appendix\}')


def expanded_tex_segments(article_root: Path, entry: str = 'wileyNJD-APA.tex') -> list[tuple[Path, str]]:
    """Expand includes in reading order, preserving source ownership and repeats.

    Repeated includes remain visible to duplicate-label checks. Cycles are
    rejected rather than silently truncated; comments cannot introduce inputs.
    """
    root = Path(article_root).resolve()
    segments: list[tuple[Path, str]] = []

    def visit(path: Path, parents: tuple[Path, ...]) -> None:
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ValueError('Manuscript include escapes article root')
        if path in parents:
            raise ValueError('Cyclic manuscript include: ' + str(path.relative_to(root)))
        if not path.is_file():
            raise FileNotFoundError(f'Missing manuscript include: {path.relative_to(root)}')
        text = active_tex(path.read_text(encoding='utf-8'))
        start = 0
        for match in INCLUDE_RE.finditer(text):
            segments.append((path, text[start:match.start()]))
            child = root / match.group(1)
            if not child.suffix:
                child = child.with_suffix('.tex')
            visit(child, parents + (path,))
            start = match.end()
        segments.append((path, text[start:]))

    visit(root / entry, ())
    return segments


def publication_segments(article_root: Path) -> list[tuple[Path, str, str]]:
    """Assign actual expanded content to the main body or native Wiley appendix."""
    result: list[tuple[Path, str, str]] = []
    scope, begins, ends = 'main', 0, 0
    for path, text in expanded_tex_segments(article_root):
        start = 0
        for match in APPENDIX_BOUNDARY_RE.finditer(text):
            result.append((path, text[start:match.start()], scope))
            if match.group(1) == 'begin':
                begins += 1
                if scope != 'main' or begins != 1 or ends:
                    raise ValueError('Article must have exactly one ordered appendix environment')
                scope = 'appendix'
            else:
                ends += 1
                if scope != 'appendix' or ends != 1:
                    raise ValueError('Article must have exactly one ordered appendix environment')
                scope = 'main'
            result.append((path, match.group(), scope))
            start = match.end()
        result.append((path, text[start:], scope))
    if begins != 1 or ends != 1 or scope != 'main':
        raise ValueError('Article must have exactly one ordered appendix environment')
    return result


def manuscript_with_includes(article_root: Path, entry: str = 'wileyNJD-APA.tex') -> str:
    """Read the actual include graph in order; unused files cannot satisfy it."""
    return '\n'.join(text for _, text in expanded_tex_segments(article_root, entry))


def document_texts(article_root: Path) -> dict[str, str]:
    """Return the single submitted document, including its integrated appendices."""
    return {'main': manuscript_with_includes(article_root)}


def publication_with_includes(article_root: Path) -> str:
    """Read the one submitted article, never arbitrary repository fragments."""
    return manuscript_with_includes(article_root)


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


def structure_checks(article: str, appendix: str | None = None) -> list[tuple[str, bool, str]]:
    labels = ['sec:introduction', 'sec:data', 'sec:methodology', 'sec:evaluation', 'sec:forecastvalidation', 'sec5']
    checks = [('label:' + label, has_label(article, label), label) for label in labels]
    checks += [
        ('six_section_order', in_order(article, *(r'\label{' + label + '}' for label in labels)), 'introduction/data/method/evaluation/results/discussion'),
        ('scoring_before_results', in_order(article, r'\label{sec:evaluation}', r'\label{sec:forecastvalidation}'), 'evaluation precedes results'),
        ('forecast_evidence', has_concepts(article, r'five', r'rolling.origin|forecast origins?', r'CRPS', r'quantile', r'illustrat'), 'five origins, distributional/quantile scores, illustrative forecast'),
    ]
    if appendix is not None:
        checks += [(name, has_label(appendix, label), label)
                   for name, label in [('appendix_matrix', 'app:stateconstruction'),
                                       ('appendix_augmentation', 'app:augmentation')]]
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


def publication_views(article_root: Path) -> dict[str, str]:
    """Separate logical body/appendix obligations within the one reading graph."""
    segments = publication_segments(article_root)
    main = '\n'.join(text for _, text, scope in segments if scope == 'main')
    appendix = '\n'.join(text for _, text, scope in segments if scope == 'appendix')
    return {'main': main, 'appendix': appendix,
            'union': '\n'.join(text for _, text, _ in segments)}


def publication_checks(article_root: Path) -> list[tuple[str, bool, str]]:
    """Check exposition and retained appendix details in their actual scopes."""
    views = publication_views(article_root)
    return publication_text_checks(views['main'], views['appendix'])


def publication_text_checks(main: str, appendix: str) -> list[tuple[str, bool, str]]:
    """Keep body exposition and appendix retention separately testable."""
    views = {'main': main, 'appendix': appendix, 'union': main + '\n' + appendix}
    checks = structure_checks(views['main'], views['appendix'])
    main_names = ['variants', 'scores', 'synthesis', 'origin_design', 'verification',
                  'likelihood', 'climate_covariates', 'data_roles', 'transfer_inputs',
                  'latest_issue', 'uncertainty_estimands', 'prior_weighting']
    checks += [('main:' + name, ok, detail)
               for name, ok, detail in scientific_checks(views['main'], main_names)]
    checks += [('package:' + name, ok, detail)
               for name, ok, detail in scientific_checks(views['union'],
                                                       ['runtime', 'archive_work', 'physical_models'])]
    checks += [('appendix:coefficient_estimands',
                has_concepts(views['appendix'], r'posterior means', r'credible intervals', r'covariate'),
                'posterior means and credible intervals for covariate coefficients'),
               ('appendix:gig_convention', has_concepts(views['appendix'], r'generalized inverse.gaussian', r'GIG'),
                'explicit generalized inverse-Gaussian convention'),
               ('appendix:vb_computation', has_concepts(views['appendix'], r'variational', r'converg', r'Laplace', r'Delta'),
                'variational updates, convergence and joint Laplace–Delta approximation')]
    return checks
