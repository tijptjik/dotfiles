"""Authored object details for the camera-led illustrated pass.

All coordinates are on the shared 64 px canvas. Texture follows material:
perforated rubber, stitched covers, folded paper, machined rings and glass.
"""
import math


def path(d, fill='none', stroke=None, width=1, **attrs):
    if stroke:
        attrs.update(stroke=stroke, **{'stroke-width': width})
    return '<path d="' + d + '" fill="' + fill + '" ' + ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()) + '/>'


def rect(x, y, w, h, fill, radius=0, **attrs):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" ' + ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()) + '/>'


def circle(x, y, r, fill, **attrs):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" ' + ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()) + '/>'


def line(d, color='#fff0d9', width=.7, opacity=.65):
    return path(d, stroke=color, width=width, opacity=opacity)


def dots(x, y, cols, rows, spacing=2, color='#38263f'):
    return '<g opacity=".27">' + ''.join(circle(x + col * spacing, y + row * spacing, .36, color) for col in range(cols) for row in range(rows)) + '</g>'


def lens(x, y, r):
    return (circle(x, y, r, '#29273e', stroke='#e8b2c4', stroke_width=.9)
            + circle(x, y, r - 1.5, 'url(#glass)', stroke='#171e36', stroke_width=.7)
            + circle(x, y, r * .46, '#819de1', opacity='.65')
            + circle(x - r * .28, y - r * .3, r * .22, '#f7dddf', opacity='.7')
            + circle(x + r * .34, y + r * .4, r * .12, '#a9ede1', opacity='.7')
            + path(f'M{x-r*.72} {y+r*.08}a{r*.75} {r*.75} 0 0 0 {r*.83} {r*.64}', stroke='#79bbdb', width=.6, opacity='.75'))


DEFS = '''<defs>
<linearGradient id="copper" x2=".2" y2="1"><stop stop-color="#ffe0a3"/><stop offset=".35" stop-color="#e6ae62"/><stop offset="1" stop-color="#a7585d"/></linearGradient>
<linearGradient id="jade" x2=".3" y2="1"><stop stop-color="#b4ead5"/><stop offset=".4" stop-color="#46b6a2"/><stop offset="1" stop-color="#306779"/></linearGradient>
<linearGradient id="rose-metal" x2=".3" y2="1"><stop stop-color="#f8c5c2"/><stop offset=".35" stop-color="#df77ac"/><stop offset="1" stop-color="#8e477e"/></linearGradient>
<linearGradient id="indigo" x2=".4" y2="1"><stop stop-color="#b6b5ec"/><stop offset=".4" stop-color="#8596ed"/><stop offset="1" stop-color="#494f85"/></linearGradient>
<linearGradient id="paper" x2=".2" y2="1"><stop stop-color="#fff4df"/><stop offset="1" stop-color="#d8c5b9"/></linearGradient>
<linearGradient id="metal" x2=".8" y2="1"><stop stop-color="#f3e8df"/><stop offset=".35" stop-color="#9cb9c6"/><stop offset=".5" stop-color="#d5dcde"/><stop offset="1" stop-color="#61788f"/></linearGradient>
<radialGradient id="glass" cx=".35" cy=".27" r=".8"><stop stop-color="#b0a5df"/><stop offset=".4" stop-color="#5b70b5"/><stop offset=".75" stop-color="#35446d"/><stop offset="1" stop-color="#172b41"/></radialGradient>
<linearGradient id="screen" x2=".6" y2="1"><stop stop-color="#354b67"/><stop offset=".5" stop-color="#232c46"/><stop offset="1" stop-color="#182339"/></linearGradient>
</defs>'''

# Complete object illustrations where the former glyph did not contain enough
# structure to support a material finish.
ART = {}
ART['files'] = (path('M11 22v-5q0-3 3-3h14l5 6h16q4 0 4 4v24H11Z', 'url(#copper)')
    + rect(15, 22, 33, 24, 'url(#paper)', 1)
    + path('M10 27h44l-3 22q-.4 3-4 3H16q-4 0-4.5-4Z', 'url(#copper)')
    + line('M12 28h40') + line('M15 49h33', '#743e59', .8, .5)
    + rect(17, 33, 15, 4, '#f4dfb7', 1) + dots(40, 42, 4, 3))
ART['obsidian'] = (path('m32 10 15 12-3 25-18 7-13-18 9-20Z', '#4a3c76')
    + path('m32 10 4 20-10 24-4-38Z', 'url(#rose-metal)')
    + path('m32 10 15 12-11 8Z', '#c2a8e5')
    + path('m36 30 11-8-3 25-18 7Z', 'url(#indigo)')
    + path('m22 16 4 38-13-18Z', '#7465ac')
    + line('m22 16 4 36 10-22-4-19', '#ead3ef', .65, .55)
    + line('m37 33 5 10', '#c6dcf0', .65, .5))
ART['vlc'] = (path('m16 47-6 6q22 5 44 0l-6-6Z', 'url(#copper)')
    + path('m29 12-12 36q15 6 30 0L35 12q-3-2-6 0Z', 'url(#copper)')
    + path('m26 22-3 8q9 3 18 0l-3-8q-6 2-12 0Zm-6 17-3 9q15 6 30 0l-3-9q-12 4-24 0Z', 'url(#paper)')
    + line('m30 15-9 29', '#fff0d9', .8, .7) + line('M13 53q19 4 38 0', '#f4be82'))
ART['monochrome-music'] = (path('M13 36v-8a19 19 0 0 1 38 0v8', stroke='#b177a9', width=6)
    + path('M13 30v-3a19 19 0 0 1 38 0v3', stroke='#ecc1d4', width=1)
    + rect(10, 30, 11, 22, 'url(#rose-metal)', 5) + rect(43, 30, 11, 22, 'url(#rose-metal)', 5)
    + rect(17, 32, 5, 18, '#383149', 2) + rect(42, 32, 5, 18, '#383149', 2)
    + dots(13, 35, 2, 7) + dots(50, 35, 1, 7)
    + path('M29 28v15m6-19v19', stroke='#e0c7e6', width=2.7))
