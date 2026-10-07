import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property bool busy: false
    property bool reviewBusy: false
    property bool reviewInvalidated: false
    property bool reviewStdoutSeen: false
    property bool reviewStderrSeen: false
    property bool reviewExitSeen: false
    property int reviewExitCode: -1
    property string reviewStdoutText: ""
    property string reviewStderrText: ""
    property string pendingReviewFingerprint: ""
    property var pendingReviewTargets: []
    property var pendingReviewDraft: ({})
    property var preflightRows: []

    property bool reviewReady: false
    property string reviewFingerprint: ""
    property string reviewText: "BUILD A BATCH, CHOOSE CHANGES, THEN REVIEW."
    property string resultText: "READY"
    property string lastError: ""
    property var batchResults: []

    readonly property int batchSuccessCount:
        batchResults.filter(function(row) {
            return String((row || {}).state || "") === "OK";
        }).length
    readonly property int batchFailureCount:
        batchResults.filter(function(row) {
            return String((row || {}).state || "") === "FAILED";
        }).length

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
        reviewInvalidated = true;
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

    function preflightReviewText(rows, targets, draft) {
        const source = Array.isArray(rows) ? rows : [];
        const cleanTargets = normalizedTargets(targets);
        const cleanDraft = normalizedDraft(draft);
        const lines = [];
        let errors = 0;
        let changeTargets = 0;
        let noops = 0;

        lines.push(
            "REVIEW PREFLIGHT // "
            + String(cleanTargets.length)
            + " REPOSITORY"
            + (cleanTargets.length === 1 ? "" : "IES")
        );

        for (let i = 0; i < source.length; ++i) {
            const row = source[i] || {};
            const repository = String(row.repo || "UNKNOWN");
            const state = String(row.state || "ERROR");
            const current = row.current || {};
            const proposed = row.proposed || {};
            const changes = row.changes || {};

            if (state !== "OK") {
                errors += 1;
                lines.push(
                    "TARGET // "
                    + repository
                    + " // READ ERROR // "
                    + String(row.detail || "UNKNOWN")
                );
                continue;
            }

            const changed =
                Boolean(changes.visibility)
                || Boolean(changes.topics)
                || Boolean(changes.description)
                || Boolean(changes.name);

            if (changed)
                changeTargets += 1;
            else
                noops += 1;

            lines.push(
                "TARGET // "
                + repository
                + " // "
                + (changed ? "CHANGE" : "NO-OP")
            );

            if (changes.visibility) {
                lines.push(
                    "  VISIBILITY // "
                    + String(current.visibility || "UNKNOWN").toUpperCase()
                    + " → "
                    + String(proposed.visibility || "UNKNOWN").toUpperCase()
                );
            }

            if (changes.topics) {
                lines.push(
                    "  TOPICS // "
                    + (
                        Array.isArray(current.topics)
                        ? current.topics.join(", ")
                        : ""
                      )
                    + " → "
                    + (
                        Array.isArray(proposed.topics)
                        ? proposed.topics.join(", ")
                        : ""
                      )
                );
            }

            if (changes.description) {
                lines.push(
                    "  DESCRIPTION // "
                    + (
                        String(current.description || "")
                        || "(EMPTY)"
                      )
                    + " → "
                    + (
                        String(proposed.description || "")
                        || "(EMPTY)"
                      )
                );
            }

            if (changes.name) {
                lines.push(
                    "  REPOSITORY // "
                    + String(current.fullName || repository)
                    + " → "
                    + String(proposed.fullName || "")
                );
            }
        }

        lines.push(
            "SUMMARY // "
            + String(changeTargets)
            + " CHANGE // "
            + String(noops)
            + " NO-OP // "
            + String(errors)
            + " ERROR"
        );

        if (cleanDraft.repositoryName)
            lines.push("WARNING // RENAME CHANGES THE GITHUB REPOSITORY URL.");

        if (cleanDraft.visibility !== "keep")
            lines.push("WARNING // VISIBILITY CHANGES TAKE EFFECT ON GITHUB.");

        return {
            text: lines.join("\n"),
            errors: errors,
            changeTargets: changeTargets,
            noops: noops
        };
    }

    function previewBatch(targets, draft) {
        if (reviewBusy || busy)
            return false;

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

        reviewBusy = true;
        reviewInvalidated = false;
        reviewReady = false;
        reviewFingerprint = "";
        pendingReviewFingerprint =
            fingerprint(cleanTargets, cleanDraft);
        pendingReviewTargets = cleanTargets.slice();
        pendingReviewDraft = cleanDraft;
        preflightRows = [];

        reviewText =
            "READING CURRENT GITHUB STATE // "
            + String(cleanTargets.length)
            + " REPOSITORY"
            + (cleanTargets.length === 1 ? "" : "IES");
        resultText = reviewText;
        lastError = "";

        reviewStdoutSeen = false;
        reviewStderrSeen = false;
        reviewExitSeen = false;
        reviewExitCode = -1;
        reviewStdoutText = "";
        reviewStderrText = "";

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
                'tmp="$(mktemp)"',
                'trap \'rm -f "$tmp"\' EXIT',
                "desired_json=\"$(printf \"%s\" \"$topics_text\" | jq -Rsc 'split(\"\\n\") | map(select(length > 0)) | unique | sort')\"",
                'for repo in "$@"; do',
                '  meta="$(gh api "repos/$repo" 2>/dev/null)" || {',
                '    jq -nc --arg repo "$repo" --arg detail "REPOSITORY READ FAILED" \'{repo:$repo,state:"ERROR",detail:$detail}\' >> "$tmp"',
                '    continue',
                '  }',
                "  topics=\"$(gh api \"repos/$repo/topics\" --jq '.names | unique | sort' 2>/dev/null)\" || {",
                '    jq -nc --arg repo "$repo" --arg detail "TOPIC READ FAILED" \'{repo:$repo,state:"ERROR",detail:$detail}\' >> "$tmp"',
                '    continue',
                '  }',
                "  current_visibility=\"$(printf \"%s\" \"$meta\" | jq -r '.visibility // (if .private then \"private\" else \"public\" end)')\"",
                "  current_description=\"$(printf \"%s\" \"$meta\" | jq -r '.description // \"\"')\"",
                "  current_name=\"$(printf \"%s\" \"$meta\" | jq -r '.name // \"\"')\"",
                "  current_full=\"$(printf \"%s\" \"$meta\" | jq -r '.full_name // \"\"')\"",
                "  current_owner=\"$(printf \"%s\" \"$meta\" | jq -r '.owner.login // \"\"')\"",
                '  proposed_visibility="$current_visibility"',
                '  [ "$visibility" = "keep" ] || proposed_visibility="$visibility"',
                '  proposed_description="$current_description"',
                '  if [ "$description_mode" = "set" ]; then proposed_description="$description"; fi',
                '  if [ "$description_mode" = "clear" ]; then proposed_description=""; fi',
                '  proposed_name="$current_name"',
                '  [ -z "$repo_name" ] || proposed_name="$repo_name"',
                '  proposed_full="$current_full"',
                '  if [ -n "$repo_name" ] && [ -n "$current_owner" ]; then proposed_full="$current_owner/$repo_name"; fi',
                '  proposed_topics="$topics"',
                '  if [ "$desired_json" != "[]" ]; then',
                '    case "$topic_mode" in',
                '      add) proposed_topics="$(jq -nc --argjson c "$topics" --argjson d "$desired_json" \'($c + $d) | unique | sort\')" ;;',
                '      remove) proposed_topics="$(jq -nc --argjson c "$topics" --argjson d "$desired_json" \'($c - $d) | unique | sort\')" ;;',
                '      replace) proposed_topics="$desired_json" ;;',
                '    esac',
                '  fi',
                '  visibility_changed=false; [ "$current_visibility" = "$proposed_visibility" ] || visibility_changed=true',
                '  description_changed=false; [ "$current_description" = "$proposed_description" ] || description_changed=true',
                '  name_changed=false; [ "$current_name" = "$proposed_name" ] || name_changed=true',
                '  topics_changed=false; [ "$(printf "%s" "$topics" | jq -cS .)" = "$(printf "%s" "$proposed_topics" | jq -cS .)" ] || topics_changed=true',
                '  jq -nc --arg repo "$repo" --arg cv "$current_visibility" --arg pv "$proposed_visibility" --arg cd "$current_description" --arg pd "$proposed_description" --arg cn "$current_name" --arg pn "$proposed_name" --arg cf "$current_full" --arg pf "$proposed_full" --argjson ct "$topics" --argjson pt "$proposed_topics" --argjson vc "$visibility_changed" --argjson tc "$topics_changed" --argjson dc "$description_changed" --argjson nc "$name_changed" \'{repo:$repo,state:"OK",current:{visibility:$cv,topics:$ct,description:$cd,name:$cn,fullName:$cf},proposed:{visibility:$pv,topics:$pt,description:$pd,name:$pn,fullName:$pf},changes:{visibility:$vc,topics:$tc,description:$dc,name:$nc}}\' >> "$tmp"',
                'done',
                'jq -s "." "$tmp"'
            ].join("\n"),
            "pa-repo-profile-preflight",
            cleanDraft.visibility,
            cleanDraft.topicMode,
            cleanDraft.topics.join("\n"),
            cleanDraft.descriptionMode,
            cleanDraft.description,
            cleanDraft.repositoryName
        ];

        for (let i = 0; i < cleanTargets.length; ++i)
            args.push(cleanTargets[i]);

        reviewProcess.exec(args);
        reviewWatchdog.restart();
        return true;
    }

    function maybeFinishReview() {
        if (!reviewBusy
                || !reviewStdoutSeen
                || !reviewStderrSeen
                || !reviewExitSeen)
            return;

        reviewBusy = false;
        reviewWatchdog.stop();

        const output = String(reviewStdoutText || "").trim();
        const error = String(reviewStderrText || "").trim();

        if (reviewInvalidated) {
            reviewReady = false;
            reviewFingerprint = "";
            reviewText =
                "CHANGES MODIFIED DURING PREFLIGHT // REVIEW AGAIN.";
            resultText = reviewText;
            return;
        }

        if (reviewExitCode !== 0) {
            reviewReady = false;
            reviewFingerprint = "";
            lastError =
                error || output || "REPOSITORY PROFILE PREFLIGHT FAILED";
            reviewText = "REVIEW FAILED // " + lastError;
            resultText = reviewText;
            return;
        }

        try {
            const parsed = JSON.parse(output || "[]");
            preflightRows = Array.isArray(parsed) ? parsed : [];

            const report = preflightReviewText(
                preflightRows,
                pendingReviewTargets,
                pendingReviewDraft
            );

            reviewText = report.text;

            if (report.errors > 0) {
                reviewReady = false;
                reviewFingerprint = "";
                resultText =
                    "REVIEW BLOCKED // "
                    + String(report.errors)
                    + " TARGET READ ERROR"
                    + (report.errors === 1 ? "" : "S");
                lastError = resultText;
                return;
            }

            if (report.changeTargets === 0) {
                reviewReady = false;
                reviewFingerprint = "";
                resultText = "NO-OP // ALL TARGETS ALREADY MATCH";
                lastError = "";
                return;
            }

            reviewFingerprint = pendingReviewFingerprint;
            reviewReady = true;
            resultText =
                "REVIEW READY // "
                + String(report.changeTargets)
                + " TARGET"
                + (report.changeTargets === 1 ? "" : "S")
                + " WILL CHANGE";
            lastError = "";
        } catch (parseError) {
            preflightRows = [];
            reviewReady = false;
            reviewFingerprint = "";
            lastError =
                "PREFLIGHT RESPONSE PARSE // "
                + String(parseError);
            reviewText = "REVIEW FAILED // " + lastError;
            resultText = reviewText;
        }
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
        batchResults = [];
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

    function parseBatchResults(text) {
        const lines = String(text || "").split("\n");
        const rows = [];

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "").trim();

            if (line.indexOf("OK // ") === 0) {
                rows.push({
                    state: "OK",
                    repository: line.slice(6).trim(),
                    detail: ""
                });
                continue;
            }

            if (line.indexOf("FAILED // ") === 0) {
                const parts = line.split(" // ");
                rows.push({
                    state: "FAILED",
                    repository:
                        parts.length > 1 ? parts[1] : "",
                    detail:
                        parts.length > 2
                        ? parts.slice(2).join(" // ")
                        : ""
                });
            }
        }

        batchResults = rows;
    }

    function maybeFinish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen)
            return;

        busy = false;
        watchdog.stop();

        const output = String(stdoutText || "").trim();
        const error = String(stderrText || "").trim();

        parseBatchResults(output);

        if (exitCode === 0) {
            resultText =
                "COMPLETE // "
                + String(batchSuccessCount)
                + " OK // 0 FAILED"
                + (output ? "\n" + output : "");
            lastError = "";
            batchFinished(true);
            return;
        }

        const summary =
            batchSuccessCount > 0
            ? (
                "PARTIAL // "
                + String(batchSuccessCount)
                + " OK // "
                + String(batchFailureCount)
                + " FAILED"
              )
            : (
                "FAILED // 0 OK // "
                + String(batchFailureCount)
                + " FAILED"
              );

        lastError =
            error
            || (
                batchFailureCount > 0
                ? String(batchFailureCount)
                  + " REPOSITORY TARGET"
                  + (batchFailureCount === 1 ? "" : "S")
                  + " FAILED"
                : "REPOSITORY PROFILE APPLY FAILED"
              );

        resultText =
            summary
            + (output ? "\n" + output : "")
            + (error ? "\nERROR // " + error : "");
        batchFinished(false);
    }

    Process {
        id: reviewProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.reviewStdoutText = this.text;
                root.reviewStdoutSeen = true;
                root.maybeFinishReview();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.reviewStderrText = this.text;
                root.reviewStderrSeen = true;
                root.maybeFinishReview();
            }
        }

        onExited: function(exitCode, exitStatus) {
            root.reviewExitCode = Number(exitCode);
            root.reviewExitSeen = true;
            root.maybeFinishReview();
        }
    }

    Timer {
        id: reviewWatchdog
        interval: 120000
        repeat: false

        onTriggered: {
            root.reviewBusy = false;
            root.reviewReady = false;
            root.reviewFingerprint = "";
            root.lastError =
                "REPOSITORY PROFILE PREFLIGHT TIMEOUT";
            root.reviewText =
                "REVIEW FAILED // "
                + root.lastError;
            root.resultText = root.reviewText;
        }
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
            root.lastError =
                "REPOSITORY PROFILE APPLY TIMEOUT // RESULT UNCERTAIN";
            root.resultText =
                "UNCERTAIN // TIMEOUT // SOME REPOSITORIES MAY HAVE CHANGED\n"
                + root.lastError;
            root.batchFinished(false);
        }
    }
}
