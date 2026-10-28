"""Illustrated app symbols on flat Rose Punk tiles."""
import xml.etree.ElementTree as ET
from build import ART, ROOT

DEST = ROOT / 'native/home/files/.local/share/icons/rose-punk/scalable/apps'
# Open marks stay open; solid silhouettes become layered enamel badges.
LINE_MARKS = {'codex-lb', 'sublime-text', 'chatgpt', 'zed', 'drizzle', 'transmission', 'steam'}


def icon(key, mark):
    wrapper = ET.fromstring('<g>' + mark + '</g>')
    for i, node in enumerate(wrapper):
        detail = node.attrib.pop('class', '')
        node.set('stroke', '#35213f' if key not in LINE_MARKS else 'url(#ink)')
        node.set('stroke-width', '2' if key not in LINE_MARKS else '4')
        node.set('fill', 'none')
        if detail == 'accent':
            node.set('stroke', '#d1c0ee')
        if detail == 'dot':
            node.set('fill', '#35213f')
            node.set('stroke', 'none')
        elif i == 0 and key not in LINE_MARKS:
            node.set('fill', 'url(#enamel)')
            node.set('stroke', '#f4b7c9')
            node.set('stroke-width', '2')
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
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<defs>
 <linearGradient id="enamel" x1="0" y1="0" x2=".6" y2="1"><stop stop-color="#f4c8d7"/><stop offset=".4" stop-color="#e88bb6"/><stop offset="1" stop-color="#b94e87"/></linearGradient>
 <linearGradient id="ink" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f4c8d7"/><stop offset=".6" stop-color="#e56ea1"/><stop offset="1" stop-color="#b39bd9"/></linearGradient>
 <linearGradient id="gem" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#d9c3f2"/><stop offset=".5" stop-color="#9272ba"/><stop offset="1" stop-color="#71385f"/></linearGradient>
</defs>
<rect id="tile" x="3" y="2" width="58" height="58" rx="17" fill="#26233a" stroke="#555169" stroke-opacity=".45" stroke-width=".65"/>
<g stroke-linecap="round" stroke-linejoin="round">''' + shapes + '</g></svg>\n'


def main():
    # Rebuild the selected complete set, including the corrected upstream identities.
    from fullset import main as build_fullset
    build_fullset()


if __name__ == '__main__':
    main()
