import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import Quickshell.Services.Pipewire

ShellRoot {
    id: root
    property bool opened: Quickshell.env("AUDIO_WIDGET_MODE") !== "ensure"
    property bool pinned: Quickshell.env("AUDIO_WIDGET_MODE") !== "ensure"
    property bool barHovered: false
    property bool suppressHover: false
    property var pointerState: ({ cursor: null, monitors: [], anchor: null })
    property bool dragging: false
    property bool dropping: false
    property bool dropFrameReady: false
    property int dropFrames: 0
    property var dragImage: null
    property var dragScreen: null
    property real dragOriginX: 0
    property real dragOriginY: 0
    property real dragWidth: 420
    property real dragHeight: 414
    property int dragGeneration: 0
    property bool dragged: false
    property real desktopX: 0
    property real desktopY: 0
    property real grabX: 0
    property real grabY: 0
    readonly property var currentMonitor: pointerState.monitors.find(monitor => monitor.name === targetScreen?.name) || ({x: 0, y: 0})
    property var targetScreen: null
    property real anchorX: 210
    property real anchorBottom: 700
    property string message: ""
    readonly property var outputs: Pipewire.nodes.values.filter(n => n.audio && !n.isStream && n.isSink && (n.description === "USB Audio Speakers" || n.description.startsWith("Navi 21/23 HDMI/DP")))
    readonly property var inputs: Pipewire.nodes.values.filter(n => n.audio && !n.isStream && !n.isSink && n.description.startsWith("BRIO Ultra HD Webcam Analog Stereo"))
    readonly property var clients: Pipewire.nodes.values.filter(n => n.audio && n.isStream && n.isSink && !((n.properties["application.name"] || "") + " " + n.name + " " + n.description).toLowerCase().includes("speech-dispatcher-dummy"))
    readonly property var clientGroups: {
        const groups = [];
        for (const node of clients) {
            const title = node.properties["application.name"] || node.description || node.name;
            let group = groups.find(item => item.title === title);
            if (!group) { group = {title: title, nodes: []}; groups.push(group); }
            group.nodes.push(node);
        }
        return groups;
    }
    readonly property var usb: outputs.find(n => n.description === "USB Audio Speakers") || null
    readonly property var screenOutput: outputs.find(n => n.description.startsWith("Navi 21/23 HDMI/DP")) || null
    readonly property var activeOutput: Pipewire.defaultAudioSink
    readonly property bool headphones: !!usb && Pipewire.defaultAudioSink === usb
    PwObjectTracker { objects: Pipewire.nodes.values.filter(n => !!n.audio) }
    Process {
        id: routing
        command: ["python3", Qt.resolvedUrl("audio.py").toString().replace("file://", ""), "route", root.headphones ? root.screenOutput?.name || "" : root.usb?.name || ""]
        stdout: StdioCollector { onStreamFinished: root.message = text.trim() }
    }

    property var levels: ({})
    Process {
        command: ["python3", Qt.resolvedUrl("levels.py").toString().replace("file://", "")]
        running: root.opened
        stdout: SplitParser {
            onRead: line => {
                try { root.levels = JSON.parse(line); } catch (_) {}
            }
        }
        onExited: root.levels = ({})
    }

    readonly property alias theme: widgetTheme
    Theme { id: widgetTheme }

    function chooseScreen(anchor) {
        const name = anchor.screen || Hyprland.focusedMonitor?.name;
        targetScreen = Quickshell.screens.find(screen => screen.name === name) || Quickshell.screens[0];
        anchorX = anchor.x !== undefined ? anchor.x : (targetScreen ? targetScreen.width / 2 : 210);
        anchorBottom = anchor.bottom !== undefined ? anchor.bottom : (targetScreen ? targetScreen.height - 60 : 700);
        dragged = false;
    }

    function hide() {
        stopDrag();
        finishDrop();
        opened = false;
        pinned = false;
        suppressHover = barHovered;
    }

    function toggle(anchor) {
        if (opened && !pinned) { pinned = true; return; }
        if (opened) { hide(); return; }
        chooseScreen(anchor || {});
        opened = true;
        pinned = true;
    }

    function pointerChanged(value) {
        pointerState = value;
        if (dragging && value.cursor) movePanel(value.cursor);
        barHovered = !!value.anchor;
        if (!barHovered) suppressHover = false;
        if (barHovered && !pinned && !suppressHover) {
            if (!opened) {
                chooseScreen(value.anchor);
                opened = true;
            }
            autoHide.stop();
        } else if (opened && !pinned && !panelHover.hovered && !dragging && !autoHide.running) autoHide.start();
    }

    function movePanel(cursor) {
        desktopX = cursor.x - grabX;
        desktopY = cursor.y - grabY;
        const monitor = cursor && pointerState.monitors.find(item => cursor.x >= item.x && cursor.x < item.x + item.width && cursor.y >= item.y && cursor.y < item.y + item.height);
        if (monitor && monitor.name !== dragScreen?.name)
            dragScreen = Quickshell.screens.find(screen => screen.name === monitor.name) || targetScreen;
    }

    function stopDrag(cursor) {
        if (!dragging) return;
        if (dragging && cursor) movePanel(cursor);
        dropping = dragImage !== null;
        dropFrameReady = false;
        dropFrames = 0;
        if (dragging) {
            targetScreen = dragScreen || targetScreen;
            dragged = true;
        }
        dragging = false;
        pointerObserver.write("drag-stop\n");
        const generation = dragGeneration;
        Qt.callLater(() => {
            if (!dropping || dragging || dragGeneration !== generation) return;
            dropFrameReady = true;
            card.Window.window?.update();
        });
    }

    function finishDrop() {
        dropping = false;
        dropFrameReady = false;
        dragImage = null;
    }

    Timer {
        id: autoHide
        interval: 100
        onTriggered: { if (!root.pinned && !root.barHovered && !panelHover.hovered && !root.dragging) root.hide(); }
    }

    Process {
        id: pointerObserver
        command: ["python3", Qt.resolvedUrl("pointer.py").toString().replace("file://", "")]
        running: true
        stdinEnabled: true
        stdout: SplitParser {
            onRead: line => {
                try { root.pointerChanged(JSON.parse(line)); }
                catch (_) {}
            }
        }
    }

    Component.onCompleted: {
        try { chooseScreen(JSON.parse(Quickshell.env("AUDIO_WIDGET_ANCHOR") || "{}")); }
        catch (_) { chooseScreen({}); }
    }

    IpcHandler {
        target: "audio"
        function toggle(): void { root.toggle(); }
        function toggleAt(anchor: string): void { root.toggle(JSON.parse(anchor)); }
        function close(): void { root.hide(); }
        function isOpen(): bool { return root.opened; }
        function geometry(): string {
            return JSON.stringify({ screen: root.targetScreen?.name, x: panel.margins.left, y: panel.margins.top,
                width: panel.width, height: panel.height, anchorX: root.anchorX, barTop: root.anchorBottom,
                hovered: panelHover.hovered, keyboardFocus: panel.WlrLayershell.keyboardFocus,
                pinned: root.pinned, barHovered: root.barHovered, opened: root.opened, dragging: root.dragging,
                dragScreen: root.dragScreen?.name, desktopX: root.desktopX, desktopY: root.desktopY,
                dropping: root.dropping, dropFrames: root.dropFrames, previewVisible: dragPreview.visible });
        }
    }

    // Keep the real surface and its implicit mouse grab on the original output.
    // Keep the image until the destination has submitted its replacement frames.
    PanelWindow {
        id: dragPreview
        visible: (root.dragging || root.dropping) && root.dragImage !== null
        screen: root.dragScreen
        anchors { top: true; left: true }
        implicitWidth: root.dragWidth
        implicitHeight: root.dragHeight
        readonly property var monitor: root.pointerState.monitors.find(item => item.name === screen?.name) || ({x: 0, y: 0})
        margins.left: Math.max(12, Math.min((screen?.width || 420) - width - 12, root.desktopX - monitor.x))
        margins.top: Math.max(12, Math.min((screen?.height || 720) - height - 12, root.desktopY - monitor.y))
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "audio-widget"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
        mask: Region {}
        Image { anchors.fill: parent; source: root.dragImage ? root.dragImage.url : "" }
    }

    PanelWindow {
        id: panel
        visible: root.opened || card.opacity > 0
        screen: root.targetScreen
        anchors { top: true; left: true }
        implicitWidth: root.dragging || root.dropping ? root.dragWidth : Math.min(420, (screen?.width || 420) - 24)
        implicitHeight: root.dragging || root.dropping ? root.dragHeight : Math.min(panelContent.implicitHeight + 32, (screen?.height || 720) - 24)
        margins {
            left: root.dragging ? root.dragOriginX : Math.max(12, Math.min((panel.screen?.width || 420) - panel.width - 12, root.dragged ? root.desktopX - root.currentMonitor.x : root.anchorX - panel.width / 2))
            top: root.dragging ? root.dragOriginY : Math.max(12, Math.min((panel.screen?.height || 720) - panel.height - 12, root.dragged ? root.desktopY - root.currentMonitor.y : root.anchorBottom - panel.height - 12))
        }
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "audio-widget"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: root.opened && (root.dragging || panelHover.hovered) ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
        mask: Region { width: root.opened ? panel.width : 0; height: root.opened ? panel.height : 0; radius: card.radius }

        Shortcut { sequence: "Escape"; onActivated: root.hide() }

        Connections {
            target: card.Window.window
            function onFrameSwapped() {
                if (!root.dropping || !root.dropFrameReady || root.dragging
                    || !panel.backingWindowVisible || card.opacity !== 1
                    || card.Screen.name !== root.dragScreen?.name) return;
                // The first queued swap can still belong to the pre-move frame.
                // Explicitly request another frame before retiring the preview.
                if (++root.dropFrames < 2) card.Window.window.update();
                else root.finishDrop();
            }
        }

        Rectangle {
            id: card
            anchors.fill: parent
            opacity: root.dragging && root.dragImage ? 0 : root.opened ? 1 : 0
            Behavior on opacity {
                enabled: !root.dragging && root.dragImage === null
                NumberAnimation {
                    duration: (root.opened ? root.pointerState.fades?.in : root.pointerState.fades?.out)?.duration ?? 500
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: (root.opened ? root.pointerState.fades?.in : root.pointerState.fades?.out)?.curve || [0.22, 1, 0.36, 1, 1, 1]
                }
            }
            radius: 12
            color: theme.background
            border.color: theme.border
            border.width: 1
            HoverHandler {
                id: panelHover
                onHoveredChanged: {
                    if (hovered) autoHide.stop();
                    else if (!root.pinned && !root.barHovered) autoHide.restart();
                }
            }
            TapHandler { onTapped: root.pinned = true }

            // Include title whitespace and padding without grabbing the close button.
            Item {
                id: headerDragArea
                width: card.width
                height: panelContent.y + header.height + panelContent.spacing
                containmentMask: QtObject {
                    function contains(point: point): bool {
                        const close = closeButton.mapFromItem(headerDragArea, point.x, point.y);
                        return point.x >= 0 && point.x < headerDragArea.width
                            && point.y >= 0 && point.y < headerDragArea.height
                            && !(close.x >= 0 && close.x < closeButton.width
                                 && close.y >= 0 && close.y < closeButton.height);
                    }
                }
                DragHandler {
                    target: null
                    acceptedButtons: Qt.LeftButton
                    onActiveChanged: {
                        if (active) {
                            root.finishDrop();
                            root.dragOriginX = panel.margins.left;
                            root.dragOriginY = panel.margins.top;
                            root.dragWidth = panel.width;
                            root.dragHeight = panel.height;
                            root.dragScreen = root.targetScreen;
                            const generation = ++root.dragGeneration;
                            root.dragging = true;
                            root.pinned = true;
                            root.grabX = centroid.scenePressPosition.x;
                            root.grabY = centroid.scenePressPosition.y;
                            root.desktopX = root.currentMonitor.x + panel.margins.left;
                            root.desktopY = root.currentMonitor.y + panel.margins.top;
                            card.grabToImage(result => {
                                if (root.dragging && root.dragGeneration === generation) root.dragImage = result;
                            });
                            pointerObserver.write("drag-start\n");
                        }
                        else root.stopDrag({x: root.currentMonitor.x + panel.margins.left + centroid.scenePosition.x,
                                            y: root.currentMonitor.y + panel.margins.top + centroid.scenePosition.y});
                    }
                }
            }

            ColumnLayout {
                id: panelContent
                x: 16
                y: 16
                width: parent.width - 32
                height: parent.height - 32
                spacing: 10

                RowLayout {
                    id: header
                    Layout.fillWidth: true
                    Label {
                        text: "Audio"
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                        color: theme.text
                        font.family: theme.font
                        Layout.fillWidth: true
                    }
                    NetworkButton { id: closeButton; theme: root.theme; symbol: "close"; text: "Close"; onClicked: root.hide() }
                }

                Label { Layout.topMargin: 4; text: "Master"; color: theme.muted; font.family: theme.font; font.pixelSize: 11 }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: masterContents.implicitHeight + 24
                    color: theme.surface
                    radius: 10
                    ColumnLayout {
                        id: masterContents
                        x: 12; y: 12
                        width: parent.width - 24
                        spacing: 4
                        AudioGroup {
                            Layout.fillWidth: true
                            theme: root.theme; title: "Output"; nodes: root.activeOutput ? [root.activeOutput] : []
                            peak: root.levels.__output || 0
                            embedded: true
                            detail: root.activeOutput?.description || "No output device available"
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: theme.background }
                        AudioGroup {
                            Layout.fillWidth: true
                            theme: root.theme; title: "BRIO microphone"; nodes: root.inputs
                            microphone: true
                            embedded: true
                            detail: (nodes.map(n => n.description || n.name).join(" · ") || "No devices available")
                        }
                    }
                }
                Label { Layout.topMargin: 4; text: "Clients"; color: theme.muted; font.family: theme.font; font.pixelSize: 11 }
                ScrollView {
                    id: clientsScroll
                    padding: 0
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: Math.min(playback.implicitHeight, 260)
                    contentWidth: availableWidth
                    clip: true
                    Column {
                        id: playback
                        width: clientsScroll.availableWidth
                        spacing: 8
                        Label {
                            visible: root.clients.length === 0
                            text: "No playback clients"
                            color: theme.muted; font.family: theme.font; font.pixelSize: 12
                        }
                        Repeater {
                            model: root.clientGroups
                            AudioGroup {
                                required property var modelData
                                width: playback.width
                                theme: root.theme
                                title: modelData.title
                                nodes: modelData.nodes
                                peak: root.levels[modelData.title] || 0
                            }
                        }
                    }
                }
                Label {
                    visible: root.message !== ""
                    text: root.message; textFormat: Text.PlainText
                    color: theme.error; font.family: theme.font; font.pixelSize: 12
                    Layout.fillWidth: true; wrapMode: Text.Wrap
                }
                Button {
                    id: headphonesButton
                    Layout.topMargin: 4
                    Layout.fillWidth: true
                    implicitHeight: 48
                    hoverEnabled: true
                    Accessible.name: text
                    contentItem: RowLayout {
                        spacing: 10
                        Item { Layout.fillWidth: true }
                        Label { text: "headphones"; font.family: "Material Symbols Rounded"; font.pixelSize: 26; color: root.headphones ? theme.accent : theme.text }
                        Label { text: "HEADPHONES"; font.family: theme.font; font.pixelSize: 13; font.weight: Font.DemiBold; color: root.headphones ? theme.accent : theme.text }
                        Item { Layout.fillWidth: true }
                    }
                    text: root.headphones ? "Headphones · switch to Screen" : "Screen · switch to Headphones"
                    enabled: !!root.usb && !!root.screenOutput && !routing.running
                    onClicked: { root.message = ""; routing.running = true; }
                    background: Rectangle { radius: 8; color: root.headphones ? Qt.alpha(theme.accent, 0.22) : theme.surface; border.color: root.headphones ? theme.accent : "transparent" }
                }
            }
        }
    }
}
