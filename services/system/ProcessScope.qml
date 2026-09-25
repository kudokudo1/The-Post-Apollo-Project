import QtQuick

QtObject {
    id: processScope

    // Generic PID-scope helpers only. This object does not decide what an
    // application/window/tab/RUN record semantically is; provider/identity
    // layers resolve their roots, then this helper expands concrete PID scope.

    function uniquePositivePids(values) {
        const source = Array.isArray(values) ? values : [];
        const seen = ({});
        const result = [];

        for (let i = 0; i < source.length; i++) {
            const pid = Number(source[i] || 0);

            if (pid <= 1 || seen[String(pid)])
                continue;

            seen[String(pid)] = true;
            result.push(pid);
        }

        return result;
    }

    function rowForPid(rows, pid) {
        const wanted = Number(pid || 0);

        if (wanted <= 1)
            return null;

        const source = Array.isArray(rows) ? rows : [];

        for (let i = 0; i < source.length; i++) {
            const row = source[i];

            if (Number(row && row.pid || 0) === wanted)
                return row;
        }

        return null;
    }

    function treeRowsForRoots(rows, rootPids) {
        const roots = uniquePositivePids(rootPids);

        if (roots.length === 0)
            return [];

        const source = Array.isArray(rows) ? rows : [];
        const wanted = ({});

        for (let i = 0; i < roots.length; i++)
            wanted[String(roots[i])] = true;

        let changed = true;
        let guard = 0;

        while (changed && guard < 64) {
            changed = false;
            guard++;

            for (let i = 0; i < source.length; i++) {
                const row = source[i];
                const pid = Number(row && row.pid || 0);
                const ppid = Number(row && row.ppid || 0);

                if (pid > 1
                        && wanted[String(ppid)]
                        && !wanted[String(pid)]) {
                    wanted[String(pid)] = true;
                    changed = true;
                }
            }
        }

        const result = [];

        for (let i = 0; i < source.length; i++) {
            const row = source[i];

            if (wanted[String(Number(row && row.pid || 0))])
                result.push(row);
        }

        return result;
    }

    function pidsForRoots(rows, rootPids) {
        return treeRowsForRoots(rows, rootPids).map(function(row) {
            return Number(row && row.pid || 0);
        }).filter(function(pid) {
            return pid > 1;
        });
    }

    function includesPid(rows, pid) {
        return rowForPid(rows, pid) !== null;
    }
}
