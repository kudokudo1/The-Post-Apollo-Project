// Banking M4d // fixed official homepages for explicit, user-initiated handoff.
// No credentials, account IDs, amounts, section paths, query strings or deep links.
// These destinations are not proof that any feature is available on the website.
// Sources checked 2026-11-23: https://cash.app/, https://www.chime.com/,
// https://www.paypal.com/. Refresh this verification before expanding the set.
var OFFICIAL = {
    cashapp: {name:"Cash App",host:"cash.app",url:"https://cash.app/"},
    chime: {name:"Chime",host:"www.chime.com",url:"https://www.chime.com/"},
    paypal: {name:"PayPal",host:"www.paypal.com",url:"https://www.paypal.com/"}
};
// Only restricted sections can offer a provider handoff. HOME, ACTIVITY
// and locally supported product views stay inside Post-Apollo.
var RESTRICTED = {
    cashapp:["payments","card","stocks","borrow","savings","security"],
    chime:["card","transfers","credit","security"],
    paypal:["payments","cards","savings","paylater","security"]
};
function destination(providerId,sectionId) {
    if(typeof providerId!=="string"||typeof sectionId!=="string")
        return {ok:false,reason:"UNSUPPORTED PROVIDER"};
    if(!Object.prototype.hasOwnProperty.call(OFFICIAL,providerId)
       ||!Object.prototype.hasOwnProperty.call(RESTRICTED,providerId))
        return {ok:false,reason:providerId==="bank"
            ?"NO VERIFIED BANK DESTINATION // USE YOUR BANK'S KNOWN OFFICIAL CHANNEL"
            :"NO HANDOFF AVAILABLE FOR THIS PROVIDER"};
    var site=OFFICIAL[providerId],sections=RESTRICTED[providerId];
    if(!site||!sections||sections.indexOf(sectionId)<0)
        return {ok:false,reason:providerId==="bank"
            ?"NO VERIFIED BANK DESTINATION // USE YOUR BANK'S KNOWN OFFICIAL CHANNEL"
            :"NO HANDOFF AVAILABLE FOR THIS FEATURE"};
    return {ok:true,providerId:providerId,sectionId:sectionId,
        providerName:site.name,host:site.host,url:site.url,
        kind:"official-homepage",requiresConfirmation:true,
        passesCredentials:false,executesFinancialAction:false};
}
// A simple fail-closed final check immediately before delegating to Qt.
// QML passes the exact object produced by destination, not a typed URL.
function canOpen(decision,providerId,sectionId) {
    var expected=destination(providerId,sectionId);
    return expected.ok===true && !!decision && decision.ok===true
        &&decision.providerId===providerId
        &&decision.sectionId===sectionId
        &&decision.url===expected.url
        &&decision.host===expected.host
        &&decision.kind==="official-homepage"
        &&decision.requiresConfirmation===true
        &&decision.passesCredentials===false
        &&decision.executesFinancialAction===false;
}
