pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "ApolloHubTodoPolicy.js" as TodoPolicy
import "TaskLocalTicketProducerM12q.js" as TicketProducer

// B7: one local, opt-in checklist store for Hub To-do.
// This is NOT a Hospital assignment manager, calendar, or AppControl task.
// Creating this singleton only reads data. Writes require an explicit
// add/rename/setDone/remove call by the owning UI.
Scope {
    id: todo

    readonly property string storagePath:
        Quickshell.dataDir + "/apollo-hub-todo-v1.json"

    // M11l: no operator-facing activation exists. Enabling guarded mode
    // without a verified OS host must fail closed, not fall through to JSON.
    // A later, separately reviewed patch must replace this constant with a
    // correctly fenced, opt-in integration before protected writes exist.
    readonly property bool guardedWriterEnabled: false

    // M12q: source-level only. This is a compile-time false gate; the
    // existing FileView/boolean methods are still the running writer.
    readonly property bool ticketProducerEnabled: false
    readonly property bool independentlyAuthenticatedTicketReceipt: false
    property string ticketSessionNonce:
        String(Date.now()) + String(Math.floor(Math.random() * 1000000000))
    property int ticketSequence: 0
    property var pendingTicket: null
    signal ticketEvent(var event)

    property string storageState: "loading"
    property string errorCode: ""
    property var document: TodoPolicy.emptyDocument()
    property var pendingDocument: null
    readonly property var snapshot:
        TodoPolicy.view(storageState, document, errorCode)

    // Reuses todoFile; no new FileView, daemon, or real-data migration.
    // A caller receives a ticket on admission, never a durable-success bool.
    // This path remains inactive until separately authorized and tested.
    function submit(surface, method, payload) {
        if (!ticketProducerEnabled || guardedWriterEnabled)
            return TicketProducer.refusal("M12Q_DISABLED_NO_WRITER");
        if (storageState !== "ready" && storageState !== "empty")
            return TicketProducer.refusal("STORAGE_NOT_READY");
        if (pendingTicket !== null || pendingDocument !== null)
            return TicketProducer.refusal("WRITE_ALREADY_PENDING");
        if (!payload || typeof payload !== "object" || !payload.args)
            return TicketProducer.refusal("INVALID_PAYLOAD");
        var nextSequence=ticketSequence+1;
        var stage=TicketProducer.plan(TodoPolicy,document,surface,method,
                payload.args,Date.now(),ticketSessionNonce,nextSequence);
        if (!stage.admitted) return stage;
        ticketSequence=nextSequence;
        pendingTicket=stage;
        pendingDocument=stage.expectedDocument;
        storageState="saving";
        errorCode="";
        todoFile.setText(stage.expectedRaw);
        // No synchronous completion event before the consumer receives ID.
        return {admitted:true,ticketId:stage.ticketId,state:"QUEUED",
                expected:stage.expected,baseline:stage.baseline};
    }

    function ticketReview(reason) {
        if (!pendingTicket) return;
        var stage=pendingTicket;
        // Last-confirmed document is retained. User draft remains with UI.
        // Never auto-retry an ambiguous FileView outcome.
        storageState="error";
        errorCode="TICKET_"+String(reason || "UNVERIFIED").slice(0,60);
        pendingDocument=null;
        pendingTicket=null;
        ticketEvent({ticketId:stage.ticketId,state:"REVIEW_REQUIRED",
                     reason:errorCode,evidence:"NONE"});
    }

    function ticketReadback(raw) {
        if (!pendingTicket || pendingTicket.state !== "VERIFYING") {
            ticketReview("UNEXPECTED_READBACK");
            return;
        }
        var stage=pendingTicket;
        var result=TicketProducer.verify(TodoPolicy,stage,raw);
        if (!result.confirmed) {
            ticketReview(result.reason);
            return;
        }
        // In this *disabled* path, confirmation would mean FileView saved
        // then reloaded exact bytes; NOT a crypto/OS provenance assertion.
        document=result.document;
        pendingDocument=null;
        pendingTicket=null;
        storageState=document.tasks.length ? "ready" : "empty";
        errorCode="";
        ticketEvent({ticketId:stage.ticketId,state:"CONFIRMED",
                     evidence:result.evidence});
    }

    function acceptLoaded(raw) {
        if (ticketProducerEnabled && storageState === "saving") {
            ticketReadback(raw);
            return;
        }
        if (storageState === "saving")
            return;
        const result = TodoPolicy.parse(raw);
        if (!result.ok) {
            // Fail closed. A damaged or future-version file must never be
            // replaced with an empty list or implicitly repaired.
            document = TodoPolicy.emptyDocument();
            storageState = result.reason === "UNSUPPORTED_VERSION"
                         ? "unsupported" : "error";
            errorCode = result.reason;
            return;
        }
        document = result.document;
        storageState = document.tasks.length ? "ready" : "empty";
        errorCode = "";
    }

    function reloadFromDisk() {
        if (storageState === "saving")
            return false;
        storageState = "loading";
        errorCode = "";
        todoFile.reload();
        return true;
    }

    function stage(result) {
        // The single shared write seam remains the only entry point.
        // An unverified guarded-mode request may never use legacy FileView.
        if (guardedWriterEnabled)
            return false;
        if (storageState !== "ready" && storageState !== "empty")
            return false;
        if (!result || result.ok !== true)
            return false;
        pendingDocument = result.document;
        storageState = "saving";
        errorCode = "";
        // FileView's atomicWrites protects an existing file on failure.
        // Do not publish the pending tasks as saved before onSaved.
        todoFile.setText(JSON.stringify(pendingDocument, null, 2) + "\n");
        return true;
    }

    function addTask(title) {
        return stage(TodoPolicy.create(document, title, Date.now()));
    }

    function setTaskDone(id, done) {
        return stage(TodoPolicy.update(document, id, "done",
                                      done, Date.now(), false));
    }

    function renameTask(id, title) {
        return stage(TodoPolicy.update(document, id, "rename",
                                      title, Date.now(), false));
    }

    // One atomic edit of all optional details, using the existing writer.
    function updateTaskDetails(id, priority, description, dueDate) {
        return stage(TodoPolicy.updateDetails(document, id, priority,
                                              description, dueDate, Date.now()));
    }

    // The only filesystem writer also owns project creation/assignment.
    function createProject(name) {
        return stage(TodoPolicy.createProject(document, name, Date.now()));
    }

    function assignTaskProject(taskId, projectId) {
        return stage(TodoPolicy.assignProject(document, taskId,
                                              projectId, Date.now()));
    }

    function renameProject(projectId, name) {
        return stage(TodoPolicy.renameProject(document, projectId,
                                             name, Date.now()));
    }

    function deleteProject(projectId, confirmed) {
        return stage(TodoPolicy.deleteProject(document, projectId,
                                             Date.now(), confirmed));
    }

    function removeTask(id, confirmed) {
        return stage(TodoPolicy.update(document, id, "delete",
                                      null, Date.now(), confirmed));
    }

    FileView {
        id: todoFile
        path: todo.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: todo.acceptLoaded(todoFile.text())
        onLoadFailed: function(error) {
            if (todo.ticketProducerEnabled && todo.pendingTicket) {
                todo.ticketReview("FILE_RELOAD_FAILED");
                return;
            }
            if (todo.storageState === "saving")
                return;
            if (error === FileViewError.FileNotFound) {
                // Missing file is the one legitimate empty initial state.
                // Do NOT write a new file until a deliberate task action.
                todo.document = TodoPolicy.emptyDocument();
                todo.storageState = "empty";
                todo.errorCode = "";
            } else {
                todo.storageState = "error";
                todo.errorCode = "FILE_LOAD_FAILED";
            }
        }
        onSaved: {
            if (todo.ticketProducerEnabled) {
                if (!todo.pendingTicket || todo.pendingTicket.state !== "WRITING") {
                    todo.ticketReview("UNEXPECTED_SAVED_HINT");
                    return;
                }
                todo.pendingTicket=TicketProducer.saved(todo.pendingTicket);
                if (todo.pendingTicket.state !== "VERIFYING") {
                    todo.ticketReview("INVALID_SAVED_TRANSITION");
                    return;
                }
                var callbackTicket=todo.pendingTicket.ticketId;
                // FileView's onSaved is merely a signal; defer reload until
                // after the callback unwinds, then compare actual text.
                Qt.callLater(function() {
                    if (todo.ticketProducerEnabled && todo.pendingTicket &&
                            todo.pendingTicket.ticketId === callbackTicket &&
                            todo.pendingTicket.state === "VERIFYING" &&
                            todo.storageState === "saving")
                        todoFile.reload();
                });
                return;
            }
            if (todo.storageState !== "saving" || !todo.pendingDocument)
                return;
            todo.document = todo.pendingDocument;
            todo.pendingDocument = null;
            todo.storageState = todo.document.tasks.length ? "ready" : "empty";
            todo.errorCode = "";
        }
        onSaveFailed: function(error) {
            if (todo.ticketProducerEnabled && todo.pendingTicket) {
                todo.ticketReview("FILE_SAVE_FAILED");
                return;
            }
            // Preserve the last confirmed document; never claim the rejected
            // change was saved. Explicit reload is needed before more writes.
            todo.pendingDocument = null;
            todo.storageState = "error";
            todo.errorCode = "FILE_SAVE_FAILED";
        }
    }
}
