.pragma library

// TASKS TODAY: pure view of the existing v2 checklist snapshot.
// Local civil dates are YYYY-MM-DD and compare lexicographically.
// Do not infer a task's completion date from its done boolean.
function view(snapshot, today) {
    var validDate = typeof today === "string"
                    && /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(today);
    var state = snapshot && typeof snapshot.state === "string"
                ? snapshot.state : "unavailable";
    var accessible = state === "ready" || state === "empty"
                     || state === "saving";
    if (!validDate || !accessible || !snapshot
            || !Array.isArray(snapshot.items)) {
        return {available:false, state:state, today:validDate ? today : "",
                overdue:0, dueToday:0, completedDueToday:0,
                unscheduled:0, upcoming:0, rows:[]};
    }

    var late = [];
    var due = [];
    var completed = [];
    var undated = 0;
    var upcoming = 0;
    snapshot.items.forEach(function(item) {
        if (!item || typeof item.id !== "string"
                || typeof item.title !== "string"
                || typeof item.done !== "boolean")
            return;
        if (item.dueDate === null || item.dueDate === "") {
            if (!item.done) undated++;
            return;
        }
        if (typeof item.dueDate !== "string"
                || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(item.dueDate))
            return;
        var row = {kind:"task", id:item.id, title:item.title,
                   dueDate:item.dueDate, done:item.done,
                   priority:typeof item.priority === "string"
                            ? item.priority : "none"};
        if (item.dueDate < today && !item.done)
            late.push(row);
        else if (item.dueDate === today && !item.done)
            due.push(row);
        else if (item.dueDate === today && item.done)
            completed.push(row);
        else if (item.dueDate > today && !item.done)
            upcoming++;
    });
    late.sort(function(a,b) {
        if (a.dueDate < b.dueDate) return -1;
        if (a.dueDate > b.dueDate) return 1;
        return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
    });
    var rows = [];
    function addSection(label, items, category) {
        if (items.length === 0) return;
        rows.push({kind:"header", text:label + " // " + items.length,
                   category:category});
        items.forEach(function(row) {
            row.category = category;
            rows.push(row);
        });
    }
    addSection("OVERDUE", late, "overdue");
    addSection("DUE TODAY", due, "due");
    addSection("DONE // DUE TODAY", completed, "completed");

    return {available:true, state:state, today:today,
            overdue:late.length, dueToday:due.length,
            completedDueToday:completed.length, unscheduled:undated,
            upcoming:upcoming, rows:rows};
}
