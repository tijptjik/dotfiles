import QtQuick
import QtQuick.Controls

Button {
    id: control
    required property QtObject theme
    required property string symbol
    property bool accented: false
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    implicitWidth: 32
    implicitHeight: 32
    padding: 6
    font.family: "Material Symbols Rounded"
    font.pixelSize: 20
    opacity: enabled ? 1 : 0.45
    Accessible.name: text
    background: Rectangle {
        radius: 8
        color: control.hovered || control.down ? control.theme.border : control.theme.surface
    }
    contentItem: Text {
        text: control.symbol
        font: control.font
        color: control.accented ? control.theme.accent : control.theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        textFormat: Text.PlainText
    }
}
