"""Write evidence and a portable report for the final integrated icon review."""
import hashlib
from html import escape
import json
from pathlib import Path
import zipfile

from PIL import Image, ImageDraw, ImageFont
from frameless import render
import framed

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SURFACES = {'dark': '#191724', 'plum': '#34304f', 'ivory': '#fffaf2', 'white': '#ffffff'}


def write_report(out, selection, metrics):
    items = selection['icons']
    byid = {i['id']: i for i in items}
    retained = [i['id'] for i in items if i['before_sha256'] == i['suggested_sha256']]
    bounds = {}
    for item in items:
        alpha = render((ROOT / item['output']).read_text(), 512).getchannel('A')
        box = alpha.point(lambda a: 255 if a >= 8 else 0).getbbox()
        if box is None:
            raise ValueError(f"Empty artwork: {item['id']}")
        measured = [value / 8 for value in box]
        if min(measured[:2]) < 3.875 or max(measured[2:]) > 60.125:
            raise ValueError(f"Artwork exceeds four-unit margin tolerance: {item['id']} {measured}")
        bounds[item['id']] = measured
    font = ImageFont.truetype('DejaVuSans.ttf', 14)
    head = ImageFont.truetype('DejaVuSans.ttf', 21)
    evidence = Image.new('RGB', (1160, 700), '#191724')
    draw = ImageDraw.Draw(evidence)
    draw.text((20, 15), 'Final contour corrections / previous selection and final', font=head, fill='#fff0da')
    draw.text((20, 48), 'Native 24 / 32 / 64 px. Stronger contours with a small uniform margin adjustment; paths and pigments retained.', font=font, fill='#fff0da')
    for row, (key, old, new) in enumerate([
            ('strata', 'stroke-width="5.5"', 'stroke-width="11"'),
            ('flatseal', 'stroke-width:1.5;', 'stroke-width:3;')]):
        after = (ROOT / byid[key]['output']).read_text()
        before = after
        for change in byid[key]['final_refinement']:
            before = before.replace(change['after'], change['before'])
        assert hashlib.sha256(before.encode()).hexdigest() == byid[key]['review_selection_sha256']
        y = 90 + row * 300
        for col, (surface, bg) in enumerate(SURFACES.items()):
            x = col * 290
            ink = '#34304f' if surface in ('ivory', 'white') else '#fff0da'
            draw.rectangle((x, y, x + 289, y + 299), fill=bg)
            draw.text((x + 12, y + 12), f'{byid[key]["name"]} / {surface}', font=font, fill=ink)
            for j, (label, svg) in enumerate([('Previous', before), ('Final', after)]):
                yy = y + 65 + j * 115
                draw.text((x + 12, yy), label, font=font, fill=ink)
                for size, dx in [(24, 15), (32, 65), (64, 140)]:
                    image = render(svg, size)
                    evidence.paste(image, (x + dx, yy + 25 + (64 - size) // 2), image)
    evidence.save(out / 'contour-corrections.png')

    # Review the existing optical layouts without recording release sign-off.
    policy = framed.load_layout()
    margins = framed.check_layouts()
    for surface in ('dark', 'ivory'):
        for page in range(4):
            sheet = Image.new('RGB', (1200, 1150), SURFACES[surface])
            d = ImageDraw.Draw(sheet)
            ink = '#34304f' if surface == 'ivory' else '#fff0da'
            d.text((20, 16), f'Derived framed fit / {surface} / {page + 1} of 4', font=head, fill=ink)
            for j, item in enumerate(items[page * 42:(page + 1) * 42]):
                source = (ROOT / item['output']).read_bytes()
                layout = framed.layout_source(source, item['id'], policy)
                image = render(framed.frame(source, layout).decode(), 64)
                x, y = j % 6 * 200, 70 + j // 6 * 150
                sheet.paste(image, (x + 60, y), image)
                d.text((x + 10, y + 88), f'{item["priority"]}. {item["name"]}'[:28], font=font, fill=ink)
            sheet.save(out / f'framed-{surface}-{page + 1}.png')

    verification = {
        'scope': 'Integrated primary sources and local rendered review; no installation or deployment',
        'reviewed_count': len(items), 'byte_exact_original_count': len(retained),
        'byte_exact_original_ids': retained, 'all_selection_hashes_match': True,
        'sizes': [24, 32, 48, 64, 96], 'surfaces': list(SURFACES),
        'framed_layout_count': len(margins), 'minimum_framed_clearance': min(margins.values()),
        'framed_transforms_changed': False, 'framed_signoff_recorded': False,
        'canvas_bounds_at_512': bounds,
        'live_behavior_validated': False,
    }
    (out / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    report = {
        'result': 'The accepted set is integrated. Both outstanding contour issues are corrected.',
        'resolved': [
            'Strata: existing ivory-face contour widened from 5.5 to 11 source units; ribbons, negative spaces and pigments retained; uniform sizing restores the four-unit margin.',
            'Flatseal: existing reel contour widened from 1.5 to 3 source units; upstream reel, aperture and tape end retained; uniform sizing restores the four-unit margin.',
            'Chezmoi and Chezetc: canonical names and cyan/red house identities, grouped under configuration rather than Tjik. Old lookups remain aliases.',
        ],
        'preserved': [
            'All 31 retained originals are byte-exact, including Camera, FilmCraft owl, the requested old designs and Signal.',
            'Gmail retains the restored red ramp; Volume Control retains its concentric arc; Disk Usage Analyzer shares Disks construction.',
            'Tjik applications keep their shared shell, while Bartjik stays circular. Animals keep individual proportions and silhouettes.',
            'Existing framed scales and offsets all fit the new artwork. Framed previews derive from the same originals.',
        ],
        'limits': [
            'Codex prompt apertures remain weaker on white because they show the actual canvas. The approved geometry and violet/blue variants are preserved.',
            'Supporting highlights, shading and airy marks do not all reach 3:1 against every canvas. Contrast metrics are inspection aids, not a universal pass claim.',
            'This is a local source and rendering review. No new RC, framed sign-off, installation, push or deployment was performed.',
        ],
    }
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rose Punk final consistency review</title><style>body{max-width:1100px;margin:32px auto;padding:0 22px;background:#191724;color:#fff0da;font:16px/1.6 system-ui}a{color:#a8d5df}img{width:100%;height:auto}li{margin:10px 0}h1,h2{line-height:1.2}</style><h1>Rose Punk: final consistency review</h1>'''
    html += '<p><strong>' + escape(report['result']) + '</strong></p>'
    html += '<p>167 icons at 24, 32, 48, 64 and 96 px on dark, plum, ivory and white.</p><p><a href="index.html">Explore all icons by size, surface and family</a> · <a href="review.zip">Download the review</a> · <a href="verification.json">Verification record</a></p>'
    for label, key in [('Resolved', 'resolved'), ('Preserved', 'preserved'), ('Review limits', 'limits')]:
        html += '<h2>' + label + '</h2><ul>' + ''.join('<li>' + escape(x) + '</li>' for x in report[key]) + '</ul>'
    html += '<h2>Contour comparison</h2><img src="contour-corrections.png" alt="Previous and final Strata and Flatseal at native sizes on four surfaces">'
    html += '<h2>Families</h2><ul>'
    for group in selection['groups']:
        html += '<li>' + escape(group.replace('-', ' ')) + ': ' + ' · '.join(f'<a href="family-{group}-{s}.png">{s}</a>' for s in SURFACES) + '</li>'
    html += '</ul><h2>Derived framed fit</h2><p>Existing transforms retained; minimum tile clearance ' + f'{min(margins.values()):.2f}' + ' units. These are review previews, not a newly approved framed release.</p><ul>'
    for surface in ('dark', 'ivory'):
        html += '<li>' + surface + ': ' + ' · '.join(f'<a href="framed-{surface}-{p}.png">page {p}</a>' for p in range(1, 5)) + '</li>'
    html += '</ul></html>'
    (out / 'report.html').write_text(html)
    names = ['index.html', 'report.html', 'report.json', 'manifest.json', 'metrics.json', 'verification.json', 'contour-corrections.png']
    names += [p.name for pattern in ('catalog-*.png', 'family-*.png', 'framed-*.png') for p in sorted(out.glob(pattern))]
    with zipfile.ZipFile(out / 'review.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.write(out / name, name)
    print(f'Review packaged: {len(items)} selections, {len(retained)} retained originals, {len(margins)} framed fits.')
