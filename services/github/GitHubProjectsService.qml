import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string owner: "@me"

    property bool busy: false
    property string operation: ""
    property string stateText: "READY"
    property string lastError: ""

    property var projects: []
    property int selectedProjectIndex: -1
    readonly property var selectedProject:
        selectedProjectIndex >= 0 && selectedProjectIndex < projects.length
        ? projects[selectedProjectIndex]
        : ({})

    property var projectView: ({})
    property var fields: []
    property var items: []

    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal projectsRefreshed()
    signal projectRefreshed()
    signal mutationFinished(bool success, string operation)

    function rowsFrom(value, key) {
        if (Array.isArray(value))
            return value;

        if (value && key && Array.isArray(value[key]))
            return value[key];

        return [];
    }

    function projectNumber(project) {
        const value = Number((project || {}).number || 0);
        return isNaN(value) ? 0 : value;
    }

    function projectTitle(project) {
        return String((project || {}).title || "UNTITLED PROJECT");
    }

    function selectedNumber() {
        return projectNumber(selectedProject);
    }

    function selectedTitle() {
        return projectTitle(selectedProject);
    }

    function selectedProjectId() {
        return String(
            projectView.id
            || selectedProject.id
            || ""
        );
    }

    function itemStatus(item) {
        const row = item || {};

        if (row.status !== undefined && row.status !== null)
            return String(row.status || "").trim();

        if (row.Status !== undefined && row.Status !== null)
            return String(row.Status || "").trim();

        if (row.fields && row.fields.Status !== undefined)
            return String(row.fields.Status || "").trim();

        return "";
    }

    function itemTitle(item) {
        const row = item || {};
        const content = row.content || {};

        return String(
            row.title
            || content.title
            || "UNTITLED WORK ITEM"
        );
    }

    function itemType(item) {
        const row = item || {};
        const content = row.content || {};

        return String(
            row.type
            || content.type
            || "ITEM"
        ).toUpperCase();
    }

    function itemRepository(item) {
        const row = item || {};
        const content = row.content || {};
        const repository = row.repository || content.repository || {};

        if (typeof repository === "string")
            return repository;

        return String(
            repository.nameWithOwner
            || repository.fullName
            || repository.name
            || ""
        );
    }

    function itemUrl(item) {
        const row = item || {};
        const content = row.content || {};

        return String(content.url || row.url || "");
    }

    function fieldName(field) {
        return String((field || {}).name || "").trim();
    }

    function fieldDataType(field) {
        return String(
            (field || {}).dataType
            || (field || {}).type
            || ""
        ).trim().toUpperCase();
    }

    function projectFieldNames() {
        const out = [];

        for (let i = 0; i < fields.length; ++i) {
            const name = fieldName(fields[i]);

            if (name)
                out.push(name);
        }

        return out;
    }

    function itemFieldValue(item, fieldNameValue) {
        const row = item || {};
        const target = String(fieldNameValue || "").trim();

        if (!target)
            return "";

        if (row[target] !== undefined && row[target] !== null)
            return row[target];

        const lower = target.toLowerCase();
        const keys = Object.keys(row);

        for (let i = 0; i < keys.length; ++i) {
            if (String(keys[i]).toLowerCase() === lower)
                return row[keys[i]];
        }

        const fieldMap = row.fields || {};

        if (fieldMap[target] !== undefined && fieldMap[target] !== null)
            return fieldMap[target];

        const fieldKeys = Object.keys(fieldMap);

        for (let i = 0; i < fieldKeys.length; ++i) {
            if (String(fieldKeys[i]).toLowerCase() === lower)
                return fieldMap[fieldKeys[i]];
        }

        const values =
            Array.isArray(row.fieldValues)
            ? row.fieldValues
            : [];

        for (let i = 0; i < values.length; ++i) {
            const value = values[i] || {};
            const name = String(
                value.fieldName
                || (value.field || {}).name
                || value.name
                || ""
            ).trim();

            if (name.toLowerCase() !== lower)
                continue;

            if (value.value !== undefined && value.value !== null)
                return value.value;

            if (value.name !== undefined && value.name !== null
                    && String(value.name).trim() !== target)
                return value.name;

            if (value.title !== undefined && value.title !== null)
                return value.title;
        }

        return "";
    }

    function displayFieldValue(item, fieldNameValue) {
        const value = itemFieldValue(item, fieldNameValue);

        if (value === undefined || value === null)
            return "";

        if (Array.isArray(value)) {
            const parts = [];

            for (let i = 0; i < value.length; ++i) {
                const row = value[i];

                if (row && typeof row === "object")
                    parts.push(String(row.name || row.title || row.login || ""));
                else
                    parts.push(String(row || ""));
            }

            return parts.filter(function(part) {
                return part.length > 0;
            }).join(", ");
        }

        if (typeof value === "object") {
            return String(
                value.name
                || value.title
                || value.login
                || value.value
                || ""
            );
        }

        return String(value || "");
    }

    function fieldNameMatching(patterns, typeHint) {
        const wantedType = String(typeHint || "").toUpperCase();
        let fallback = "";

        for (let i = 0; i < fields.length; ++i) {
            const field = fields[i] || {};
            const name = fieldName(field);
            const lower = name.toLowerCase();
            const dataType = fieldDataType(field);

            for (let j = 0; j < patterns.length; ++j) {
                if (lower.indexOf(patterns[j]) < 0)
                    continue;

                if (!fallback)
                    fallback = name;

                if (!wantedType
                        || !dataType
                        || dataType.indexOf(wantedType) >= 0)
                    return name;
            }
        }

        return fallback;
    }

    function startDateFieldName() {
        return fieldNameMatching(
            ["start date", "start", "begin"],
            "DATE"
        );
    }

    function targetDateFieldName() {
        return fieldNameMatching(
            ["target date", "target", "due", "end date", "finish"],
            "DATE"
        );
    }

    function iterationFieldName() {
        return fieldNameMatching(
            ["iteration", "sprint", "cycle"],
            "ITERATION"
        );
    }

    function priorityFieldName() {
        return fieldNameMatching(
            ["priority"],
            ""
        );
    }

    function itemStartDate(item) {
        const name = startDateFieldName();
        return name ? displayFieldValue(item, name) : "";
    }

    function itemTargetDate(item) {
        const name = targetDateFieldName();
        return name ? displayFieldValue(item, name) : "";
    }

    function itemIteration(item) {
        const name = iterationFieldName();
        return name ? displayFieldValue(item, name) : "";
    }

    function itemPriority(item) {
        const name = priorityFieldName();
        return name ? displayFieldValue(item, name) : "";
    }

    function dateMs(value) {
        const text = String(value || "").trim();

        if (!text)
            return NaN;

        const valueMs = Date.parse(text);
        return isNaN(valueMs) ? NaN : valueMs;
    }

    function itemStartMs(item) {
        const start = dateMs(itemStartDate(item));

        if (!isNaN(start))
            return start;

        return dateMs(itemTargetDate(item));
    }

    function itemEndMs(item) {
        const target = dateMs(itemTargetDate(item));

        if (!isNaN(target))
            return target;

        return itemStartMs(item);
    }

    function scheduledItems() {
        const out = [];

        for (let i = 0; i < items.length; ++i) {
            if (!isNaN(itemStartMs(items[i])))
                out.push(items[i]);
        }

        return out;
    }

    function unscheduledItems() {
        const out = [];

        for (let i = 0; i < items.length; ++i) {
            if (isNaN(itemStartMs(items[i])))
                out.push(items[i]);
        }

        return out;
    }

    function roadmapStartMs() {
        const scheduled = scheduledItems();

        if (scheduled.length === 0)
            return NaN;

        let result = itemStartMs(scheduled[0]);

        for (let i = 1; i < scheduled.length; ++i)
            result = Math.min(result, itemStartMs(scheduled[i]));

        return result;
    }

    function roadmapEndMs() {
        const scheduled = scheduledItems();

        if (scheduled.length === 0)
            return NaN;

        let result = itemEndMs(scheduled[0]);

        for (let i = 1; i < scheduled.length; ++i)
            result = Math.max(result, itemEndMs(scheduled[i]));

        return result;
    }

    function roadmapSpanMs() {
        const start = roadmapStartMs();
        const end = roadmapEndMs();

        if (isNaN(start) || isNaN(end))
            return NaN;

        const oneDay = 86400000;
        return Math.max(end - start, oneDay);
    }

    function roadmapRatio(valueMs) {
        const start = roadmapStartMs();
        const span = roadmapSpanMs();

        if (isNaN(valueMs) || isNaN(start) || isNaN(span))
            return 0;

        return Math.max(0, Math.min(1, (valueMs - start) / span));
    }

    function roadmapBarX(item, width) {
        return roadmapRatio(itemStartMs(item)) * Number(width || 0);
    }

    function roadmapBarWidth(item, width) {
        const start = itemStartMs(item);
        const end = itemEndMs(item);
        const totalWidth = Number(width || 0);

        if (isNaN(start) || isNaN(end) || totalWidth <= 0)
            return 0;

        return Math.max(
            6,
            (roadmapRatio(end) - roadmapRatio(start)) * totalWidth
        );
    }

    function roadmapDateAt(ratio) {
        const start = roadmapStartMs();
        const span = roadmapSpanMs();

        if (isNaN(start) || isNaN(span))
            return "";

        const date = new Date(start + span * Number(ratio || 0));
        return date.toISOString().slice(0, 10);
    }

    function statusField() {
        for (let i = 0; i < fields.length; ++i) {
            const row = fields[i] || {};

            if (String(row.name || "").trim().toLowerCase() === "status")
                return row;
        }

        return null;
    }

    function statusOptions() {
        const field = statusField();
        const source =
            field && Array.isArray(field.options)
            ? field.options
            : [];
        const out = [];

        for (let i = 0; i < source.length; ++i) {
            const row = source[i] || {};
            const name = String(row.name || "").trim();

            if (name)
                out.push(name);
        }

        return out;
    }

    function laneNames() {
        const lanes = statusOptions();
        const seen = ({});

        for (let i = 0; i < lanes.length; ++i)
            seen[lanes[i]] = true;

        for (let i = 0; i < items.length; ++i) {
            const status = itemStatus(items[i]) || "NO STATUS";

            if (!seen[status]) {
                seen[status] = true;
                lanes.push(status);
            }
        }

        if (lanes.length === 0)
            lanes.push("NO STATUS");

        return lanes;
    }

    function itemsForStatus(status) {
        const target = String(status || "");
        const out = [];

        for (let i = 0; i < items.length; ++i) {
            const actual = itemStatus(items[i]) || "NO STATUS";

            if (actual === target)
                out.push(items[i]);
        }

        return out;
    }

    function statusOptionByName(name) {
        const field = statusField();
        const source =
            field && Array.isArray(field.options)
            ? field.options
            : [];
        const target = String(name || "").trim();

        for (let i = 0; i < source.length; ++i) {
            const row = source[i] || {};

            if (String(row.name || "").trim() === target)
                return row;
        }

        return null;
    }

    function clearProjectDetail() {
        projectView = ({});
        fields = [];
        items = [];
    }

    function startOperation(name, args, label) {
        if (busy)
            return false;

        busy = true;
        operation = String(name || "");
        stateText = String(label || "WORKING");
        lastError = "";
        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        commandProcess.exec(args);
        watchdog.restart();
        return true;
    }

    function refreshProjects() {
        return startOperation(
            "list",
            [
                "bash",
                "-lc",
                'exec gh project list --owner "$1" --limit 100 --format json',
                "pa-project-list",
                owner
            ],
            "DISCOVERING PROJECTS"
        );
    }

    function selectProject(index) {
        const next = Number(index);

        if (isNaN(next) || next < 0 || next >= projects.length)
            return false;

        selectedProjectIndex = next;
        clearProjectDetail();
        return refreshSelectedProject();
    }

    function cycleProject(delta) {
        if (projects.length === 0)
            return false;

        let index = selectedProjectIndex;

        if (index < 0)
            index = 0;

        index =
            (
                index
                + Number(delta || 0)
                + projects.length
            )
            % projects.length;

        return selectProject(index);
    }

    function refreshSelectedProject() {
        const number = selectedNumber();

        if (!number) {
            clearProjectDetail();
            stateText = "NO PROJECT SELECTED";
            return false;
        }

        return startOperation(
            "detail",
            [
                "bash",
                "-lc",
                [
                    'number="$1"',
                    'owner="$2"',
                    'view="$(gh project view "$number" --owner "$owner" --format json)" || exit $?',
                    'fields="$(gh project field-list "$number" --owner "$owner" --limit 100 --format json)" || exit $?',
                    'items="$(gh project item-list "$number" --owner "$owner" --limit 200 --format json)" || exit $?',
                    "jq -nc --argjson view \"$view\" --argjson fields \"$fields\" --argjson items \"$items\" '{view:$view,fields:$fields,items:$items}'"
                ].join("\n"),
                "pa-project-detail",
                String(number),
                owner
            ],
            "READING OPERATING MAP"
        );
    }

    function createProject(title) {
        const clean = String(title || "").trim();

        if (!clean)
            return false;

        return startOperation(
            "create-project",
            [
                "bash",
                "-lc",
                'exec gh project create --owner "$1" --title "$2" --format json',
                "pa-project-create",
                owner,
                clean
            ],
            "CREATING PROJECT"
        );
    }

    function createDraft(title, body) {
        const number = selectedNumber();
        const cleanTitle = String(title || "").trim();

        if (!number || !cleanTitle)
            return false;

        return startOperation(
            "create-draft",
            [
                "bash",
                "-lc",
                'exec gh project item-create "$1" --owner "$2" --title "$3" --body "$4" --format json',
                "pa-project-item-create",
                String(number),
                owner,
                cleanTitle,
                String(body || "")
            ],
            "ADDING WORK ITEM"
        );
    }

    function createIssue(repoSlug, title, body) {
        const number = selectedNumber();
        const cleanRepo = String(repoSlug || "").trim();
        const cleanTitle = String(title || "").trim();

        if (!number || !cleanRepo || !cleanTitle) {
            lastError =
                !cleanRepo
                ? "ISSUE CREATE UNAVAILABLE // ACTIVE REPOSITORY MISSING"
                : "ISSUE CREATE UNAVAILABLE // TITLE MISSING";
            stateText = lastError;
            return false;
        }

        return startOperation(
            "create-issue",
            [
                "bash",
                "-lc",
                [
                    'issue_url="$(gh issue create --repo "$3" --title "$4" --body "$5")" || exit $?',
                    'issue_url="$(printf "%s\\n" "$issue_url" | tail -n 1)"',
                    '[ -n "$issue_url" ] || { printf "ISSUE CREATE RETURNED NO URL\\n" >&2; exit 1; }',
                    'exec gh project item-add "$1" --owner "$2" --url "$issue_url" --format json'
                ].join("\n"),
                "pa-project-issue-create",
                String(number),
                owner,
                cleanRepo,
                cleanTitle,
                String(body || "")
            ],
            "CREATING ISSUE"
        );
    }

    function addPullRequest(url) {
        const cleanUrl = String(url || "").trim();
        const lower = cleanUrl.toLowerCase();

        if (!cleanUrl
                || lower.indexOf("github.com/") < 0
                || lower.indexOf("/pull/") < 0) {
            lastError = "PULL REQUEST ADD UNAVAILABLE // EXPECTED GITHUB PR URL";
            stateText = lastError;
            return false;
        }

        return addExistingItem(cleanUrl, "pull");
    }

    function canonicalItemUrl(url) {
        let value = String(url || "").trim();

        if (!value)
            return "";

        const hash = value.indexOf("#");
        if (hash >= 0)
            value = value.slice(0, hash);

        const query = value.indexOf("?");
        if (query >= 0)
            value = value.slice(0, query);

        while (value.length > 0
                && value.charAt(value.length - 1) === "/")
            value = value.slice(0, -1);

        return value;
    }

    function itemByUrl(url) {
        const needle = canonicalItemUrl(url);

        if (!needle)
            return null;

        for (let i = 0; i < items.length; ++i) {
            if (canonicalItemUrl(itemUrl(items[i])) === needle)
                return items[i];
        }

        return null;
    }

    function containsItemUrl(url) {
        return itemByUrl(url) !== null;
    }

    function itemStatusByUrl(url) {
        const row = itemByUrl(url);
        return row ? itemStatus(row) : "";
    }

    function addExistingItem(url, kind) {
        const number = selectedNumber();
        const cleanUrl = canonicalItemUrl(url);
        const cleanKind = String(kind || "item").toLowerCase();
        const operationName =
            cleanKind === "pull"
            ? "add-pr"
            : cleanKind === "issue"
            ? "add-issue"
            : "add-item";

        if (!number || !cleanUrl) {
            lastError =
                "ADD TO PROJECT UNAVAILABLE // "
                + (!number ? "PROJECT NOT SELECTED" : "ITEM URL MISSING");
            stateText = lastError;
            return false;
        }

        if (containsItemUrl(cleanUrl)) {
            lastError = "ADD TO PROJECT REFUSED // ITEM ALREADY PRESENT";
            stateText = lastError;
            return false;
        }

        return startOperation(
            operationName,
            [
                "bash",
                "-lc",
                'exec gh project item-add "$1" --owner "$2" --url "$3" --format json',
                "pa-project-item-add",
                String(number),
                owner,
                cleanUrl
            ],
            cleanKind === "pull"
            ? "ADDING PULL REQUEST"
            : cleanKind === "issue"
            ? "ADDING ISSUE"
            : "ADDING PROJECT ITEM"
        );
    }

    function itemId(item) {
        return String((item || {}).id || "");
    }

    function archiveItem(item, confirmed) {
        const number = selectedNumber();
        const id = itemId(item);

        if (!confirmed) {
            lastError =
                "ARCHIVE REFUSED // EXPLICIT CONFIRMATION REQUIRED";
            stateText = lastError;
            return false;
        }

        if (!number || !id) {
            lastError = "ARCHIVE UNAVAILABLE // PROJECT ITEM ID MISSING";
            stateText = lastError;
            return false;
        }

        return startOperation(
            "archive-item",
            [
                "bash",
                "-lc",
                'exec gh project item-archive "$1" --owner "$2" --id "$3" --format json',
                "pa-project-item-archive",
                String(number),
                owner,
                id
            ],
            "ARCHIVING WORK ITEM"
        );
    }

    function removeItem(item, confirmed) {
        const number = selectedNumber();
        const id = itemId(item);

        if (!confirmed) {
            lastError =
                "REMOVE REFUSED // EXPLICIT CONFIRMATION REQUIRED";
            stateText = lastError;
            return false;
        }

        if (!number || !id) {
            lastError = "REMOVE UNAVAILABLE // PROJECT ITEM ID MISSING";
            stateText = lastError;
            return false;
        }

        return startOperation(
            "remove-item",
            [
                "bash",
                "-lc",
                'exec gh project item-delete "$1" --owner "$2" --id "$3" --format json',
                "pa-project-item-remove",
                String(number),
                owner,
                id
            ],
            "REMOVING WORK ITEM"
        );
    }

    function linkRepository(repoSlug) {
        const number = selectedNumber();
        const cleanRepo = String(repoSlug || "").trim();

        if (!number || !cleanRepo)
            return false;

        return startOperation(
            "link-repo",
            [
                "bash",
                "-lc",
                'exec gh project link "$1" --owner "$2" --repo "$3"',
                "pa-project-link",
                String(number),
                owner,
                cleanRepo
            ],
            "LINKING REPOSITORY"
        );
    }

    function setItemStatus(item, status) {
        const number = selectedNumber();
        const cleanStatus = String(status || "").trim();
        const row = item || {};
        const url = itemUrl(row);

        if (!number || !cleanStatus)
            return false;

        if (url) {
            return startOperation(
                "set-status",
                [
                    "bash",
                    "-lc",
                    'exec gh project item-edit "$1" --owner "$2" --url "$3" --field Status --value "$4" --format json',
                    "pa-project-status",
                    String(number),
                    owner,
                    url,
                    cleanStatus
                ],
                "MOVING WORK ITEM"
            );
        }

        const field = statusField();
        const option = statusOptionByName(cleanStatus);
        const itemId = String(row.id || "");
        const projectId = selectedProjectId();
        const fieldId = String((field || {}).id || "");
        const optionId = String((option || {}).id || "");

        if (!itemId || !projectId || !fieldId || !optionId) {
            lastError =
                "STATUS MOVE UNAVAILABLE // PROJECT FIELD IDENTITIES MISSING";
            stateText = lastError;
            return false;
        }

        return startOperation(
            "set-status",
            [
                "bash",
                "-lc",
                'exec gh project item-edit --id "$1" --project-id "$2" --field-id "$3" --single-select-option-id "$4" --format json',
                "pa-project-status-ids",
                itemId,
                projectId,
                fieldId,
                optionId
            ],
            "MOVING WORK ITEM"
        );
    }

    function parseProjects(payload) {
        const parsed = JSON.parse(String(payload || "{}"));
        const rows = rowsFrom(parsed, "projects");
        const previousNumber = selectedNumber();

        projects = rows;

        if (rows.length === 0) {
            selectedProjectIndex = -1;
            clearProjectDetail();
            return;
        }

        let nextIndex = 0;

        if (previousNumber) {
            for (let i = 0; i < rows.length; ++i) {
                if (projectNumber(rows[i]) === previousNumber) {
                    nextIndex = i;
                    break;
                }
            }
        }

        selectedProjectIndex = nextIndex;
    }

    function parseDetail(payload) {
        const parsed = JSON.parse(String(payload || "{}"));

        projectView = parsed.view || ({});
        fields = rowsFrom(parsed.fields, "fields");
        items = rowsFrom(parsed.items, "items");
    }

    function authHint(errorText) {
        const lower = String(errorText || "").toLowerCase();

        if (lower.indexOf("project") >= 0
                && (
                    lower.indexOf("scope") >= 0
                    || lower.indexOf("oauth") >= 0
                    || lower.indexOf("authorization") >= 0
                )) {
            return "AUTH // RUN: gh auth refresh -s project";
        }

        return "";
    }

    function maybeFinish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen)
            return;

        const finishedOperation = operation;
        const output = String(stdoutText || "").trim();
        const error = String(stderrText || "").trim();

        busy = false;
        watchdog.stop();

        if (exitCode !== 0) {
            lastError = error || output || "GITHUB PROJECT OPERATION FAILED";
            const hint = authHint(lastError);
            stateText =
                "ERROR // "
                + lastError
                + (hint ? "\n" + hint : "");
            mutationFinished(false, finishedOperation);
            return;
        }

        try {
            if (finishedOperation === "list") {
                parseProjects(output || "{}");
                stateText =
                    projects.length > 0
                    ? "PROJECTS READY // " + String(projects.length)
                    : "NO PROJECTS";
                projectsRefreshed();

                if (projects.length > 0) {
                    Qt.callLater(function() {
                        root.refreshSelectedProject();
                    });
                }

                return;
            }

            if (finishedOperation === "detail") {
                parseDetail(output || "{}");
                stateText =
                    "OPERATING MAP READY // "
                    + String(items.length)
                    + " ITEM"
                    + (items.length === 1 ? "" : "S");
                projectRefreshed();
                return;
            }
        } catch (parseError) {
            lastError =
                "PROJECT RESPONSE PARSE // "
                + String(parseError);
            stateText = "ERROR // " + lastError;
            mutationFinished(false, finishedOperation);
            return;
        }

        stateText = "COMPLETE // " + finishedOperation.toUpperCase();
        mutationFinished(true, finishedOperation);

        if (finishedOperation === "create-project") {
            Qt.callLater(function() {
                root.refreshProjects();
            });
        } else {
            Qt.callLater(function() {
                root.refreshSelectedProject();
            });
        }
    }

    Process {
        id: commandProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = this.text;
                root.stdoutSeen = true;
                root.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.stderrText = this.text;
                root.stderrSeen = true;
                root.maybeFinish();
            }
        }

        onExited: function(code, status) {
            root.exitCode = Number(code);
            root.exitSeen = true;
            root.maybeFinish();
        }
    }

    Timer {
        id: watchdog
        interval: 120000
        repeat: false

        onTriggered: {
            const finishedOperation = root.operation;
            root.busy = false;
            root.lastError = "GITHUB PROJECT OPERATION TIMEOUT";
            root.stateText = "ERROR // " + root.lastError;
            root.mutationFinished(false, finishedOperation);
        }
    }
}
