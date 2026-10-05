import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property bool busy: false
    property bool reviewReady: false
    property string reviewFingerprint: ""
    property string reviewText: "BUILD A BATCH, CHOOSE CHANGES, THEN REVIEW."
    property string resultText: "READY"
    property string lastError: ""

    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal batchFinished(bool success)

    function normalizeTopics(value) {
        const raw = Array.isArray(value)
            ? value
            : String(value || "").split(/[\n,]+/);
        const seen = ({});
        const out = [];

        for (let i = 0; i < raw.length; ++i) {
            const topic = String(raw[i] || "").trim().toLowerCase();

            if (!topic || seen[topic])
                continue;

            seen[topic] = true;
            out.push(topic);
        }

        return out;
    }

    function normalizedDraft(draft) {
        const source = draft || {};

        return {
            visibility: ["keep", "private", "public"].indexOf(
                String(source.visibility || "keep")
            ) >= 0
                ? String(source.visibility || "keep")
                : "keep",
            topicMode: ["add", "remove", "replace"].indexOf(
                String(source.topicMode || "add")
            ) >= 0
                ? String(source.topicMode || "add")
                : "add",
            topics: normalizeTopics(source.topics || []),
            descriptionMode: ["keep", "set", "clear"].indexOf(
                String(source.descriptionMode || "keep")
            ) >= 0
                ? String(source.descriptionMode || "keep")
                : "keep",
            description: String(source.description || "").trim(),
            repositoryName: String(source.repositoryName || "").trim()
        };
    }

    function normalizedTargets(targets) {
        const raw = Array.isArray(targets) ? targets : [];
        const seen = ({});
        const out = [];

        for (let i = 0; i < raw.length; ++i) {
            const slug = String(raw[i] || "").trim();

            if (!slug || seen[slug])
                continue;

            seen[slug] = true;
            out.push(slug);
        }

        return out;
    }

    function fingerprint(targets, draft) {
        return JSON.stringify({
            targets: normalizedTargets(targets),
            draft: normalizedDraft(draft)
        });
    }

    function invalidateReview() {
        reviewReady = false;
        reviewFingerprint = "";
        reviewText = "CHANGES MODIFIED // REVIEW AGAIN BEFORE APPLY.";
    }

    function validate(targets, draft) {
        const cleanTargets = normalizedTargets(targets);
        const cleanDraft = normalizedDraft(draft);

        if (cleanTargets.length === 0)
            return "ADD AT LEAST ONE REPOSITORY.";

        if (cleanDraft.repositoryName && cleanTargets.length !== 1)
            return "REPOSITORY NAME / TITLE CAN ONLY BE CHANGED FOR ONE TARGET AT A TIME.";

        if (cleanDraft.descriptionMode === "set"
                && !cleanDraft.description)
            return "DESCRIPTION MODE IS SET, BUT DESCRIPTION IS EMPTY.";

        const hasChange =
            cleanDraft.visibility !== "keep"
            || cleanDraft.topics.length > 0
            || cleanDraft.descriptionMode !== "keep"
            || !!cleanDraft.repositoryName;

        if (!hasChange)
            return "NO CHANGES SELECTED.";

        return "";
    }

    function previewBatch(targets, draft) {
        const cleanTargets = normalizedTargets(targets);
        const cleanDraft = normalizedDraft(draft);
        const error = validate(cleanTargets, cleanDraft);

        if (error) {
            reviewReady = false;
            reviewFingerprint = "";
            reviewText = "REVIEW BLOCKED // " + error;
            resultText = reviewText;
            return false;
        }

        const lines = [];
        lines.push("REVIEW // " + String(cleanTargets.length) + " REPOSITORY"
                   + (cleanTargets.length === 1 ? "" : "IES"));

        for (let i = 0; i < cleanTargets.length; ++i)
            lines.push("TARGET // " + cleanTargets[i]);

        if (cleanDraft.visibility !== "keep")
            lines.push("VISIBILITY // " + cleanDraft.visibility.toUpperCase());

        if (cleanDraft.topics.length > 0)
            lines.push(
                "TOPICS // "
                + cleanDraft.topicMode.toUpperCase()
                + " // "
                + cleanDraft.topics.join(", ")
            );

        if (cleanDraft.descriptionMode === "set")
            lines.push("DESCRIPTION // SET // " + cleanDraft.description);
        else if (cleanDraft.descriptionMode === "clear")
            lines.push("DESCRIPTION // CLEAR");

        if (cleanDraft.repositoryName) {
            lines.push("RENAME // " + cleanDraft.repositoryName);
            lines.push("WARNING // RENAME CHANGES THE GITHUB REPOSITORY URL.");
        }

        if (cleanDraft.visibility !== "keep")
            lines.push("WARNING // VISIBILITY CHANGES TAKE EFFECT ON GITHUB.");

        reviewFingerprint = fingerprint(cleanTargets, cleanDraft);
        reviewReady = true;
        reviewText = lines.join("\n");
        resultText = "REVIEW READY // APPLY IS ARMED.";
        lastError = "";
        return true;
    }

    function applyBatch(targets, draft) {
        if (busy)
            return false;

        const cleanTargets = normalizedTargets(targets);
        const cleanDraft = normalizedDraft(draft);
        const error = validate(cleanTargets, cleanDraft);
        const nextFingerprint = fingerprint(cleanTargets, cleanDraft);

        if (error) {
            resultText = "APPLY BLOCKED // " + error;
            return false;
        }

        if (!reviewReady || reviewFingerprint !== nextFingerprint) {
            resultText = "APPLY BLOCKED // REVIEW CURRENT CHANGES FIRST.";
            reviewReady = false;
            return false;
        }

        busy = true;
        reviewReady = false;
        resultText = "APPLYING // " + String(cleanTargets.length) + " REPOSITORY"
                   + (cleanTargets.length === 1 ? "" : "IES");
        lastError = "";
        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        const args = [
            "bash",
            "-lc",
            [
                'visibility="$1"',
                'topic_mode="$2"',
                'topics_text="$3"',
                'description_mode="$4"',
                'description="$5"',
                'repo_name="$6"',
                'shift 6',
                'overall=0',
                "desired_json=\"$(printf \"%s\" \"$topics_text\" | jq -Rsc 'split(\"\\n\") | map(select(length > 0)) | unique')\"",
                'for repo in "$@"; do',
                '  active="$repo"',
                '  repo_rc=0',
                '  printf "APPLY // %s\\n" "$repo"',
                '  if [ "$visibility" != "keep" ]; then',
                '    gh api --method PATCH "repos/$active" -f "visibility=$visibility" >/dev/null || repo_rc=$?',
                '  fi',
                '  if [ "$repo_rc" -eq 0 ] && [ "$description_mode" = "set" ]; then',
                '    gh api --method PATCH "repos/$active" -f "description=$description" >/dev/null || repo_rc=$?',
                '  elif [ "$repo_rc" -eq 0 ] && [ "$description_mode" = "clear" ]; then',
                '    gh api --method PATCH "repos/$active" -f "description=" >/dev/null || repo_rc=$?',
                '  fi',
                '  if [ "$repo_rc" -eq 0 ] && [ -n "$repo_name" ]; then',
                '    response="$(gh api --method PATCH "repos/$active" -f "name=$repo_name")" || repo_rc=$?',
                '    if [ "$repo_rc" -eq 0 ]; then',
                "      renamed=\"$(printf \"%s\" \"$response\" | jq -r '.full_name // empty')\"",
                '      [ -n "$renamed" ] && active="$renamed"',
                '    fi',
                '  fi',
                '  if [ "$repo_rc" -eq 0 ] && [ "$desired_json" != "[]" ]; then',
                "    current_json=\"$(gh api \"repos/$active/topics\" --jq '.names')\" || repo_rc=$?",
                '    if [ "$repo_rc" -eq 0 ]; then',
                '      case "$topic_mode" in',
                '        add)',
                "          final_json=\"$(jq -nc --argjson c \"$current_json\" --argjson d \"$desired_json\" '($c + $d) | unique')\"",
                '          ;;',
                '        remove)',
                "          final_json=\"$(jq -nc --argjson c \"$current_json\" --argjson d \"$desired_json\" '$c - $d')\"",
                '          ;;',
                '        replace)',
                '          final_json="$desired_json"',
                '          ;;',
                '      esac',
                "      payload=\"$(jq -nc --argjson names \"$final_json\" '{names:$names}')\"",
                '      printf "%s" "$payload" | gh api --method PUT "repos/$active/topics" --input - >/dev/null || repo_rc=$?',
                '    fi',
                '  fi',
                '  if [ "$repo_rc" -eq 0 ]; then',
                '    printf "OK // %s\\n" "$active"',
                '  else',
                '    printf "FAILED // %s // RC %s\\n" "$active" "$repo_rc"',
                '    overall=1',
                '  fi',
                'done',
                'exit "$overall"'
            ].join("\n"),
            "pa-repo-profile",
            cleanDraft.visibility,
            cleanDraft.topicMode,
            cleanDraft.topics.join("\n"),
            cleanDraft.descriptionMode,
            cleanDraft.description,
            cleanDraft.repositoryName
        ];

        for (let i = 0; i < cleanTargets.length; ++i)
            args.push(cleanTargets[i]);

        applyProcess.exec(args);
        watchdog.restart();
        return true;
    }

    function maybeFinish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen)
            return;

        busy = false;
        watchdog.stop();

        const output = String(stdoutText || "").trim();
        const error = String(stderrText || "").trim();

        if (exitCode === 0) {
            resultText = output
                ? "COMPLETE\n" + output
                : "COMPLETE";
            lastError = "";
            batchFinished(true);
            return;
        }

        lastError = error || output || "REPOSITORY PROFILE APPLY FAILED";
        resultText =
            (output ? output + "\n" : "")
            + "ERROR // "
            + lastError;
        batchFinished(false);
    }

    Process {
        id: applyProcess

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

        onExited: function(exitCode, exitStatus) {
            root.exitCode = Number(exitCode);
            root.exitSeen = true;
            root.maybeFinish();
        }
    }

    Timer {
        id: watchdog
        interval: 120000
        repeat: false

        onTriggered: {
            root.busy = false;
            root.lastError = "REPOSITORY PROFILE APPLY TIMEOUT";
            root.resultText = "ERROR // " + root.lastError;
            root.batchFinished(false);
        }
    }
}