ART['disks'] = (rect(13, 10, 38, 44, 'url(#metal)', 4)
    + rect(16, 13, 32, 36, '#384158', 2)
    + circle(31, 30, 13, 'url(#metal)', stroke='#bbc7d6', stroke_width='.5')
    + circle(31, 30, 10.7, 'none', stroke='#6f809b', stroke_width='.6')
    + circle(31, 30, 6.8, 'none', stroke='#e0d4e4', stroke_width='.55')
    + circle(31, 30, 3, 'url(#glass)')
    + path('m45 18-3 19-9-6 2-3 5 2 2-13Z', 'url(#copper)', '#38344b', .6)
    + circle(43, 18, 2, '#dbbf9d') + rect(20, 50, 22, 2, '#4d5c72', .5)
    + ''.join(circle(x, y, .8, '#e8e5df') + line(f'M{x-.35} {y}h.7', '#657285', .5) for x,y in [(16,13),(48,13),(16,51),(48,51)]))
ART['cheese'] = (path('M13 21h10l5-7h12l5 7h5q5 0 5 5v22q0 5-5 5H13q-5 0-5-5V26q0-5 5-5Z', 'url(#copper)')
    + path('M9 27h12v21H9Z', '#bd825c') + dots(11,29,4,9,2)
    + rect(29, 16, 10, 3, '#594255', 1) + line('M25 21h21')
    + lens(35, 36, 12) + rect(47, 24, 5, 3, 'url(#paper)', 1)
    + circle(16, 25, 2, '#d06879') + line('M24 49h25', '#ffdb91', .8))
ART['bottles'] = ''
for x,y,color in [(10,19,'indigo'),(26,13,'jade'),(43,21,'rose-metal')]:
    ART['bottles'] += (rect(x+3,y-5,8,6,'url(#metal)',1)
        + path(f'M{x+3} {y}h8v6q4 3 4 8v21H{x-1}V{y+14}q0-5 4-8Z',f'url(#{color})')
        + rect(x+1,y+18,12,10,'url(#paper)',1)
        + line(f'M{x+2} {y+15}v-2q0-3 3-5v-5', '#edfff2', .9, .65)
        + line(f'M{x+3} {y+21}h8m-8 3h5','#7a7286',.55,.8)
        + line(f'M{x+2} {y+32}h10','#c4e0de',.6,.5))
ART['software'] = (path('M13 24h38l3 26q0 4-4 4H14q-4 0-4-4Z','url(#rose-metal)')
    + path('M23 26v-8a9 9 0 0 1 18 0v8', stroke='#e8c5bf', width=3)
    + line('M24 21v-3a8 8 0 0 1 16 0', '#fff0da', .7)
    + line('M14 29 13 49h38l-1-20','#f7c0ce',.65,.6)
    + ''.join(rect(x,y,5,5,'url(#paper)',.8) for x in (24,35) for y in (33,43))
    + path('m48 31 3 20-5-2Z','#843d6c',opacity='.4'))
ART['snapraid'] = ''
for y in (13,34):
    ART['snapraid'] += (rect(11,y,42,18,'url(#metal)',3) + rect(14,y+3,36,11,'url(#screen)',2)
        + circle(19,y+8,2,'#73d3b8') + circle(18.5,y+7.4,.65,'#e7f4cf')
        + ''.join(line(f'M{x} {y+6}v4','#9baec7',.75,.8) for x in range(31,46,3))
        + line(f'M15 {y+16}h34','#d7e4df',.6,.5))
ART['llmtrim'] = (path('m27 27 24 22q2-8-5-14L29 23Z','url(#metal)', '#647895', 1.1)
    + path('m27 36 23-23q2 8-5 14L30 39Z','url(#metal)', '#647895', 1.1)
    + circle(20,22,8,'url(#copper)') + circle(20,42,8,'url(#copper)')
    + circle(20,22,4.4,'#26233a') + circle(20,42,4.4,'#26233a')
    + circle(31,32,2.4,'url(#rose-metal)') + line('m30 33 2-2','#fff0d9',.7))
ART['tippecanoe'] = (path('m10 17 14-5 16 5 14-5v35l-14 5-16-5-14 5Z','url(#jade)')
    + path('m24 12 16 5v35l-16-5Z','url(#paper)')
    + line('M24 13v33m16-28v33','#f9efce',.8)
    + path('m12 37 12-8 16 7 12-10',stroke='#c58c66',width=2)
    + path('m13 25 10-4m4 19 9 3m8-3 7-3',stroke='#618f91',width=.8)
    + path('M13 45q4-6 8-3m23-20 6-2',stroke='#d4f0ca',width=1.3))
ART['gpu-screen-recorder'] = (rect(10,13,44,33,'url(#metal)',4) + rect(13,16,38,26,'url(#screen)',2)
    + path('M28 46v6h-7v2h22v-2h-7v-6Z','url(#metal)')
    + rect(19,23,14,12,'url(#jade)',2) + rect(22,26,8,6,'#354460',1)
    + circle(43,24,4,'url(#rose-metal)') + circle(42,23,1,'#f8d4c3')
    + line('M17 19h20','#c4dee2',.6,.35))
ART['uuctl'] = (rect(11,12,42,36,'url(#metal)',3)+rect(14,15,36,29,'url(#screen)',2)
    + path('m21 23 7 7-7 7m13 0h9',stroke='#a2dedb',width=2.8)
    + path('M27 48v4h-6v2h22v-2h-6v-4Z','url(#metal)')
    + line('M17 18h16','#dbf2ec',.6,.3))
