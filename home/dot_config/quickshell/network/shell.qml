import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

ShellRoot {
    id: root
    property bool opened: true
    property bool busy: false
    property bool hasState: false
    property string operation: "status"
    readonly property bool showProgress: busy && (operation !== "status" || !hasState)
    property var state: ({ enabled: false, devices: [], networks: [] })
    property var selected: null
    property string message: ""
    property string pending: ""
    property var targetScreen: null
    property real anchorX: 210
    property real anchorBottom: 700
    property real dragX: 0
    property real dragY: 0
    readonly property var connectedDevices: state.devices.filter(device => device.state === "connected")

    readonly property alias theme: widgetTheme
    Theme { id: widgetTheme }

    function chooseScreen(anchor) {
        const name = anchor.screen || Hyprland.focusedMonitor?.name;
        targetScreen = Quickshell.screens.find(screen => screen.name === name) || Quickshell.screens[0];
        anchorX = anchor.x !== undefined ? anchor.x : (targetScreen ? targetScreen.width / 2 : 210);
        anchorBottom = anchor.bottom !== undefined ? anchor.bottom : (targetScreen ? targetScreen.height - 60 : 700);
        dragX = 0;
        dragY = 0;
    }

    function hide() {
        opened = false;
        selected = null;
        password.text = "";
    }

    function toggle(anchor) {
        if (opened) { hide(); return; }
        chooseScreen(anchor || {});
        opened = true;
        run({ action: "status" });
    }

    function run(request) {
        if (busy) return;
        busy = true;
        operation = request.action;
        if (request.action !== "status") message = "";
        pending = JSON.stringify(request);
        backend.stdinEnabled = true;
        backend.running = true;
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
        run({ action: "status" });
    }

    IpcHandler {
        target: "network"
        function toggle(): void { root.toggle(); }
        function toggleAt(anchor: string): void { root.toggle(JSON.parse(anchor)); }
        function close(): void { root.hide(); }
        function isOpen(): bool { return root.opened; }
        function geometry(): string {
            return JSON.stringify({ screen: root.targetScreen?.name, x: card.x, y: card.y,
                width: card.width, height: card.height, anchorX: root.anchorX, barTop: root.anchorBottom });
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

    PanelWindow {
        id: panel
        visible: root.opened
        screen: root.targetScreen
        anchors { top: true; bottom: true; left: true; right: true }
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "network-widget"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
        // Only the visible card receives pointer input, not the full-screen surface.
        mask: Region { item: card; radius: card.radius }

        Shortcut { sequence: "Escape"; onActivated: root.hide() }

        Rectangle {
            id: card
            width: Math.min(420, panel.width - 24)
            height: Math.min(680, panel.height - 24,
                160 + root.state.devices.filter(device => device.kind === "ethernet").length * 50
                + Math.max(70, root.state.networks.length * 66)
                + (root.showProgress || root.message !== "" ? 72 : 0)
                + (root.selected !== null ? 150 : 0)
                + root.connectedDevices.length * 150)
            x: Math.max(12, Math.min(panel.width - width - 12, root.anchorX - width / 2 + root.dragX))
            y: Math.max(12, Math.min(panel.height - height - 12, root.anchorBottom - height - 12 + root.dragY))
            radius: 12
            color: Qt.alpha(theme.background, 0.95)
            border.color: theme.surface
            border.width: 2

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: "Networking"
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        color: theme.text
                        font.family: theme.font
                        Layout.fillWidth: true
                        DragHandler {
                            target: null
                            onTranslationChanged: delta => {
                                root.dragX += delta.x;
                                root.dragY += delta.y;
                            }
                        }
                    }
                    NetworkButton { theme: root.theme; text: "Close"; onClicked: root.hide() }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: root.state.enabled ? "  Wi-Fi" : "  Wi-Fi off"
                        font.family: theme.font
                        font.pixelSize: 14
                        color: root.state.enabled ? theme.accent : theme.text
                        Layout.fillWidth: true
                    }
                    NetworkButton {
                        theme: root.theme
                        text: "Scan"
                        enabled: !root.busy && root.state.enabled
                        onClicked: root.run({ action: "scan" })
                    }
                    NetworkButton {
                        theme: root.theme
                        text: root.state.enabled ? "Turn off" : "Turn on"
                        enabled: !root.busy
                        onClicked: root.run({ action: "radio", enabled: !root.state.enabled })
                    }
                }

                Repeater {
                    model: root.state.devices.filter(device => device.kind === "ethernet")
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Label {
                            text: "Ethernet · " + modelData.interface + "\n" + (modelData.connection && modelData.connection !== "--" ? modelData.connection + " · " : "") + modelData.state
                            textFormat: Text.PlainText
                            font.family: theme.font
                            font.pixelSize: 14
                            color: theme.text
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        NetworkButton {
                            theme: root.theme
                            text: modelData.state === "connected" ? "Disconnect" : "Connect"
                            enabled: !root.busy && !["unavailable", "unmanaged"].includes(modelData.state)
                            onClicked: root.run({ action: modelData.state === "connected" ? "disconnect" : "ethernet", interface: modelData.interface })
                        }
                    }
                }

                Label {
                    visible: root.showProgress || root.message !== ""
                    text: root.showProgress ? "Working…" : root.message
                    textFormat: Text.PlainText
                    color: root.message !== "" && !root.showProgress ? theme.error : theme.text
                    font.family: theme.font
                    font.pixelSize: 13
                    wrapMode: Text.Wrap
                    maximumLineCount: 4
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Repeater {
                    model: root.connectedDevices
                    delegate: NetworkStats {
                        required property var modelData
                        theme: root.theme
                        device: modelData
                        Layout.fillWidth: true
                    }
                }

                ScrollView {
                    id: networkScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: Math.max(70, root.state.networks.length * 66)
                    Layout.minimumHeight: 70
                    contentWidth: availableWidth
                    clip: true
                    ColumnLayout {
                        id: networkList
                        width: networkScroll.availableWidth
                        spacing: 6
                        Label {
                            visible: root.state.networks.length === 0 && !root.busy
                            text: !root.state.devices.some(device => device.kind === "wifi") ? "No Wi-Fi adapter found." : !root.state.enabled ? "Turn on Wi-Fi to find networks." : "No networks found. Try scanning again."
                            color: theme.text
                            font.family: theme.font
                            font.pixelSize: 14
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                        Repeater {
                            model: root.state.networks
                            delegate: Button {
                                id: networkRow
                                required property var modelData
                                Layout.fillWidth: true
                                padding: 12
                                hoverEnabled: true
                                enabled: !root.busy
                                background: Rectangle {
                                    radius: 10
                                    color: networkRow.hovered ? theme.surface : "transparent"
                                    border.width: networkRow.activeFocus || root.selected?.bssid === networkRow.modelData.bssid ? 1 : 0
                                    border.color: theme.accent
                                }
                                contentItem: ColumnLayout {
                                    spacing: 4
                                    Label {
                                        text: (networkRow.modelData.active ? "●  " : "") + networkRow.modelData.ssid
                                        textFormat: Text.PlainText
                                        color: networkRow.modelData.active ? theme.accent : theme.text
                                        font.family: theme.font
                                        font.pixelSize: 14
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        text: (networkRow.modelData.active ? "Connected · " : "") + networkRow.modelData.signal + "% · " + (networkRow.modelData.security || "Open") + " · " + networkRow.modelData.interface
                                        textFormat: Text.PlainText
                                        color: theme.text
                                        opacity: 0.65
                                        font.family: theme.font
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }
                                onClicked: {
                                    root.selected = modelData;
                                    password.text = "";
                                    if (!modelData.active) password.forceActiveFocus();
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    visible: root.selected !== null
                    Layout.fillWidth: true
                    spacing: 8
                    Label {
                        text: root.selected?.ssid || ""
                        textFormat: Text.PlainText
                        color: theme.accent
                        font.family: theme.font
                        font.pixelSize: 14
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    TextField {
                        id: password
                        visible: root.selected !== null && !root.selected.active && !!root.selected.security && root.selected.security !== "--"
                        Layout.fillWidth: true
                        placeholderText: "Password · leave blank for saved networks"
                        echoMode: TextInput.Password
                        color: theme.text
                        placeholderTextColor: theme.muted
                        selectionColor: theme.accent
                        font.family: theme.font
                        font.pixelSize: 13
                        padding: 12
                        enabled: !root.busy
                        background: Rectangle { color: theme.surface; radius: 10; border.color: password.activeFocus ? theme.accent : theme.border }
                        onAccepted: root.connectSelected()
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Item { Layout.fillWidth: true }
                        NetworkButton {
                            theme: root.theme
                            text: "Cancel"
                            onClicked: { root.selected = null; password.text = ""; }
                        }
                        NetworkButton {
                            theme: root.theme
                            text: root.selected?.active ? "Disconnect" : "Connect"
                            accented: true
                            enabled: !root.busy
                            onClicked: {
                                if (root.selected.active) {
                                    root.run({ action: "disconnect", interface: root.selected.interface });
                                    root.selected = null;
                                } else root.connectSelected();
                            }
                        }
                    }
                }
            }
        }
    }
}
