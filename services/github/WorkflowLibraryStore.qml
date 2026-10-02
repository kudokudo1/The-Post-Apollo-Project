import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    required property var githubService

    property var queue: []
    property var savedSets: []

    readonly property string repoSlug:
        githubService ? String(githubService.repoSlug || "") : ""

    readonly property var workflows:
        githubService && Array.isArray(githubService.workflows)
        ? githubService.workflows
        : []

    readonly property var repoSets:
        savedSets.filter(function(set) {
            return String(set.repository || "") === root.repoSlug;
        })

    readonly property int missingQueueCount:
        queue.filter(function(item) {
            return !root.workflowAvailable(item.path);
        }).length

    function workflowAvailable(path) {
        const target = String(path || "");

        for (let i = 0; i < workflows.length; ++i) {
            if (String(workflows[i].path || "") === target)
                return true;
        }

        return false;
    }

    function addWorkflow(workflow) {
        if (!workflow)
            return;

        const path = String(workflow.path || "");
        if (!path)
            return;

        queue = queue.concat([{
            path: path,
            name: String(workflow.name || path)
        }]);
    }

    function removeQueueIndex(index) {
        const next = queue.slice();
        next.splice(index, 1);
        queue = next;
    }

    function moveQueueIndex(index, delta) {
        const target = index + delta;

        if (index < 0 || index >= queue.length
                || target < 0 || target >= queue.length)
            return;

        const next = queue.slice();
        const item = next[index];

        next.splice(index, 1);
        next.splice(target, 0, item);
        queue = next;
    }

    function clearQueue() {
        queue = [];
    }

    function runQueue() {
        if (!githubService || queue.length === 0 || missingQueueCount > 0)
            return;

        githubService.runWorkflowBatch(
            queue.map(function(item) {
                return String(item.path || "");
            })
        );
    }

    function globalSetIndex(repository, name) {
        for (let i = 0; i < savedSets.length; ++i) {
            if (String(savedSets[i].repository || "") === repository
                    && String(savedSets[i].name || "") === name)
                return i;
        }

        return -1;
    }

    function saveQueueAsSet(name) {
        const clean = String(name || "").trim();

        if (!clean || !repoSlug || queue.length === 0)
            return;

        const record = {
            repository: repoSlug,
            name: clean,
            items: queue.map(function(item) {
                return {
                    path: String(item.path || ""),
                    name: String(item.name || item.path || "")
                };
            })
        };

        const next = savedSets.slice();
        const existing = globalSetIndex(repoSlug, clean);

        if (existing >= 0)
            next[existing] = record;
        else
            next.push(record);

        savedSets = next;
        persistSets();
    }

    function loadSet(setRecord) {
        if (!setRecord || !Array.isArray(setRecord.items))
            return;

        queue = setRecord.items.map(function(item) {
            return {
                path: String(item.path || ""),
                name: String(item.name || item.path || "")
            };
        });
    }

    function deleteSet(setRecord) {
        if (!setRecord)
            return;

        const index = globalSetIndex(
            String(setRecord.repository || ""),
            String(setRecord.name || "")
        );

        if (index < 0)
            return;

        const next = savedSets.slice();
        next.splice(index, 1);
        savedSets = next;
        persistSets();
    }

    function setMissingCount(setRecord) {
        if (!setRecord || !Array.isArray(setRecord.items))
            return 0;

        return setRecord.items.filter(function(item) {
            return !workflowAvailable(item.path);
        }).length;
    }

    function runSet(setRecord) {
        if (!githubService || !setRecord
                || !Array.isArray(setRecord.items)
                || setRecord.items.length === 0
                || setMissingCount(setRecord) > 0)
            return;

        githubService.runWorkflowBatch(
            setRecord.items.map(function(item) {
                return String(item.path || "");
            })
        );
    }

    function loadSetsFromDisk() {
        const raw = String(setsFile.text() || "").trim();

        if (!raw) {
            savedSets = [];
            return;
        }

        try {
            const parsed = JSON.parse(raw);
            savedSets = parsed && Array.isArray(parsed.sets)
                        ? parsed.sets
                        : [];
        } catch (error) {
            savedSets = [];
        }
    }

    function persistSets() {
        setsFile.setText(JSON.stringify({
            version: 1,
            sets: savedSets
        }, null, 2));
    }

    FileView {
        id: setsFile

        path: Qt.resolvedUrl("../../workflow-sets.json")
        blockWrites: true
        atomicWrites: true
        printErrors: false

        onLoaded: root.loadSetsFromDisk()
    }
}