# Authored overlays for retained geometry, kept subtle at launcher sizes.
DETAILS = {
 'calendar': line('M14 47h34m-33 3h33','#9d8093',.55,.65)+dots(15,14,17,2,2,'#783e64'),
 'contacts': line('M19 14h26v35H19Z','#dae0f4',.6,.4)+line('M20 14v35','#363350',.8,.5),
 'fonts': line('M16 16h32M16 17v30','#eadbd9',.7,.65)+line('M17 49h30','#353452',.7,.5),
 'bluetooth-adapters': line('M21 24v23q0 4 4 4h15','#c2efe1',.6,.6)+dots(39,24,2,8),
 'bluetooth-manager': line('M18 28q0-13 13-14','#c0efde',.9,.7)+line('M19 44q8 11 21 5','#254e65',.8,.55),
 'file-roller': line('M13 27v22h12m14 0h11V27','#c3d3f4',.65,.5)+dots(14,30,5,7)+dots(40,30,5,7)+rect(30,45,4,3,'#6c6b83',.5),
 'document-scanner': line('M17 14h29','#d9f3e0',.8,.6)+line('M18 40h28','#73d3b8',1,.7)+dots(17,48,8,2,1.4),
 'connections': path('m12 15 19 0-19 16Z','#c6e6f2',opacity='.16')+path('m29 33h17L29 48Z','#d3f2de',opacity='.18'),
 'scrcpy': path('m39 17h10L39 36Z','#cce7f6',opacity='.24')+line('M40 12h8','#526880',.7,.7),
 'system-monitor': ''.join(line(f'M16 {y}h32','#92a6c3',.5,.12) for y in (20,26,32,38))+line('M15 15h34','#dce0ef',.65,.5),
 'simplescreenrecorder': path('m16 19h22L16 36Z','#acc9dd',opacity='.13')+circle(30,27,1.6,'#f5c4c8',opacity='.65'),
 'video-player': line('M14 26v20q0 2 3 2h30','#cbd4f2',.7,.5)+dots(16,30,2,8),
 'passwords-and-keys': line('M15 22v24h34','#d0c8ef',.65,.5)+rect(34,24,12,5,'#403957',1)+dots(35,25,5,2,2,'#b5a7d4'),
 'weather': path('M17 33q-6 1-5 6m9-10q3-8 11-5',stroke='#fff5d8',width=1.2,opacity='.7')+line('M21 46h22','#899bc1',.7,.6),
 'thumbnails': path('m16 17h23L16 35Z','#e0eaf2',opacity='.16')+line('M15 44h34','#afa5bd',.5,.6),
 'image-viewer': circle(42,41,7.5,'#96cfdd',opacity='.22')+path('M37 42a5 5 0 0 1 6-6',stroke='#f4f2e5',width=1,opacity='.8')+line('m49 49 4 4','#f8b6c6',.8,.8),
 'eye-of-gnome': circle(21,36,8.8,'#96cfdd',opacity='.18')+path('M15 37a6 6 0 0 1 7-7',stroke='#f4f2e5',width=1,opacity='.8')+line('m12 47-3 5','#f8b6c6',.8,.8),
 'maps': line('m13 22 8-2m24 22 6-2','#5b9394',.7,.7)+line('m29 20q2-3 5-3','#ffd9c6',.85,.7),
 'audio-player': line('M17 16 46 31','#b4efdf',.7,.6)+dots(17,39,2,4,1.8),
 'fcitx-5-configuration': line('M22 21q0-8 7-8','#c4e6da',.8,.65)+line('M24 44q8 6 16 0','#b3bbc4',.7,.5),
 'kitty': path('m20 20 7 5h-7Zm25 0-7 5h7Z','#efb8a8')+line('M20 33q-1 13 11 14','#f2c4cd',.7,.6),
 'help': path('m17 17 8 8m14 14 8 8m-30 0 8-8m14-14 8-8',stroke='#f5e8d6',width=6)+line('M15 32a17 17 0 0 1 14-17','#ffe9bd',.8,.7),
 'handbrake': dots(34,33,4,7,3,'#66454f')+line('M12 25h12M33 30q-4 8-2 15','#fff1cb',.7,.65),
}
# Machined clock dial, with fine secondary minute ticks and a glass glint.
DETAILS['clocks'] = ''.join(line(f'M{32+17*math.sin(i*math.pi/6):.3f} {32-17*math.cos(i*math.pi/6):.3f}l{math.sin(i*math.pi/6):.3f} {-math.cos(i*math.pi/6):.3f}', '#bac9e1', .65,.7) for i in range(12) if i % 3)
DETAILS['clocks'] += path('M18 28a15 15 0 0 1 19-10',stroke='#e2e1ee',width=.7,opacity='.5')
DETAILS['settings'] = circle(32,32,12,'none',stroke='#cad9eb',stroke_width='.6',opacity='.5') + circle(32,32,9.5,'none',stroke='#454776',stroke_width='1',opacity='.65')


# Revision 2 sources carry their own clean material treatment.
for key in ('vlc', 'cheese', 'bottles', 'disks', 'audio-player', 'bluetooth-adapters', 'bluetooth-manager', 'calendar', 'systjik', 'dotjik', 'chatgpt', 'codex', 'codex-lb', 'collie', 'disk-usage-analyzer', 'fonts', 'chrome', 'kitty', 'rust', 'zapzap', 'zoom', 'prowlarr'):
    ART.pop(key, None)
    DETAILS.pop(key, None)

# Consistency pass: each revised object owns its finished material treatment.
for key in ('contacts', 'file-roller', 'software', 'connections', 'image-viewer', 'eye-of-gnome', 'thumbnails', 'terminal', 'keyboard-layout-viewer', 'htop', 'steam', 'signal', 'settings', 'help', 'files', 'python', 'qgis-desktop'):
    ART.pop(key, None)
    DETAILS.pop(key, None)

for key in ('lutris', 'scrcpy', 'uuctl', 'video-player', 'logs', 'document-scanner', 'tweaks'):
    ART.pop(key, None)
    DETAILS.pop(key, None)

# Final refinement sources own their material paint.
for key in ('gimp', 'flatpak', 'mullvad', 'spotify', 'solaar', 'text-editor', 'tippecanoe', 'zed-preview', 'runtjik', 'obsidian'):
    ART.pop(key, None)
    DETAILS.pop(key, None)

