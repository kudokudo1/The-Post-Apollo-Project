import QtQuick
import Quickshell
import Quickshell.Io

// Cross-application desktop-surface provider extracted from the certified
// fused baseline 943d273.
//
// This service deliberately owns provider-native surface physiology only:
// discovery, discovered records/controls, activation, diagnostics, refresh
// lifecycle, and native DEVTOOLS tab suspend/resume.
//
// It deliberately does NOT own:
// - canonical DesktopEntry/Application/Sway/PID identity (Team 7)
// - APP/WINDOW/TAB audio matching or mutation (Team 6)
// - Linux process/resource freeze or limits (Team 1)
// - Favorites reconstruction/persistence (Team 2)
// - AppControl navigation, result selection, or detail presentation
Scope {
    id: tabSurfaceProvider

    // View/host lifetime input. A consumer may mark the provider active while
    // it needs live surfaces. The provider has no knowledge of AppControl
    // modes, menu state, focus, or selection.
    property bool active: false

    // Provider-native records. Their current IDs remain temporary/provider
    // identity evidence; they are not a canonical application identity.
    property var tabs: []
    property var controls: []

    property bool loading: false
    property string errorText: ""
    property var diagnostics: []
    property string diagnosticsSignature: ""
    property string dataSignature: ""

    property bool bridgeReady: false
    property string bridgeError: ""

    // Native tab lifecycle state is intentionally keyed by provider record
    // identity, not by Team 7's future canonical application identity.
    property var lifecycleFrozenKeys: ({})
    property string lifecyclePendingKey: ""
    property bool lifecyclePendingFrozen: false
    property bool lifecyclePendingPreviousFrozen: false
    property string lifecycleError: ""

    signal snapshotWillChange()
    signal snapshotChanged()
    signal activationFinished(bool ok, string message)
    signal lifecycleFinished(bool ok, string message)

function appTabBridgeScript() {
    return "import ctypes\nimport ctypes.util\nimport json\nimport os\nimport re\nimport signal\nimport subprocess\nimport sys\nimport time\nimport urllib.request\n\nrunning = True\ndirty = True\n\nROLE_DIALOG = 16\nROLE_FRAME = 23\nROLE_PAGE_TAB = 37\nROLE_PAGE_TAB_LIST = 38\nROLE_LIST_ITEM = 32\nROLE_PUSH_BUTTON = 43\nROLE_RADIO_BUTTON = 44\nROLE_TOGGLE_BUTTON = 62\nROLE_WINDOW = 69\nROLE_APPLICATION = 75\n\nSTATE_ACTIVE = 1\nSTATE_FOCUSED = 12\nSTATE_SELECTED = 23\n\ndef stop(*_args):\n    global running\n    running = False\n\nsignal.signal(signal.SIGTERM, stop)\nsignal.signal(signal.SIGINT, stop)\n\ndef run_cmd(argv, timeout=1.0):\n    try:\n        proc = subprocess.run(\n            argv,\n            stdout=subprocess.PIPE,\n            stderr=subprocess.PIPE,\n            text=True,\n            timeout=timeout\n        )\n        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()\n    except Exception as exc:\n        return 1, \"\", str(exc)\n\ndef process_provider_tabs():\n    rows = []\n    diagnostics = []\n\n    # Kitty remote control.\n    kitty_addresses = []\n    kitty_errors = []\n\n    try:\n        for pid in os.listdir(\"/proc\"):\n            if not pid.isdigit():\n                continue\n\n            try:\n                env = open(\n                    \"/proc/%s/environ\" % pid,\n                    \"rb\"\n                ).read().split(b\"\\0\")\n            except Exception:\n                continue\n\n            for item in env:\n                if item.startswith(b\"KITTY_LISTEN_ON=\"):\n                    address = item.split(\n                        b\"=\",\n                        1\n                    )[1].decode(\n                        \"utf-8\",\n                        \"ignore\"\n                    ).strip()\n\n                    if address and address not in kitty_addresses:\n                        kitty_addresses.append(address)\n    except Exception as exc:\n        kitty_errors.append(\"DISCOVERY: \" + str(exc))\n\n    for address in kitty_addresses:\n        try:\n            proc = subprocess.run(\n                [\n                    \"kitty\",\n                    \"@\",\n                    \"--to\",\n                    address,\n                    \"ls\"\n                ],\n                stdout=subprocess.PIPE,\n                stderr=subprocess.PIPE,\n                text=True,\n                timeout=0.8\n            )\n\n            if proc.returncode != 0 or not proc.stdout.strip():\n                raw_error = str(proc.stderr or \"\").strip()\n                kitty_errors.append(\n                    (\"%s: %s\" % (address, raw_error))\n                    if raw_error\n                    else (\"%s: kitty @ ls returned %d\" % (\n                        address,\n                        proc.returncode\n                    ))\n                )\n                continue\n\n            payload = json.loads(proc.stdout)\n\n            for os_window in (\n                payload\n                if isinstance(payload, list)\n                else []\n            ):\n                for tab in os_window.get(\"tabs\", []) or []:\n                    tab_id = tab.get(\"id\")\n                    title = str(tab.get(\"title\") or \"\").strip()\n\n                    if not title:\n                        wins = tab.get(\"windows\", []) or []\n                        active = next(\n                            (\n                                w for w in wins\n                                if w.get(\"is_active\")\n                            ),\n                            None\n                        )\n                        active = active or (wins[0] if wins else {})\n                        title = str(\n                            active.get(\"title\")\n                            or active.get(\"cwd\")\n                            or (\"KITTY TAB \" + str(tab_id))\n                        )\n\n                    rows.append({\n                        \"_tabRecord\": True,\n                        \"id\": \"kitty:\" + str(tab_id),\n                        \"path\": \"\",\n                        \"name\": title,\n                        \"tabTitle\": title,\n                        \"appName\": \"Kitty\",\n                        \"windowName\": str(os_window.get(\"id\") or \"\"),\n                        \"selected\": bool(tab.get(\"is_active\")),\n                        \"provider\": \"KITTY\",\n                        \"kittyAddress\": address,\n                        \"kittyTabId\": tab_id,\n                        \"processPids\": sorted(set(\n                            [int(w.get(\"pid\")) for w in (tab.get(\"windows\", []) or []) if w.get(\"pid\")]\n                            + [int(proc.get(\"pid\")) for w in (tab.get(\"windows\", []) or []) for proc in (w.get(\"foreground_processes\", []) or []) if proc.get(\"pid\")]\n                        ))\n                    })\n        except Exception as exc:\n            kitty_errors.append(\"%s: %s\" % (address, str(exc)))\n\n    kitty_tab_count = sum(\n        1 for item in rows\n        if item.get(\"provider\") == \"KITTY\"\n    )\n\n    diagnostics.append(\n        \"KITTY SOCKETS:%d\" % len(kitty_addresses)\n    )\n    diagnostics.append(\n        \"KITTY TABS:%d\" % kitty_tab_count\n    )\n    diagnostics.append(\n        \"KITTY ERROR:%s\"\n        % (\n            \" | \".join(kitty_errors[:3])\n            if kitty_errors\n            else \"NONE\"\n        )\n    )\n\n    # Chromium / Electron DevTools when a debug port exists.\n    ports = {}\n    devtools_errors = []\n\n    try:\n        for pid in os.listdir(\"/proc\"):\n            if not pid.isdigit():\n                continue\n\n            try:\n                raw = open(\n                    \"/proc/%s/cmdline\" % pid,\n                    \"rb\"\n                ).read()\n\n                argv = [\n                    part.decode(\"utf-8\", \"ignore\")\n                    for part in raw.split(b\"\\0\")\n                    if part\n                ]\n            except Exception:\n                continue\n\n            if not argv:\n                continue\n\n            exe = os.path.basename(argv[0]).lower()\n\n            app_name = (\n                \"Brave\"\n                if \"brave\" in exe\n                else \"Chrome\"\n                if \"chrome\" in exe\n                else \"Chromium\"\n                if \"chromium\" in exe\n                else \"VS Code\"\n                if exe in (\"code\", \"code-oss\", \"codium\")\n                else \"Electron\"\n                if \"electron\" in exe\n                else \"\"\n            )\n\n            if not app_name:\n                continue\n\n            port = None\n\n            for index, arg in enumerate(argv):\n                if arg.startswith(\"--remote-debugging-port=\"):\n                    try:\n                        port = int(arg.split(\"=\", 1)[1])\n                    except Exception:\n                        port = None\n                    break\n\n                if arg == \"--remote-debugging-port\" and index + 1 < len(argv):\n                    try:\n                        port = int(argv[index + 1])\n                    except Exception:\n                        port = None\n                    break\n\n            if port and port > 0:\n                ports[port] = app_name\n\n    except Exception as exc:\n        devtools_errors.append(\"DISCOVERY: \" + str(exc))\n\n    devtools_target_count = 0\n\n    for port, app_name in ports.items():\n        try:\n            with urllib.request.urlopen(\n                \"http://127.0.0.1:%d/json/list\" % port,\n                timeout=0.55\n            ) as response:\n                targets = json.loads(\n                    response.read().decode(\"utf-8\", \"ignore\")\n                )\n        except Exception as exc:\n            devtools_errors.append(\n                \"PORT %d: %s\" % (port, str(exc))\n            )\n            continue\n\n        for target in targets:\n            if str(target.get(\"type\", \"\")).lower() not in (\"page\", \"webview\"):\n                continue\n\n            devtools_target_count += 1\n\n            target_id = str(target.get(\"id\") or \"\").strip()\n            title = str(\n                target.get(\"title\")\n                or target.get(\"url\")\n                or \"\"\n            ).strip()\n\n            if not target_id or not title:\n                continue\n\n            rows.append({\n                \"_tabRecord\": True,\n                \"id\": \"devtools:%d:%s\" % (port, target_id),\n                \"path\": \"\",\n                \"name\": title,\n                \"tabTitle\": title,\n                \"appName\": app_name,\n                \"windowName\": str(target.get(\"url\") or \"\"),\n                \"selected\": False,\n                \"provider\": \"DEVTOOLS\",\n                \"debugPort\": port,\n                \"targetId\": target_id,\n                \"webSocketDebuggerUrl\": str(target.get(\"webSocketDebuggerUrl\") or \"\")\n            })\n\n    port_text = (\n        \",\".join(str(port) for port in sorted(ports))\n        if ports\n        else \"NONE\"\n    )\n\n    diagnostics.append(\n        \"DEVTOOLS PORTS:%s\" % port_text\n    )\n    diagnostics.append(\n        \"DEVTOOLS TARGETS:%d\" % devtools_target_count\n    )\n    diagnostics.append(\n        \"DEVTOOLS ERROR:%s\"\n        % (\n            \" | \".join(devtools_errors[:3])\n            if devtools_errors\n            else \"NONE\"\n        )\n    )\n\n    return rows, diagnostics\n\ntry:\n    lib_name = ctypes.util.find_library(\"atspi\") or \"libatspi.so.0\"\n    atspi = ctypes.CDLL(lib_name)\n\n    # Core.\n    atspi.atspi_init.argtypes = []\n    atspi.atspi_init.restype = ctypes.c_int\n\n    atspi.atspi_get_desktop.argtypes = [ctypes.c_int]\n    atspi.atspi_get_desktop.restype = ctypes.c_void_p\n\n    # Accessible.\n    atspi.atspi_accessible_get_child_count.argtypes = [\n        ctypes.c_void_p,\n        ctypes.c_void_p\n    ]\n    atspi.atspi_accessible_get_child_count.restype = ctypes.c_int\n\n    atspi.atspi_accessible_get_child_at_index.argtypes = [\n        ctypes.c_void_p,\n        ctypes.c_int,\n        ctypes.c_void_p\n    ]\n    atspi.atspi_accessible_get_child_at_index.restype = ctypes.c_void_p\n\n    atspi.atspi_accessible_get_role.argtypes = [\n        ctypes.c_void_p,\n        ctypes.c_void_p\n    ]\n    atspi.atspi_accessible_get_role.restype = ctypes.c_int\n\n    atspi.atspi_accessible_get_name.argtypes = [\n        ctypes.c_void_p,\n        ctypes.c_void_p\n    ]\n    atspi.atspi_accessible_get_name.restype = ctypes.c_void_p\n\n    atspi.atspi_accessible_get_role_name.argtypes = [\n        ctypes.c_void_p,\n        ctypes.c_void_p\n    ]\n    atspi.atspi_accessible_get_role_name.restype = ctypes.c_void_p\n\n    atspi.atspi_accessible_get_state_set.argtypes = [\n        ctypes.c_void_p\n    ]\n    atspi.atspi_accessible_get_state_set.restype = ctypes.c_void_p\n\n    atspi.atspi_state_set_contains.argtypes = [\n        ctypes.c_void_p,\n        ctypes.c_int\n    ]\n    atspi.atspi_state_set_contains.restype = ctypes.c_int\n\n    # Event listener — keeps the AT registration alive.\n    CALLBACK = ctypes.CFUNCTYPE(\n        None,\n        ctypes.c_void_p,\n        ctypes.c_void_p\n    )\n\n    @CALLBACK\n    def event_callback(_event, _user_data):\n        global dirty\n        dirty = True\n\n    atspi.atspi_event_listener_new.argtypes = [\n        CALLBACK,\n        ctypes.c_void_p,\n        ctypes.c_void_p\n    ]\n    atspi.atspi_event_listener_new.restype = ctypes.c_void_p\n\n    atspi.atspi_event_listener_register.argtypes = [\n        ctypes.c_void_p,\n        ctypes.c_char_p,\n        ctypes.c_void_p\n    ]\n    atspi.atspi_event_listener_register.restype = ctypes.c_int\n\n    init_result = int(atspi.atspi_init())\n\n    listener = atspi.atspi_event_listener_new(\n        event_callback,\n        None,\n        None\n    )\n\n    registrations = []\n\n    if listener:\n        for event_name in (\n            b\"object:children-changed\",\n            b\"object:selection-changed\",\n            b\"object:state-changed:selected\",\n            b\"window:activate\"\n        ):\n            try:\n                ok = int(\n                    atspi.atspi_event_listener_register(\n                        listener,\n                        event_name,\n                        None\n                    )\n                )\n            except Exception:\n                ok = 0\n\n            registrations.append(ok)\n\n    ready = bool(listener) and any(registrations)\n\n    print(\n        json.dumps({\n            \"ready\": ready,\n            \"library\": lib_name,\n            \"init\": init_result,\n            \"registrations\": registrations,\n            \"diagnostics\": [\n                \"LIBATSPI BRIDGE:%s\"\n                % (\"READY\" if ready else \"NOT READY\"),\n                \"LIBATSPI LIBRARY:%s\" % lib_name,\n                \"LIBATSPI INIT:%d\" % init_result,\n                \"LIBATSPI REGISTRATIONS:%s\"\n                % \",\".join(str(value) for value in registrations),\n                \"LIBATSPI ERROR:%s\"\n                % (\n                    \"NONE\"\n                    if ready\n                    else \"LIBATSPI EVENT REGISTRATION FAILED\"\n                )\n            ],\n            \"error\": \"\" if ready else \"LIBATSPI EVENT REGISTRATION FAILED\"\n        }),\n        flush=True\n    )\n\n    def c_string(pointer):\n        if not pointer:\n            return \"\"\n\n        try:\n            return ctypes.string_at(pointer).decode(\n                \"utf-8\",\n                \"replace\"\n            )\n        except Exception:\n            return \"\"\n\n    def get_name(obj):\n        if not obj:\n            return \"\"\n\n        try:\n            return c_string(\n                atspi.atspi_accessible_get_name(\n                    obj,\n                    None\n                )\n            ).strip()\n        except Exception:\n            return \"\"\n\n    def get_role_name(obj):\n        if not obj:\n            return \"\"\n\n        try:\n            return c_string(\n                atspi.atspi_accessible_get_role_name(\n                    obj,\n                    None\n                )\n            ).strip().lower().replace(\"_\", \" \")\n        except Exception:\n            return \"\"\n\n    def selected_state(obj):\n        try:\n            state_set = atspi.atspi_accessible_get_state_set(obj)\n\n            if not state_set:\n                return False\n\n            return bool(\n                atspi.atspi_state_set_contains(\n                    state_set,\n                    STATE_SELECTED\n                )\n                or atspi.atspi_state_set_contains(\n                    state_set,\n                    STATE_FOCUSED\n                )\n                or atspi.atspi_state_set_contains(\n                    state_set,\n                    STATE_ACTIVE\n                )\n            )\n        except Exception:\n            return False\n\n    def scan_libatspi():\n        rows = []\n        controls = []\n        diagnostics = [\n            \"LIBATSPI BRIDGE:%s\"\n            % (\"READY\" if ready else \"NOT READY\")\n        ]\n        seen = set()\n        control_seen = set()\n\n        desktop = atspi.atspi_get_desktop(0)\n\n        if not desktop:\n            diagnostics.extend([\n                \"LIBATSPI APPS:0\",\n                \"LIBATSPI NODES:0\",\n                \"LIBATSPI PAGE_TAB:0\",\n                \"LIBATSPI TABS:0\",\n                \"LIBATSPI CONTROLS:0\",\n                \"LIBATSPI ERROR:NO DESKTOP\"\n            ])\n            return rows, controls, diagnostics\n\n        visited = 0\n        app_count = 0\n        page_tab_count = 0\n        reclassified_control_count = 0\n        vscode_editor_candidate_count = 0\n        max_nodes = 30000\n        max_depth = 40\n\n        def add_row(item):\n            key = (\n                re.sub(\n                    r\"\\s+\",\n                    \" \",\n                    str(item.get(\"appName\") or \"\").lower()\n                ),\n                re.sub(\n                    r\"\\s+\",\n                    \" \",\n                    str(item.get(\"windowName\") or \"\").lower()\n                ),\n                re.sub(\n                    r\"\\s+\",\n                    \" \",\n                    str(item.get(\"tabTitle\") or \"\").lower()\n                )\n            )\n\n            if not key[2] or key in seen:\n                return\n\n            seen.add(key)\n            rows.append(item)\n\n        def add_control(item):\n            key = (\n                re.sub(\n                    r\"\\s+\",\n                    \" \",\n                    str(item.get(\"appName\") or \"\").lower()\n                ),\n                re.sub(\n                    r\"\\s+\",\n                    \" \",\n                    str(item.get(\"name\") or \"\").lower()\n                ),\n                int(item.get(\"role\") or -1)\n            )\n\n            if not key[1] or key in control_seen:\n                return\n\n            control_seen.add(key)\n            controls.append(item)\n\n        def walk(\n                obj,\n                path,\n                app_name=\"\",\n                window_name=\"\",\n                tab_context=False,\n                depth=0):\n            nonlocal visited, app_count, page_tab_count, reclassified_control_count, vscode_editor_candidate_count\n\n            if (\n                not obj\n                or depth > max_depth\n                or visited >= max_nodes\n            ):\n                return\n\n            visited += 1\n\n            try:\n                role = int(\n                    atspi.atspi_accessible_get_role(\n                        obj,\n                        None\n                    )\n                )\n            except Exception:\n                role = -1\n\n            name = get_name(obj)\n            role_name = get_role_name(obj)\n\n            if role == ROLE_APPLICATION:\n                app_count += 1\n\n                if name:\n                    app_name = name\n\n            if role == ROLE_PAGE_TAB:\n                page_tab_count += 1\n\n            if (\n                role in (\n                    ROLE_DIALOG,\n                    ROLE_FRAME,\n                    ROLE_WINDOW\n                )\n                and name\n            ):\n                window_name = name\n\n            is_tab_container = (\n                role == ROLE_PAGE_TAB_LIST\n                or \"page tab list\" in role_name\n                or role_name == \"tab list\"\n                or role_name == \"tablist\"\n                or role_name == \"tab bar\"\n            )\n\n            is_real_tab = (\n                role == ROLE_PAGE_TAB\n                or role_name == \"page tab\"\n                or role_name == \"tab\"\n                or role_name == \"document tab\"\n            )\n\n            # Chromium/Electron accessibility uses PAGE_TAB for more than\n            # document/editor tabs. VS Code's Activity Bar/view switcher is\n            # exposed as tabs too (Explorer, Search, Source Control, etc.).\n            # Preserve those objects, but classify them as alternate app\n            # controls so the left TABS list can stay document-focused.\n            app_key = re.sub(\n                r\"\\s+\",\n                \" \",\n                str(app_name or \"\").strip().lower()\n            )\n            label_key = re.sub(\n                r\"\\s+\",\n                \" \",\n                str(name or \"\").strip().lower()\n            )\n            label_base = re.sub(\n                r\"\\s*\\([^)]*\\)\\s*$\",\n                \"\",\n                label_key\n            ).strip()\n\n            is_vscode = (\n                app_key in (\n                    \"code\",\n                    \"visual studio code\",\n                    \"code - oss\",\n                    \"code-oss\",\n                    \"vscodium\"\n                )\n                or \"visual studio code\" in app_key\n            )\n\n            has_command_shortcut = bool(\n                re.search(\n                    r\"\\([^)]*(?:ctrl|alt|shift|cmd|super|meta)[^)]*\\)\\s*$\",\n                    label_key,\n                    re.IGNORECASE\n                )\n            )\n\n            vscode_view_labels = {\n                \"explorer\",\n                \"search\",\n                \"source control\",\n                \"run and debug\",\n                \"extensions\",\n                \"chat\",\n                \"testing\",\n                \"remote explorer\",\n                \"problems\",\n                \"output\",\n                \"debug console\",\n                \"terminal\",\n                \"ports\"\n            }\n\n            reclassified_vscode_control = (\n                is_real_tab\n                and is_vscode\n                and (\n                    has_command_shortcut\n                    or label_base in vscode_view_labels\n                )\n            )\n\n            if reclassified_vscode_control:\n                is_real_tab = False\n                reclassified_control_count += 1\n\n            # VS Code may expose the active editor as PAGE_TAB while sibling\n            # inactive editors become button/list-item objects in the same\n            # tab container. Promote those siblings to editor tabs, while\n            # keeping known Activity Bar/view controls on the right panel.\n            vscode_editor_candidate = (\n                is_vscode\n                and tab_context\n                and not is_real_tab\n                and not reclassified_vscode_control\n                and role in (\n                    ROLE_PUSH_BUTTON,\n                    ROLE_TOGGLE_BUTTON,\n                    ROLE_LIST_ITEM\n                )\n                and bool(label_base)\n                and label_base not in vscode_view_labels\n                and not label_base.startswith(\"close\")\n                and not label_base.startswith(\"split\")\n                and not label_base.startswith(\"more actions\")\n                and not has_command_shortcut\n            )\n\n            if vscode_editor_candidate:\n                is_real_tab = True\n                vscode_editor_candidate_count += 1\n\n            is_app_control = (\n                reclassified_vscode_control\n                or (\n                    tab_context\n                    and not is_real_tab\n                    and role in (\n                        ROLE_PUSH_BUTTON,\n                        ROLE_RADIO_BUTTON,\n                        ROLE_TOGGLE_BUTTON,\n                        ROLE_LIST_ITEM\n                    )\n                )\n            )\n\n            if is_real_tab and name:\n                add_row({\n                    \"_tabRecord\": True,\n                    \"id\": \"libatspi:\" + path,\n                    \"path\": path,\n                    \"name\": name,\n                    \"tabTitle\": name,\n                    \"appName\": app_name or \"APPLICATION\",\n                    \"windowName\": window_name,\n                    \"selected\": selected_state(obj),\n                    \"provider\": \"LIBATSPI\",\n                    \"role\": role,\n                    \"roleName\": role_name\n                })\n            elif is_app_control and name:\n                add_control({\n                    \"_tabControlRecord\": True,\n                    \"id\": \"libatspi-control:\" + path,\n                    \"path\": path,\n                    \"name\": name,\n                    \"controlName\": name,\n                    \"appName\": app_name or \"APPLICATION\",\n                    \"windowName\": window_name,\n                    \"selected\": selected_state(obj),\n                    \"provider\": \"LIBATSPI\",\n                    \"role\": role,\n                    \"roleName\": role_name\n                })\n\n            try:\n                child_count = int(\n                    atspi.atspi_accessible_get_child_count(\n                        obj,\n                        None\n                    )\n                )\n            except Exception:\n                child_count = 0\n\n            child_context = tab_context or is_tab_container\n\n            for index in range(max(0, child_count)):\n                if visited >= max_nodes:\n                    break\n\n                try:\n                    child = atspi.atspi_accessible_get_child_at_index(\n                        obj,\n                        index,\n                        None\n                    )\n                except Exception:\n                    child = None\n\n                if not child:\n                    continue\n\n                child_path = (\n                    str(index)\n                    if not path\n                    else path + \".\" + str(index)\n                )\n\n                walk(\n                    child,\n                    child_path,\n                    app_name,\n                    window_name,\n                    child_context,\n                    depth + 1\n                )\n\n        walk(desktop, \"\")\n\n        diagnostics.extend([\n            \"LIBATSPI APPS:%d\" % app_count,\n            \"LIBATSPI NODES:%d\" % visited,\n            \"LIBATSPI PAGE_TAB:%d\" % page_tab_count,\n            \"LIBATSPI TABS:%d\" % len(rows),\n            \"LIBATSPI CONTROLS:%d\" % len(controls),\n            \"LIBATSPI RECLASSIFIED:%d\" % reclassified_control_count,\n            \"VSCODE EDITOR CANDIDATES:%d\" % vscode_editor_candidate_count,\n            \"LIBATSPI ERROR:NONE\"\n        ])\n\n        return rows, controls, diagnostics\n\n    last_emit = 0.0\n    last_signature = None\n\n    while running:\n        now = time.monotonic()\n\n        if dirty or (now - last_emit) >= 1.15:\n            dirty = False\n\n            lib_rows, lib_controls, diagnostics = scan_libatspi()\n            extra_rows, extra_diagnostics = process_provider_tabs()\n            diagnostics.extend(extra_diagnostics)\n\n            all_rows = []\n            dedupe = set()\n\n            for item in lib_rows + extra_rows:\n                key = (\n                    re.sub(\n                        r\"\\s+\",\n                        \" \",\n                        str(item.get(\"appName\") or \"\").lower()\n                    ),\n                    re.sub(\n                        r\"\\s+\",\n                        \" \",\n                        str(item.get(\"tabTitle\") or \"\").lower()\n                    )\n                )\n\n                if not key[1] or key in dedupe:\n                    continue\n\n                dedupe.add(key)\n                all_rows.append(item)\n\n            diagnostics.append(\n                \"PROVIDER TABS TOTAL:%d\"\n                % len(all_rows)\n            )\n\n            signature = json.dumps(\n                {\n                    \"tabs\": [\n                        (\n                            item.get(\"provider\"),\n                            item.get(\"id\"),\n                            item.get(\"selected\")\n                        )\n                        for item in all_rows\n                    ],\n                    \"controls\": [\n                        (\n                            item.get(\"provider\"),\n                            item.get(\"id\"),\n                            item.get(\"selected\")\n                        )\n                        for item in lib_controls\n                    ]\n                },\n                sort_keys=True\n            )\n\n            # Emit at least every interval so QML can recover if it missed\n            # an earlier snapshot. Changes emit immediately.\n            if signature != last_signature or (now - last_emit) >= 1.15:\n                print(\n                    json.dumps({\n                        \"ready\": ready,\n                        \"tabs\": all_rows,\n                        \"controls\": lib_controls,\n                        \"diagnostics\": diagnostics,\n                        \"error\":\n                            \"\"\n                            if all_rows\n                            else \" • \".join(diagnostics)\n                    }),\n                    flush=True\n                )\n\n                last_signature = signature\n                last_emit = now\n\n        time.sleep(0.10)\n\nexcept Exception as exc:\n    print(\n        json.dumps({\n            \"ready\": False,\n            \"tabs\": [],\n            \"controls\": [],\n            \"diagnostics\": [\n                \"LIBATSPI BRIDGE:NOT READY\",\n                \"LIBATSPI ERROR:\" + str(exc),\n                \"KITTY ERROR:BRIDGE ABORTED BEFORE PROVIDER SCAN\",\n                \"DEVTOOLS ERROR:BRIDGE ABORTED BEFORE PROVIDER SCAN\"\n            ],\n            \"error\": \"LIBATSPI BRIDGE: \" + str(exc)\n        }),\n        flush=True\n    )\n    sys.exit(1)\n";
}

function appTabScanScript() {
    return "import ast\nimport json\nimport os\nimport re\nimport shutil\nimport subprocess\nimport time\nimport urllib.request\n\ntabs = []\ndiagnostics = []\nseen = set()\n\nROLE_DIALOG = 16\nROLE_FRAME = 23\nROLE_PAGE_TAB = 37\nROLE_PAGE_TAB_LIST = 38\nROLE_PUSH_BUTTON = 43\nROLE_RADIO_BUTTON = 44\nROLE_WINDOW = 69\nROLE_APPLICATION = 75\n\nSTATE_ACTIVE = 1\nSTATE_FOCUSED = 12\nSTATE_SELECTED = 23\n\ndef add_tab(item):\n    title = str(item.get(\"tabTitle\") or item.get(\"name\") or \"\").strip()\n    app = str(item.get(\"appName\") or \"\").strip()\n    window = str(item.get(\"windowName\") or \"\").strip()\n\n    if not title:\n        return\n\n    # Cross-provider dedupe. The same Brave/Code tab may be visible through\n    # libatspi and the raw cache at the same time.\n    key = (\n        re.sub(r\"\\s+\", \" \", app.lower()),\n        re.sub(r\"\\s+\", \" \", window.lower()),\n        re.sub(r\"\\s+\", \" \", title.lower())\n    )\n\n    if key in seen:\n        return\n\n    seen.add(key)\n    tabs.append(item)\n\ndef run_cmd(argv, timeout=1.5):\n    try:\n        proc = subprocess.run(\n            argv,\n            stdout=subprocess.PIPE,\n            stderr=subprocess.PIPE,\n            text=True,\n            timeout=timeout\n        )\n        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()\n    except Exception as exc:\n        return 1, \"\", str(exc)\n\ndef first_string(raw):\n    match = re.search(r\"'((?:\\\\.|[^'])*)'\", str(raw or \"\"))\n    if not match:\n        return \"\"\n\n    try:\n        return ast.literal_eval(\"'\" + match.group(1) + \"'\")\n    except Exception:\n        return match.group(1).replace(\"\\\\'\", \"'\").replace(\"\\\\\\\\\", \"\\\\\")\n\ndef parse_gvariant_literal(raw):\n    text = str(raw or \"\").strip()\n\n    if not text:\n        return None\n\n    # gdbus prints valid Python-ish containers plus GVariant type words.\n    # Cache.GetItems has no arbitrary variants, so stripping the annotations\n    # leaves a safe literal that ast.literal_eval can consume.\n    text = re.sub(\n        r\"@[A-Za-z0-9_{}()]+(?=\\s)\",\n        \"\",\n        text\n    )\n    text = re.sub(\n        r\"\\b(?:objectpath|signature|byte|uint16|uint32|uint64|\"\n        r\"int16|int32|int64|double)\\s+\",\n        \"\",\n        text\n    )\n    text = re.sub(r\"\\btrue\\b\", \"True\", text, flags=re.I)\n    text = re.sub(r\"\\bfalse\\b\", \"False\", text, flags=re.I)\n\n    return ast.literal_eval(text)\n\ndef as_ref(value):\n    if (\n        isinstance(value, (tuple, list))\n        and len(value) >= 2\n    ):\n        return (\n            str(value[0] or \"\"),\n            str(value[1] or \"\")\n        )\n\n    return (\"\", \"\")\n\ndef parse_registry_roots(raw):\n    try:\n        payload = parse_gvariant_literal(raw)\n    except Exception:\n        payload = None\n\n    if (\n        isinstance(payload, tuple)\n        and len(payload) == 1\n    ):\n        payload = payload[0]\n\n    refs = []\n\n    if isinstance(payload, list):\n        for value in payload:\n            ref = as_ref(value)\n            if ref[0] and ref[1] and not ref[1].endswith(\"/null\"):\n                refs.append(ref)\n\n    # Fallback for older/newer gdbus formatting.\n    if not refs:\n        pattern = re.compile(\n            r\"\\('([^']*)',\\s*(?:objectpath\\s*)?'([^']*)'\\)\"\n        )\n\n        for bus_name, object_path in pattern.findall(str(raw or \"\")):\n            if (\n                bus_name\n                and object_path\n                and not object_path.endswith(\"/null\")\n            ):\n                refs.append((bus_name, object_path))\n\n    return refs\n\ndef enable_a11y_runtime():\n    enabled = False\n    notes = []\n\n    if shutil.which(\"busctl\"):\n        rc, out, err = run_cmd([\n            \"busctl\",\n            \"--user\",\n            \"set-property\",\n            \"org.a11y.Bus\",\n            \"/org/a11y/bus\",\n            \"org.a11y.Status\",\n            \"IsEnabled\",\n            \"b\",\n            \"true\"\n        ], 1.5)\n\n        if rc == 0:\n            enabled = True\n            notes.append(\"BUSCTL\")\n        elif err:\n            notes.append(\"BUSCTL:\" + err)\n\n    if not enabled and shutil.which(\"gdbus\"):\n        rc, out, err = run_cmd([\n            \"gdbus\",\n            \"call\",\n            \"--session\",\n            \"--dest\", \"org.a11y.Bus\",\n            \"--object-path\", \"/org/a11y/bus\",\n            \"--method\", \"org.freedesktop.DBus.Properties.Set\",\n            \"org.a11y.Status\",\n            \"IsEnabled\",\n            \"<true>\"\n        ], 1.5)\n\n        if rc == 0:\n            enabled = True\n            notes.append(\"GDBUS\")\n        elif err:\n            notes.append(\"GDBUS:\" + err)\n\n    state = \"\"\n\n    if shutil.which(\"gdbus\"):\n        rc, out, err = run_cmd([\n            \"gdbus\",\n            \"call\",\n            \"--session\",\n            \"--dest\", \"org.a11y.Bus\",\n            \"--object-path\", \"/org/a11y/bus\",\n            \"--method\", \"org.freedesktop.DBus.Properties.Get\",\n            \"org.a11y.Status\",\n            \"IsEnabled\"\n        ], 1.5)\n\n        if rc == 0:\n            state = out\n\n    actually_enabled = enabled or \"true\" in state.lower()\n\n    diagnostics.append(\n        \"A11Y:%s%s\"\n        % (\n            \"ON\" if actually_enabled else \"OFF\",\n            (\"(\" + \",\".join(notes) + \")\") if notes else \"\"\n        )\n    )\n\n    if actually_enabled:\n        time.sleep(0.55)\n\n    return actually_enabled\n\n\ndef get_a11y_bus_address():\n    if not shutil.which(\"gdbus\"):\n        return \"\"\n\n    code, out, _ = run_cmd([\n        \"gdbus\", \"call\",\n        \"--session\",\n        \"--dest\", \"org.a11y.Bus\",\n        \"--object-path\", \"/org/a11y/bus\",\n        \"--method\", \"org.a11y.Bus.GetAddress\"\n    ], 1.5)\n\n    if code != 0:\n        return \"\"\n\n    return first_string(out)\n\ndef role_number(value):\n    try:\n        return int(value)\n    except Exception:\n        return -1\n\ndef state_values(value):\n    if isinstance(value, (tuple, list)):\n        result = []\n        for item in value:\n            try:\n                result.append(int(item))\n            except Exception:\n                pass\n        return result\n    return []\n\ndef normalize_cache_item(item):\n    if not isinstance(item, (tuple, list)):\n        return None\n\n    # Current cache signature:\n    # ((so)(so)(so)iiassusau)\n    if (\n        len(item) >= 10\n        and isinstance(item[3], int)\n        and isinstance(item[4], int)\n    ):\n        return {\n            \"ref\": as_ref(item[0]),\n            \"appRef\": as_ref(item[1]),\n            \"parentRef\": as_ref(item[2]),\n            \"interfaces\": list(item[5]) if isinstance(item[5], (list, tuple)) else [],\n            \"name\": str(item[6] or \"\"),\n            \"role\": role_number(item[7]),\n            \"description\": str(item[8] or \"\"),\n            \"states\": state_values(item[9])\n        }\n\n    # Qt legacy cache signature:\n    # ((so)(so)(so)a(so)assusau)\n    if len(item) >= 9:\n        return {\n            \"ref\": as_ref(item[0]),\n            \"appRef\": as_ref(item[1]),\n            \"parentRef\": as_ref(item[2]),\n            \"interfaces\": list(item[4]) if isinstance(item[4], (list, tuple)) else [],\n            \"name\": str(item[5] or \"\"),\n            \"role\": role_number(item[6]),\n            \"description\": str(item[7] or \"\"),\n            \"states\": state_values(item[8])\n        }\n\n    return None\n\ndef parse_cache_items(raw):\n    payload = parse_gvariant_literal(raw)\n\n    if (\n        isinstance(payload, tuple)\n        and len(payload) == 1\n    ):\n        payload = payload[0]\n\n    if not isinstance(payload, list):\n        return []\n\n    rows = []\n\n    for item in payload:\n        normalized = normalize_cache_item(item)\n\n        if normalized is not None:\n            rows.append(normalized)\n\n    return rows\n\ndef ancestor_info(row, by_ref):\n    app_name = \"\"\n    window_name = \"\"\n    parent = row.get(\"parentRef\", (\"\", \"\"))\n    visited = set()\n\n    while parent and parent not in visited:\n        visited.add(parent)\n        ancestor = by_ref.get(parent)\n\n        if not ancestor:\n            break\n\n        role = ancestor.get(\"role\", -1)\n        name = str(ancestor.get(\"name\") or \"\").strip()\n\n        if (\n            not window_name\n            and role in (\n                ROLE_DIALOG,\n                ROLE_FRAME,\n                ROLE_WINDOW\n            )\n            and name\n        ):\n            window_name = name\n\n        if role == ROLE_APPLICATION and name:\n            app_name = name\n            break\n\n        parent = ancestor.get(\"parentRef\", (\"\", \"\"))\n\n    return app_name, window_name\n\na11y_runtime_enabled = enable_a11y_runtime()\na11y_address = get_a11y_bus_address()\n\n# ------------------------------------------------------------\n# Provider 1: libatspi through PyGObject, when installed.\n# Use numeric roles instead of GetRoleName(); GetRoleName is optional.\n# ------------------------------------------------------------\ngi_count = 0\n\ntry:\n    import gi\n    gi.require_version(\"Atspi\", \"2.0\")\n    from gi.repository import Atspi\n\n    try:\n        Atspi.init()\n    except Exception:\n        pass\n\n    desktop = Atspi.get_desktop(0)\n    visited = 0\n    max_nodes = 26000\n    max_depth = 36\n\n    def gi_name(obj):\n        try:\n            return str(obj.get_name() or \"\")\n        except Exception:\n            return \"\"\n\n    def gi_role(obj):\n        try:\n            return int(obj.get_role())\n        except Exception:\n            return -1\n\n    def gi_selected(obj):\n        try:\n            states = obj.get_state_set()\n\n            return bool(\n                states.contains(Atspi.StateType.SELECTED)\n                or states.contains(Atspi.StateType.FOCUSED)\n                or states.contains(Atspi.StateType.ACTIVE)\n            )\n        except Exception:\n            return False\n\n    def gi_walk(\n            obj,\n            path,\n            app_name=\"\",\n            window_name=\"\",\n            tab_context=False,\n            depth=0):\n        global visited, gi_count\n\n        if (\n            obj is None\n            or depth > max_depth\n            or visited >= max_nodes\n        ):\n            return\n\n        visited += 1\n\n        role = gi_role(obj)\n        name = gi_name(obj).strip()\n\n        if role == ROLE_APPLICATION and name:\n            app_name = name\n\n        if (\n            role in (\n                ROLE_DIALOG,\n                ROLE_FRAME,\n                ROLE_WINDOW\n            )\n            and name\n        ):\n            window_name = name\n\n        is_tab_container = role == ROLE_PAGE_TAB_LIST\n\n        is_tab = (\n            role == ROLE_PAGE_TAB\n            or (\n                tab_context\n                and role in (\n                    ROLE_PUSH_BUTTON,\n                    ROLE_RADIO_BUTTON\n                )\n            )\n        )\n\n        if is_tab and name:\n            add_tab({\n                \"_tabRecord\": True,\n                \"id\": \"atspi:\" + path,\n                \"path\": path,\n                \"name\": name,\n                \"tabTitle\": name,\n                \"appName\": app_name or \"APPLICATION\",\n                \"windowName\": window_name,\n                \"selected\": gi_selected(obj),\n                \"provider\": \"AT-SPI\"\n            })\n            gi_count += 1\n\n        try:\n            count = int(obj.get_child_count())\n        except Exception:\n            count = 0\n\n        child_tab_context = tab_context or is_tab_container\n\n        for index in range(count):\n            try:\n                child = obj.get_child_at_index(index)\n            except Exception:\n                continue\n\n            child_path = (\n                str(index)\n                if not path\n                else path + \".\" + str(index)\n            )\n\n            gi_walk(\n                child,\n                child_path,\n                app_name,\n                window_name,\n                child_tab_context,\n                depth + 1\n            )\n\n    gi_walk(desktop, \"\")\n    diagnostics.append(\"AT-SPI GI:%d\" % gi_count)\n\nexcept Exception as exc:\n    diagnostics.append(\"AT-SPI GI ERROR:%s\" % exc)\n\n# ------------------------------------------------------------\n# Provider 2: AT-SPI Cache.GetItems through gdbus.\n#\n# This is the important fallback. Cache.GetItems returns each app's\n# accessibility tree in ONE D-Bus call, including Name, Role, Parent and\n# State. It avoids launching thousands of gdbus processes and works even\n# when python3-gi is not installed.\n# ------------------------------------------------------------\ncache_count = 0\ncache_apps = 0\n\nif a11y_address and shutil.which(\"gdbus\"):\n    code, roots_raw, roots_err = run_cmd([\n        \"gdbus\", \"call\",\n        \"--address\", a11y_address,\n        \"--dest\", \"org.a11y.atspi.Registry\",\n        \"--object-path\", \"/org/a11y/atspi/accessible/root\",\n        \"--method\", \"org.a11y.atspi.Accessible.GetChildren\"\n    ], 2.0)\n\n    roots = parse_registry_roots(roots_raw) if code == 0 else []\n\n    if code != 0:\n        diagnostics.append(\n            \"AT-SPI CACHE ROOT ERROR:\"\n            + (roots_err or \"GetChildren failed\")\n        )\n    else:\n        unique_buses = []\n        seen_buses = set()\n\n        for bus_name, _ in roots:\n            if bus_name and bus_name not in seen_buses:\n                seen_buses.add(bus_name)\n                unique_buses.append(bus_name)\n\n        for bus_name in unique_buses:\n            code, cache_raw, cache_err = run_cmd([\n                \"gdbus\", \"call\",\n                \"--address\", a11y_address,\n                \"--dest\", bus_name,\n                \"--object-path\", \"/org/a11y/atspi/cache\",\n                \"--method\", \"org.a11y.atspi.Cache.GetItems\"\n            ], 2.4)\n\n            if (code != 0 or not cache_raw) and a11y_runtime_enabled:\n                time.sleep(0.12)\n                code, cache_raw, cache_err = run_cmd([\n                    \"gdbus\", \"call\",\n                    \"--address\", a11y_address,\n                    \"--dest\", bus_name,\n                    \"--object-path\", \"/org/a11y/atspi/cache\",\n                    \"--method\", \"org.a11y.atspi.Cache.GetItems\"\n                ], 2.4)\n\n            if code != 0 or not cache_raw:\n                continue\n\n            try:\n                rows = parse_cache_items(cache_raw)\n            except Exception:\n                continue\n\n            if not rows:\n                continue\n\n            cache_apps += 1\n\n            by_ref = {\n                row[\"ref\"]: row\n                for row in rows\n                if row.get(\"ref\", (\"\", \"\"))[0]\n                and row.get(\"ref\", (\"\", \"\"))[1]\n            }\n\n            for row in rows:\n                role = row.get(\"role\", -1)\n                parent_row = by_ref.get(\n                    row.get(\"parentRef\", (\"\", \"\"))\n                )\n                parent_role = (\n                    parent_row.get(\"role\", -1)\n                    if parent_row\n                    else -1\n                )\n\n                is_tab = (\n                    role == ROLE_PAGE_TAB\n                    or (\n                        parent_role == ROLE_PAGE_TAB_LIST\n                        and role in (\n                            ROLE_PUSH_BUTTON,\n                            ROLE_RADIO_BUTTON\n                        )\n                    )\n                )\n\n                if not is_tab:\n                    continue\n\n                name = str(row.get(\"name\") or \"\").strip()\n\n                if not name:\n                    continue\n\n                app_name, window_name = ancestor_info(\n                    row,\n                    by_ref\n                )\n\n                states = row.get(\"states\", [])\n\n                add_tab({\n                    \"_tabRecord\": True,\n                    \"id\":\n                        \"atspi-cache:\"\n                        + row[\"ref\"][0]\n                        + \":\"\n                        + row[\"ref\"][1],\n                    \"path\": \"\",\n                    \"busName\": row[\"ref\"][0],\n                    \"objectPath\": row[\"ref\"][1],\n                    \"name\": name,\n                    \"tabTitle\": name,\n                    \"appName\": app_name or \"APPLICATION\",\n                    \"windowName\": window_name,\n                    \"selected\":\n                        STATE_SELECTED in states\n                        or STATE_FOCUSED in states\n                        or STATE_ACTIVE in states,\n                    \"provider\": \"AT-SPI-CACHE\"\n                })\n                cache_count += 1\n\n        diagnostics.append(\n            \"AT-SPI CACHE:%d/%d\"\n            % (cache_count, cache_apps)\n        )\nelse:\n    diagnostics.append(\"AT-SPI CACHE:UNAVAILABLE\")\n\n# ------------------------------------------------------------\n# Provider 3: Kitty remote control.\n# ------------------------------------------------------------\nkitty_addresses = []\n\ntry:\n    for pid in os.listdir(\"/proc\"):\n        if not pid.isdigit():\n            continue\n\n        try:\n            env = open(\n                \"/proc/%s/environ\" % pid,\n                \"rb\"\n            ).read().split(b\"\\0\")\n        except Exception:\n            continue\n\n        for item in env:\n            if item.startswith(b\"KITTY_LISTEN_ON=\"):\n                address = item.split(\n                    b\"=\",\n                    1\n                )[1].decode(\n                    \"utf-8\",\n                    \"ignore\"\n                ).strip()\n\n                if (\n                    address\n                    and address not in kitty_addresses\n                ):\n                    kitty_addresses.append(address)\nexcept Exception:\n    pass\n\nkitty_count = 0\n\nfor address in kitty_addresses:\n    try:\n        proc = subprocess.run(\n            [\n                \"kitty\",\n                \"@\",\n                \"--to\",\n                address,\n                \"ls\"\n            ],\n            stdout=subprocess.PIPE,\n            stderr=subprocess.DEVNULL,\n            text=True,\n            timeout=1.5\n        )\n\n        if (\n            proc.returncode != 0\n            or not proc.stdout.strip()\n        ):\n            continue\n\n        payload = json.loads(proc.stdout)\n\n        for os_window in (\n            payload\n            if isinstance(payload, list)\n            else []\n        ):\n            for tab in os_window.get(\"tabs\", []) or []:\n                tab_id = tab.get(\"id\")\n                title = str(\n                    tab.get(\"title\")\n                    or \"\"\n                ).strip()\n\n                if not title:\n                    wins = tab.get(\"windows\", []) or []\n                    active = next(\n                        (\n                            w for w in wins\n                            if w.get(\"is_active\")\n                        ),\n                        None\n                    )\n                    active = (\n                        active\n                        or (wins[0] if wins else {})\n                    )\n                    title = str(\n                        active.get(\"title\")\n                        or active.get(\"cwd\")\n                        or (\n                            \"KITTY TAB \"\n                            + str(tab_id)\n                        )\n                    )\n\n                add_tab({\n                    \"_tabRecord\": True,\n                    \"id\":\n                        \"kitty:\"\n                        + str(tab_id),\n                    \"path\": \"\",\n                    \"name\": title,\n                    \"tabTitle\": title,\n                    \"appName\": \"Kitty\",\n                    \"windowName\":\n                        str(\n                            os_window.get(\"id\")\n                            or \"\"\n                        ),\n                    \"selected\":\n                        bool(tab.get(\"is_active\")),\n                    \"provider\": \"KITTY\",\n                    \"kittyAddress\": address,\n                    \"kittyTabId\": tab_id,\n                    \"processPids\": sorted(set(\n                        [int(w.get(\"pid\")) for w in (tab.get(\"windows\", []) or []) if w.get(\"pid\")]\n                        + [int(proc.get(\"pid\")) for w in (tab.get(\"windows\", []) or []) for proc in (w.get(\"foreground_processes\", []) or []) if proc.get(\"pid\")]\n                    ))\n                })\n                kitty_count += 1\n\n    except Exception:\n        pass\n\ndiagnostics.append(\"KITTY:%d\" % kitty_count)\n\n# ------------------------------------------------------------\n# Provider 4: Chromium/Electron DevTools, when already enabled.\n# ------------------------------------------------------------\nports = {}\n\ntry:\n    for pid in os.listdir(\"/proc\"):\n        if not pid.isdigit():\n            continue\n\n        try:\n            raw = open(\n                \"/proc/%s/cmdline\" % pid,\n                \"rb\"\n            ).read()\n\n            argv = [\n                part.decode(\n                    \"utf-8\",\n                    \"ignore\"\n                )\n                for part in raw.split(b\"\\0\")\n                if part\n            ]\n        except Exception:\n            continue\n\n        if not argv:\n            continue\n\n        exe = os.path.basename(\n            argv[0]\n        ).lower()\n\n        app_name = (\n            \"Brave\"\n            if \"brave\" in exe\n            else \"Chrome\"\n            if \"chrome\" in exe\n            else \"Chromium\"\n            if \"chromium\" in exe\n            else \"VS Code\"\n            if exe in (\n                \"code\",\n                \"code-oss\",\n                \"codium\"\n            )\n            else \"Electron\"\n            if \"electron\" in exe\n            else \"\"\n        )\n\n        if not app_name:\n            continue\n\n        port = None\n\n        for index, arg in enumerate(argv):\n            if arg.startswith(\n                    \"--remote-debugging-port=\"):\n                try:\n                    port = int(\n                        arg.split(\"=\", 1)[1]\n                    )\n                except Exception:\n                    port = None\n                break\n\n            if (\n                arg == \"--remote-debugging-port\"\n                and index + 1 < len(argv)\n            ):\n                try:\n                    port = int(argv[index + 1])\n                except Exception:\n                    port = None\n                break\n\n        if port and port > 0:\n            ports[port] = app_name\n\nexcept Exception:\n    pass\n\ndevtools_count = 0\n\nfor port, app_name in ports.items():\n    try:\n        with urllib.request.urlopen(\n            \"http://127.0.0.1:%d/json/list\"\n            % port,\n            timeout=0.8\n        ) as response:\n            targets = json.loads(\n                response.read().decode(\n                    \"utf-8\",\n                    \"ignore\"\n                )\n            )\n    except Exception:\n        continue\n\n    for target in targets:\n        if str(\n            target.get(\"type\", \"\")\n        ).lower() not in (\n            \"page\",\n            \"webview\"\n        ):\n            continue\n\n        target_id = str(\n            target.get(\"id\")\n            or \"\"\n        ).strip()\n\n        title = str(\n            target.get(\"title\")\n            or target.get(\"url\")\n            or \"\"\n        ).strip()\n\n        if not target_id or not title:\n            continue\n\n        add_tab({\n            \"_tabRecord\": True,\n            \"id\":\n                \"devtools:%d:%s\"\n                % (port, target_id),\n            \"path\": \"\",\n            \"name\": title,\n            \"tabTitle\": title,\n            \"appName\": app_name,\n            \"windowName\":\n                str(target.get(\"url\") or \"\"),\n            \"selected\": False,\n            \"provider\": \"DEVTOOLS\",\n            \"debugPort\": port,\n            \"targetId\": target_id,\n            \"webSocketDebuggerUrl\": str(target.get(\"webSocketDebuggerUrl\") or \"\")\n        })\n        devtools_count += 1\n\ndiagnostics.append(\n    \"DEVTOOLS:%d\"\n    % devtools_count\n)\n\nprint(json.dumps({\n    \"error\":\n        \"\"\n        if tabs\n        else \"NO TABS \u2022 \" + \" | \".join(diagnostics),\n    \"tabs\": tabs,\n    \"diagnostics\": diagnostics\n}))\n";
}

function appTabActivateScript() {
    return "import ast\nimport ctypes\nimport ctypes.util\nimport json\nimport re\nimport subprocess\nimport sys\nimport urllib.request\n\nprovider = sys.argv[1] if len(sys.argv) > 1 else \"\"\npayload = sys.argv[2] if len(sys.argv) > 2 else \"\"\n\ntry:\n    data = json.loads(payload or \"{}\")\nexcept Exception:\n    data = {}\n\nacted = False\nerror = \"\"\n\ntry:\n    if provider == \"LIBATSPI\":\n        lib_name = (\n            ctypes.util.find_library(\"atspi\")\n            or \"libatspi.so.0\"\n        )\n        atspi = ctypes.CDLL(lib_name)\n\n        atspi.atspi_init.argtypes = []\n        atspi.atspi_init.restype = ctypes.c_int\n\n        atspi.atspi_get_desktop.argtypes = [ctypes.c_int]\n        atspi.atspi_get_desktop.restype = ctypes.c_void_p\n\n        atspi.atspi_accessible_get_child_at_index.argtypes = [\n            ctypes.c_void_p,\n            ctypes.c_int,\n            ctypes.c_void_p\n        ]\n        atspi.atspi_accessible_get_child_at_index.restype = ctypes.c_void_p\n\n        atspi.atspi_accessible_get_child_count.argtypes = [\n            ctypes.c_void_p,\n            ctypes.c_void_p\n        ]\n        atspi.atspi_accessible_get_child_count.restype = ctypes.c_int\n\n        atspi.atspi_accessible_get_role.argtypes = [\n            ctypes.c_void_p,\n            ctypes.c_void_p\n        ]\n        atspi.atspi_accessible_get_role.restype = ctypes.c_int\n\n        atspi.atspi_accessible_get_name.argtypes = [\n            ctypes.c_void_p,\n            ctypes.c_void_p\n        ]\n        atspi.atspi_accessible_get_name.restype = ctypes.c_void_p\n\n        atspi.atspi_accessible_get_action_iface.argtypes = [\n            ctypes.c_void_p\n        ]\n        atspi.atspi_accessible_get_action_iface.restype = ctypes.c_void_p\n\n        atspi.atspi_action_get_n_actions.argtypes = [\n            ctypes.c_void_p,\n            ctypes.c_void_p\n        ]\n        atspi.atspi_action_get_n_actions.restype = ctypes.c_int\n\n        atspi.atspi_action_get_action_name.argtypes = [\n            ctypes.c_void_p,\n            ctypes.c_int,\n            ctypes.c_void_p\n        ]\n        atspi.atspi_action_get_action_name.restype = ctypes.c_void_p\n\n        atspi.atspi_action_do_action.argtypes = [\n            ctypes.c_void_p,\n            ctypes.c_int,\n            ctypes.c_void_p\n        ]\n        atspi.atspi_action_do_action.restype = ctypes.c_int\n\n        atspi.atspi_accessible_get_component_iface.argtypes = [\n            ctypes.c_void_p\n        ]\n        atspi.atspi_accessible_get_component_iface.restype = ctypes.c_void_p\n\n        atspi.atspi_component_grab_focus.argtypes = [\n            ctypes.c_void_p,\n            ctypes.c_void_p\n        ]\n        atspi.atspi_component_grab_focus.restype = ctypes.c_int\n\n        atspi.atspi_init()\n\n        def read_string(pointer):\n            if not pointer:\n                return \"\"\n\n            try:\n                return ctypes.string_at(pointer).decode(\n                    \"utf-8\",\n                    \"replace\"\n                )\n            except Exception:\n                return \"\"\n\n        def obj_name(obj):\n            try:\n                return read_string(\n                    atspi.atspi_accessible_get_name(\n                        obj,\n                        None\n                    )\n                ).strip()\n            except Exception:\n                return \"\"\n\n        desktop = atspi.atspi_get_desktop(0)\n        obj = desktop\n        path = str(data.get(\"path\") or \"\")\n\n        for piece in path.split(\".\"):\n            if not piece:\n                continue\n\n            if not obj:\n                break\n\n            try:\n                obj = atspi.atspi_accessible_get_child_at_index(\n                    obj,\n                    int(piece),\n                    None\n                )\n            except Exception:\n                obj = None\n\n        wanted_title = str(\n            data.get(\"tabTitle\")\n            or data.get(\"controlName\")\n            or data.get(\"name\")\n            or \"\"\n        ).strip()\n        wanted_role = int(data.get(\"role\") or -1)\n        is_control = bool(data.get(\"_tabControlRecord\"))\n\n        # If the tree changed between scan and click, search by current title.\n        if not obj or (\n            wanted_title\n            and obj_name(obj) != wanted_title\n        ):\n            obj = None\n            max_nodes = 20000\n            visited = 0\n            stack = [desktop] if desktop else []\n\n            while stack and visited < max_nodes and not obj:\n                candidate = stack.pop()\n                visited += 1\n\n                try:\n                    role = int(\n                        atspi.atspi_accessible_get_role(\n                            candidate,\n                            None\n                        )\n                    )\n                except Exception:\n                    role = -1\n\n                role_matches = (\n                    role == wanted_role\n                    if is_control and wanted_role >= 0\n                    else role == 37\n                )\n\n                if role_matches and obj_name(candidate) == wanted_title:\n                    obj = candidate\n                    break\n\n                try:\n                    count = int(\n                        atspi.atspi_accessible_get_child_count(\n                            candidate,\n                            None\n                        )\n                    )\n                except Exception:\n                    count = 0\n\n                for index in range(max(0, count) - 1, -1, -1):\n                    try:\n                        child = atspi.atspi_accessible_get_child_at_index(\n                            candidate,\n                            index,\n                            None\n                        )\n                    except Exception:\n                        child = None\n\n                    if child:\n                        stack.append(child)\n\n        if obj:\n            action = atspi.atspi_accessible_get_action_iface(obj)\n\n            if action:\n                try:\n                    count = int(\n                        atspi.atspi_action_get_n_actions(\n                            action,\n                            None\n                        )\n                    )\n                except Exception:\n                    count = 0\n\n                preferred = []\n                other = []\n\n                for index in range(max(0, count)):\n                    try:\n                        name = read_string(\n                            atspi.atspi_action_get_action_name(\n                                action,\n                                index,\n                                None\n                            )\n                        ).lower()\n                    except Exception:\n                        name = \"\"\n\n                    if any(\n                        word in name\n                        for word in (\n                            \"activate\",\n                            \"click\",\n                            \"press\",\n                            \"select\",\n                            \"switch\"\n                        )\n                    ):\n                        preferred.append(index)\n                    else:\n                        other.append(index)\n\n                for index in preferred + other:\n                    try:\n                        if atspi.atspi_action_do_action(\n                            action,\n                            index,\n                            None\n                        ):\n                            acted = True\n                            break\n                    except Exception:\n                        pass\n\n            if not acted:\n                component = atspi.atspi_accessible_get_component_iface(obj)\n\n                if component:\n                    try:\n                        acted = bool(\n                            atspi.atspi_component_grab_focus(\n                                component,\n                                None\n                            )\n                        )\n                    except Exception:\n                        acted = False\n\n    elif provider == \"AT-SPI\":\n        import gi\n        gi.require_version(\"Atspi\", \"2.0\")\n        from gi.repository import Atspi\n\n        try:\n            Atspi.init()\n        except Exception:\n            pass\n\n        desktop = Atspi.get_desktop(0)\n        obj = desktop\n        path = str(data.get(\"path\") or \"\")\n\n        for piece in path.split(\".\"):\n            if piece:\n                obj = obj.get_child_at_index(int(piece))\n\n        try:\n            action = obj.get_action_iface()\n        except Exception:\n            action = None\n\n        if action is not None:\n            try:\n                count = int(action.get_n_actions())\n            except Exception:\n                count = 0\n\n            preferred = []\n\n            for index in range(count):\n                try:\n                    name = str(action.get_action_name(index) or \"\").lower()\n                except Exception:\n                    name = \"\"\n\n                if any(word in name for word in (\n                    \"activate\", \"click\", \"press\", \"select\", \"switch\"\n                )):\n                    preferred.append(index)\n\n            order = preferred + [\n                index for index in range(count)\n                if index not in preferred\n            ]\n\n            for index in order:\n                try:\n                    if action.do_action(index):\n                        acted = True\n                        break\n                except Exception:\n                    pass\n\n        if not acted:\n            try:\n                component = obj.get_component_iface()\n                if component is not None:\n                    acted = bool(component.grab_focus())\n            except Exception:\n                pass\n\n    elif provider == \"AT-SPI-CACHE\":\n        bus_name = str(data.get(\"busName\") or \"\")\n        object_path = str(data.get(\"objectPath\") or \"\")\n\n        def first_string(raw):\n            match = re.search(\n                r\"'((?:\\\\.|[^'])*)'\",\n                str(raw or \"\")\n            )\n            if not match:\n                return \"\"\n            try:\n                return ast.literal_eval(\n                    \"'\" + match.group(1) + \"'\"\n                )\n            except Exception:\n                return match.group(1)\n\n        address_proc = subprocess.run(\n            [\n                \"gdbus\",\n                \"call\",\n                \"--session\",\n                \"--dest\",\n                \"org.a11y.Bus\",\n                \"--object-path\",\n                \"/org/a11y/bus\",\n                \"--method\",\n                \"org.a11y.Bus.GetAddress\"\n            ],\n            stdout=subprocess.PIPE,\n            stderr=subprocess.PIPE,\n            text=True,\n            timeout=1.0\n        )\n\n        address = first_string(\n            address_proc.stdout\n        )\n\n        if address and bus_name and object_path:\n            # Page tabs conventionally expose their default activate/select\n            # action at slot 0. Query action names first when possible.\n            order = []\n\n            get_actions = subprocess.run(\n                [\n                    \"gdbus\",\n                    \"call\",\n                    \"--address\",\n                    address,\n                    \"--dest\",\n                    bus_name,\n                    \"--object-path\",\n                    object_path,\n                    \"--method\",\n                    \"org.a11y.atspi.Action.GetActions\"\n                ],\n                stdout=subprocess.PIPE,\n                stderr=subprocess.PIPE,\n                text=True,\n                timeout=0.65\n            )\n\n            if get_actions.returncode == 0:\n                names = re.findall(\n                    r\"\\('([^']*)',\",\n                    get_actions.stdout\n                )\n\n                preferred = []\n                other = []\n\n                for index, name in enumerate(names):\n                    low = name.lower()\n\n                    if any(\n                        word in low\n                        for word in (\n                            \"activate\",\n                            \"click\",\n                            \"press\",\n                            \"select\",\n                            \"switch\"\n                        )\n                    ):\n                        preferred.append(index)\n                    else:\n                        other.append(index)\n\n                order = preferred + other\n\n            if not order:\n                order = [0, 1, 2, 3]\n\n            for index in order:\n                proc = subprocess.run(\n                    [\n                        \"gdbus\",\n                        \"call\",\n                        \"--address\",\n                        address,\n                        \"--dest\",\n                        bus_name,\n                        \"--object-path\",\n                        object_path,\n                        \"--method\",\n                        \"org.a11y.atspi.Action.DoAction\",\n                        str(index)\n                    ],\n                    stdout=subprocess.PIPE,\n                    stderr=subprocess.PIPE,\n                    text=True,\n                    timeout=0.65\n                )\n\n                if (\n                    proc.returncode == 0\n                    and \"true\" in proc.stdout.lower()\n                ):\n                    acted = True\n                    break\n\n            if not acted:\n                proc = subprocess.run(\n                    [\n                        \"gdbus\",\n                        \"call\",\n                        \"--address\",\n                        address,\n                        \"--dest\",\n                        bus_name,\n                        \"--object-path\",\n                        object_path,\n                        \"--method\",\n                        \"org.a11y.atspi.Component.GrabFocus\"\n                    ],\n                    stdout=subprocess.PIPE,\n                    stderr=subprocess.PIPE,\n                    text=True,\n                    timeout=0.65\n                )\n\n                acted = (\n                    proc.returncode == 0\n                    and \"true\" in proc.stdout.lower()\n                )\n\n                if not acted:\n                    error = proc.stderr.strip()\n\n    elif provider == \"AT-SPI-DBUS\":\n        bus_name = str(data.get(\"busName\") or \"\")\n        object_path = str(data.get(\"objectPath\") or \"\")\n\n        def first_string(raw):\n            match = re.search(r\"'((?:\\\\.|[^'])*)'\", str(raw or \"\"))\n            if not match:\n                return \"\"\n            try:\n                return ast.literal_eval(\"'\" + match.group(1) + \"'\")\n            except Exception:\n                return match.group(1)\n\n        address_proc = subprocess.run(\n            [\n                \"gdbus\", \"call\",\n                \"--session\",\n                \"--dest\", \"org.a11y.Bus\",\n                \"--object-path\", \"/org/a11y/bus\",\n                \"--method\", \"org.a11y.Bus.GetAddress\"\n            ],\n            stdout=subprocess.PIPE,\n            stderr=subprocess.PIPE,\n            text=True,\n            timeout=1.0\n        )\n\n        address = first_string(address_proc.stdout)\n\n        if address and bus_name and object_path:\n            # Toolkit action ordering differs. Try a few action slots, then\n            # fall back to keyboard focus.\n            for index in range(6):\n                proc = subprocess.run(\n                    [\n                        \"gdbus\", \"call\",\n                        \"--address\", address,\n                        \"--dest\", bus_name,\n                        \"--object-path\", object_path,\n                        \"--method\", \"org.a11y.atspi.Action.DoAction\",\n                        str(index)\n                    ],\n                    stdout=subprocess.PIPE,\n                    stderr=subprocess.PIPE,\n                    text=True,\n                    timeout=0.65\n                )\n\n                if proc.returncode == 0 and \"true\" in proc.stdout.lower():\n                    acted = True\n                    break\n\n            if not acted:\n                proc = subprocess.run(\n                    [\n                        \"gdbus\", \"call\",\n                        \"--address\", address,\n                        \"--dest\", bus_name,\n                        \"--object-path\", object_path,\n                        \"--method\", \"org.a11y.atspi.Component.GrabFocus\"\n                    ],\n                    stdout=subprocess.PIPE,\n                    stderr=subprocess.PIPE,\n                    text=True,\n                    timeout=0.65\n                )\n\n                acted = (\n                    proc.returncode == 0\n                    and \"true\" in proc.stdout.lower()\n                )\n\n                if not acted:\n                    error = proc.stderr.strip()\n\n    elif provider == \"KITTY\":\n        address = str(data.get(\"kittyAddress\") or \"\")\n        tab_id = data.get(\"kittyTabId\")\n\n        cmd = [\"kitty\", \"@\"]\n        if address:\n            cmd += [\"--to\", address]\n\n        cmd += [\"focus-tab\", \"--match\", \"id:\" + str(tab_id)]\n\n        proc = subprocess.run(\n            cmd,\n            stdout=subprocess.DEVNULL,\n            stderr=subprocess.PIPE,\n            text=True,\n            timeout=2.0\n        )\n        acted = proc.returncode == 0\n\n        if not acted:\n            error = proc.stderr.strip()\n\n    elif provider == \"DEVTOOLS\":\n        port = int(data.get(\"debugPort\") or 0)\n        target_id = str(data.get(\"targetId\") or \"\")\n\n        req = urllib.request.Request(\n            \"http://127.0.0.1:%d/json/activate/%s\" % (port, target_id),\n            method=\"PUT\"\n        )\n\n        with urllib.request.urlopen(req, timeout=1.0) as response:\n            response.read()\n\n        acted = True\n\nexcept Exception as exc:\n    error = str(exc)\n\nprint(json.dumps({\"ok\": acted, \"error\": error}))\n";
}

function tabLifecycleScript() {
    return "import base64\nimport hashlib\nimport json\nimport os\nimport socket\nimport struct\nimport sys\nimport urllib.parse\nimport urllib.request\n\nentry = json.loads(sys.argv[1])\nstate = sys.argv[2] if len(sys.argv) > 2 else \"active\"\nport = int(entry.get(\"debugPort\") or 0)\ntarget_id = str(entry.get(\"targetId\") or \"\")\nws_url = str(entry.get(\"webSocketDebuggerUrl\") or \"\")\n\ntry:\n    if (not ws_url) and port and target_id:\n        with urllib.request.urlopen(\"http://127.0.0.1:%d/json/list\" % port, timeout=0.8) as response:\n            for target in json.loads(response.read().decode(\"utf-8\", \"ignore\")):\n                if str(target.get(\"id\") or \"\") == target_id:\n                    ws_url = str(target.get(\"webSocketDebuggerUrl\") or \"\")\n                    break\n    if not ws_url:\n        raise RuntimeError(\"NO DEVTOOLS WEBSOCKET FOR TAB\")\n\n    parsed = urllib.parse.urlparse(ws_url)\n    if parsed.scheme != \"ws\":\n        raise RuntimeError(\"UNSUPPORTED DEVTOOLS WEBSOCKET SCHEME\")\n    host = parsed.hostname or \"127.0.0.1\"\n    port_num = parsed.port or 80\n    path = parsed.path or \"/\"\n    if parsed.query:\n        path += \"?\" + parsed.query\n\n    sock = socket.create_connection((host, port_num), timeout=1.5)\n    key = base64.b64encode(os.urandom(16)).decode(\"ascii\")\n    request = (\n        \"GET %s HTTP/1.1\\r\\nHost: %s:%d\\r\\nUpgrade: websocket\\r\\nConnection: Upgrade\\r\\n\"\n        \"Sec-WebSocket-Key: %s\\r\\nSec-WebSocket-Version: 13\\r\\n\\r\\n\"\n    ) % (path, host, port_num, key)\n    sock.sendall(request.encode(\"ascii\"))\n    response = b\"\"\n    while b\"\\r\\n\\r\\n\" not in response:\n        chunk = sock.recv(4096)\n        if not chunk:\n            break\n        response += chunk\n    if b\" 101 \" not in response.split(b\"\\r\\n\", 1)[0]:\n        raise RuntimeError(\"DEVTOOLS WEBSOCKET HANDSHAKE FAILED\")\n\n    def send_text(text):\n        payload = text.encode(\"utf-8\")\n        mask = os.urandom(4)\n        header = bytearray([0x81])\n        length = len(payload)\n        if length < 126:\n            header.append(0x80 | length)\n        elif length < 65536:\n            header.append(0x80 | 126)\n            header.extend(struct.pack(\"!H\", length))\n        else:\n            header.append(0x80 | 127)\n            header.extend(struct.pack(\"!Q\", length))\n        header.extend(mask)\n        masked = bytes(payload[i] ^ mask[i % 4] for i in range(length))\n        sock.sendall(bytes(header) + masked)\n\n    def recv_exact(count):\n        data = b\"\"\n        while len(data) < count:\n            chunk = sock.recv(count - len(data))\n            if not chunk:\n                raise RuntimeError(\"DEVTOOLS WEBSOCKET CLOSED\")\n            data += chunk\n        return data\n\n    def recv_frame():\n        first, second = recv_exact(2)\n        opcode = first & 0x0f\n        masked = bool(second & 0x80)\n        length = second & 0x7f\n        if length == 126:\n            length = struct.unpack(\"!H\", recv_exact(2))[0]\n        elif length == 127:\n            length = struct.unpack(\"!Q\", recv_exact(8))[0]\n        mask = recv_exact(4) if masked else b\"\"\n        payload = recv_exact(length) if length else b\"\"\n        if masked:\n            payload = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))\n        if opcode == 0x9:\n            return None\n        if opcode == 0x8:\n            raise RuntimeError(\"DEVTOOLS WEBSOCKET CLOSED\")\n        return payload.decode(\"utf-8\", \"ignore\")\n\n    send_text(json.dumps({\n        \"id\": 1,\n        \"method\": \"Page.setWebLifecycleState\",\n        \"params\": {\"state\": \"frozen\" if state == \"frozen\" else \"active\"}\n    }))\n\n    result = None\n    for _ in range(40):\n        raw = recv_frame()\n        if not raw:\n            continue\n        message = json.loads(raw)\n        if message.get(\"id\") == 1:\n            result = message\n            break\n    sock.close()\n    if result is None:\n        raise RuntimeError(\"NO DEVTOOLS LIFECYCLE RESPONSE\")\n    if result.get(\"error\"):\n        raise RuntimeError(str(result[\"error\"]))\n    print(json.dumps({\"ok\": True, \"state\": state}))\nexcept Exception as exc:\n    print(json.dumps({\"ok\": False, \"state\": state, \"error\": str(exc)}))\n";
}

    function tabRowsSignature(rows) {
        const normalized = [];

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i] || ({});
            normalized.push([
                String(row.provider || ""),
                String(row.id || row.path || ""),
                String(row.tabTitle || row.name || ""),
                !!row.selected
            ]);
        }

        return JSON.stringify(normalized);
    }

    function updateTabsStable(nextTabs) {
        if (!Array.isArray(nextTabs))
            return;

        const signature = tabRowsSignature(nextTabs);

        // Persistent providers emit heartbeat snapshots. Do not churn the
        // consumer model when the meaningful tab set has not changed.
        if (signature === dataSignature)
            return;

        snapshotWillChange();
        dataSignature = signature;
        tabs = nextTabs;
        snapshotChanged();
    }

    function setDiagnostics(rows) {
        const next = Array.isArray(rows)
            ? rows.map(function(value) {
                return String(value || "");
            })
            : [];
        const signature = next.join(" • ");

        if (signature === diagnosticsSignature)
            return;

        diagnosticsSignature = signature;
        diagnostics = next;
    }

    function refresh() {
        // The persistent bridge continuously publishes live snapshots.
        // The scanner is only a fallback while that bridge is unavailable.
        if (bridgeReady || appTabsProcess.running)
            return;

        if (tabs.length === 0 && errorText.length === 0)
            loading = true;

        appTabsProcess.exec([
            "/usr/bin/python3",
            "-c",
            appTabScanScript()
        ]);
    }

    function warmRefresh() {
        if (!active)
            return;

        refresh();
        appTabsWarmRefreshTimer.restart();
        appTabsSecondWarmRefreshTimer.restart();
    }

    function activate(entry) {
        if (!entry || !entry._tabRecord || entry._tabUnavailable)
            return false;

        appTabsActivateProcess.exec([
            "/usr/bin/python3",
            "-c",
            appTabActivateScript(),
            String(entry.provider || ""),
            JSON.stringify(entry)
        ]);

        return true;
    }

    function activateControl(entry) {
        if (!entry || !entry._tabControlRecord)
            return false;

        appTabsActivateProcess.exec([
            "/usr/bin/python3",
            "-c",
            appTabActivateScript(),
            String(entry.provider || ""),
            JSON.stringify(entry)
        ]);

        return true;
    }

    function hasNativeLifecycleControl(entry) {
        return !!entry
            && String(entry.provider || "").toUpperCase() === "DEVTOOLS"
            && Number(entry.debugPort || 0) > 0
            && String(entry.targetId || "").length > 0;
    }

    function providerRecordKey(entry) {
        if (!entry)
            return "";

        // This is provider-local identity evidence only. It intentionally
        // preserves the donor's current record id and does not attempt to
        // canonicalize DesktopEntry/Application/Sway/PID relationships.
        return String(entry.id || "");
    }

    function identityEvidence(entry) {
        if (!entry)
            return ({});

        // Raw evidence exported for Team 7 / future identity adapters.
        // Consumers must not treat this object as canonical application
        // identity; fields vary by provider and may be absent.
        return {
            providerKey: providerRecordKey(entry),
            provider: String(entry.provider || ""),
            appName: String(entry.appName || ""),
            windowName: String(entry.windowName || ""),
            path: String(entry.path || ""),
            roleName: String(entry.roleName || ""),
            processPids: Array.isArray(entry.processPids)
                         ? entry.processPids.slice()
                         : [],
            debugPort: Number(entry.debugPort || 0),
            targetId: String(entry.targetId || ""),
            webSocketDebuggerUrl:
                String(entry.webSocketDebuggerUrl || ""),
            kittyAddress: String(entry.kittyAddress || ""),
            kittyTabId:
                entry.kittyTabId !== undefined
                ? entry.kittyTabId
                : null
        };
    }

    function nativeLifecycleKey(entry) {
        const value = providerRecordKey(entry);
        return value.length > 0 ? "tab|" + value : "";
    }

    function lifecycleFrozen(entry) {
        const key = nativeLifecycleKey(entry);
        return !!key && !!lifecycleFrozenKeys[key];
    }

    function rollbackPendingLifecycle() {
        if (!lifecyclePendingKey)
            return;

        const rollback = Object.assign({}, lifecycleFrozenKeys);

        if (lifecyclePendingPreviousFrozen)
            rollback[lifecyclePendingKey] = true;
        else
            delete rollback[lifecyclePendingKey];

        lifecycleFrozenKeys = rollback;
    }

    function setLifecycleFrozen(entry, frozen) {
        const key = nativeLifecycleKey(entry);

        if (!entry || !key || !hasNativeLifecycleControl(entry))
            return false;

        lifecyclePendingKey = key;
        lifecyclePendingFrozen = !!frozen;
        lifecyclePendingPreviousFrozen = !!lifecycleFrozenKeys[key];
        lifecycleError = "";

        const optimistic = Object.assign({}, lifecycleFrozenKeys);

        if (frozen)
            optimistic[key] = true;
        else
            delete optimistic[key];

        lifecycleFrozenKeys = optimistic;

        tabLifecycleProcess.exec([
            "/usr/bin/python3",
            "-c",
            tabLifecycleScript(),
            JSON.stringify(entry),
            frozen ? "frozen" : "active"
        ]);

        return true;
    }

    onActiveChanged: {
        if (active) {
            if (tabs.length === 0 && errorText.length === 0)
                loading = true;

            warmRefresh();
        } else {
            appTabsWarmRefreshTimer.stop();
            appTabsSecondWarmRefreshTimer.stop();
            appTabsBridgeRefreshTimer.stop();
        }
    }

    Process {
        id: appTabsBridgeProcess

        command: [
            "/usr/bin/python3",
            "-u",
            "-c",
            tabSurfaceProvider.appTabBridgeScript()
        ]

        running: tabSurfaceProvider.active

        stdout: SplitParser {
            onRead: function(line) {
                const raw = String(line || "").trim();

                if (!raw)
                    return;

                try {
                    const payload = JSON.parse(raw);

                    tabSurfaceProvider.bridgeReady = !!payload.ready;
                    tabSurfaceProvider.bridgeError =
                        String(payload.error || "");

                    if (Array.isArray(payload.diagnostics)) {
                        tabSurfaceProvider.setDiagnostics(
                            payload.diagnostics
                        );

                        if (tabSurfaceProvider.diagnosticsSignature.length > 0)
                            console.log(
                                "TabSurfaceProvider diagnostics:",
                                tabSurfaceProvider.diagnosticsSignature
                            );
                    }

                    if (Array.isArray(payload.controls))
                        tabSurfaceProvider.controls =
                            payload.controls.slice();

                    if (Array.isArray(payload.tabs)) {
                        const nextTabs = payload.tabs;

                        if (nextTabs.length > 0
                                || tabSurfaceProvider.tabs.length === 0)
                            tabSurfaceProvider.updateTabsStable(nextTabs);

                        tabSurfaceProvider.loading = false;

                        if (nextTabs.length > 0)
                            tabSurfaceProvider.errorText = "";
                        else if (Array.isArray(payload.diagnostics))
                            tabSurfaceProvider.errorText =
                                payload.diagnostics.join(" • ");
                    }

                    if (payload.ready)
                        appTabsBridgeRefreshTimer.restart();
                } catch (error) {
                    tabSurfaceProvider.bridgeReady = false;
                    tabSurfaceProvider.bridgeError =
                        "TAB BRIDGE PARSE: " + String(error);
                }
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message.length > 0)
                    tabSurfaceProvider.bridgeError = message;
            }
        }

        onRunningChanged: {
            if (!running)
                tabSurfaceProvider.bridgeReady = false;
        }
    }

    Timer {
        id: appTabsBridgeRefreshTimer
        interval: 700
        repeat: false
        onTriggered: {
            if (tabSurfaceProvider.active)
                tabSurfaceProvider.refresh();
        }
    }

    Process {
        id: tabLifecycleProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const payload = JSON.parse(text || "{}");

                    if (payload.ok) {
                        tabSurfaceProvider.lifecycleError = "";
                        tabSurfaceProvider.lifecycleFinished(true, "");
                    } else {
                        tabSurfaceProvider.rollbackPendingLifecycle();
                        tabSurfaceProvider.lifecycleError =
                            String(payload.error || "TAB SUSPEND FAILED");
                        tabSurfaceProvider.lifecycleFinished(
                            false,
                            tabSurfaceProvider.lifecycleError
                        );
                    }
                } catch (error) {
                    tabSurfaceProvider.rollbackPendingLifecycle();
                    tabSurfaceProvider.lifecycleError =
                        "TAB SUSPEND PARSE: " + String(error);
                    tabSurfaceProvider.lifecycleFinished(
                        false,
                        tabSurfaceProvider.lifecycleError
                    );
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0) {
                    tabSurfaceProvider.rollbackPendingLifecycle();
                    tabSurfaceProvider.lifecycleError = message;
                    tabSurfaceProvider.lifecycleFinished(false, message);
                }
            }
        }
    }

    Process {
        id: appTabsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const payload = JSON.parse(text || "{}");
                    const nextTabs =
                        Array.isArray(payload.tabs)
                        ? payload.tabs
                        : [];

                    if (nextTabs.length > 0
                            || tabSurfaceProvider.tabs.length === 0)
                        tabSurfaceProvider.updateTabsStable(nextTabs);

                    tabSurfaceProvider.errorText =
                        String(payload.error || "");

                    if (Array.isArray(payload.diagnostics))
                        tabSurfaceProvider.setDiagnostics(
                            payload.diagnostics
                        );
                } catch (error) {
                    tabSurfaceProvider.errorText =
                        "TAB SCAN PARSE: " + String(error);
                }

                tabSurfaceProvider.loading = false;
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0)
                    tabSurfaceProvider.errorText = message;

                tabSurfaceProvider.loading = false;
            }
        }
    }

    Process {
        id: appTabsActivateProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0)
                    console.log(
                        "TabSurfaceProvider activation:",
                        message
                    );

                tabSurfaceProvider.activationFinished(true, message);
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0) {
                    console.log(
                        "TabSurfaceProvider activation error:",
                        message
                    );
                    tabSurfaceProvider.activationFinished(false, message);
                }
            }
        }
    }

    Timer {
        id: appTabsWarmRefreshTimer
        interval: 850
        repeat: false
        onTriggered: {
            if (tabSurfaceProvider.active)
                tabSurfaceProvider.refresh();
        }
    }

    Timer {
        id: appTabsSecondWarmRefreshTimer
        interval: 1800
        repeat: false
        onTriggered: {
            if (tabSurfaceProvider.active)
                tabSurfaceProvider.refresh();
        }
    }

    Timer {
        id: appTabsRefreshTimer
        interval: 2200
        repeat: true
        running:
            tabSurfaceProvider.active
            && !tabSurfaceProvider.bridgeReady
        onTriggered: tabSurfaceProvider.refresh()
    }
}
