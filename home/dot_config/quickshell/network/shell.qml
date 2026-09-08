import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

ShellRoot {
    id: root
    property bool opened: Quickshell.env("NETWORK_WIDGET_MODE") !== "ensure"
    property bool pinned: Quickshell.env("NETWORK_WIDGET_MODE") !== "ensure"
    property bool barHovered: false
    property bool suppressHover: false
    property var pointerState: ({ cursor: null, monitors: [], anchor: null })
    property bool dragging: false
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
    property bool busy: false
    property bool hasState: false
    property string operation: "status"
    property bool scanMessageReady: false
    readonly property bool showProgress: busy && (operation === "scan" ? scanMessageReady : operation !== "status" || !hasState)
    onBusyChanged: {
        if (!busy) { scanMessageDelay.stop(); scanMessageReady = false; }
    }
    property var state: ({ enabled: false, devices: [], networks: [] })
    property var traffic: ({})
    property var selected: null
    property string message: ""
    property string pending: ""
    property var targetScreen: null
    property real anchorX: 210
    property real anchorBottom: 700
    readonly property var connectedDevices: state.devices.filter(device => device.state === "connected")

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
        opened = false;
        pinned = false;
        suppressHover = barHovered;
        selected = null;
        password.text = "";
    }

    function toggle(anchor) {
        if (opened && !pinned) { pinned = true; return; }
        if (opened) { hide(); return; }
        chooseScreen(anchor || {});
        opened = true;
        pinned = true;
        run({ action: "status" });
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
                run({ action: "status" });
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
        if (dragging && cursor) movePanel(cursor);
        if (dragging) {
            targetScreen = dragScreen || targetScreen;
            dragged = true;
        }
        dragging = false;
        dragImage = null;
        pointerObserver.write("drag-stop\n");
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

    function run(request) {
        if (busy) return;
        operation = request.action;
        scanMessageReady = false;
        busy = true;
        if (operation === "scan") scanMessageDelay.restart();
        if (request.action !== "status") message = "";
        pending = JSON.stringify(request);
        backend.stdinEnabled = true;
        backend.running = true;
    }

    Timer {
        id: scanMessageDelay
        interval: 1000
        onTriggered: { if (root.busy && root.operation === "scan") root.scanMessageReady = true; }
    }

    function connectSelected() {
        if (!selected || busy) return;
        run({ action: "connect", interface: selected.interface, bssid: selected.bssid, password: password.text });
        password.text = "";
        selected = null;
    }

    Component.onCompleted: {
        try { chooseScreen(JSON.parse(Quickshell.env("NETWORK_WIDGET_ANCHOR") || "{}")); }
        catch (_) { chooseScreen({}); }
        if (opened) run({ action: "status" });
    }

    IpcHandler {
        target: "network"
        function toggle(): void { root.toggle(); }
        function toggleAt(anchor: string): void { root.toggle(JSON.parse(anchor)); }
        function close(): void { root.hide(); }
        function isOpen(): bool { return root.opened; }
        function geometry(): string {
            return JSON.stringify({ screen: root.targetScreen?.name, x: panel.margins.left, y: panel.margins.top,
                width: panel.width, height: panel.height, anchorX: root.anchorX, barTop: root.anchorBottom,
                hovered: panelHover.hovered, keyboardFocus: panel.WlrLayershell.keyboardFocus,
                pinned: root.pinned, barHovered: root.barHovered, opened: root.opened, dragging: root.dragging,
                dragScreen: root.dragScreen?.name, desktopX: root.desktopX, desktopY: root.desktopY });
        }
    }

    Process {
        id: backend
        command: ["python3", Qt.resolvedUrl("network.py").toString().replace("file://", "")]
        onStarted: {
            write(root.pending + "\n");
            root.pending = "";
            stdinEnabled = false;
        }
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    if (result.ok) {
                        root.state = result;
                        root.hasState = true;
                        root.message = "";
                    }
                    else root.message = result.error;
                } catch (_) {
                    root.message = "Could not read network status. Check that Python 3 and nmcli are installed.";
                }
            }
        }
        onExited: (code, status) => {
            root.pending = "";
            root.busy = false;
            if (code !== 0) root.message = "The networking helper stopped unexpectedly.";
        }
    }

    Timer {
        interval: 10000
        repeat: true
        running: root.opened
        onTriggered: root.run({ action: "status" })
    }

    Process {
        command: ["python3", Qt.resolvedUrl("network.py").toString().replace("file://", ""), "traffic"]
        running: root.opened
        stdout: SplitParser {
            onRead: line => {
                try { root.traffic = JSON.parse(line); }
                catch (_) { root.traffic = ({}); }
            }
        }
    }

    // Keep the real surface and its implicit mouse grab on the original output.
    // Only this non-interactive image crosses outputs until the button releases.
    PanelWindow {
        visible: root.dragging && root.dragImage !== null
        screen: root.dragScreen
        anchors { top: true; left: true }
        implicitWidth: panel.width
        implicitHeight: panel.height
        readonly property var monitor: root.pointerState.monitors.find(item => item.name === screen?.name) || ({x: 0, y: 0})
        margins.left: Math.max(12, Math.min((screen?.width || 420) - width - 12, root.desktopX - monitor.x))
        margins.top: Math.max(12, Math.min((screen?.height || 720) - height - 12, root.desktopY - monitor.y))
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "network-widget"
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
        implicitWidth: root.dragging ? root.dragWidth : Math.min(420, (screen?.width || 420) - 24)
        implicitHeight: root.dragging ? root.dragHeight : Math.min(panelContent.implicitHeight + 24, (screen?.height || 720) - 24)
        margins {
            left: root.dragging ? root.dragOriginX : Math.max(12, Math.min((panel.screen?.width || 420) - panel.width - 12, root.dragged ? root.desktopX - root.currentMonitor.x : root.anchorX - panel.width / 2))
            top: root.dragging ? root.dragOriginY : Math.max(12, Math.min((panel.screen?.height || 720) - panel.height - 12, root.dragged ? root.desktopY - root.currentMonitor.y : root.anchorBottom - panel.height - 12))
        }
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "network-widget"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: root.opened && (root.dragging || panelHover.hovered) ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
        mask: Region { width: root.opened ? panel.width : 0; height: root.opened ? panel.height : 0; radius: card.radius }

        Shortcut { sequence: "Escape"; onActivated: root.hide() }

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
                x: 12
                y: 12
                width: parent.width - 24
                height: parent.height - 24
                spacing: 10

                RowLayout {
                    id: header
                    Layout.fillWidth: true
                    Label {
                        text: "Networking"
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                        color: theme.text
                        font.family: theme.font
                        Layout.fillWidth: true
                    }
                    NetworkButton { id: closeButton; theme: root.theme; symbol: "close"; text: "Close"; onClicked: root.hide() }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: theme.surface }

                ColumnLayout {
                    id: body
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 12

                    Repeater {
                        model: root.connectedDevices
                        delegate: ConnectionCard {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: implicitHeight
                            theme: root.theme
                            device: modelData
                            networks: root.state.networks
                            traffic: root.traffic[modelData.interface] || ({})
                            defaultDns: root.state.defaultDns || []
                            busy: root.busy
                            onDisconnectRequested: root.run({ action: "disconnect", interface: modelData.interface })
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 6
                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                text: root.state.enabled ? "Wi-Fi networks" : "Wi-Fi is off"
                                font.family: theme.font
                                font.pixelSize: 13
                                color: theme.text
                                Layout.fillWidth: true
                            }
                            NetworkButton {
                                theme: root.theme
                                symbol: "refresh"
                                text: "Scan for networks"
                                enabled: !root.busy && root.state.enabled
                                onClicked: root.run({ action: "scan" })
                            }
                            NetworkButton {
                                theme: root.theme
                                symbol: "power_settings_new"
                                text: root.state.enabled ? "Turn Wi-Fi off" : "Turn Wi-Fi on"
                                accented: root.state.enabled
                                enabled: !root.busy
                                onClicked: root.run({ action: "radio", enabled: !root.state.enabled })
                            }
                        }

                        ScrollView {
                            id: wifiScroll
                            Layout.fillWidth: true
                            Layout.rightMargin: -6
                            Layout.fillHeight: true
                            Layout.minimumHeight: 0
                            Layout.preferredHeight: root.hasState ? Math.min(wifiItems.implicitHeight, 260) : 80
                            contentWidth: availableWidth
                            contentHeight: wifiItems.implicitHeight
                            clip: true
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            ScrollBar.vertical: ScrollBar {
                                id: wifiBar
                                parent: wifiScroll
                                x: wifiScroll.width - width
                                y: 0
                                height: wifiScroll.height
                                width: 6
                                padding: 0
                                policy: ScrollBar.AsNeeded
                                contentItem: Rectangle {
                                    implicitWidth: 6
                                    radius: 3
                                    color: wifiBar.pressed ? "#555555" : wifiBar.hovered ? "#484848" : "#383838"
                                }
                                background: Item {}
                            }

                            Column {
                                id: wifiItems
                                width: wifiScroll.availableWidth - 12
                                spacing: 6
                                opacity: root.showProgress || root.message !== "" ? 0 : 1
                                enabled: !root.showProgress && root.message === ""
                                Label {
                                    width: parent.width
                                    visible: !root.state.networks.some(network => !network.active)
                                    text: !root.state.devices.some(device => device.kind === "wifi")
                                        ? "No Wi-Fi adapter found."
                                        : !root.state.enabled ? "Turn on Wi-Fi to find networks."
                                        : root.state.networks.length ? "No other networks nearby" : "No networks found · try scanning"
                                    color: theme.text
                                    opacity: 0.65
                                    font.family: theme.font
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                }

                                Repeater {
                                    model: root.state.networks.filter(network => !network.active)
                                    delegate: Button {
                                        id: networkRow
                                        required property var modelData
                                        width: wifiItems.width
                                        padding: 10
                                        hoverEnabled: true
                                        focusPolicy: Qt.NoFocus
                                        enabled: !root.busy
                                        Accessible.name: "Connect to " + modelData.ssid
                                        background: Rectangle {
                                            radius: 8
                                            color: networkRow.hovered || root.selected?.bssid === networkRow.modelData.bssid ? theme.surface : "transparent"
                                        }
                                        contentItem: RowLayout {
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 2
                                                Label {
                                                    text: networkRow.modelData.ssid
                                                    textFormat: Text.PlainText
                                                    color: theme.text
                                                    font.family: theme.font
                                                    font.pixelSize: 13
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }
                                                Label {
                                                    text: networkRow.modelData.signal + "% · " + (networkRow.modelData.security || "Open") + " · " + networkRow.modelData.interface
                                                    textFormat: Text.PlainText
                                                    color: theme.text
                                                    opacity: 0.65
                                                    font.family: theme.font
                                                    font.pixelSize: 11
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }
                                            }
                                            Label { text: "chevron_right"; font.family: "Material Symbols Rounded"; font.pixelSize: 18; color: theme.text }
                                        }
                                        onClicked: {
                                            root.selected = modelData;
                                            password.text = "";
                                            password.forceActiveFocus();
                                        }
                                    }
                                }
                            }
                            Label {
                                parent: wifiScroll
                                anchors.fill: parent
                                anchors.margins: 10
                                visible: root.showProgress || root.message !== ""
                                text: root.message || (root.operation === "scan" ? "Scanning for networks…" : "Working…")
                                textFormat: Text.PlainText
                                verticalAlignment: Text.AlignVCenter
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.Wrap
                                color: root.message ? theme.error : theme.muted
                                font.family: theme.font
                                font.pixelSize: 12
                            }
                        }
                    }

                    Rectangle {
                        visible: root.selected !== null
                        Layout.fillWidth: true
                        implicitHeight: connectionForm.implicitHeight + 20
                        Layout.minimumHeight: implicitHeight
                        radius: 8
                        color: theme.surface
                        ColumnLayout {
                            id: connectionForm
                            x: 10
                            y: 10
                            width: parent.width - 20
                            spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: root.selected?.ssid || ""
                                    textFormat: Text.PlainText
                                    color: theme.accent
                                    font.family: theme.font
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                NetworkButton {
                                    theme: root.theme
                                    symbol: "close"
                                    text: "Cancel connection"
                                    onClicked: { root.selected = null; password.text = ""; }
                                }
                                NetworkButton {
                                    theme: root.theme
                                    symbol: "check"
                                    text: "Connect"
                                    accented: true
                                    enabled: !root.busy
                                    onClicked: root.connectSelected()
                                }
                            }
                            TextField {
                                id: password
                                visible: root.selected !== null && !!root.selected.security && root.selected.security !== "--"
                                Layout.fillWidth: true
                                placeholderText: "Password · blank uses saved credentials"
                                echoMode: TextInput.Password
                                color: theme.text
                                placeholderTextColor: theme.muted
                                selectionColor: theme.accent
                                font.family: theme.font
                                font.pixelSize: 12
                                padding: 10
                                enabled: !root.busy
                                background: Rectangle { color: theme.background; radius: 8; border.color: password.activeFocus ? theme.accent : theme.border }
                                onAccepted: root.connectSelected()
                            }
                        }
                    }

                    Repeater {
                        model: root.state.devices.filter(device => device.kind === "ethernet" && device.state !== "connected")
                        delegate: Column {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle { width: parent.width; height: 1; color: theme.surface }
                            RowLayout {
                                width: parent.width
                                spacing: 8
                                Label { text: "lan"; font.family: "Material Symbols Rounded"; font.pixelSize: 20; color: theme.muted }
                                Label {
                                    text: "Ethernet · " + modelData.interface + " · " + modelData.state
                                    textFormat: Text.PlainText
                                    font.family: theme.font
                                    font.pixelSize: 11
                                    color: theme.text
                                    opacity: 0.65
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                NetworkButton {
                                    theme: root.theme
                                    symbol: "link"
                                    text: "Connect Ethernet"
                                    enabled: !root.busy && !["unavailable", "unmanaged"].includes(modelData.state)
                                    onClicked: root.run({ action: "ethernet", interface: modelData.interface })
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
