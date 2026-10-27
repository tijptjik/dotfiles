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
ART['llmtrim'] = (path('m27 27 24 22q2-8-5-14L29 23Z','url(#metal)')
    + path('m27 36 23-23q2 8-5 14L30 39Z','url(#metal)')
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
for key in ('vlc', 'cheese', 'bottles', 'disks', 'audio-player', 'bluetooth-adapters', 'bluetooth-manager', 'calendar', 'chezetc', 'chezmoi', 'chatgpt', 'codex', 'codex-lb', 'collie', 'disk-usage-analyzer', 'fonts', 'chrome', 'kitty', 'rust', 'zapzap', 'zoom', 'prowlarr'):
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


def command_artwork(key):
    return COMMAND_DEFS + '<g data-material="authored" stroke-linecap="round" stroke-linejoin="round">' + COMMAND_ART[key] + '</g>'


def artwork(key):
    if key not in ART:
        return None
    return DEFS + '<g data-material="authored" stroke-linecap="round" stroke-linejoin="round">' + ART[key] + '</g>'


def details(key):
    if key not in DETAILS:
        return ''
    return DEFS + '<g data-material="authored" stroke-linecap="round" stroke-linejoin="round">' + DETAILS[key] + '</g>'
