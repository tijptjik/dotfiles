import QtQuick
import QtQuick.Templates as T

T.ToolTip {
    id:tip
    objectName:'rose-punk-tooltip'
    x:parent ? (parent.width-implicitWidth)/2 : 0
    y:-implicitHeight-3
    implicitWidth:Math.min(280,Math.max(implicitBackgroundWidth+leftInset+rightInset,implicitContentWidth+leftPadding+rightPadding))
    implicitHeight:Math.max(implicitBackgroundHeight+topInset+bottomInset,implicitContentHeight+topPadding+bottomPadding)
    font.family:'tijpset'
    font.pixelSize:12
    delay:650
    padding:8;leftPadding:10;rightPadding:10;margins:8
    closePolicy:T.Popup.CloseOnEscape | T.Popup.CloseOnPressOutsideParent | T.Popup.CloseOnReleaseOutsideParent
    contentItem:Text {
        text:tip.text;textFormat:Text.PlainText
        font:tip.font;color:'#e5e5e5';wrapMode:Text.Wrap
    }
    background:Rectangle {
        radius:8;color:'#1f1d2e'
        border.width:1;border.color:'#555169'
    }
}