# Craft apps: independently drawn silhouettes following the official subjects.
# Broad colour planes carry the identity; texture stays in one focal feature.
# Upstream engravings are reference images, never traced or embedded here.
# FilmCraft is the fixed geometry/shading reference. The other entries share
# its broad ramps and quiet secondary planes without modifying the reference.
CRAFT_REVISED = {
    'photocraft', 'vectorcraft', 'lightcraft', 'pdfcraft', 'effectcraft',
    'designcraft', 'figcraft', 'texturecraft', 'soundcraft', 'craft-anything',
    'wordcraft', 'deckcraft', 'cadcraft', 'gridcraft',
}
CRAFT_DEFS = '''<defs>
<linearGradient id="craft-sand" x2=".4" y2="1"><stop stop-color="#f1cc92"/><stop offset=".4" stop-color="#dfab6e"/><stop offset="1" stop-color="#b57668"/></linearGradient>
<linearGradient id="craft-jade" x2=".4" y2="1"><stop stop-color="#9fd6c3"/><stop offset=".4" stop-color="#5fb7a5"/><stop offset="1" stop-color="#3d7d83"/></linearGradient>
<linearGradient id="craft-rose" x2=".4" y2="1"><stop stop-color="#efb7ce"/><stop offset=".4" stop-color="#d784b0"/><stop offset="1" stop-color="#925a8b"/></linearGradient>
<linearGradient id="craft-paper" x2=".4" y2="1"><stop stop-color="#fff3de"/><stop offset=".4" stop-color="#f4e7d4"/><stop offset="1" stop-color="#d2c8ce"/></linearGradient>
</defs>'''
ART['photocraft'] = (
    # Nine overlapping tails radiate from the haunch, behind a substantial body.
    path('M30 46C21 31 25 16 30 9C35 20 32 31 35 39C33 25 35 12 40 6C44 18 41 31 40 39C43 27 44 17 50 13C52 25 48 34 45 41C51 34 52 26 58 24C59 35 53 43 48 46C54 43 57 39 61 40C60 49 52 51 46 51C52 52 56 49 59 51C54 58 47 58 40 55C43 59 49 57 51 60C42 64 36 60 32 55C33 60 30 62 27 61L24 51C18 56 11 55 8 51C13 47 21 46 27 48Z', 'url(#indigo)')
    + path('M30 9Q33 17 32 23L29 21 26 23Q26 15 30 9Z M40 6Q43 15 41 21L38 19 35 22Q35 12 40 6Z M50 13Q51 22 47 28L46 24 43 26Q45 18 50 13Z M58 24Q58 33 53 37L53 33 50 34Q53 27 58 24Z M61 40Q59 47 53 49L54 46 51 46Q57 42 61 40Z M59 51Q55 57 49 56L51 53Z M51 60Q44 62 40 59L43 58Z', '#bcb7df')
    + path('M18 29C13 36 14 47 17 55Q24 59 37 56C39 51 34 47 31 45L30 32Z', 'url(#craft-sand)')
    + path('M30 37C36 40 37 48 34 52L30 52Q33 46 28 44Z', '#b57668')
    + path('M20 33Q17 43 21 54H27L26 35Z', '#fff0da')
    + path('M18 53Q22 51 24 54H28Q31 52 34 55Q26 58 18 56Z', '#bb806c')
    + path('M10 13Q16 15 20 20Q24 18 28 20L36 12Q37 22 34 27Q36 32 31 36L24 40Q15 38 11 33L8 31 11 27Q9 21 10 13Z', 'url(#craft-sand)')
    + path('M13 18 19 23 13 25Z M33 18 29 24 33 25Z', '#62517f')
    + path('M11 30Q17 29 24 35Q29 30 34 29Q33 35 24 40Q15 37 11 30Z', '#fff0da')
    + path('M15 28Q18 26 21 29L18 30Z M27 29Q30 26 33 27L30 30Z', '#34304f')
    + path('M21 34Q24 33 27 34L24 37Z', '#34304f'))
ART['vectorcraft'] = (
    path('M40 23 48 18 47 28 54 28 50 36 57 40 51 44 54 54 43 52Z', '#dfab6e')
    + path('M32 24C47 24 52 40 48 56Q35 59 23 55C34 48 37 39 31 33Z', 'url(#craft-jade)')
    + path('M34 34C41 40 41 49 36 56L23 55Q36 45 34 34Z', '#dfab6e')
    + path('M36 43 40 44M32 49 39 50', stroke='#a66d69', width=1.1)
    + path('M8 24 19 22Q24 16 32 16L39 18 44 24Q44 31 36 35L24 39Q15 38 9 34L6 30Z', 'url(#craft-jade)')
    + path('M26 17Q23 10 28 5Q28 12 33 15Z M36 18Q40 11 47 10Q42 15 41 23Z', '#fff0da', '#706079', .65)
    + path('M24 24Q29 20 35 23L34 25 27 26Z', '#3d7d83')
    + path('M25 26Q29 23 34 25Q32 30 27 29Z', '#34304f')
    + circle(29.5, 26.5, 1.7, '#e6ae62') + path('M29.5 25.2v2.6', stroke='#34304f', width=.9)
    + path('M8 31Q20 35 31 32L35 30Q31 37 23 38L12 35Z', '#3d7d83')
    + path('M8 31Q19 34 30 32', stroke='#34304f', width=1.2)
    + path('M14 33 18 33 17 37Z', '#fff0da') + circle(12, 27, 1.2, '#34304f')
    + path('M40 35Q47 40 46 49L42 52Q44 42 40 35Z', '#3d7d83'))
ART['filmcraft'] = (
    # One continuous symmetric contour, with paired curves sharing a centreline.
    path('M12 7 26 17Q32 14 38 17L52 7 49 29C54 44 46 56 32 56S10 44 15 29Z', 'url(#indigo)')
    + path('M16 14 24 20 18 24Z M48 14 40 20 46 24Z', '#514363')
    + path('M15 33C13 42 19 51 26 53C21 47 21 39 23 35Z M49 33C51 42 45 51 38 53C43 47 43 39 41 35Z', '#62517f')
    + path('M32 25C27 17 18 19 17 28C16 36 24 41 32 44C40 41 48 36 47 28C46 19 37 17 32 25Z', '#fff0da')
    + circle(24, 29, 4.8, '#34304f') + circle(40, 29, 4.8, '#34304f')
    + circle(24, 29, 2.2, '#e6ae62') + circle(40, 29, 2.2, '#e6ae62')
    + circle(24, 29, 1.1, '#34304f') + circle(40, 29, 1.1, '#34304f')
    + path('M29.5 37Q32 35.5 34.5 37L32 41Z', '#b96d5a')
    + path('M26 46q2 3 4 0m4 0q2 3 4 0m-8 4q2 3 4 0', stroke='#d2c8ed', width=1.1)
    + path('M23 54v3m-2 0h4m16-3v3m-2 0h4', stroke='#e6ae62', width=1.7))
