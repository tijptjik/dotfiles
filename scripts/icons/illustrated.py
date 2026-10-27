"""Version B: sculpted enamel illustrations sharing A's recognizable silhouettes."""
import xml.etree.ElementTree as ET
from build import ART, ROOT

DEST = ROOT / 'home/dot_local/share/icons/rose-punk-illustrated/scalable/apps'
# Open marks stay open; solid silhouettes become layered enamel badges.
LINE_MARKS = {'codex-lb', 'sublime-text', 'chatgpt', 'zed', 'drizzle', 'transmission', 'steam'}


def icon(key, mark):
    wrapper = ET.fromstring('<g>' + mark + '</g>')
    for i, node in enumerate(wrapper):
        detail = node.attrib.pop('class', '')
        node.set('stroke', '#35213f' if key not in LINE_MARKS else 'url(#ink)')
        node.set('stroke-width', '1.8' if key not in LINE_MARKS else '3.4')
        node.set('fill', 'none')
        if detail == 'dot':
            node.set('fill', '#35213f')
            node.set('stroke', 'none')
        elif i == 0 and key not in LINE_MARKS:
            node.set('fill', 'url(#enamel)')
            node.set('stroke', '#f4b7c9')
            node.set('stroke-width', '1.2')
        elif detail == 'detail':
            node.set('stroke', '#482b53' if key not in LINE_MARKS else '#d1c0ee')
        if key == 'signal':
            if i == 0:
                node.set('fill', 'none')
                node.set('stroke', '#d1c0ee')
            else:
                node.set('fill', 'url(#enamel)')
                node.set('stroke', '#f4b7c9')
        if key == 'obsidian' and i == 0:
            node.set('fill', 'url(#gem)')
        if key == 'obsidian' and detail == 'detail':
            node.set('stroke', '#f4b7c9')
    shapes = ''.join(ET.tostring(n, encoding='unicode') for n in wrapper)
    if key == 'datagrip':
        shapes = '<path d="M15 19v25c0 10 34 10 34 0V19Z" fill="url(#enamel)" stroke="#f4b7c9" stroke-width="1.2"/><ellipse cx="32" cy="19" rx="17" ry="7" fill="url(#gem)" stroke="#f4b7c9" stroke-width="1.2"/><path d="M15 31c0 9 34 9 34 0m-25 9h7m5 0h4" fill="none" stroke="#482b53" stroke-width="1.8"/>'
    # The shadows are SVG primitives, so there is no filter blur at small sizes.
    shadow = '<g transform="translate(0 2.2)" opacity=".5" fill="none" stroke="#100d1c" stroke-width="4">' + mark.replace('class="detail"', '').replace('class="dot"', '') + '</g>'
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<defs>
 <linearGradient id="tile" x1="0" y1="0" x2=".8" y2="1"><stop stop-color="#44304e"/><stop offset=".5" stop-color="#2d233e"/><stop offset="1" stop-color="#211d32"/></linearGradient>
 <linearGradient id="enamel" x1="0" y1="0" x2=".6" y2="1"><stop stop-color="#f4c8d7"/><stop offset=".4" stop-color="#e88bb6"/><stop offset="1" stop-color="#b94e87"/></linearGradient>
 <linearGradient id="ink" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f4c8d7"/><stop offset=".6" stop-color="#e56ea1"/><stop offset="1" stop-color="#b39bd9"/></linearGradient>
 <linearGradient id="gem" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#d9c3f2"/><stop offset=".5" stop-color="#9272ba"/><stop offset="1" stop-color="#71385f"/></linearGradient>
</defs>
<rect x="3" y="5" width="58" height="57" rx="17" fill="#100d1c"/>
<rect x="3" y="2" width="58" height="58" rx="17" fill="url(#tile)" stroke="#68516c" stroke-width=".65"/>
<path d="M9 14Q12 5 23 5h18" fill="none" stroke="#f4b7c9" stroke-opacity=".22" stroke-width="1.3" stroke-linecap="round"/>
<g stroke-linecap="round" stroke-linejoin="round">''' + shadow + shapes + '</g></svg>\n'


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for key, (_, mark) in ART.items():
        (DEST / f'{key}.svg').write_text(icon(key, mark))


if __name__ == '__main__':
    main()
