.pragma library

// Source-backed help map, intentionally separate from the Prism placement
// registry. These are mounted shell entry points, not live service statuses.
// Order within each group follows shell.qml; the map is not pixel-scaled.
var zones = [
    { id: "top-left", label: "TOP LEFT", entries: [
        { name: "APP CONTROL", mount: "AppControlW" },
        { name: "WORKSPACES", mount: "Workspaces" },
        { name: "MEDIA", mount: "Mediaplayer" },
        { name: "CAMERA", mount: "CameraW" },
        { name: "HOSPITAL", mount: "HospitalW" },
        { name: "FINANCE", mount: "FinanceW" },
        { name: "GIT", mount: "GitW" },
        { name: "COMPANY NETWORK", mount: "CompanyNetworkW" },
        { name: "TO-DO", mount: "TasksW" },
        { name: "FOREST", mount: "ForestW" }
    ] },
    { id: "top-center", label: "TOP CENTER", entries: [
        { name: "APOLLO HUB", mount: "ApolloHubW" }
    ] },
    { id: "top-right", label: "TOP RIGHT", entries: [
        { name: "NETWORK", mount: "Network" },
        { name: "BLUETOOTH", mount: "Bluetooth" },
        { name: "CPU++", mount: "CpuPlusW" },
        { name: "WEATHER", mount: "WeatherStationW" },
        { name: "VOLUME", mount: "Volumebar" },
        { name: "MESSAGING", mount: "MessagingW" },
        { name: "CLOCK / TIME", mount: "TimeW" },
        { name: "NOTIFICATIONS", mount: "NotificationsHubW" }
    ] },
    { id: "bottom-left", label: "BOTTOM LEFT", entries: [
        { name: "TRASH", mount: "Trash" },
        { name: "PRISM", mount: "PrismDock" }
    ] },
    { id: "bottom-center", label: "BOTTOM CENTER", entries: [
        { name: "SYSTEM TRAY", mount: "Tray" }
    ] },
    { id: "bottom-right", label: "BOTTOM RIGHT", entries: [
        { name: "POWER", mount: "Power" }
    ] }
];

function mapZones() {
    return zones.map(function(zone) {
        return { id: zone.id, label: zone.label,
                 entries: zone.entries.map(function(entry) {
                     return { name: entry.name, mount: entry.mount };
                 }) };
    });
}

/* Functional map. Stable keys identify help topics, never live QObjects or
 * actions. Related topics are navigational links inside Prism only.
 * Keep claims about installed features narrower than the intended design.
 */
