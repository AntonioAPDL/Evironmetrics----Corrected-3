# Software Availability Artifact

This directory contains the compact software availability manifest used by the
revised article and corrections response.

The manifest is intentionally small. It records public software locations,
archive status, and validation policy. It does not contain runtime outputs,
large support data, `.RData` files, or self-referential commit pins.

Current manifest:

- `software_availability_manifest.json`

The workflow-side validators emit current local commit metadata at validation
time, so this tracked article-side manifest does not become stale whenever it is
committed.
