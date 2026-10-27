#!/usr/bin/env python3
"""Build the editable Rose Punk application icon collection and review sheet."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
# Artwork is drawn on a 64-unit grid. Keep marks inside the 14..50 safe area.
ART = {
'zapzap': ('ZapZap', '<path d="M48 30a16 16 0 0 1-23 15l-10 4 3-10a16 16 0 1 1 30-9Z"/><path class="detail" d="m25 22 13 0-12 17h14"/>'),
'files': ('Files', '<path d="M13 24v-5a3 3 0 0 1 3-3h11l5 6h16a3 3 0 0 1 3 3v20a3 3 0 0 1-3 3H16a3 3 0 0 1-3-3Z"/><path class="detail" d="M14 28h36"/>'),
'codex-lb': ('Codex LB', '<path d="m23 21-11 11 11 11m18-22 11 11-11 11"/><path class="detail" d="M29 42V30m6 12V23"/><circle cx="29" cy="23" r="1" class="dot"/>'),
'chrome': ('Chrome', '<circle cx="32" cy="32" r="19"/><circle class="detail" cx="32" cy="32" r="8"/><path d="M32 24h17M25 36l-8-15m19 18-8 12"/>'),
'sublime-text': ('Sublime Text', '<path d="m45 16-26 9v9l26-9Zm0 18-26-9m0 14 26-9v9l-26 9Z"/><path class="detail" d="m21 27 22 9"/>'),
'mullvad': ('Mullvad VPN', '<path d="M15 30q0-13 16-13 17 0 18 16l-8 2-3 9-14 3-8-9Z"/><path class="detail" d="m17 30 14 5 12-7m-17 7-4 7m10-7-2 10"/><circle cx="37" cy="24" r="1.7" class="dot"/><path d="m45 33 6-1"/>'),
'signal': ('Signal', '<circle cx="32" cy="30" r="19" stroke-dasharray="3 5"/><path class="detail" d="M44 30a12 12 0 0 1-17 11l-7 4 2-8a12 12 0 1 1 22-7Z"/>'),
 'telegram': ('Telegram', '<path d="m12 29 39-15-8 36-13-12-8 7 1-12Z"/><path class="detail" d="m23 33 20-12-13 17"/>'),
'spotify': ('Spotify', '<circle cx="32" cy="32" r="20"/><path class="detail" d="M20 25q14-5 26 2M22 33q11-4 21 2M24 41q8-3 16 1"/>'),
'chatgpt': ('ChatGPT', '<g transform="translate(32 32)">'+''.join(f'<path transform="rotate({a})" d="M0-6-8-11q-9-1-11 7-1 5 3 9l8 5 8-4Z"/>' for a in range(0,360,60))+'</g>'),
'zen': ('Zen Browser', '<circle cx="32" cy="32" r="19"/><path class="detail" d="M22 23h20L22 41h20"/><path d="M18 18 15 15m34 34-3-3"/>'),
'kitty': ('Kitty', '<path d="M17 31V15l12 8h7l12-8v18q0 17-16 17T17 31Z"/><path class="detail" d="m23 31 5 4-5 4m11 0h7"/>'),
'zed': ('Zed', '<path d="M17 16h30L19 45h28M17 23h18L17 42"/><path class="detail" d="m45 24-17 18"/>'),
'brave': ('Brave', '<path d="m19 17 5-4h16l5 4 5 12-6 16-12 7-12-7-6-16Z"/><path class="detail" d="m22 24 4 6-4 6 10 9 10-9-4-6 4-6m-16 6h12m-9 7h6"/>'),
'firefox': ('Firefox', '<path d="M43 16q12 9 7 24T24 49Q8 43 14 27l4 5 2-15 10 9q-10 1-8 10t15 6q9-6 2-15l-5-1 10-13Z"/><path class="detail" d="M30 31q7-2 10 3m-19 6q4 11 17 5"/>'),
'datagrip': ('DataGrip', '<ellipse cx="32" cy="19" rx="17" ry="7"/><path d="M15 19v25c0 10 34 10 34 0V19"/><path class="detail" d="M15 31c0 9 34 9 34 0m-25 9h7m5 0h4"/>'),
'drizzle': ('Drizzle Studio', '<path d="m23 14-9 18m23-18-9 18m23-18-9 18"/><path class="detail" d="m23 37-6 12m20-12-6 12m20-12-6 12"/>'),
'obsidian': ('Obsidian', '<path d="m32 11 16 12-4 24-18 6-13-17 9-20Z"/><path class="detail" d="m22 16 4 37 10-22-4-20m4 20 12-8m-12 8 8 16"/>'),
'steam': ('Steam', '<circle cx="42" cy="22" r="10"/><circle class="detail" cx="42" cy="22" r="5"/><circle cx="22" cy="42" r="8"/><path d="m17 37-7-3m14 0 9-13m-3 22 13-11"/><path class="detail" d="m11 41 10 5q5 0 5-4"/>'),
'vlc': ('VLC', '<path d="m29 13-12 35h30L35 13Zm-16 35-3 6h44l-3-6"/><path class="detail" d="M25 24h14m-18 12h22"/>'),
'discord': ('Discord', '<path d="m21 19 7-2 2 4h4l2-4 7 2q8 12 8 24l-11 5-3-5H27l-3 5-11-5q0-12 8-24Z"/><path class="detail" d="M23 26q9-4 18 0m-18 14q9 4 18 0"/><ellipse cx="25" cy="33" rx="2" ry="3" class="dot"/><ellipse cx="39" cy="33" rx="2" ry="3" class="dot"/>'),
 'thunderbird': ('Thunderbird', '<path d="M49 24q-3-14-20-11T12 33q0 20 23 19l-8-5q18 0 23-14l-9 4 5-8-12 2Z"/><path class="detail" d="M18 29h25v16H18Zm0 0 12 10 13-10"/>'),
'gimp': ('GIMP', '<path d="m14 23 9 3 13-5 13-2-2 19q-6 12-22 8L13 38Z"/><path class="detail" d="m22 37 15 3 12-11m-9 15 8 7 4-4-8-7"/><circle cx="27" cy="29" r="2" class="dot"/><circle cx="39" cy="27" r="3" class="dot"/>'),
'settings': ('Settings', '<path d="m27 12 10 0 2 7 6 3 7-1 4 9-5 5v7l-9 6-6-4h-7l-6 4-9-6v-7l-5-5 4-9 7 1 6-3Z" transform="translate(1 2) scale(.94)"/><circle class="detail" cx="32" cy="32" r="8"/>'),
'transmission': ('Transmission', '<path d="M17 46h30v6H17Z M20 42V13m-8 9 8-9 8 9M44 13v29m-8-9 8 9 8-9"/><path class="detail" d="M17 48h30"/>'),
}
STYLE='<style>.detail{stroke:#c4b5db}.dot{fill:#e56ea1;stroke:none}</style>'
def icon(mark):
 return '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'+STYLE+'<rect x="3" y="3" width="58" height="58" rx="17" fill="#232032"/><path d="M17 4h30" stroke="#e56ea1" stroke-opacity=".28" stroke-width="1"/><g fill="none" stroke="#e56ea1" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'+mark+'</g></svg>\n'

def main():
 from review_paths import prepare_review
 prepare_review(ROOT)
 DEST.mkdir(parents=True,exist_ok=True)
 for key,(name,mark) in ART.items():
  (DEST/f'{key}.svg').write_text(icon(mark))
 rows=[]
 for i,(key,(name,mark)) in enumerate(ART.items()):
  x=32+(i%5)*196;y=136+(i//5)*158
  rows.append(f'<g transform="translate({x+50} {y}) scale(1.5)">'+icon(mark).split('>',1)[1].rsplit('</svg>',1)[0]+'</g>')
  rows.append(f'<text x="{x+98}" y="{y+122}" text-anchor="middle" fill="#e5e5e5" font-size="16">{name}</text>')
 sheet='<svg xmlns="http://www.w3.org/2000/svg" width="1044" height="970" viewBox="0 0 1044 970"><rect width="1044" height="970" fill="#191724"/><g font-family="sans-serif"><text x="32" y="56" fill="#e56ea1" font-size="30">ROSE PUNK / APPLICATIONS</text><text x="32" y="90" fill="#c4b5db" font-size="15">01 — Local review · 25 marks · SVG originals · 64 px grid</text>'+''.join(rows)+'</g></svg>'
 (ROOT / '.local/icon-reviews/docs/rose-punk-icons-preview.svg').write_text(sheet)

if __name__=='__main__':main()
