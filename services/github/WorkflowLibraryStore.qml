import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    required property var githubService

    property var queue: []
    property var savedSets: []
    property string queueRepository: ""
    property string queueRef: ""
    property string activeProcedureName: ""

    signal procedureDispatched(string name, var procedure)

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

    readonly property bool queueRepositoryMatches:
        queue.length === 0
        || !queueRepository
        || queueRepository === repoSlug

    onRepoSlugChanged: {
        if (queue.length > 0
                && queueRepository
                && queueRepository !== repoSlug) {
            queue = [];
            queueRef = "";
        }

        queueRepository = repoSlug;
    }

    function ensureQueueRepository() {
        if (!repoSlug)
            return false;

        if (queueRepository && queueRepository !== repoSlug) {
            queue = [];
            queueRef = "";
        }

        queueRepository = repoSlug;
        return true;
    }

    function workflowAvailable(path) {
        const target = String(path || "");

        for (let i = 0; i < workflows.length; ++i) {
            if (String(workflows[i].path || "") === target)
                return true;
        }

        return false;
    }

    function addWorkflow(workflow) {
        if (!workflow || !ensureQueueRepository())
            return false;

        const path = String(workflow.path || "");
        if (!path)
            return false;

        queue = queue.concat([{
            path: path,
            name: String(workflow.name || path)
        }]);
        return true;
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
        queueRef = "";
        queueRepository = repoSlug;
    }

    function setQueueRef(value) {
        queueRef = String(value || "").trim();
    }

    function runQueue() {
        if (!githubService
                || queue.length === 0
                || missingQueueCount > 0
                || !queueRepositoryMatches
                || queueRepository !== repoSlug)
            return false;

        activeProcedureName = "AD HOC QUEUE";

        githubService.runWorkflowBatch(
            queue.map(function(item) {
                return String(item.path || "");
            }),
            queueRef
        );
        return true;
    }

    function globalSetIndex(repository, name) {
        for (let i = 0; i < savedSets.length; ++i) {
            if (String(savedSets[i].repository || "") === repository
                    && String(savedSets[i].name || "") === name)
                return i;
        }

        return -1;
    }

    function saveQueueAsSet(name, confirmedOverwrite) {
        const clean = String(name || "").trim();

        if (!clean
                || !repoSlug
                || queue.length === 0
                || queueRepository !== repoSlug)
            return false;

        const existing = globalSetIndex(repoSlug, clean);

        if (existing >= 0 && !confirmedOverwrite)
            return false;

        const record = {
            schemaVersion: 2,
            repository: repoSlug,
            name: clean,
            ref: String(queueRef || "").trim(),
            items: queue.map(function(item) {
                return {
                    path: String(item.path || ""),
                    name: String(item.name || item.path || "")
                };
            })
        };

        const next = savedSets.slice();

        if (existing >= 0)
            next[existing] = record;
        else
            next.push(record);

        savedSets = next;
        persistSets();
        return true;
    }

    function loadSet(setRecord) {
        if (!setRecord
                || !Array.isArray(setRecord.items)
                || String(setRecord.repository || "") !== repoSlug)
            return false;

        queueRepository = repoSlug;
        queueRef = String(setRecord.ref || "").trim();
        queue = setRecord.items.map(function(item) {
            return {
                path: String(item.path || ""),
                name: String(item.name || item.path || "")
            };
        });
        return true;
    }

    function deleteSet(setRecord, confirmed) {
        if (!setRecord || !confirmed)
            return false;

        const index = globalSetIndex(
            String(setRecord.repository || ""),
            String(setRecord.name || "")
        );

        if (index < 0)
            return false;

        const next = savedSets.slice();
        next.splice(index, 1);
        savedSets = next;
        persistSets();
        return true;
    }

    function setMissingCount(setRecord) {
        if (!setRecord || !Array.isArray(setRecord.items))
            return 0;

        return setRecord.items.filter(function(item) {
            return !workflowAvailable(item.path);
        }).length;
    }

    function normalizedProcedure(setRecord) {
        if (!setRecord || !Array.isArray(setRecord.items))
            return null;

        const items = setRecord.items.map(function(item) {
            const path = String(item.path || "");
            return {
                path: path,
                name: String(item.name || path),
                available: root.workflowAvailable(path)
            };
        });

        const missing = items.filter(function(item) {
            return !item.available;
        }).length;

        const repository =
            String(setRecord.repository || "");
        const repositoryMatches =
            repository === repoSlug;

        return {
            schemaVersion: Number(setRecord.schemaVersion || 1),
            repository: repository,
            name: String(setRecord.name || ""),
            ref: String(setRecord.ref || "").trim(),
            workflowCount: items.length,
            missingCount: missing,
            repositoryMatches: repositoryMatches,
            runnable:
                items.length > 0
                && missing === 0
                && repositoryMatches,
            workflows: items
        };
    }

    function procedureByName(name) {
        const clean = String(name || "").trim();

        if (!clean || !repoSlug)
            return null;

        const index = globalSetIndex(repoSlug, clean);

        if (index < 0)
            return null;

        return normalizedProcedure(savedSets[index]);
    }

    function procedures() {
        return repoSets.map(function(setRecord) {
            return root.normalizedProcedure(setRecord);
        }).filter(function(record) {
            return record !== null;
        });
    }

    function runProcedure(name) {
        const clean = String(name || "").trim();

        if (!clean || !repoSlug)
            return false;

        const index = globalSetIndex(repoSlug, clean);

        if (index < 0)
            return false;

        const setRecord = savedSets[index];
        const procedure = normalizedProcedure(setRecord);

        if (!procedure || !procedure.runnable)
            return false;

        activeProcedureName = clean;

        runSet(setRecord);
        procedureDispatched(clean, procedure);
        return true;
    }

    function runSet(setRecord) {
        if (!githubService || !setRecord
                || String(setRecord.repository || "") !== repoSlug
                || !Array.isArray(setRecord.items)
                || setRecord.items.length === 0
                || setMissingCount(setRecord) > 0)
            return false;

        githubService.runWorkflowBatch(
            setRecord.items.map(function(item) {
                return String(item.path || "");
            }),
            String(setRecord.ref || "").trim()
        );
        return true;
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
