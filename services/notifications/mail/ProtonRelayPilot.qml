import QtQuick
import Quickshell
import Quickshell.Io

// Dormant receiver matching the native-host's restricted Unix socket probe.
// NOT instantiated by NotificationsService or shell.qml. Remains disabled
// even if manually instantiated until a separate operator-approved change.
// The response is constant and discloses no account, notification, or mail.
Item {
    id: root
    visible: false

    readonly property string runtimeDir: String(Quickshell.env("XDG_RUNTIME_DIR") || "")
    readonly property string socketPath: runtimeDir === ""
        ? "" : runtimeDir + "/post-apollo-proton-relay.sock"

    SocketServer {
        id: relayServer
        active: false
        path: root.socketPath

        handler: Socket {
            id: connection

            parser: SplitParser {
                onRead: message => {
                    // Never log or deserialize arbitrary lengthy local messages.
                    if (typeof message !== "string" || message.length > 128) {
                        connection.connected = false;
                        return;
                    }
                    let request;
                    try {
                        request = JSON.parse(message);
                    } catch (_) {
                        connection.connected = false;
                        return;
                    }
                    if (!request || typeof request !== "object"
                            || Object.keys(request).length !== 2
                            || request.protocol !== 1
                            || request.kind !== "PROTON_RELAY_PROBE") {
                        connection.connected = false;
                        return;
                    }
                    connection.write(
                        '{"protocol":1,"kind":"PROTON_RELAY_ACK",'
                        + '"mailboxAccess":false,'
                        + '"messageIdentityVerified":false,"capabilities":[]}\n');
                    connection.flush();
                }
            }
        }
    }
}