ART['lightcraft'] = (
    path('M15 25C12 20 12 13 14 9C20 10 24 15 26 18Q32 16 38 18C40 15 44 10 50 9C52 16 50 23 49 25Q54 31 52 37Q54 40 50 42L51 45 45 46C42 50 37 52 32 52S22 50 19 46L13 45 14 42Q10 40 12 37Q10 31 15 25Z', 'url(#craft-sand)')
    + path('M13 11 11 3 14 8 15 5 15 11Z M51 11 53 3 50 8 49 5 49 11Z', '#92718b')
    + path('M16 14q6 3 8 10-5-3-8-1-1-5 0-9Z M48 14q-6 3-8 10 5-3 8-1 1-5 0-9Z', '#62517f')
    + path('M13 34C18 38 22 38 25 36Q32 34 39 36C42 38 46 38 51 34Q50 41 44 43C41 48 37 50 32 50S23 48 20 43Q14 41 13 34Z', '#fff0da')
    + path('M18 29Q23 25 28 29Q25 33 21 32Z M46 29Q41 25 36 29Q39 33 43 32Z', '#34304f')
    + circle(24, 29.5, 1.5, '#e6ae62') + circle(40, 29.5, 1.5, '#e6ae62')
    + circle(24, 29.5, .8, '#34304f') + circle(40, 29.5, .8, '#34304f')
    + path('M27 21Q30 22 30 26Q27 25 27 21Z M37 21Q34 22 34 26Q37 25 37 21Z', '#aa785f')
    + path('M29 36Q32 35 35 36L32 39Z', '#34304f')
    + path('M32 39v3q-2 1-4 0m4 0q2 1 4 0', stroke='#34304f', width=1.1)
    + path('M13 30q3 0 5 3l-5-1Z M51 30q-3 0-5 3l5-1Z', '#aa785f'))
ART['pdfcraft'] = (
    '<defs><linearGradient id="lion-mane" gradientUnits="userSpaceOnUse" x1="20" y1="7" x2="45" y2="58"><stop stop-color="#d99563"/><stop offset=".5" stop-color="#bb7359"/><stop offset="1" stop-color="#804355"/></linearGradient></defs>'
    # Four broad mane masses frame the larger brow, bridge and whisker pads.
    + path('M32 6Q21 4 16 12Q10 12 8 22L6 24 8 31Q4 39 10 47L12 46Q16 57 26 57L32 60 38 57Q48 57 52 46L54 47Q60 39 56 31L58 24 56 22Q54 12 48 12Q43 4 32 6Z', 'url(#lion-mane)')
    + path('M31 8C20 6 12 17 13 29Q16 25 20 24Q20 13 31 8Z M33 8C44 6 52 17 51 29Q48 25 44 24Q44 13 33 8Z', '#dc9b6c')
    + path('M14 28C9 42 18 45 20 53Q24 55 27 55C22 45 22 37 21 30Z M50 28C55 42 46 45 44 53Q40 55 37 55C42 45 42 37 43 30Z', '#99505a')
    + path('M24 42Q25 53 32 57Q39 53 40 42Z', '#683d4c')
    + path('M17 24Q11 15 18 14Q23 14 24 21Z M47 24Q53 15 46 14Q41 14 40 21Z', '#dca375')
    + path('M18 21Q15 17 18 17L22 21Z M46 21Q49 17 46 17L42 21Z', '#765064')
    + path('M20 21Q32 14 44 21Q47 28 43 35L42 41Q38 49 32 50Q26 49 22 41L21 35Q17 28 20 21Z', 'url(#craft-sand)')
    + path('M21 25Q27 23 30 28L26 29Z M43 25Q37 23 34 28L38 29Z', '#ad765e')
    + path('M22 28Q26 26 29 29Q26 32 23 30Z M42 28Q38 26 35 29Q38 32 41 30Z', '#34304f')
    + circle(26, 29, 1.35, '#e6ae62') + circle(38, 29, 1.35, '#e6ae62')
    + circle(26, 29, .65, '#34304f') + circle(38, 29, .65, '#34304f')
    + path('M28 30Q32 28 36 30L38 37H26Z', '#edbf85')
    + path('M24 36Q28 33 32 36Q36 33 40 36Q44 42 37 44L32 43 27 44Q20 42 24 36Z', '#fff0da')
    + path('M28 35Q32 33 36 35L35 38 32 40 29 38Z', '#34304f')
    + path('M32 40v3m-6-1q3 2 6 1 3 1 6-1', stroke='#34304f', width=1.1)
    + path('M27 46Q32 48 37 46L35 49H29Z', '#fff0da'))
ART['effectcraft'] = (
    # A rounded shoulder continues the arched neck; the jaw is a curved volume.
    path('M29 18C18 11 8 21 9 32C10 41 4 49 9 56Q15 60 22 56L28 32 35 19Z', 'url(#craft-rose)')
    + path('M24 19C15 24 19 32 14 41Q10 49 12 55Q20 50 19 41C25 32 20 27 24 19Z', '#a55086')
    + path('M38 23 47 7 43 26Z', '#dfab6e', '#706079', .65)
    + path('M44 14 45 15M41.5 18.5 43.8 20', stroke='#fff0da', width=.75)
    + path('M30 19Q28 14 30 9Q35 12 36 20C41 21 44 27 46 32L54 44Q57 49 52 51Q49 52 46 49L36 40Q32 39 30 35C27 43 30 49 36 52Q41 54 42 57Q26 61 10 56C16 47 13 39 17 29Q21 20 30 19Z', 'url(#craft-paper)', '#706079', .65)
    + path('M31 13Q34 16 34 19L32 18Z', '#b39bd9')
    + path('M30 21C25 21 23 27 18 31Q19 21 27 18Z', '#d784b0')
    + path('M29 37C25 45 29 52 36 57Q31 59 27 58C21 51 23 42 29 37Z', '#b9adbf')
    + path('M31 30Q32 36 37 37L40 40Q32 40 30 35Z', '#c7bbc7')
    + path('M35 28Q38 26 41 29Q38 31 35 28Z', '#34304f')
    + circle(38.5, 28.7, .9, '#e6ae62')
    + path('M50 43Q53 43 52 46Q49 47 49 45Z', '#34304f')
    + path('M48 49 52 48', stroke='#34304f', width=1.1))
