import QtQuick
import Quickshell

// M28-B disposable news test service, never installed in live Weather.
Scope {
    property string domain: "map"
    property string mapCategory: ""
    property bool active: true
    property bool ready: domain === "news"
    property bool usingCache: false
    property bool failed: false
    property bool loading: false
    property string errorText: ""
    property date lastUpdated: new Date()
    property double sourceClockMs: Date.now()
    property int retryWaitSeconds: 0
    property bool canRetry: true
    property var rows: domain === "news" ? [
        {
            title:"M28B SYNTHETIC WEATHER REPORT",
            url:"https://example.invalid/m28b/weather",
            domain:"synthetic.invalid",
            country:"United States",
            language:"English",
            detail:"SYNTHETIC SOURCE // UNITED STATES // ENGLISH",
            time:"2026-11-03 10:00 UTC",
            rawTime:"20261103100000",
            seenMillis:Date.now()-60000,
            topics:["weather"],
            primaryTopic:"weather",
            sourceGroup:{
                articleCount:1,sourceCount:1,multiSource:false,
                domains:["synthetic.invalid"],countries:["United States"],
                languages:["English"]
            }
        },
        {
            title:"M28B SYNTHETIC SKY REPORT",
            url:"https://example.invalid/m28b/sky",
            domain:"synthetic.invalid",
            country:"United States",
            language:"English",
            detail:"SYNTHETIC SOURCE // UNITED STATES // ENGLISH",
            time:"2026-11-03 10:01 UTC",
            rawTime:"20261103100100",
            seenMillis:Date.now()-120000,
            topics:["sky"],
            primaryTopic:"sky",
            sourceGroup:{
                articleCount:1,sourceCount:1,multiSource:false,
                domains:["synthetic.invalid"],countries:["United States"],
                languages:["English"]
            }
        }
    ] : []
    function refresh(manual) {return false;}
}
