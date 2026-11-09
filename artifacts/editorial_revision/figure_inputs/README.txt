Long-cycle component figure: retained numerical inputs
=====================================================

long_cycle_component.csv.gz contains the exact 35,088 displayed rows from the
previously retained component summary, including the original decimal strings,
row order and source-object identifiers. It selects component 6 under the
raw_state_component contract for q05, q50 and q95, then applies the same initial
history trim as the original plot. No fitted model object is needed for replay.
long_cycle_source.json records the full source-file hashes, selection, source
renderer and style hashes, and original figure hash.

Render the revised figure and manifest:
  python3 -B scripts/editorial_long_cycle_figure.py

Verify the tracked figure and manifest without changing either:
  python3 -B scripts/editorial_long_cycle_figure.py --check

If the retained full CSV is available, verify every selected source row too:
  python3 -B scripts/editorial_long_cycle_figure.py --check --verify-source /path/to/authoritative_component_summary.csv

The standalone R renderer first reconstructs the original panel. Its PNG must
have the exact original SHA256 before a revised result can be accepted. The
revised plot uses precisely the same source rows, plotted layers, coordinates,
limits, shading, colors, line widths, title and theme. The only changed plot
label is the y axis, from "State component (log1p_cms)" to
"Long-cycle component on log(1+discharge) scale". The new figure is written to
Figures/manuscript/editorial_long_cycle_component.png; the historical figure
and its associated files remain unchanged.

The figure manifest records rendering versions and checks of identical plotted
layer data and panel parameters. Exact PNG reproduction requires the recorded
rendering environment; a mismatch stops verification rather than silently
accepting different rendering.
