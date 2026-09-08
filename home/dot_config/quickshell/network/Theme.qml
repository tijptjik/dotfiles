import QtQuick
import Quickshell
import Quickshell.Io

QtObject {
    id: theme
    property var palette: ({})
    readonly property color background: palette.base01 || "#1f1d2e"
    readonly property color surface: palette.base02 || "#26233a"
    readonly property color border: palette.base03 || "#555169"
    readonly property color muted: palette.base04 || "#6e6a86"
    readonly property color text: palette.base05 || "#e5e5e5"
    readonly property color accent: palette.base0E || "#ff53a6"
    readonly property color error: palette.base08 || "#eb6f92"
    readonly property string font: "tijpset"

    property FileView colors: FileView {
        path: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/waybar/colors.css"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: {
            const parsed = {};
            const expression = /@define-color\s+(base[0-9A-Fa-f]{2})\s+(#[0-9A-Fa-f]{6})\s*;/g;
            const css = text();
            let match;
            while ((match = expression.exec(css)) !== null)
                parsed[match[1].slice(0, 4) + match[1].slice(4).toUpperCase()] = match[2];
            theme.palette = parsed;
        }
    }
}