var guides = {
    AppControlW: {
        title: "APP CONTROL", path: "APP CONTROL",
        purpose: "Find and manage applications and their running processes.",
        detail: "Start here when you want to work with an application. KILL is the process-management section; it is not a separate application launcher.",
        related: ["app-kill", "CpuPlusW"]
    },
    "app-kill": {
        title: "APP CONTROL // KILL", path: "APP CONTROL > KILL > SELECT PROCESS",
        purpose: "Inspect a running process and reach its process controls.",
        detail: "Select a live process to see its details and available actions. CPU++ also presents the extracted Kill task-manager view through the shared Kill backend. Use CPU++ for the wider resource and process workspace. Ending or changing a critical process can disrupt the desktop; review the target and confirmation before acting.",
        related: ["AppControlW", "cpu-kill"]
    },
    CpuPlusW: {
        title: "CPU++", path: "CPU++",
        purpose: "Inspect system resources and investigate performance.",
        detail: "CPU++ organizes resource views and diagnostics, including its KILL mode for process management. Go to KILL when a resource problem needs to be traced to a running process.",
        related: ["cpu-kill", "AppControlW"]
    },
    "cpu-kill": {
        title: "CPU++ // KILL", path: "CPU++ > KILL > SELECT LIVE PROCESS",
        purpose: "Inspect a process in the larger resource-management workspace.",
        detail: "This view reuses the extracted App Control task-manager detail and the shared KillStore. Select a live process in the middle bay, inspect CPU, memory, RSS, threads, swap, I/O and uptime evidence, then use the controls that are actually available. An unavailable capability is not permission to change it. Review and confirmation are required for destructive actions.",
        related: ["app-kill", "CpuPlusW"]
    },
    ForestW: {
        title: "FOREST", path: "FOREST > TREES",
        purpose: "A local-first workspace for organizing AI assistants, their chats and model equipment.",
        detail: "Trees represent assistant roles and equipment. Forest is intended to organize conversations and local AI work without confusing a selected Tree, a model inventory or a visual preview with permission to run a model. Interactive inference depends on the installed runtime and its current readiness.",
        related: ["HospitalW", "PrismDock"]
    },
    HospitalW: {
        title: "HOSPITAL", path: "HOSPITAL > RECEPTION / SURGERY",
        purpose: "Coordinate project work, worker assignments, handoffs and review.",
        detail: "Reception is an entry point to the Hospital workflow. Surgery includes registered workers and their work context. Use it to understand who owns an assignment and what work is being reviewed. Navigating these views does not dispatch a worker or approve a change.",
        related: ["GitW", "ForestW"]
    },
    PrismDock: {
        title: "PRISM", path: "BOTTOM DOCK > PRISM",
        purpose: "Make Post Apollo understandable: separate its visual language, features, routes and relationships into distinguishable layers.",
        detail: "Like a prism separating light, this help system separates the desktop's complexity into understandable parts. SYNTAGMA explains the visual grammar; ATLAS explains what features do, where to find them and how they connect. The diagnostic index lists installed Prism entry points.",
        related: ["AppControlW", "ForestW", "HospitalW"]
    },
    Workspaces: { title:"WORKSPACES",path:"TOP DOCK > WORKSPACES",purpose:"Switch between desktop workspaces.",detail:"Click a workspace to select it or scroll between workspaces.",related:[] },
    Mediaplayer: { title:"MEDIA",path:"TOP DOCK > MEDIA",purpose:"Reach media playback and the expanded media deck.",detail:"The compact media module owns the initial MPD controls; its expanded deck is a separate window.",related:["Volumebar"] },
    CameraW: { title:"CAMERA",path:"CAMERA > CAPTURE / GALLERY / ZOOM",purpose:"Capture, inspect and organize images.",detail:"Camera owns its capture, gallery and zoom views. The Cleanup workflow is presented in Trash while Camera retains its shared cleanup queue.",related:["Trash"] },
    FinanceW: { title:"FINANCE",path:"FINANCE",purpose:"Navigate budgeting, market research and account management.",detail:"Budget, public Market and manual Banking are distinct areas. A public market view does not grant permission to access or change banking data.",related:[] },
    GitW: { title:"GIT",path:"GIT",purpose:"Inspect repositories and navigate development work.",detail:"Use the Git workspace for project and repository operations. Reviewing information is separate from applying or merging changes.",related:["HospitalW"] },
    CompanyNetworkW: { title:"COMPANY NETWORK",path:"COMPANY NETWORK > COVERAGE / NETWORK / WORKFORCE / EXPANSION",purpose:"Organize territory, partner, workforce and expansion planning.",detail:"The current shell includes those navigation sections. Some company data and views are still scaffolding.",related:[] },
    TasksW: { title:"TO-DO",path:"TO-DO > TASKS / TODAY / PROJECTS / PLANNER",purpose:"Organize tasks and plans.",detail:"Use the task, day, project and planner modes to navigate work at different levels.",related:["GitW"] },
    ApolloHubW: { title:"APOLLO HUB",path:"CENTER DOCK > APOLLO HUB",purpose:"A configurable central dashboard for existing Post Apollo modules.",detail:"Hub tiles present information and supported owner-routed actions. They do not create independent copies of the underlying services.",related:["CpuPlusW","TasksW","TimeW"] },
    Network: { title:"NETWORK",path:"TOP DOCK > NETWORK",purpose:"Inspect network device and connection state.",detail:"The network module owns its existing connection observations. CPU++ can consume a bounded read-only summary.",related:["CpuPlusW"] },
    Bluetooth: { title:"BLUETOOTH",path:"TOP DOCK > BLUETOOTH",purpose:"Find the Bluetooth module.",detail:"Detailed controls and navigation still need a source-backed guide.",related:[] },
    WeatherStationW: { title:"WEATHER",path:"TOP DOCK > WEATHER",purpose:"Find the weather workspace.",detail:"Detailed weather modes and service relationships still need a source-backed guide.",related:[] },
    Volumebar: { title:"VOLUME",path:"TOP DOCK > VOLUME",purpose:"Control the master audio output.",detail:"The shared volume module is the owner of the master-output control. It is distinct from the media player's playback controls.",related:["Mediaplayer","ApolloHubW"] },
    MessagingW: { title:"MESSAGING",path:"TOP DOCK > MESSAGING",purpose:"Find the messaging workspace.",detail:"Detailed provider and conversation navigation still need a source-backed guide.",related:[] },
    TimeW: { title:"CLOCK / TIME",path:"CLOCK > TIME",purpose:"Navigate clocks, time zones and time tools.",detail:"The Clock dock opens TimeW, which owns the time-tool views and timer state. Other widgets may present the same owner-controlled timers.",related:["ApolloHubW"] },
    NotificationsHubW: { title:"NOTIFICATIONS",path:"TOP DOCK > NOTIFICATIONS",purpose:"Find notification history and controls.",detail:"The shell mounts a separate incoming-notification popup and the notification history/control hub. Detailed mode navigation still needs a guide.",related:[] },
    Trash: { title:"TRASH",path:"BOTTOM DOCK > TRASH",purpose:"Review discarded files and records and access cleanup.",detail:"Trash provides file and record views and hosts the Camera cleanup workflow. Reviewing an item is separate from permanently deleting it.",related:["CameraW"] },
    Tray: { title:"SYSTEM TRAY",path:"BOTTOM CENTER > SYSTEM TRAY",purpose:"See application-provided tray items.",detail:"The shell displays a tray area independent of the Post Apollo widget dock; its contents depend on registered tray items.",related:[] },
    Power: { title:"POWER",path:"BOTTOM RIGHT > POWER",purpose:"Find system power controls.",detail:"The power menu is separate from the help system. Atlas never triggers power actions.",related:[] }
};

function guideFor(key) {
    if (!Object.prototype.hasOwnProperty.call(guides,key)) return null;
    const g=guides[key];
    return { key:key, title:g.title, path:g.path, purpose:g.purpose,
             detail:g.detail, related:g.related.slice() };
}

function guideEntries() {
    const result=[];
    for (let i=0;i<zones.length;i++)
        for(let j=0;j<zones[i].entries.length;j++)
            result.push(guideFor(zones[i].entries[j].mount));
    return result;
}
