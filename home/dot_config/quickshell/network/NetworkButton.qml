import QtQuick
import QtQuick.Controls

Button {
    id: control
    required property QtObject theme
    property bool accented: false
    hoverEnabled: true
    padding: 10
    leftPadding: 12
    rightPadding: 12
    font.family: theme.font
    font.pixelSize: 14
    opacity: enabled ? 1 : 0.45
    background: Rectangle {
        radius: 10
        color: control.hovered || control.down ? control.theme.border : control.theme.surface
        border.width: control.activeFocus ? 1 : 0
        border.color: control.theme.accent
    }
    contentItem: Text {
        text: control.text
        font: control.font
        color: control.accented ? control.theme.accent : control.theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        textFormat: Text.PlainText
    }
}
