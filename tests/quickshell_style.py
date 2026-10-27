"""Private-bus native check of the shared, attached Qt Quick tooltip style."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert os.environ.get('DBUS_SESSION_BUS_ADDRESS', '').startswith('unix:path=/tmp/')
    destination = Path(sys.argv[1]).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='quickshell-style-') as directory:
        temp = Path(directory)
        style = temp / 'data/quickshell/styles/RosePunk'
        shutil.copytree(ROOT / 'home/dot_local/share/quickshell/styles/RosePunk', style)
        (temp / 'shell.qml').write_text('''
//@ pragma UseQApplication
//@ pragma RespectSystemStyle
import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
ShellRoot {
    FileView {id:result;path:Quickshell.env('STYLE_RESULT');blockWrites:true}
    PanelWindow {
        id:window
        implicitWidth:360;implicitHeight:160;color:'#26233a'
        WlrLayershell.namespace:'quickshell-shared-style-fixture'
        Button {
            id:control
            anchors.centerIn:parent
            text:'Shared tooltip style'
            ToolTip.visible:true
            ToolTip.delay:0
            ToolTip.text:'Themed by default, including attached ToolTip'
        }
    }
    Timer {
        interval:600;running:true
        onTriggered:{
            const tip=control.ToolTip.toolTip;
            const position=tip.background.mapToItem(window.contentItem,0,0);
            result.setText(JSON.stringify({name:tip.objectName,color:String(tip.background.color),
                radius:tip.background.radius,textColor:String(tip.contentItem.color),
                visible:tip.visible,fontSize:tip.font.pixelSize,buttonWidth:control.width,
                capture:{x:position.x,y:position.y,width:tip.background.width,height:tip.background.height}}));
        }
    }
}
''')
        result = destination / 'style.json'
        image = destination / 'style.png'
        result.unlink(missing_ok=True)
        image.unlink(missing_ok=True)
        env = {**os.environ, 'XDG_DATA_HOME': str(temp / 'data'),
               'STYLE_RESULT': str(result)}
        for key in ('QT_QUICK_CONTROLS_STYLE', 'QT_QUICK_CONTROLS_FALLBACK_STYLE'):
            env.pop(key, None)
        with (destination / 'style.log').open('w') as log:
            process = subprocess.Popen(['sh', str(ROOT / 'home/dot_local/bin/executable_quickshell'),
                                        '--path', str(temp)], env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and not result.exists():
                    if process.poll() is not None:
                        break
                    time.sleep(.1)
                assert result.exists(), (destination / 'style.log').read_text()
                state = json.loads(result.read_text())
                assert state['name'] == 'rose-punk-tooltip', state
                assert state['color'] == '#1f1d2e' and state['textColor'] == '#e5e5e5', state
                assert state['radius'] == 8 and state['fontSize'] == 12, state
                assert state['visible'] and state['buttonWidth'] > 0, state
                rect = state['capture']
                layers = json.loads(subprocess.check_output(['hyprctl', '-j', 'layers']))
                def find_layer(value):
                    if isinstance(value, dict):
                        if value.get('namespace') == 'quickshell-shared-style-fixture':
                            return value
                        for child in value.values():
                            match = find_layer(child)
                            if match:
                                return match
                    elif isinstance(value, list):
                        for child in value:
                            match = find_layer(child)
                            if match:
                                return match
                    return None
                layer = find_layer(layers)
                assert layer and rect['x'] >= 0 and rect['y'] >= 0, (layer, rect)
                assert rect['x'] + rect['width'] <= layer['w'] and rect['y'] + rect['height'] <= layer['h'], (layer, rect)
                region = f"{round(layer['x']+rect['x'])},{round(layer['y']+rect['y'])} {round(rect['width'])}x{round(rect['height'])}"
                subprocess.run(['grim', '-g', region, str(image)], check=True)
            finally:
                process.terminate()
                process.wait(timeout=5)
    print('PASS: global attached tooltip theme and fallback button render through the Quickshell wrapper.')


if __name__ == '__main__':
    main()