ART['designcraft'] = (
    path('M23 38Q12 43 11 57H53Q52 43 41 38Z', 'url(#craft-jade)')
    + path('M16 12 27 21Q32 19 37 21L48 12 48 28C54 40 44 47 32 47S10 40 16 27Z', 'url(#craft-paper)', '#706079', .65)
    + path('M19 17 26 23Q23 25 19 26Z M45 17 38 23 45 26Z', '#62517f')
    + path('M20 19 24 23 20 24Z M44 19 40 23 44 24Z', '#d784b0')
    + path('M18 27Q22 23 28 23Q29 29 25 34L19 37Q14 33 18 27Z', '#dfab6e')
    + path('M38 23Q45 23 48 28Q52 36 45 40L39 35Q42 29 38 23Z', '#62517f')
    + circle(24, 31, 2.8, '#34304f') + circle(40, 31, 2.8, '#34304f')
    + circle(24, 31, 1.5, '#e6ae62') + circle(40, 31, 1.5, '#e6ae62')
    + circle(24, 31, .8, '#34304f') + circle(40, 31, .8, '#34304f')
    + path('M29 36Q32 34.5 35 36L32 39Z', '#855b67')
    + path('M32 39v2m-4 0q2 2 4 0 2 2 4 0', stroke='#34304f', width=1.1)
    + path('M15 43Q31 49 46 42L49 48Q31 55 14 49Z', '#dfab6e')
    + path('M43 49 51 50 49 59 41 54Z', '#dfab6e')
    + ''.join(circle(x,y,1.1,'#34304f') for x,y in [(21,47),(29,49),(37,48),(45,53)]))
ART['figcraft'] = (
    # A horizontal ribcage, folded limbs and a continuous tail replace the gap.
    path('M44 28C58 28 61 41 55 50C50 59 37 59 35 51C33 44 39 40 44 43Q49 47 43 50', stroke='#44878c', width=4.8, stroke_linecap='round')
    + path('M23 26C31 16 47 18 50 29C53 40 44 44 31 40L22 35Z', 'url(#craft-jade)')
    + path('M31 36Q40 39 47 32Q47 42 35 42L28 38Z', '#44878c')
    + path('M39 30Q45 29 45 34Q44 38 40 41L45 43Q48 43 47 45L44 47 37 43Q34 41 37 37L39 34Z', '#529c94')
    + path('M21 32Q26 31 26 35L23 41Q25 43 28 43Q31 44 29 46Q25 48 20 45Q17 44 18 40Z', '#44878c')
    + path('M7 28C10 23 16 20 22 18L29 12Q34 20 33 28Q32 35 23 36L11 35Q6 34 7 28Z', 'url(#craft-jade)')
    + path('M8 29Q19 32 32 28Q31 35 22 36L11 35Q7 34 8 29Z', '#9fd6c3')
    + circle(23, 25, 5.8, '#44878c') + circle(23, 25, 4.2, '#dfab6e')
    + circle(23, 25, 2.3, '#34304f')
    + path('M9 31Q19 34 29 31', stroke='#34304f', width=1.1)
    + circle(11, 27, .9, '#34304f')
    + path('M34 24Q39 22 43 25', stroke='#9fd6c3', width=1.4, stroke_linecap='round'))
ART['texturecraft'] = (
    # Short upright mane follows the rounded neck; no geometric crest.
    path('M32 17 35 13Q41 18 46 27L48 26 49 33 51 33 52 40 54 41 55 49 56 50V58H43Z', '#49435f')
    + path('M27 19C22 17 20 12 21 9Q28 9 29 17Zm6-1Q32 10 38 8Q42 13 36 20Z', '#fff0da', '#706079', .65)
    + path('M26 16Q23 14 23 11Q27 12 26 16Z M35 16Q35 12 38 11Q39 14 35 16Z', '#b39bd9')
    + path('M30 17C23 18 21 24 18 29L7 39c-4 4-2 9 3 11 5 2 11-4 15-8l5-5c2 7-2 14-5 20q13 3 29 0c1-12-5-27-13-35-4-4-7-6-11-5Z', 'url(#craft-paper)', '#706079', .65)
    # Tapered black stripes wrap around the neck instead of forming chevrons.
    + path('M33 17Q31 24 38 30L49 37 47 33Q37 28 35 18Z', '#49435f')
    + path('M30 26Q31 36 41 42L53 47 52 44Q38 39 30 26Z', '#49435f')
    + path('M31 37Q36 49 50 53L54 55V57Q36 52 31 42Z', '#49435f')
    + path('M29 49Q33 55 41 59L34 58 27 53Z', '#49435f')
    + path('M26 20q-1 6 3 12l-2 3q-5-8-4-12Z', '#49435f')
    + path('M20 27q1 6 5 10l-3 3q-2-7-5-10Z', '#49435f')
    + path('M15 32q4 3 5 10l-3 3q0-6-4-11Z', '#49435f')
    # Soft muzzle, clear nostril and a small dark eye surrounded by ivory.
    + path('M7 40Q13 39 16 45L14 49Q8 53 5 48Q3 44 7 40Z', '#b39bd9')
    + circle(8, 44, 1.5, '#49435f')
    + path('M6 48q4 2 7 0', stroke='#34304f', width=1.1)
    + circle(26, 27, 3, '#fff0da') + circle(26, 27, 2, '#49435f')
    + circle(26, 27, .8, '#e6ae62'))
ART['soundcraft'] = (
    # Fine insectivore bill, small eye, full breast and long rufous tail.
    path('M36 37Q45 42 57 48L55 54Q42 51 32 46Z', 'url(#craft-rose)')
    + path('M40 44 55 54 49 56 32 46Z', '#925a8b')
    + path('M14 25C11 19 15 12 22 12Q31 12 34 22C37 28 44 33 44 40C43 49 31 52 22 47Q12 41 14 25Z', 'url(#craft-sand)')
    + path('M15 24Q19 29 25 28C24 34 30 43 37 47Q26 52 19 44C14 39 13 32 15 24Z', 'url(#craft-paper)')
    + path('M26 27C35 28 43 34 43 41Q35 43 28 37Q25 33 26 27Z', '#a86673')
    + path('M29 30Q35 31 39 37Q32 36 29 30Z', '#d28a85')
    + path('M15 20 6 19 14 23Z M14 24 8 26 16 26Z', '#34304f')
    + circle(20, 21, 2.6, '#e6ae62') + circle(20, 21, 1.65, '#34304f')
    + path('M25 48 24 54 20 55M32 49 32 54 28 55', stroke='#8c6683', width=1.3, stroke_linecap='round')
    + path('M7 14Q10 12 9 9M3 16Q5 12 3 9', stroke='#5b9b93', width=1.3, stroke_linecap='round'))
