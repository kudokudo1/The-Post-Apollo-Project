import QtQuick

QtObject {
    id: globalTaskActions

    required property var host
    required property var favoriteStoreObject
    required property var hunterExecutorObject
    required property var hunterPresentationObject
    required property var refreshTimer

    function hunterTargetsFromRows(rows) {
        return rows.map(function(entry) {
            return {
                pid: Number(entry.pid || 0),
                name: String(entry.comm || entry.name || "PROCESS").trim(),
                identity: host.taskPersistentIdentity(entry)
            };
        });
    }

    function hunterTargetIsFavorite(target) {
        if (!target)
            return false;

        const identity = String(target.identity || "").trim().toLowerCase();
        if (!identity)
            return false;

        const key = "task|" + encodeURIComponent(identity);
        return favoriteStoreObject.favoriteKeys.indexOf(key) !== -1;
    }



    function hunterOperationLabel() {
        return host.hunterOperationKind === "kill-mice" ? "MICE" : "HOGS";
    }

    function hunterOperationStatusLine(result) {
        const status = String(result && result.status || "");
        const name = String(result && result.name || "PROCESS");
        const pid = String(result && result.pid || "?");
        const detail = String(result && result.detail || "");
        const mark = status === "killed" ? "✓"
                     : status === "gone" ? "◇"
                     : status === "favorite" ? "♥"
                     : "⚠︎";
        return mark + " " + name + "  [PID " + pid + "] — " + detail;
    }

    function refreshHunterOperationMessage() {
        const label = hunterOperationLabel();
        const lines = [];

        if (host.hunterOperationPhase === "running") {
            lines.push(
                "HUNTING " + label + " • "
                + String(host.hunterOperationCompleted) + " / "
                + String(host.hunterOperationTotal) + " CHECKED"
            );
            lines.push("");

            for (let i = 0; i < host.hunterOperationResults.length; i++)
                lines.push(hunterOperationStatusLine(host.hunterOperationResults[i]));

            if (host.hunterOperationCompleted < host.hunterOperationTotal) {
                lines.push("");
                lines.push("… HUNTER STILL TRACKING "
                           + String(host.hunterOperationTotal - host.hunterOperationCompleted)
                           + " TARGET(S)");
            }
        } else if (host.hunterOperationPhase === "report") {
            let killed = 0;
            let escaped = 0;
            let gone = 0;
            let favoritesReleased = 0;
            for (let i = 0; i < host.hunterOperationResults.length; i++) {
                const status = String(host.hunterOperationResults[i].status || "");
                if (status === "killed") killed += 1;
                else if (status === "gone") gone += 1;
                else if (status === "favorite") favoritesReleased += 1;
                else escaped += 1;
            }

            lines.push(
                label + " HUNT REPORT • " + String(host.hunterOperationTotal)
                + " TARGET(S)"
            );
            lines.push(
                "KILLED " + String(killed)
                + " • GOT AWAY " + String(escaped)
                + " • ALREADY GONE " + String(gone)
                + " • LET LOOSE FAVORITES " + String(favoritesReleased)
            );
            lines.push("");

            for (let i = 0; i < host.hunterOperationResults.length; i++)
                lines.push(hunterOperationStatusLine(host.hunterOperationResults[i]));
        }

        host.destructiveConfirmMessage = lines.join("\n");
    }

    function showHunterOperationWindow() {
        if (host.hunterOperationPhase !== "running"
                && host.hunterOperationPhase !== "report")
            return false;

        host.destructiveConfirmKind = host.hunterOperationKind;
        host.destructiveConfirmChoice = 0;
        host.destructiveConfirmOpen = true;
        refreshHunterOperationMessage();
        return true;
    }

    function startHunterOperation(kind, targets) {
        if (host.hunterOperationActive) {
            showHunterOperationWindow();
            return;
        }

        const captured = Array.isArray(targets) ? targets.slice() : [];
        if (captured.length === 0) {
            host.cancelDestructiveConfirm();
            return;
        }

        const activeTargets = [];
        const releasedFavorites = [];

        for (let i = 0; i < captured.length; i++) {
            const target = captured[i];
            if (hunterTargetIsFavorite(target)) {
                releasedFavorites.push({
                    type: "result",
                    pid: Number(target.pid || 0),
                    name: String(target.name || "PROCESS"),
                    status: "favorite",
                    detail: "LET LOOSE • FAVORITE PROTECTED BEFORE FIRING"
                });
            } else {
                activeTargets.push(target);
            }
        }

        host.hunterOperationPhase = "running";
        host.hunterOperationKind = String(kind || "kill-hogs");
        host.hunterOperationTargets = captured;
        host.hunterOperationResults = releasedFavorites;
        host.hunterOperationCompleted = releasedFavorites.length;
        host.hunterOperationTotal = captured.length;
        host.hunterPendingTargets = [];
        host.destructiveConfirmTargetPids = [];
        host.destructiveConfirmKind = host.hunterOperationKind;
        host.destructiveConfirmChoice = 0;
        host.destructiveConfirmTitle =
            host.hunterOperationKind === "kill-mice"
            ? "⚠︎ (-_•)デ╾━  (ᐢ..ᐢ)౨  HUNTING MICE…  ⚠︎" : "⚠︎ (-_•)デ╾━  ₍˄·͈⚇·͈˄₎  HUNTING HOGS…  ⚠︎";
        host.destructiveConfirmOpen = true;
        refreshHunterOperationMessage();

        if (activeTargets.length === 0) {
            finishHunterOperation();
            return;
        }

        hunterExecutorObject.start(activeTargets);
    }

    function applyHunterOperationResult(result) {
        if (host.hunterOperationPhase !== "running")
            return;

        const payload = result || ({});
        const next = host.hunterOperationResults.slice();
        next.push(payload);
        host.hunterOperationResults = next;
        host.hunterOperationCompleted = Math.min(
            host.hunterOperationTotal,
            next.length
        );
        refreshHunterOperationMessage();
        refreshTimer.restart();
    }

    function finishHunterOperation() {
        if (host.hunterOperationPhase !== "running")
            return;

        // Never retry missing results. A bulk target receives SIGTERM at most
        // once per hunt; an unreported target is explicitly marked unknown.
        const seen = ({});
        for (let i = 0; i < host.hunterOperationResults.length; i++)
            seen[String(host.hunterOperationResults[i].pid || 0)] = true;

        const completed = host.hunterOperationResults.slice();
        for (let i = 0; i < host.hunterOperationTargets.length; i++) {
            const target = host.hunterOperationTargets[i];
            const key = String(target.pid || 0);
            if (!seen[key]) {
                completed.push({
                    type: "result",
                    pid: Number(target.pid || 0),
                    name: String(target.name || "PROCESS"),
                    status: "escaped",
                    detail: "NO VERIFIED RESULT • NOT RETRIED"
                });
            }
        }

        host.hunterOperationResults = completed;
        host.hunterOperationCompleted = host.hunterOperationTotal;
        host.hunterOperationPhase = "report";
        host.destructiveConfirmTitle =
            host.hunterOperationKind === "kill-mice"
            ? "⚠︎ (-_•)デ╾━  (ᐢ××ᐢ)౨  MICE HUNT COMPLETE  ⚠︎" : "⚠︎ (-_•)デ╾━  ₍˄×⚇×˄₎  HOG HUNT COMPLETE  ⚠︎";
        host.destructiveConfirmKind = host.hunterOperationKind;
        host.destructiveConfirmOpen = true;
        refreshHunterOperationMessage();
        refreshTimer.restart();
    }

    function taskHistoryValuesForHunter(entry) {
        return hunterPresentationObject.taskHistoryValues(entry);
    }

    function hunterTaskPeak(entry) {
        return hunterPresentationObject.taskPeak(entry);
    }

    function hunterTaskAverage(entry) {
        return hunterPresentationObject.taskAverage(entry);
    }

    function hunterTaskIoRate(entry) {
        return hunterPresentationObject.taskIoRate(entry);
    }

    function hunterTaskMemoryMiB(entry) {
        return hunterPresentationObject.taskMemoryMiB(entry);
    }

    function hunterTaskMetricScore(entry) {
        return hunterPresentationObject.taskMetricScore(entry);
    }

    function hunterTaskScore(entry) {
        return hunterTaskMetricScore(entry);
    }

    function hunterTaskActive(entry) {
        if (!entry || !entry._taskRecord)
            return false;

        if (host.hunterMetricMode === host.hunterMetricMemory)
            return hunterTaskMemoryMiB(entry) >= 16;

        if (host.hunterMetricMode === host.hunterMetricIo)
            return hunterTaskIoRate(entry) >= 1024;

        if (host.hunterMetricMode === host.hunterMetricAge)
            return taskElapsedSeconds(entry.elapsed) > 0;

        return hunterTaskPeak(entry) >= 0.35
               || hunterTaskAverage(entry) >= 0.15
               || (host.hunterMetricMode === host.hunterMetricCombined
                   && hunterTaskMemoryMiB(entry) >= 128);
    }

    function hunterTaskClassVisible(entry) {
        if (!entry || !entry._taskRecord)
            return false;

        const protectedTask = host.taskRequiresDangerUnlock(entry);

        if (host.hunterVisibilityMode === host.hunterVisibilityProtected)
            return protectedTask;

        if (host.hunterVisibilityMode === host.hunterVisibilityAll)
            return true;

        return !protectedTask;
    }

    function hunterMetricAccent() {
        return hunterPresentationObject.metricAccent();
    }

    function hunterMetricGraphLabel() {
        return hunterPresentationObject.metricGraphLabel();
    }

    function hunterMetricGraphValue(entry) {
        return hunterPresentationObject.metricGraphValue(entry);
    }

    function hunterMetricRangeForKey(metric) {
        return hunterPresentationObject.metricRangeForKey(metric);
    }

    function hunterMetricGraphRange() {
        return hunterPresentationObject.metricGraphRange();
    }

    function hunterFormatBytesPerSecond(value) {
        return hunterPresentationObject.formatBytesPerSecond(value);
    }

    function hunterFormatAge(seconds) {
        return hunterPresentationObject.formatAge(seconds);
    }

    function hunterMetricReason(entry) {
        if (!entry)
            return "NO METRIC";

        if (host.hunterMetricMode === host.hunterMetricCpu)
            return "CPU HOG • " + hunterTaskPeak(entry).toFixed(1)
                   + "% PEAK • " + hunterTaskAverage(entry).toFixed(1) + "% RECENT";

        if (host.hunterMetricMode === host.hunterMetricMemory)
            return "MEMORY HOG • " + hunterTaskMemoryMiB(entry).toFixed(0) + " MiB RSS";

        if (host.hunterMetricMode === host.hunterMetricIo)
            return "I/O HOG • R "
                   + hunterFormatBytesPerSecond(entry.ioReadRate)
                   + " • W "
                   + hunterFormatBytesPerSecond(entry.ioWriteRate);

        if (host.hunterMetricMode === host.hunterMetricAge)
            return "OLD PROCESS • " + hunterFormatAge(taskElapsedSeconds(entry.elapsed));

        return host.hunterCombiIcon + " • CPU " + hunterTaskPeak(entry).toFixed(1)
               + "% • MEM " + hunterTaskMemoryMiB(entry).toFixed(0)
               + " MiB • I/O " + hunterFormatBytesPerSecond(hunterTaskIoRate(entry));
    }

    function taskElapsedSeconds(value) {
        return hunterPresentationObject.elapsedSeconds(value);
    }

    function hunterHogCandidates() {
        // Bulk HOG execution always excludes protected/session-critical rows,
        // even when PROTECTED or ALL is selected for inspection.
        const rows = host.taskRows.filter(function(entry) {
            return host.taskEligibleForKillAll(entry)
                   && hunterTaskActive(entry)
                   && !host.isFavoriteItem(entry, host.killModeIndex);
        });
        rows.sort(function(a, b) {
            return hunterTaskMetricScore(b) - hunterTaskMetricScore(a);
        });
        if (rows.length === 0)
            return [];

        const topScore = Math.max(0.01, hunterTaskMetricScore(rows[0]));
        let minimum = 0;
        let ratio = 0.48;
        if (host.hunterMetricMode === host.hunterMetricCpu)
            minimum = 8.0;
        else if (host.hunterMetricMode === host.hunterMetricMemory)
            minimum = 128.0; // MiB RSS
        else if (host.hunterMetricMode === host.hunterMetricIo)
            minimum = 1024 * 1024; // 1 MiB/s
        else if (host.hunterMetricMode === host.hunterMetricAge) {
            minimum = 3600;
            ratio = 0.72;
        } else
            minimum = 8.0;

        const threshold = Math.max(minimum, topScore * ratio);
        return rows.filter(function(entry) {
            return hunterTaskMetricScore(entry) >= threshold;
        }).slice(0, 8);
    }

    function hunterVisibleWindowPidSet() {
        const visible = ({});
        const windows = Array.isArray(host.swayWindows) ? host.swayWindows : [];
        for (let i = 0; i < windows.length; i++) {
            const pid = Number(windows[i] && windows[i].pid || 0);
            if (pid > 1)
                visible[String(pid)] = true;
        }
        return visible;
    }

    function hunterTaskPidMap() {
        const byPid = ({});
        for (let i = 0; i < host.taskRows.length; i++) {
            const row = host.taskRows[i];
            const pid = Number(row && row.pid || 0);
            if (pid > 1)
                byPid[String(pid)] = row;
        }
        return byPid;
    }

    function hunterDescendsFromVisibleWindow(entry) {
        if (!entry)
            return false;

        const visible = hunterVisibleWindowPidSet();
        const byPid = hunterTaskPidMap();
        let pid = Number(entry.pid || 0);
        let guard = 0;

        while (pid > 1 && guard < 48) {
            if (visible[String(pid)])
                return true;

            const row = byPid[String(pid)];
            if (!row)
                break;

            const parent = Number(row.ppid || 0);
            if (parent <= 1 || parent === pid)
                break;

            pid = parent;
            guard++;
        }

        return false;
    }

    function hunterTaskHasChildren(entry) {
        if (!entry)
            return false;
        const pid = Number(entry.pid || 0);
        if (pid <= 1)
            return true;
        for (let i = 0; i < host.taskRows.length; i++) {
            if (Number(host.taskRows[i] && host.taskRows[i].ppid || 0) === pid)
                return true;
        }
        return false;
    }

    function hunterInteractiveTask(entry) {
        if (!entry)
            return false;

        const tty = String(entry.tty || "?").trim();
        if (tty.length > 0 && tty !== "?" && tty !== "-")
            return true;

        const name = String(entry.comm || entry.name || "")
                     .trim().toLowerCase();
        const args = String(entry.args || "").trim().toLowerCase();
        const haystack = name + " " + args;
        const interactiveTokens = [
            // Interactive shells / multiplexers / terminal emulators.
            "zsh", "bash", "fish", "nushell", " nu ", "dash", "ksh",
            "zellij", "tmux", "screen", "kitty", "foot", "alacritty",
            "wezterm", "ghostty", "konsole", "gnome-terminal",

            // Prompt/status helpers and keyboard-heavy interactive tools.
            "gitstatusd", "starship", "oh-my-posh", "powerlevel10k",
            "nvim", "neovim", "vim", "helix", "hx ", "emacs", "yazi",
            "btop", "htop", "top ", "less", "fzf", "ranger"
        ];

        for (let i = 0; i < interactiveTokens.length; i++) {
            if (haystack.indexOf(interactiveTokens[i]) !== -1)
                return true;
        }
        return false;
    }

    function hunterDescendsFromInteractiveTask(entry) {
        if (!entry)
            return false;
        const byPid = hunterTaskPidMap();
        let current = entry;
        let guard = 0;
        while (current && guard < 48) {
            if (hunterInteractiveTask(current))
                return true;
            const parentPid = Number(current.ppid || 0);
            if (parentPid <= 1 || parentPid === Number(current.pid || 0))
                break;
            current = byPid[String(parentPid)];
            guard++;
        }
        return false;
    }

    function hunterMouseProtectedReason(entry) {
        if (!entry)
            return "INVALID";

        if (host.isFavoriteItem(entry, host.killModeIndex))
            return "FAVORITE";

        if (!host.taskEligibleForKillAll(entry))
            return "SESSION/PROTECTED";

        // Never let the low-activity heuristic dismantle a currently visible
        // GUI application. Chromium/Electron in particular split downloads,
        // networking, rendering and utility work across quiet child processes.
        if (hunterDescendsFromVisibleWindow(entry))
            return "ACTIVE APP TREE";

        if (hunterDescendsFromInteractiveTask(entry))
            return "INTERACTIVE/TTY TREE";

        // MICE only hunts detached leaves. Parents are intentionally retained:
        // killing a quiet parent can orphan or destabilize still-useful children.
        if (hunterTaskHasChildren(entry))
            return "PROCESS TREE";

        // PPID 1/user-service leaves are ambiguous (systemd --user services,
        // daemons, agents). Treat them as infrastructure rather than mice.
        if (Number(entry.ppid || 0) <= 1)
            return "USER SERVICE/ORPHAN";

        const name = String(entry.comm || entry.name || "")
                     .trim().toLowerCase();
        const args = String(entry.args || "").trim().toLowerCase();
        const haystack = name + " " + args;

        const protectedTokens = [
            // Browsers / web runtimes and their helper processes.
            "brave", "chromium", "chrome", "firefox", "vivaldi",
            "opera", "electron", "qtwebengine", "webkit", "webprocess",
            "code", "codium",

            // File transfer / download / sync tools.
            "curl", "wget", "aria2", "rclone", "rsync", "scp", "sftp",
            "syncthing", "megasync", "dropbox", "onedrive",

            // Interactive shells / terminals / prompt helpers. These can be
            // nearly idle for hours and are still absolutely user-owned state.
            "zsh", "bash", "fish", "nushell", "zellij", "tmux", "screen",
            "kitty", "foot", "alacritty", "wezterm", "ghostty",
            "gitstatusd", "starship", "oh-my-posh", "powerlevel10k",
            "nvim", "neovim", "vim", "helix", "emacs", "yazi",

            // Desktop/session/portal/file-service infrastructure.
            "xdg-desktop-portal", "xdg-document-portal", "xdg-permission-store",
            "gvfs", "fuse", "dconf", "dbus", "pipewire", "wireplumber",
            "at-spi", "ssh-agent", "gpg-agent", "polkit", "keyring",
            "systemd", "systemd-oomd", "systemd-resolved", "systemd-timesyncd",

            // Sandboxes, containers and transactional package operations.
            "flatpak", "bwrap", "bubblewrap", "xdg-dbus-proxy", "toolbox",
            "podman", "conmon", "rpm-ostree", "ostree"
        ];

        for (let i = 0; i < protectedTokens.length; i++) {
            if (haystack.indexOf(protectedTokens[i]) !== -1)
                return "IMPORTANT HELPER";
        }

        // Do not hunt a process that is already explicitly stopped/frozen;
        // that state is intentional and managed by the per-process controls.
        if (String(entry.state || "").indexOf("T") !== -1)
            return "FROZEN";

        return "";
    }

    function hunterMouseCandidates() {
        const rows = host.taskRows.filter(function(entry) {
            if (hunterMouseProtectedReason(entry).length > 0)
                return false;

            // MICE is intentionally conservative. A process must have been
            // around for a while AND remain tiny/quiet across the recent graph,
            // rather than merely being momentarily idle.
            const oldEnough = taskElapsedSeconds(entry.elapsed) >= 45 * 60;
            const quiet = hunterTaskPeak(entry) <= 0.20
                          && hunterTaskAverage(entry) <= 0.08
                          && Number(entry.cpu || 0) <= 0.20;
            const small = Number(entry.mem || 0) <= 0.50;
            const tty = String(entry.tty || "?").trim();
            const detached = tty === "?" || tty === "-" || tty.length === 0;
            return oldEnough && quiet && small && detached;
        });
        rows.sort(function(a, b) {
            const rssDelta = Number(a.rss || 0) - Number(b.rss || 0);
            if (Math.abs(rssDelta) > 1)
                return rssDelta;
            return taskElapsedSeconds(b.elapsed) - taskElapsedSeconds(a.elapsed);
        });
        return rows.slice(0, 10);
    }

    function bulkTaskConfirmList(rows) {
        return rows.map(function(entry) {
            const reason = hunterMetricReason(entry);
            return "• " + String(entry.comm || entry.name || "PROCESS")
                   + "  [PID " + String(entry.pid || "?") + "]"
                   + (reason ? "  •  " + reason : "");
        }).join("\n");
    }

    function hunterMouseReason(entry) {
        const age = hunterFormatAge(taskElapsedSeconds(entry && entry.elapsed || ""));
        const avg = hunterTaskAverage(entry);
        return "MOUSE CANDIDATE • " + age
               + " • NO TTY • LEAF • CPU " + avg.toFixed(2) + "%";
    }

    function bulkMouseConfirmList(rows) {
        return rows.map(function(entry) {
            return "• " + String(entry.comm || entry.name || "PROCESS")
                   + "  [PID " + String(entry.pid || "?") + "]"
                   + "  •  " + hunterMouseReason(entry);
        }).join("\n");
    }

    function requestKillHogs() {
        // Repeated clicks during an active hunt are view actions only. They
        // reopen the single live progress window and never send another TERM.
        if (host.hunterOperationActive) {
            showHunterOperationWindow();
            return;
        }

        const rows = hunterHogCandidates();
        if (rows.length === 0)
            return;

        host.hunterPendingTargets = hunterTargetsFromRows(rows);
        host.openDestructiveConfirm(
            "kill-hogs",
            "⚠︎ (-_•)デ╾━  ₍˄·͈⚇·͈˄₎  CONFIRM KILL HOGS  ⚠︎",
            "HUNTER WILL TERMINATE THESE " + String(rows.length)
            + " HIGH-PRESSURE PROCESSES:\n\n"
            + bulkTaskConfirmList(rows)
            + "\n\nFAVORITED PROCESSES ARE EXCLUDED AND RE-CHECKED "
            + "BEFORE HUNTER FIRES. A NEW FAVORITE IS LET LOOSE AND "
            + "REPORTED.\n\n"
            + "EACH CAPTURED PID IS SENT SIGTERM ONCE. "
            + "SURVIVORS ARE REPORTED; THEY ARE NOT RETRIED AUTOMATICALLY.",
            "KILL HOGS"
        );
        host.destructiveConfirmTargetPids = rows.map(function(entry) {
            return Number(entry.pid || 0);
        });
    }

    function requestKillMice() {
        if (host.hunterOperationActive) {
            showHunterOperationWindow();
            return;
        }

        const rows = hunterMouseCandidates();
        if (rows.length === 0)
            return;

        host.hunterPendingTargets = hunterTargetsFromRows(rows);
        host.openDestructiveConfirm(
            "kill-mice",
            "⚠︎ (-_•)デ╾━  (ᐢ..ᐢ)౨  CONFIRM KILL MICE  ⚠︎",
            "HUNTER FOUND THESE DETACHED, NONINTERACTIVE, IDLE LEAF PROCESSES:\n\n"
            + bulkMouseConfirmList(rows)
            + "\n\nACTIVE GUI APP TREES, BROWSERS/ELECTRON HELPERS, DOWNLOAD/TRANSFER "
            + "TOOLS, SHELL/TTY TREES, PROMPT HELPERS, PORTALS, AUDIO/SESSION "
            + "SERVICES, FLATPAK AND CONTAINER INFRASTRUCTURE ARE PROTECTED.\n\n"
            + "FAVORITED PROCESSES ARE ALSO EXCLUDED AND RE-CHECKED BEFORE "
            + "HUNTER FIRES; A NEW FAVORITE IS LET LOOSE AND REPORTED.\n\n"
            + "EACH CAPTURED PID IS SENT SIGTERM ONCE. "
            + "SURVIVORS ARE REPORTED; THEY ARE NOT RETRIED AUTOMATICALLY.",
            "KILL MICE"
        );
        host.destructiveConfirmTargetPids = rows.map(function(entry) {
            return Number(entry.pid || 0);
        });
    }
}
