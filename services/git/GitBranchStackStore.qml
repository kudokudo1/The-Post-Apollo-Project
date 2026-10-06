import QtQuick
import Quickshell
import Quickshell.Io

// Lightweight Post-Apollo branch dependency metadata.
//
// Git commit ancestry alone is not enough to preserve the operator's intended
// stack. This store records that intent without mutating Git refs. Actual
// restack/rebase operations belong to the branch operation layer.
Scope {
    id: root

    property string repositoryKey: ""
    property string trunkBranch: "main"
    property var relations: []

    signal relationRejected(string reason)

    readonly property var repositoryRelations:
        relations.filter(function(row) {
            return String((row || {}).repository || "")
                === String(root.repositoryKey || "");
        })

    function relationIndex(repository, branch) {
        const repo = String(repository || "");
        const name = String(branch || "");

        for (let i = 0; i < relations.length; ++i) {
            const row = relations[i] || {};

            if (String(row.repository || "") === repo
                    && String(row.branch || "") === name)
                return i;
        }

        return -1;
    }

    function relationFor(branch) {
        const index = relationIndex(repositoryKey, branch);
        return index >= 0 ? relations[index] : null;
    }

    function parentOf(branch) {
        const row = relationFor(branch);
        return row ? String(row.parent || "") : "";
    }

    function childrenOf(branch) {
        const needle = String(branch || "");

        return repositoryRelations
            .filter(function(row) {
                return String((row || {}).parent || "") === needle;
            })
            .map(function(row) {
                return String((row || {}).branch || "");
            });
    }

    function descendantsOf(branch) {
        const start = String(branch || "");
        const result = [];
        const visited = {};

        function visit(parent) {
            const children = root.childrenOf(parent);

            for (let i = 0; i < children.length; ++i) {
                const child = String(children[i] || "");

                if (!child || visited[child])
                    continue;

                visited[child] = true;
                result.push(child);
                visit(child);
            }
        }

        visit(start);
        return result;
    }

    function ancestorsOf(branch) {
        const start = String(branch || "");
        const result = [];
        const visited = {};
        let current = start;

        while (current) {
            const parent = parentOf(current);

            if (!parent || visited[parent])
                break;

            visited[parent] = true;
            result.push(parent);
            current = parent;
        }

        return result;
    }

    function wouldCreateCycle(branch, parent) {
        const child = String(branch || "");
        const candidateParent = String(parent || "");

        if (!child || !candidateParent)
            return false;

        if (child === candidateParent)
            return true;

        return descendantsOf(child).indexOf(candidateParent) >= 0;
    }

    function setParent(branch, parent) {
        const repo = String(repositoryKey || "").trim();
        const child = String(branch || "").trim();
        const candidateParent = String(parent || "").trim();

        if (!repo || !child) {
            relationRejected("REPOSITORY + BRANCH REQUIRED");
            return false;
        }

        if (candidateParent && wouldCreateCycle(child, candidateParent)) {
            relationRejected(
                "STACK CYCLE REFUSED // "
                + child
                + " -> "
                + candidateParent
            );
            return false;
        }

        const next = relations.slice();
        const existing = relationIndex(repo, child);

        if (!candidateParent) {
            if (existing >= 0)
                next.splice(existing, 1);

            relations = next;
            persist();
                return true;
        }

        const record = {
            repository: repo,
            branch: child,
            parent: candidateParent
        };

        if (existing >= 0)
            next[existing] = record;
        else
            next.push(record);

        relations = next;
        persist();
        return true;
    }

    function clearParent(branch) {
        return setParent(branch, "");
    }

    function removeBranch(branch) {
        const repo = String(repositoryKey || "").trim();
        const target = String(branch || "").trim();

        if (!repo || !target)
            return false;

        const next = [];

        for (let i = 0; i < relations.length; ++i) {
            const row = relations[i] || {};
            const sameRepo =
                String(row.repository || "") === repo;
            const isTarget =
                String(row.branch || "") === target;

            if (sameRepo && isTarget)
                continue;

            if (sameRepo && String(row.parent || "") === target) {
                next.push({
                    repository: repo,
                    branch: String(row.branch || ""),
                    parent: ""
                });
                continue;
            }

            next.push(row);
        }

        relations = next.filter(function(row) {
            return String((row || {}).parent || "").length > 0;
        });

        persist();
        return true;
    }

    function stackRoot(branch) {
        let current = String(branch || "");
        const visited = {};

        if (!current)
            return "";

        while (true) {
            if (visited[current])
                return current;

            visited[current] = true;

            const parent = parentOf(current);

            if (!parent)
                return current;

            current = parent;
        }
    }

    function linearStackFrom(branch) {
        const rootBranch = stackRoot(branch);

        if (!rootBranch)
            return [];

        const result = [];
        const visited = {};

        function append(node, depth) {
            const name = String(node || "");

            if (!name || visited[name])
                return;

            visited[name] = true;
            result.push({
                branch: name,
                parent: root.parentOf(name),
                depth: depth
            });

            const children = root.childrenOf(name);

            for (let i = 0; i < children.length; ++i)
                append(children[i], depth + 1);
        }

        append(rootBranch, 0);
        return result;
    }

    function load() {
        const raw = String(stackFile.text() || "").trim();

        if (!raw) {
            relations = [];
            return;
        }

        try {
            const parsed = JSON.parse(raw);

            trunkBranch =
                parsed && parsed.trunkBranch
                ? String(parsed.trunkBranch)
                : "main";

            relations =
                parsed && Array.isArray(parsed.relations)
                ? parsed.relations
                : [];
        } catch (error) {
            relations = [];
        }
    }

    function persist() {
        stackFile.setText(JSON.stringify({
            version: 1,
            trunkBranch: trunkBranch,
            relations: relations
        }, null, 2));
    }

    FileView {
        id: stackFile

        path: Qt.resolvedUrl("../../branch-stacks.json")
        blockWrites: true
        atomicWrites: true
        printErrors: false

        onLoaded: root.load()
    }
}
