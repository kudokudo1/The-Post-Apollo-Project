.pragma library

// Pure, allowlisted destination resolver. An Apollo notification may choose
// a known UI surface from structured producer metadata only. Never execute
// a title, body, repository slug, Room ID, URL, or arbitrary action string.
function text(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}

function routeFor(entry) {
    if (!entry)
        return null;
    const id = text(entry.sourceId);
    const ctx = entry.context && typeof entry.context === "object"
        ? entry.context : {};
    const event = text(ctx.eventType);

    if (id === "cpu-plus" && event === "hardware-thermal-limit")
        return { widget: "cpu", mode: "thermal", subMode: "temp" };
    if (id === "cpu-plus-fan-health"
            && (event === "fan-rpm-recovered" || event.startsWith("fan-rpm-")))
        return { widget: "cpu", mode: "thermal", subMode: "fan" };
    if (id === "cpu-plus-system" && event === "system-observation-report")
        return { widget: "cpu", mode: "system", subMode: "ALL" };
    if (id === "cpu-plus-telemetry-health"
            && (event === "cpu-monitor-unavailable" || event === "cpu-monitor-restored"))
        return { widget: "cpu", mode: "system", subMode: "ALL" };
    if (id === "cpu-plus-resource-pressure" && event.startsWith("resource-pressure-")) {
        const metric = text(ctx.metric).toLowerCase();
        const subMode = metric === "memory" ? "MEMORY"
            : metric === "storage" ? "STORAGE"
            : metric === "swap" ? "SWAP" : "ALL";
        return { widget: "cpu", mode: "system", subMode: subMode };
    }

    if (id === "weather-brief" && event === "weather-daily-report")
        return { widget: "weather", view: "ground" };
    if (id === "weather-station" && event === "aqi-unhealthy-transition")
        return { widget: "weather", view: "ground" };
    if (id === "weather-station-nws" && event.startsWith("nws-"))
        return { widget: "weather", view: "ground" };
    if (id === "weather-space" && event === "solar-daily-report")
        return { widget: "weather", view: "space" };
    if (id === "weather-space-storm" && event.startsWith("geomagnetic-storm-"))
        return { widget: "weather", view: "space" };

    if (id === "hospital" && event === "room-reports-newly-listed") {
        const team = text(ctx.roomId);
        // Filter only; never rebind the live Room/Patient based on a stale
        // notification. The established Hospital-wide Reports view handles it.
        return { widget: "hospital", view: "reports",
                 team: team.length <= 128 ? team : "" };
    }
    if (id === "hospital" && event !== "")
        return { widget: "hospital", view: "reception" };

    if (id === "git-local-journal" && event.startsWith("git-journal-"))
        return { widget: "git", view: "operations" };
    if (id === "github" && event !== "") {
        const slug = text(ctx.repository);
        const number = Number(ctx.pullRequestNumber || 0);
        if (/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(slug)
                && Number.isSafeInteger(number) && number > 0)
            return { widget: "git", view: "pull", repository: slug, number: number };
        if (Number(ctx.issueNumber || 0) > 0)
            return { widget: "git", view: "issues" };
        return { widget: "git", view: "github" };
    }

    if (id === "notifications-storage-health"
            && event.startsWith("notification-"))
        return { widget: "notifications", view: "system" };

    return null;
}
