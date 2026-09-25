import QtQuick

QtObject {
    id: processIdentity

    // Process identity only. This is deliberately narrower than Team 7's
    // DesktopEntry/application/Sway/tab semantic identity architecture.
    //
    // It preserves the donor's current Task persistent-identity semantics:
    // prefer comm/name/label, otherwise use the basename of argv[0].

    function sourceEntry(entry) {
        if (entry && entry._favoriteRecord && entry._sourceItem)
            return entry._sourceItem;

        return entry;
    }

    function persistentIdentity(entry) {
        const source = sourceEntry(entry);

        if (!source)
            return "";

        const comm =
            String(
                source.comm
                || source.name
                || source.label
                || ""
            ).trim();

        if (comm)
            return comm.toLowerCase();

        const args = String(source.args || "").trim();

        if (!args)
            return "";

        const first = args.split(/\s+/)[0] || "";
        const pieces = first.split("/");

        return String(
            pieces[pieces.length - 1] || first
        ).toLowerCase();
    }

    function pidPolicyKey(entry) {
        const source = sourceEntry(entry);
        const pid = Number(source && source.pid || 0);

        if (pid <= 1)
            return "";

        const identity = persistentIdentity(source);

        return String(pid)
               + "|"
               + String(identity || "?");
    }

    function capturedIdentity(entry) {
        const source = sourceEntry(entry);

        if (!source)
            return {
                pid: 0,
                name: "",
                identity: ""
            };

        return {
            pid: Number(source.pid || 0),
            name: String(
                source.comm
                || source.name
                || ""
            ).trim(),
            identity: persistentIdentity(source)
        };
    }

    function matchesCaptured(entry, captured) {
        const source = sourceEntry(entry);

        if (!source || !captured)
            return false;

        const pid = Number(source.pid || 0);
        const wantedPid = Number(captured.pid || 0);

        if (pid <= 1 || pid !== wantedPid)
            return false;

        const wantedIdentity =
            String(captured.identity || "").trim().toLowerCase();

        if (wantedIdentity
                && persistentIdentity(source) !== wantedIdentity)
            return false;

        const wantedName =
            String(captured.name || "").trim().toLowerCase();
        const liveName =
            String(
                source.comm
                || source.name
                || ""
            ).trim().toLowerCase();

        return !wantedName || liveName === wantedName;
    }
}