ART['craft-anything'] = (
    # Broad corvid skull, low brow and deep-based tapering bill share one profile.
    '<defs><linearGradient id="raven-feather" gradientUnits="userSpaceOnUse" x1="19" y1="12" x2="37" y2="59"><stop stop-color="#a8afeb"/><stop offset=".45" stop-color="#8596ed"/><stop offset="1" stop-color="#747bb2"/></linearGradient></defs>'
    + path('M9 57C16 48 16 40 15 32Q12 23 20 16C25 10 34 10 41 15L45 20 43 28Q38 34 37 40C38 47 44 53 48 57Q29 60 9 57Z', 'url(#raven-feather)')
    + path('M19 22C15 34 24 40 19 50L15 57 9 57C16 48 16 40 15 32Q13 26 19 22Z', '#8379a8')
    + path('M40 21C48 20 56 23 59 28Q55 26.5 51 27L42 28 39 25Z', '#65b9c8')
    + path('M40 25.5Q49 25 57 27.5L51 29 42 29 38 27Z', '#4e6987')
    + path('M30 21Q35 18 41 20L42 23Q36 21 32 24Z', '#494f85')
    + path('M30 24Q33 21 36 23Q35 26 32 26Z', '#34304f')
    + circle(33.5, 23.6, 1, '#e6ae62')
    + path('M38 29 36 33 34 32 33 36 31 34 29 38Q25 36 23 32Q30 34 38 29Z', '#62517f')
    + path('M29 43Q38 47 42 55Q31 58 24 56Q29 50 29 43Z', '#8379a8'))
ART['wordcraft'] = (
    path('M12 8H39L50 19V56H12Q10 56 10 54V10Q10 8 12 8Z', 'url(#craft-paper)', '#706079', .8)
    + path('M10 53H50V56H12Q10 56 10 54Z', '#b9adbf')
    + path('M39 8V19H50Z', '#b39bd9')
    + path('M18 26h22m-22 8h19m-19 8h11', stroke='#34304f', width=2)
    + path('M34 51 37 41 54 24 60 30 43 47Z', 'url(#indigo)', '#62517f', .65)
    + path('M34 51 37 41 43 47Z', '#dfab6e')
    + path('M34 51 35.5 46 39 49Z', '#34304f')
    + path('M54 24 57 21 63 27 60 30Z', '#d784b0'))
ART['deckcraft'] = (
    path('M30 43H34V54H43Q45 54 45 57H19Q19 54 21 54H30Z', '#8c79b3')
    + rect(5, 8, 54, 37, 'url(#indigo)', 4)
    + rect(7.5, 10.5, 49, 31.5, '#fff0da', 1.8)
    + path('M14 17H34', stroke='#34304f', width=2)
    + rect(14, 29, 6, 8, '#dfab6e', .8) + rect(24, 25, 6, 12, '#5fb7a5', .8)
    + rect(34, 21, 6, 16, '#8596ed', .8) + circle(47, 19, 3.5, '#d784b0'))
ART['cadcraft'] = (
    path('M9 12 54 57H9Zm9 20v16h16Z', 'url(#craft-paper)', '#706079', .9, fill_rule='evenodd')
    + path('M18 32V48H34Z', '#65b9c8', '#706079', .9, fill_opacity='.24')
    + path('M34 12A23 23 0 0 1 57 35', stroke='#5b9b93', width=3.2)
    + path('M34 12V35H57', stroke='#8596ed', width=1.4, stroke_dasharray='3 3')
    + circle(34, 35, 2, '#34304f') + circle(57, 35, 2.8, '#dfab6e')
    + path('M10 28h3M10 38h3M10 48h3', stroke='#34304f', width=1.1))
ART['gridcraft'] = (
    path('M12 7H42L54 19V57H10V9Q10 7 12 7Z', 'url(#craft-paper)', '#706079', .8)
    + path('M42 7V19H54Z', '#b39bd9')
    + path('M17 15h17', stroke='#34304f', width=2)
    + path('M10 25H54V35H10Zm0 10h14v22H10Z', '#5fb7a5')
    + rect(24, 35, 15, 11, '#e6ae62')
    + path('M10 25H54M10 35H54M10 46H54M24 25V57M39 25V57', stroke='#62517f', width=1)
    + path('M24 35H39V46H24Z', stroke='#34304f', width=1.5)
    + rect(37.5, 44.5, 3, 3, '#34304f'))

# Launcher controls are companion objects, separate from the application catalog.
# Their authored pigment and surface detail must not pass through generic shading.
COMMAND_DEFS = '''<defs>
<linearGradient id="cmd-jade" gradientUnits="userSpaceOnUse" x1="8" y1="6" x2="45" y2="58"><stop stop-color="#8cdbc3"/><stop offset=".55" stop-color="#46b6a2"/><stop offset="1" stop-color="#347b87"/></linearGradient>
<linearGradient id="cmd-copper" gradientUnits="userSpaceOnUse" x1="10" y1="8" x2="48" y2="57"><stop stop-color="#f0c889"/><stop offset=".55" stop-color="#e6ae62"/><stop offset="1" stop-color="#bd785f"/></linearGradient>
<linearGradient id="cmd-rose" gradientUnits="userSpaceOnUse" x1="12" y1="7" x2="48" y2="55"><stop stop-color="#e9a4b9"/><stop offset=".55" stop-color="#df77ac"/><stop offset="1" stop-color="#a86192"/></linearGradient>
<linearGradient id="cmd-violet" gradientUnits="userSpaceOnUse" x1="7" y1="6" x2="48" y2="57"><stop stop-color="#b8b7e7"/><stop offset=".55" stop-color="#8596ed"/><stop offset="1" stop-color="#626ca7"/></linearGradient>
<linearGradient id="cmd-paper" gradientUnits="userSpaceOnUse" x1="9" y1="7" x2="48" y2="57"><stop stop-color="#fff0da"/><stop offset="1" stop-color="#e5d8c9"/></linearGradient>
<linearGradient id="cmd-steel" gradientUnits="userSpaceOnUse" x1="16" y1="6" x2="41" y2="58"><stop stop-color="#cfddd9"/><stop offset=".5" stop-color="#9eb9ca"/><stop offset="1" stop-color="#667b9b"/></linearGradient>
</defs>'''

