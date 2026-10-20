import QtQuick
import Quickshell
import qs.services.notifications
import "GitHubActionNotificationPolicy.js" as ActionsPolicy

// Existing GitHub Issue and PR review-thread mutationFinished only.
// Does not mutate GitHub, fetch, poll, or include review text / issue body.
Scope {
    id: producer
    required property var issueLifecycle
    required property var reviewLifecycle

    function publish(item) {
        if (!item || !NotificationsService.historyReady)
            return;
        const ok = item.outcome === "VERIFIED";
        const target = item.type === "issue" ? "ISSUE" : "PR REVIEW THREAD";
        NotificationsService.pushRich({
            "source": "GITHUB",
            "sourceId": "github",
            "category": "internal",
            "severity": ok ? "normal" : "warning",
            "title": "GITHUB // " + target + " "
                     + item.action.toUpperCase() + " " + item.outcome,
            "message": ok
                ? "GitHub evidence confirmed the completed " + item.action
                  + " operation. // " + item.repository + " #" + item.number
                : "The " + item.action + " operation "
                  + (item.outcome === "UNVERIFIED"
                     ? "reported process success without confirmed evidence."
                     : "failed to complete.")
                  + " Inspect GitHub before acting. // " + item.repository
                  + (item.number ? " #" + item.number : ""),
            "tags": ["github", item.type === "issue" ? "issue" : "pr-review",
                     "mutation-outcome"],
            "context": {
                "repository": item.repository,
                "eventType": "github-" + item.type + "-"
                           + item.action + "-" + item.outcome.toLowerCase(),
                "origin": "apollo",
                "domain": "git",
                "issueNumber": item.type === "issue" ? item.number : 0,
                "pullRequestNumber": item.type === "review" ? item.number : 0,
                "evidence": item.outcome === "VERIFIED"
                            ? "readback-confirmed" : "unconfirmed"
            }
        });
    }
    function issueFinished(succeeded, verified, operation, evidence) {
        producer.publish(ActionsPolicy.issue(
            succeeded, verified, operation, evidence,
            producer.issueLifecycle.pendingRepository,
            producer.issueLifecycle.pendingEvidenceTarget));
    }
    function reviewFinished(succeeded, verified, operation, evidence) {
        producer.publish(ActionsPolicy.review(
            succeeded, verified, operation, evidence,
            producer.reviewLifecycle.repository,
            producer.reviewLifecycle.pullRequestNumber));
    }
    Connections {
        target: producer.issueLifecycle
        function onMutationFinished(succeeded, verified, operation, evidence) {
            producer.issueFinished(succeeded, verified, operation, evidence);
        }
    }
    Connections {
        target: producer.reviewLifecycle
        function onMutationFinished(succeeded, verified, operation, evidence) {
            producer.reviewFinished(succeeded, verified, operation, evidence);
        }
    }
}
