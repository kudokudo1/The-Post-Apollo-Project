import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.I3

// Shared, read-only compositor snapshot. One process and one event listener.
// Last good data may remain visible; safety consumers require a settled probe.
Scope {
    id: root
    property bool enabled: false
    readonly property var windows: snapshot.windows
    readonly property var outputNames: snapshot.outputs
    property var snapshot: ({windows: [], outputs: []})
    property bool ready: false
    property string error: ""
    property bool loading: false
    property bool pending: false
    property bool exited: false
    property bool stdoutDone: false
    property bool stderrDone: false
    property int exitCode: -1
    property int exitStatus: -1
    property string stdoutText: ""
    property string stderrText: ""
    readonly property bool settled: enabled && ready && !error && !loading && !pending
    signal snapshotPublished()

    function collectSwayOutputNames(node, names) {
        if (!node)
            return;

        if (node.type === "output"
                && node.name
                && String(node.name).indexOf("__") !== 0
                && names.indexOf(String(node.name)) === -1) {
            names.push(String(node.name));
        }

        const children = node.nodes || [];

        for (let i = 0; i < children.length; i++)
            collectSwayOutputNames(children[i], names);

        const floatingChildren = node.floating_nodes || [];

        for (let i = 0; i < floatingChildren.length; i++)
            collectSwayOutputNames(floatingChildren[i], names);
    }

    function collectSwayWindows(
        node,
        currentWorkspace,
        currentOutput,
        output,
        inheritedFloating,
        inheritedTabbed,
        inheritedTabGroupId,
        inheritedTabGroupName
    ) {
        if (!node)
            return;

        let workspace = currentWorkspace || "";
        let outputName = currentOutput || "";
        let floatingContext = !!inheritedFloating;
        let tabbedContext = !!inheritedTabbed;
        let tabGroupId = Number(inheritedTabGroupId || 0);
        let tabGroupName = String(inheritedTabGroupName || "");

        if (node.type === "output"
                && node.name
                && String(node.name).indexOf("__") !== 0)
            outputName = String(node.name);

        if (node.type === "workspace")
            workspace = node.name || workspace;

        // Sway commonly wraps floating clients in a floating_con. The client
        // child itself may report floating:auto_off, so carry the state down.
        if (node.type === "floating_con"
                || String(node.floating || "").indexOf("_on") !== -1)
            floatingContext = true;

        // A client can sit several levels below the container that actually
        // owns the tabbed layout, so carry tab-group ancestry down the tree.
        //
        // Sway normally reports layout:"tabbed". Some tree shapes are easier
        // to recognize from representation:"T[...]", so support both.
        const nodeLayout =
            String(node.layout || "").trim().toLowerCase();
        const nodeRepresentation =
            String(node.representation || "").trim();

        const beginsTabbedRepresentation =
            nodeRepresentation.toUpperCase().indexOf("T[") === 0;

        if (nodeLayout === "tabbed" || beginsTabbedRepresentation) {
            tabbedContext = true;

            if (node.id)
                tabGroupId = Number(node.id);

            tabGroupName =
                String(node.name || workspace || "TABS");
        }

        const properties = node.window_properties || {};
        const appId = node.app_id || "";
        const className = properties.class || "";
        const instance = properties.instance || "";
        const hasIdentity = appId || className || instance;
        const hasLiveClient = !!node.pid && !!node.name;

        // Include ordinary tiled clients AND floating/centered clients whose
        // compositor identity fields are sparse but still have a live pid/title.
        if (node.type === "con" && (hasIdentity || hasLiveClient)) {
            output.push({
                id: node.id || 0,
                name: node.name || "",
                appId: appId,
                className: className,
                instance: instance,
                pid: node.pid || 0,
                focused: !!node.focused,
                workspace: workspace,
                output: outputName,
                floating: floatingContext,
                tabbed: tabbedContext || tabGroupId !== 0,
                tabGroupId: tabGroupId,
                tabGroupName: tabGroupName,
                fullscreen: Number(node.fullscreen_mode || 0) !== 0,
                rect: node.rect || {}
            });
        }

        const children = node.nodes || [];

        for (let i = 0; i < children.length; i++) {
            collectSwayWindows(
                children[i],
                workspace,
                outputName,
                output,
                floatingContext,
                tabbedContext,
                tabGroupId,
                tabGroupName
            );
        }

        const floatingChildren = node.floating_nodes || [];

        for (let i = 0; i < floatingChildren.length; i++) {
            collectSwayWindows(
                floatingChildren[i],
                workspace,
                outputName,
                output,
                true,
                tabbedContext,
                tabGroupId,
                tabGroupName
            );
        }
    }

    function parseSnapshot(rawText) {
        const tree = JSON.parse(rawText);
        if (!tree || tree.type !== "root" || !Array.isArray(tree.nodes))
            throw new Error("Invalid Sway tree");
        const windows = [], outputs = [];
        collectSwayOutputNames(tree, outputs);
        collectSwayWindows(tree, "", "", windows, false, false, 0, "");
        return {windows:windows, outputs:outputs};
    }

    function refresh() {
        if (!enabled) return false;
        if (loading || swayTreeProcess.running) {
            pending = true;
            return false;
        }
        pending = false;
        loading = true;
        exited = false;
        stdoutDone = false;
        stderrDone = false;
        exitCode = -1;
        exitStatus = -1;
        stdoutText = "";
        stderrText = "";
        swayTreeProcess.exec(["swaymsg", "-t", "get_tree"]);
        return true;
    }

    function maybeFinish() {
        if (!loading || !exited || !stdoutDone || !stderrDone) return;
        if (exitCode !== 0 || exitStatus !== 0 || stderrText.trim()) {
            ready = false;
            error = stderrText.trim() || "Sway tree query failed";
        } else {
            try {
                const next = parseSnapshot(stdoutText);
                snapshot = next;
                ready = true;
                error = "";
                snapshotPublished();
            } catch (err) {
                ready = false;
                error = String(err);
            }
        }
        loading = false;
        if (pending && enabled) Qt.callLater(function() { if (root.pending) root.refresh(); });
    }

    Process {
        id: swayTreeProcess
        onExited: function(code, status) {
            root.exitCode = code;
            root.exitStatus = status;
            root.exited = true;
            root.maybeFinish();
        }
        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = String(text || "");
                root.stdoutDone = true;
                root.maybeFinish();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                root.stderrText = String(text || "");
                root.stderrDone = true;
                root.maybeFinish();
            }
        }
    }

    I3IpcListener {
        subscriptions: ["window", "workspace"]
        onIpcEvent: function(event) { root.refresh(); }
    }
}