COMMAND_ART = {}
COMMAND_ART['refresh'] = (
    rect(22, 22, 22, 23, '#b9b9c7', 2)
    + rect(19, 18, 22, 24, 'url(#cmd-paper)', 2)
    + rect(24, 25, 12, 2.5, '#8596ed', 1)
    + rect(24, 31, 9, 2.5, '#8596ed', 1)
    + path('M8 31A24 24 0 0 1 46 12l5-5 4 17-17-3 4-4A17 17 0 0 0 15 31Z', 'url(#cmd-jade)')
    + path('M56 33A24 24 0 0 1 18 52l-5 5-4-17 17 3-4 4a17 17 0 0 0 27-14Z', 'url(#cmd-copper)'))

COMMAND_ART['pin'] = (
    '<g transform="rotate(30 32 32)">'
    + path('M29.5 37h5L33 56l-1 3-1-3Z', 'url(#cmd-steel)')
    + path('M25 16h14l-2 13 9 7v5H18v-5l9-7Z', 'url(#cmd-rose)')
    + path('M18 36h28v5H18Z', '#ad6190')
    + rect(16, 6, 32, 13, 'url(#cmd-copper)', 6)
    + path('M18 14q14 4 28 0v2q-1 3-6 3H24q-5 0-6-3Z', '#c98964')
    + '</g>')

COMMAND_ART['grid'] = ''
for x, y, pigment, shade in [(7, 7, 'copper', '#bd785f'), (35, 7, 'jade', '#347b87'),
                              (7, 35, 'violet', '#626ca7'), (35, 35, 'rose', '#a86192')]:
    COMMAND_ART['grid'] += (rect(x, y, 22, 22, f'url(#cmd-{pigment})', 4)
        + path(f'M{x} {y+17}q11 2 22 0v1q0 4-4 4H{x+4}q-4 0-4-4Z', shade, opacity='.45'))
COMMAND_ART['grid'] += (circle(18, 17, 4.5, '#fff0da')
    + path('m46 12 5 5-5 5-5-5Z', '#fff0da')
    + rect(13, 42, 10, 7, '#fff0da', 1.3)
    + path('M43 43h6v3h3v3H40v-3h3Z', '#fff0da'))

COMMAND_ART['list'] = ''
for y, pigment in [(8, 'jade'), (26, 'violet'), (44, 'copper')]:
    COMMAND_ART['list'] += (rect(6, y, 52, 13, 'url(#cmd-paper)', 2)
        + path(f'M6 {y+10}h52v1q0 2-2 2H8q-2 0-2-2Z', '#c5bebf')
        + rect(6, y, 13, 11, f'url(#cmd-{pigment})', 2)
        + rect(25, y+3, 23, 2.5, '#565b79', 1)
        + rect(25, y+7, 16, 1.5, '#a5a4b5', .75))

COMMAND_ART['stats'] = (
    path('M13 6h30l9 9v41q0 2-2 2H13q-3 0-3-3V9q0-3 3-3Z', 'url(#cmd-paper)')
    + path('M43 6v9h9Z', '#c9c8d7')
    + rect(17, 14, 12, 2.5, '#777b9a', 1)
    + rect(18, 35, 7, 15, 'url(#cmd-jade)', 1)
    + rect(29, 27, 7, 23, 'url(#cmd-violet)', 1)
    + rect(40, 20, 7, 30, 'url(#cmd-copper)', 1)
    + rect(16, 50, 33, 2, '#565b79', 1)
    + path('M11 55h40v1q0 2-2 2H13q-2 0-2-3Z', '#c8bdc1'))

COMMAND_ART['config'] = ''
for x, y, pigment, underside in [(12, 14, 'jade', '#347b87'), (32, 37, 'rose', '#a86192'),
                                (52, 24, 'copper', '#bd785f')]:
    COMMAND_ART['config'] += (rect(x-2.5, 6, 5, 52, '#34304f', 2.5)
        + rect(x-1.2, 7, 2.4, 50, 'url(#cmd-steel)', 1.2)
        + rect(x-7, y, 14, 11, f'url(#cmd-{pigment})', 2)
        + path(f'M{x-7} {y+8}h14v1q0 2-2 2H{x-5}q-2 0-2-2Z', underside)
        + rect(x-4, y+3, 8, 1.2, '#fff0da', .6, opacity='.65'))

COMMAND_ART['shortcuts'] = ''
for x, y, fill in [(23, 7, 'paper'), (4, 33, 'paper'), (23, 33, 'violet'), (42, 33, 'paper')]:
    COMMAND_ART['shortcuts'] += (rect(x, y, 18, 22, '#626c94', 3)
        + rect(x, y, 18, 18, f'url(#cmd-{fill})', 3))
COMMAND_ART['shortcuts'] += (path('m32 12 5 6h-3v6h-4v-6h-3Z', '#4b567b')
    + path('m8 42 6-5v3h5v4h-5v3Z', '#4b567b')
    + path('m32 47-5-6h3v-5h4v5h3Z', '#fff0da')
    + path('m56 42-6-5v3h-5v4h5v3Z', '#4b567b'))


COMMAND_ART['fish'] = (
    path('M26 22 32 8q9 3 12 14Z', 'url(#cmd-rose)')
    + path('m27 42 8 14 8-13Z', 'url(#cmd-copper)')
    + path('M23 27 5 17l4 15-4 15 18-10Z', 'url(#cmd-copper)')
    + path('M18 30C23 15 43 14 56 28q5 4 0 8C43 50 23 49 18 34Z', 'url(#cmd-jade)')
    + path('M35 32q-1 8 7 10l-1-10Z', 'url(#cmd-copper)')
    + path('M43 24q-4 8 0 16', stroke='#347b87', width=1.2, opacity='.65')
    + circle(49, 28, 3.3, '#fff0da')
    + circle(50, 28.5, 1.8, '#34304f')
    + path('M51 36q3 2 5-1', stroke='#34304f', width=1.2)
    + path('M27 28q3 3 0 6m5-10q3 3 0 6', stroke='#347b87', width=.8, opacity='.4'))


def command_artwork(key):
    return COMMAND_DEFS + '<g data-material="authored" stroke-linecap="round" stroke-linejoin="round">' + COMMAND_ART[key] + '</g>'


def artwork(key):
    if key not in ART:
        return None
    definitions = DEFS + (CRAFT_DEFS if key in CRAFT_REVISED else '')
    return definitions + '<g data-material="authored" stroke-linecap="round" stroke-linejoin="round">' + ART[key] + '</g>'


def details(key):
    if key not in DETAILS:
        return ''
    return DEFS + '<g data-material="authored" stroke-linecap="round" stroke-linejoin="round">' + DETAILS[key] + '</g>'
