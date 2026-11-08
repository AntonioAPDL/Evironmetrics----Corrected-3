#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from article_repo_layout import APPENDIX_PANEL_FILENAMES, build_layout

FIGURE_ORDER = [
    ('usgs.png', 'A. USGS observations to cutoff'),
    ('precip_soilmoisture_climatePC1_faceted_labeled.png', 'B. PPT, SOIL, and 1st GDPC histories'),
    ('retrospective_log_discharge_plot_faceted.png', 'C. Retrospective support used by fit'),
    ('forecats.png', 'D. Forecast-product context'),
]

APPENDIX_ORDER = [
    '20210123_exal_m_t1',
    '20211112_exal_m_t1',
    '20211221_exal_m_t1',
    '20220511_exal_m_t1',
    '20221225_exal_m_t1',
]


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in ['DejaVuSans.ttf', 'Arial.ttf', 'LiberationSans-Regular.ttf']:
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _fit_image(im: Image.Image, max_w: int, max_h: int) -> Image.Image:
    w, h = im.size
    scale = min(max_w / w, max_h / h)
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return im.resize(new_size, Image.Resampling.LANCZOS)


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont) -> int:
    draw.text(xy, text, fill='black', font=font)
    bbox = draw.textbbox(xy, text, font=font)
    return bbox[3] - bbox[1]


def build_panel(cutoff_dir: Path, out_path: Path) -> dict[str, str]:
    meta = json.loads((cutoff_dir / 'metadata' / 'cutoff_entry.json').read_text())
    lines = (cutoff_dir / 'metadata' / 'support_window.yaml').read_text().splitlines()
    support_map = {}
    for line in lines:
        if ':' in line:
            k, v = line.split(':', 1)
            support_map[k.strip()] = v.strip().strip("'")

    panel_w = 1900
    panel_h = 1280
    outer_pad = 70
    gap = 50
    header_h = 210
    label_h = 70
    canvas_w = outer_pad * 2 + panel_w * 2 + gap
    canvas_h = outer_pad * 2 + header_h + label_h * 2 + panel_h * 2 + gap

    canvas = Image.new('RGB', (canvas_w, canvas_h), 'white')
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(62)
    subtitle_font = _load_font(34)
    label_font = _load_font(34)

    cutoff = meta['cutoff_date']
    title = f'exAL-M-T1 setup/support panel: cutoff {cutoff}'
    subtitle = (
        f"Bundle class: {meta['bundle_class']} | Requested history: {support_map.get('support_start','?')} to {support_map.get('support_end','?')} | "
        f"Retros available from: {support_map.get('retrospective_available_start','?')} | CRPS: {meta['published_crps']}"
    )
    _draw_text(draw, (outer_pad, outer_pad), title, title_font)
    _draw_text(draw, (outer_pad, outer_pad + 86), subtitle, subtitle_font)

    positions = [
        (outer_pad, outer_pad + header_h),
        (outer_pad + panel_w + gap, outer_pad + header_h),
        (outer_pad, outer_pad + header_h + label_h + panel_h + gap),
        (outer_pad + panel_w + gap, outer_pad + header_h + label_h + panel_h + gap),
    ]

    for (fig_name, label), (x, y) in zip(FIGURE_ORDER, positions):
        fig_path = cutoff_dir / 'figures' / fig_name
        im = Image.open(fig_path).convert('RGB')
        fitted = _fit_image(im, panel_w, panel_h)
        _draw_text(draw, (x, y), label, label_font)
        ix = x + (panel_w - fitted.size[0]) // 2
        iy = y + label_h + (panel_h - fitted.size[1]) // 2
        canvas.paste(fitted, (ix, iy))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return {
        'cutoff_dir': cutoff_dir.name,
        'cutoff_date': cutoff,
        'published_crps': str(meta['published_crps']),
        'bundle_class': meta['bundle_class'],
        'panel_path': str(out_path),
        'support_start': support_map.get('support_start', ''),
        'support_end': support_map.get('support_end', ''),
        'retrospective_available_start': support_map.get('retrospective_available_start', ''),
    }


def mirror_to_lowercase(article_root: Path, uppercase_dir: Path, rows: list[dict[str, str]]) -> None:
    lowercase_dir = article_root / 'figures' / uppercase_dir.name
    lowercase_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(path for path in uppercase_dir.iterdir() if path.is_file() and path.name != 'manifest.csv'):
        shutil.copy2(source, lowercase_dir / source.name)

    lower_rows = []
    for row in rows:
        lower = dict(row)
        panel_path = Path(lower['panel_path'])
        lower['panel_path'] = str(lowercase_dir / panel_path.name)
        lower_rows.append(lower)

    with (lowercase_dir / 'manifest.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(lower_rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(lower_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description='Build support-only composite panels for the five-cutoff setup/support figures.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    layout = build_layout(article_root)
    layout.ensure_base_dirs()
    src_root = layout.five_cutoff_setup_support_dir
    out_root = layout.appendix_cutoff_panels_dir
    out_root.mkdir(parents=True, exist_ok=True)

    rows = []
    for slug in APPENDIX_ORDER:
        cutoff_dir = src_root / slug
        if not cutoff_dir.exists():
            raise FileNotFoundError(f'Missing cutoff directory: {cutoff_dir}')
        out_path = out_root / APPENDIX_PANEL_FILENAMES[slug]
        rows.append(build_panel(cutoff_dir, out_path))

    with (out_root / 'manifest.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

    readme = [
        '# Appendix Cutoff Panels\n\n',
        'This figure family contains support-only composite setup/support panels for the five rolling-origin cutoffs used in the revised article workflow. They are retained for review and provenance, but the manuscript appendix now uses the cutoff-specific multivariate synthesis overlay figures.\n\n',
        'Each panel contains four subplots for one cutoff:\n',
        '- USGS observations to cutoff\n',
        '- PPT/SOIL/GDPC histories to cutoff\n',
        '- retrospective support used by fit\n',
        '- forecast-product context over the short forecast review window\n\n',
        'Canonical source family:\n',
        f'- `{layout.five_cutoff_setup_support_dir.relative_to(article_root)}/`\n\n',
        'Manifest:\n',
        '- `manifest.csv`\n',
    ]
    (out_root / 'README.md').write_text(''.join(readme))
    mirror_to_lowercase(article_root, out_root, rows)
    print(f'Built appendix cutoff panels in {out_root}')


if __name__ == '__main__':
    main()
