# Software Availability Contract

Date: 2026-08-12

This document records the manuscript-side HE-5 reproducibility contract. The
companion machine-readable manifest is:

- `artifacts/software_availability/software_availability_manifest.json`

## Contract

The revised article uses a three-layer reproducibility model:

1. The reusable exDQLM estimation routines are available through the CRAN
   package `exdqlm`; the accompanying software paper is cited in the
   manuscript.
2. The study-specific forecasting workflow is available through the clean
   public reproducibility repository
   `https://github.com/AntonioAPDL/san-lorenzo-exdqlm-reproducibility`.
3. This article repository freezes manuscript-facing figures, tables, generated
   TeX fragments, and compact provenance artifacts.

The article repository is not meant to carry large runtime outputs or all raw
forecast archives. Applying the workflow to a new basin requires staging the
corresponding observations, current forecast products, and covariates.
Reproducing the retrospective validation design additionally requires a
basin-specific, version-consistent archive that aligns historical observations,
retrospective products, issued forecast products, forecast-window covariates,
product versions, spatial extraction rules, and source-specific forecast
horizons.

## Current Public Software Status

- CRAN package: `https://CRAN.R-project.org/package=exdqlm`
- Verified CRAN version for this contract: `1.1.0`
- Verified CRAN publication date for this contract: `2026-07-09`
- Package DOI: `https://doi.org/10.32614/CRAN.package.exdqlm`
- Software paper: `https://arxiv.org/abs/2607.22760`
- Software paper DOI: `https://doi.org/10.48550/arXiv.2607.22760`
- Public reproducibility repository:
  `https://github.com/AntonioAPDL/san-lorenzo-exdqlm-reproducibility`
- Reproducibility archive DOI: pending final revision freeze

The public reproducibility repository carries the reader-facing files and
validation entrypoint that will support the final archived release:

- `README.md`
- `CITATION.cff`
- `LICENSE`
- `scripts/validate_public_repository.py`

These files document the current public repository state and the remaining final
archive steps. They do not replace the final archive DOI, which remains pending.

## Validation

The workflow repository validates this contract through:

- `scripts/validate_publication_freeze.py`
- `scripts/validate_revision_cross_repo_wiring.py`

Those validators check the article manuscript, corrections response, and
software availability manifest together.
