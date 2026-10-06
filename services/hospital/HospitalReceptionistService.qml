import QtQuick

QtObject {
    id: root

    property var transcript: [
        {
            sender: "RECEPTION",
            body: "Front desk online. I can route you to Surgery, Reports, Rounds, Staff, Phone, or Intercom."
        }
    ]

    signal routeRequested(string route)

    function append(sender, body) {
        const next = transcript.concat([{
            sender: String(sender || ""),
            body: String(body || "")
        }]);

        transcript = next.length > 40
            ? next.slice(next.length - 40)
            : next;
    }

    function request(route, operatorText) {
        const target = String(route || "").toLowerCase();

        if (operatorText)
            append("OPERATOR", operatorText);

        let response = "";

        if (target === "surgery")
            response = "Routing to Surgery.";
        else if (target === "reports")
            response = "Opening surgical history and evidence.";
        else if (target === "rounds")
            response = "Opening Hospital-wide rounds.";
        else if (target === "staff")
            response = "Opening the specialist registry.";
        else if (target === "phone")
            response = "Opening Phone.";
        else if (target === "intercom")
            response = "Opening Intercom.";
        else {
            append(
                "RECEPTION",
                "I can route Surgery, Reports, Rounds, Staff, Phone, or Intercom."
            );
            return false;
        }

        append("RECEPTION", response);
        routeRequested(target);
        return true;
    }

    function submit(text) {
        const raw = String(text || "").trim();

        if (!raw)
            return false;

        const query = raw.toLowerCase();

        if (query.indexOf("intercom") >= 0
                || query.indexOf("message") >= 0
                || query.indexOf("talk to") >= 0)
            return request("intercom", raw);

        if (query.indexOf("phone") >= 0
                || query.indexOf("call") >= 0
                || query.indexOf("dial") >= 0)
            return request("phone", raw);

        if (query.indexOf("report") >= 0
                || query.indexOf("history") >= 0
                || query.indexOf("evidence") >= 0
                || query.indexOf("clipboard") >= 0)
            return request("reports", raw);

        if (query.indexOf("round") >= 0
                || query.indexOf("attention") >= 0
                || query.indexOf("bell") >= 0
                || query.indexOf("hospital wide") >= 0)
            return request("rounds", raw);

        if (query.indexOf("staff") >= 0
                || query.indexOf("specialist") >= 0
                || query.indexOf("codex") >= 0
                || query.indexOf("hermes") >= 0)
            return request("staff", raw);

        if (query.indexOf("surgery") >= 0
                || query.indexOf("room") >= 0
                || query.indexOf("patient") >= 0)
            return request("surgery", raw);

        append("OPERATOR", raw);
        append(
            "RECEPTION",
            "I don't have authority to improvise that action. Ask for Surgery, Reports, Rounds, Staff, Phone, or Intercom."
        );
        return false;
    }
}
