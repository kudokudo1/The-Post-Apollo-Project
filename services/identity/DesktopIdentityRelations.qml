import QtQuick

// Team 7 — non-resolving cross-provider relation layer.
//
// This component converts observations into inspectable relationship evidence.
// It deliberately does NOT construct an ApplicationEntity, assign a semantic
// application key, choose a winning DesktopEntry, or mutate provider state.
QtObject {
    id: relations

    readonly property DesktopIdentityEvidence evidence:
        DesktopIdentityEvidence {}

    readonly property string relationAliasExact: "ALIAS_EXACT"
    readonly property string relationTokenNormalized: "TOKEN_NORMALIZED_MATCH"
    readonly property string relationTokenSuffix: "TOKEN_SUFFIX_HEURISTIC"
    readonly property string relationDebugPortOwner: "EXACT_DEBUG_PORT_OWNER"

    function asText(value) {
        return value === undefined || value === null
               ? ""
               : String(value);
    }

    function coordinate(provider, providerKey) {
        const source = asText(provider);
        const key = asText(providerKey);

        return source && key ? source + "|" + key : "";
    }

    function observationCoordinate(observation) {
        if (!observation)
            return "";

        return coordinate(
            observation.provider,
            observation.providerKey
        );
    }

    function edge(left, right, kind, strength, sourceField, details) {
        return {
            leftProvider: asText(left && left.provider),
            leftKey: asText(left && left.providerKey),
            rightProvider: asText(right && right.provider),
            rightKey: asText(right && right.providerKey),
            kind: asText(kind),
            strength: strength === evidence.strengthExact
                      ? evidence.strengthExact
                      : evidence.strengthHeuristic,
            sourceField: asText(sourceField),
            details: details || ({})
        };
    }

    function edgeKey(value) {
        if (!value)
            return "";

        return [
            value.leftProvider,
            value.leftKey,
            value.rightProvider,
            value.rightKey,
            value.kind,
            value.sourceField,
            asText(value.details && value.details.leftAliasKind),
            asText(value.details && value.details.rightAliasKind)
        ].join("\u001f");
    }

    function pushUniqueEdge(target, seen, value) {
        if (!value)
            return;

        const key = edgeKey(value);

        if (!key || seen[key])
            return;

        seen[key] = true;
        target.push(value);
    }

    function observationIndex(observations) {
        const source = Array.isArray(observations)
                     ? observations
                     : [];
        const index = ({});

        for (let i = 0; i < source.length; i++) {
            const item = source[i];
            const key = observationCoordinate(item);

            if (key && !index[key])
                index[key] = item;
        }

        return index;
    }

    // Provider-declared relationships are materialized only when the target
    // observation is present. A dangling relation remains visible on the source
    // observation and is not silently promoted into a fabricated object.
    function explicitEdges(observations) {
        const source = Array.isArray(observations)
                     ? observations
                     : [];
        const index = observationIndex(source);
        const result = [];
        const seen = ({});

        for (let i = 0; i < source.length; i++) {
            const item = source[i];
            const declared = Array.isArray(item && item.relationships)
                           ? item.relationships
                           : [];

            for (let j = 0; j < declared.length; j++) {
                const relation = declared[j] || ({});
                const target = index[
                    coordinate(
                        relation.targetProvider,
                        relation.targetKey
                    )
                ];

                if (!target)
                    continue;

                pushUniqueEdge(
                    result,
                    seen,
                    edge(
                        item,
                        target,
                        relation.kind,
                        relation.strength,
                        relation.sourceField,
                        {
                            provenance: "provider-declared"
                        }
                    )
                );
            }
        }

        return result;
    }

    function addPid(target, value, sourceField) {
        const pid = evidence.positivePid(value);

        if (pid <= 1)
            return;

        for (let i = 0; i < target.length; i++) {
            if (target[i].pid === pid
                    && target[i].sourceField === sourceField)
                return;
        }

        target.push({
            pid: pid,
            sourceField: sourceField
        });
    }

    // Extracts raw PID attachments without deciding what application owns the
    // process. Team 6's PIPEWIRE observation is intentionally supported here
    // even though it has no Team-7-generated relationship array.
    function pidAttachments(observation) {
        if (!observation)
            return [];

        const raw = observation.raw || ({});
        const result = [];

        addPid(result, raw.pid, "raw.pid");
        addPid(
            result,
            raw.applicationProcessId,
            "raw.applicationProcessId"
        );

        const processPids = Array.isArray(raw.processPids)
                          ? raw.processPids
                          : [];

        for (let i = 0; i < processPids.length; i++)
            addPid(result, processPids[i], "raw.processPids");

        const declared = Array.isArray(observation.relationships)
                       ? observation.relationships
                       : [];

        for (let i = 0; i < declared.length; i++) {
            const relation = declared[i] || ({});

            if (asText(relation.targetProvider) !== "PROCFS")
                continue;

            const key = asText(relation.targetKey);

            if (key.indexOf("pid:") !== 0)
                continue;

            addPid(
                result,
                Number(key.substring(4)),
                "relationship:" + asText(relation.kind)
            );
        }

        return result;
    }

    // Shared PID evidence is represented as one group, not a pairwise clique.
    // This prevents one underlying PID fact from looking like several
    // independent confirmations merely because many providers observed it.
    function pidGroups(observations) {
        const source = Array.isArray(observations)
                     ? observations
                     : [];
        const groups = ({});

        for (let i = 0; i < source.length; i++) {
            const item = source[i];
            const attachments = pidAttachments(item);
            const itemCoordinate = observationCoordinate(item);

            if (!itemCoordinate)
                continue;

            for (let j = 0; j < attachments.length; j++) {
                const attachment = attachments[j];
                const pidKey = String(attachment.pid);

                if (!groups[pidKey]) {
                    groups[pidKey] = {
                        pid: attachment.pid,
                        evidenceFamily: "pid",
                        members: []
                    };
                }

                let exists = false;

                for (let k = 0; k < groups[pidKey].members.length; k++) {
                    const member = groups[pidKey].members[k];

                    if (member.coordinate === itemCoordinate) {
                        exists = true;

                        if (member.sourceFields.indexOf(
                                attachment.sourceField
                            ) === -1) {
                            member.sourceFields.push(
                                attachment.sourceField
                            );
                        }

                        break;
                    }
                }

                if (!exists) {
                    groups[pidKey].members.push({
                        coordinate: itemCoordinate,
                        provider: asText(item.provider),
                        providerKey: asText(item.providerKey),
                        sourceFields: [attachment.sourceField]
                    });
                }
            }
        }

        const result = [];
        const keys = Object.keys(groups);

        for (let i = 0; i < keys.length; i++) {
            const group = groups[keys[i]];

            if (group.members.length >= 2)
                result.push(group);
        }

        result.sort(function(left, right) {
            return left.pid - right.pid;
        });

        return result;
    }

    function processOwnsDebugPort(processObservation, port) {
        if (!processObservation
                || asText(processObservation.provider) !== "PROCFS")
            return false;

        const wanted = Number(port || 0);

        if (wanted <= 0)
            return false;

        const raw = processObservation.raw || ({});
        const args = asText(raw.args);
        const tokens = args.split(/\s+/);
        const equalForm = "--remote-debugging-port="
                        + String(wanted);

        for (let i = 0; i < tokens.length; i++) {
            if (tokens[i] === equalForm)
                return true;

            if (tokens[i] === "--remote-debugging-port"
                    && i + 1 < tokens.length
                    && Number(tokens[i + 1]) === wanted)
                return true;
        }

        return false;
    }

    // The command line's explicit debug-port flag is strong process ownership
    // evidence. It still does not imply that the surface and process are the
    // complete semantic application.
    function debugPortEdges(observations) {
        const source = Array.isArray(observations)
                     ? observations
                     : [];
        const result = [];
        const seen = ({});

        for (let i = 0; i < source.length; i++) {
            const surface = source[i];
            const raw = surface && surface.raw || ({});
            const port = Number(raw.debugPort || 0);

            if (port <= 0)
                continue;

            for (let j = 0; j < source.length; j++) {
                const process = source[j];

                if (!processOwnsDebugPort(process, port))
                    continue;

                pushUniqueEdge(
                    result,
                    seen,
                    edge(
                        surface,
                        process,
                        relationDebugPortOwner,
                        evidence.strengthExact,
                        "raw.debugPort<->raw.args",
                        {
                            debugPort: port,
                            evidenceFamily: "debug-port"
                        }
                    )
                );
            }
        }

        return result;
    }

    function rawComparable(value) {
        return asText(value).trim().toLowerCase();
    }

    function aliasPairEvidence(leftObservation, leftAlias,
                               rightObservation, rightAlias) {
        if (!leftAlias || !rightAlias)
            return null;

        const leftRaw = rawComparable(leftAlias.value);
        const rightRaw = rawComparable(rightAlias.value);

        if (!leftRaw || !rightRaw)
            return null;

        const details = {
            evidenceFamily: "alias",
            leftAliasKind: asText(leftAlias.kind),
            leftRaw: asText(leftAlias.value),
            rightAliasKind: asText(rightAlias.kind),
            rightRaw: asText(rightAlias.value)
        };

        if (leftRaw === rightRaw) {
            return edge(
                leftObservation,
                rightObservation,
                relationAliasExact,
                evidence.strengthExact,
                "aliases",
                details
            );
        }

        const leftToken = asText(
            leftAlias.normalized
            || evidence.normalizeToken(leftAlias.value)
        );
        const rightToken = asText(
            rightAlias.normalized
            || evidence.normalizeToken(rightAlias.value)
        );

        if (!leftToken || !rightToken)
            return null;

        if (leftToken === rightToken && leftToken.length >= 4) {
            return edge(
                leftObservation,
                rightObservation,
                relationTokenNormalized,
                evidence.strengthHeuristic,
                "aliases.normalized",
                details
            );
        }

        const shorter = Math.min(
            leftToken.length,
            rightToken.length
        );

        if (shorter < 4)
            return null;

        if (leftToken.endsWith(rightToken)
                || rightToken.endsWith(leftToken)) {
            return edge(
                leftObservation,
                rightObservation,
                relationTokenSuffix,
                evidence.strengthHeuristic,
                "aliases.normalized",
                details
            );
        }

        return null;
    }

    // Alias evidence is intentionally exhaustive within the supplied fixture.
    // Nothing here converts a match into a winner.
    function aliasEdges(observations) {
        const source = Array.isArray(observations)
                     ? observations
                     : [];
        const result = [];
        const seen = ({});

        for (let i = 0; i < source.length; i++) {
            const left = source[i];

            if (!observationCoordinate(left))
                continue;

            const leftAliases = Array.isArray(left.aliases)
                              ? left.aliases
                              : [];

            for (let j = i + 1; j < source.length; j++) {
                const right = source[j];

                if (!observationCoordinate(right)
                        || asText(left.provider)
                        === asText(right.provider))
                    continue;

                const rightAliases = Array.isArray(right.aliases)
                                   ? right.aliases
                                   : [];

                for (let a = 0; a < leftAliases.length; a++) {
                    for (let b = 0; b < rightAliases.length; b++) {
                        pushUniqueEdge(
                            result,
                            seen,
                            aliasPairEvidence(
                                left,
                                leftAliases[a],
                                right,
                                rightAliases[b]
                            )
                        );
                    }
                }
            }
        }

        return result;
    }

    function relationSnapshot(observations) {
        return {
            explicitEdges: explicitEdges(observations),
            pidGroups: pidGroups(observations),
            debugPortEdges: debugPortEdges(observations),
            aliasEdges: aliasEdges(observations)
        };
    }
}
