import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property var queue: []
    property var savedSets: []

    signal setLoaded(var record)

    readonly property int queueCount: queue.length

    function queueContains(slug) {
        const needle = String(slug || "");

        for (let i = 0; i < queue.length; ++i) {
            if (String(queue[i] || "") === needle)
                return true;
        }

        return false;
    }

    function addTarget(slug) {
        const clean = String(slug || "").trim();

        if (!clean || queueContains(clean))
            return false;

        queue = queue.concat([clean]);
        return true;
    }

    function removeTarget(index) {
        if (index < 0 || index >= queue.length)
            return;

        const next = queue.slice();
        next.splice(index, 1);
        queue = next;
    }

    function clearTargets() {
        queue = [];
    }

    function slugSet(values) {
        const rows = Array.isArray(values) ? values : [];
        const out = ({});

        for (let i = 0; i < rows.length; ++i) {
            const slug = String(rows[i] || "").trim();

            if (slug)
                out[slug] = true;
        }

        return out;
    }

    function pruneQueue(validSlugs) {
        const valid = slugSet(validSlugs);
        const before = queue.length;

        queue = queue.filter(function(slug) {
            return !!valid[String(slug || "").trim()];
        });

        return before - queue.length;
    }

    function pruneSet(record, validSlugs) {
        if (!record)
            return 0;

        const index = setIndex(String(record.name || ""));

        if (index < 0)
            return 0;

        const valid = slugSet(validSlugs);
        const source = savedSets[index] || {};
        const targets =
            Array.isArray(source.targets)
            ? source.targets
            : [];
        const kept = targets.filter(function(slug) {
            return !!valid[String(slug || "").trim()];
        });
        const removed = targets.length - kept.length;

        if (removed <= 0)
            return 0;

        const updated = {
            name: String(source.name || ""),
            targets: kept,
            visibility: String(source.visibility || "keep"),
            topicMode: String(source.topicMode || "add"),
            topics: Array.isArray(source.topics)
                ? source.topics.slice()
                : [],
            descriptionMode: String(source.descriptionMode || "keep"),
            description: String(source.description || ""),
            repositoryName: String(source.repositoryName || "")
        };

        const next = savedSets.slice();
        next[index] = updated;
        savedSets = next;
        persistSets();

        return removed;
    }

    function setIndex(name) {
        const needle = String(name || "").trim();

        for (let i = 0; i < savedSets.length; ++i) {
            if (String(savedSets[i].name || "") === needle)
                return i;
        }

        return -1;
    }

    function saveSet(name, draft, confirmedOverwrite) {
        const clean = String(name || "").trim();

        if (!clean || queue.length === 0)
            return false;

        const existing = setIndex(clean);

        if (existing >= 0 && !confirmedOverwrite)
            return false;

        const source = draft || {};
        const record = {
            name: clean,
            targets: queue.slice(),
            visibility: String(source.visibility || "keep"),
            topicMode: String(source.topicMode || "add"),
            topics: Array.isArray(source.topics)
                ? source.topics.slice()
                : [],
            descriptionMode: String(source.descriptionMode || "keep"),
            description: String(source.description || ""),
            repositoryName: String(source.repositoryName || "")
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

    function loadSet(record) {
        if (!record)
            return;

        queue = Array.isArray(record.targets)
            ? record.targets.slice()
            : [];
        setLoaded(record);
    }

    function deleteSet(record, confirmed) {
        if (!record || !confirmed)
            return false;

        const index = setIndex(String(record.name || ""));

        if (index < 0)
            return false;

        const next = savedSets.slice();
        next.splice(index, 1);
        savedSets = next;
        persistSets();
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
            savedSets =
                parsed && Array.isArray(parsed.sets)
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

        path: Qt.resolvedUrl("../../repository-profile-sets.json")
        blockWrites: true
        atomicWrites: true
        printErrors: false

        onLoaded: root.loadSetsFromDisk()
    }
}
