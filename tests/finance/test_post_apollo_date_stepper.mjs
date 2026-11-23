import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const root=new URL("../../",import.meta.url);
function file(path){return readFileSync(new URL(path,root),"utf8");}
const tasks=file("widgets/tasks/TaskDateSegments.js");
const scope=vm.createContext({Date});
vm.runInContext(tasks.replace(/^\.pragma library\s*/,""),scope);

assert.equal(scope.format({year:2026,month:11,day:23}),"2026-11-23");
assert.equal(scope.parse("2024-02-29").day,29);
assert.equal(scope.parse("2023-02-29"),null);
assert.equal(scope.parse("2026-13-01"),null);
assert.equal(scope.parse("2026-11-31"),null);
assert.equal(scope.step("2024-01-31","month",1),"2024-02-29");
assert.equal(scope.step("2024-02-29","year",1),"2025-02-28");
assert.equal(scope.step("2026-12-31","day",1),"2027-01-01");
assert.equal(scope.step("2026-01-01","day",-1),"2025-12-31");
assert.equal(scope.step("2026-12-31","month",1),"2027-01-31");
assert.equal(scope.step("2026-01-31","month",-1),"2025-12-31");
assert.equal(scope.setPart("2024-02-29","year","2025").date,"2025-02-28");
assert.equal(scope.setPart("2024-02-29","month","4").date,"2024-04-29");
assert.equal(scope.setPart("2026-02-28","day","31").date,"2026-02-28");
assert.equal(scope.setPart("2026-11-23","year","99999").accepted,false);
assert.equal(scope.step("2026-11-23","day",2),"2026-11-23");
assert.equal(scope.step("9999-12-31","day",1),"9999-12-31");

const segment=file("widgets/tasks/TaskDateSegment.qml");
assert(segment.includes('signal stepRequested(string part, int direction)'));
assert(segment.includes('signal editCommitted(string part, string value)'));
assert(segment.includes('Keys.onUpPressed:'));
assert(segment.includes('Keys.onDownPressed:'));
assert(segment.includes('onClicked: segment.stepRequested(segment.part, modelData)'));
const shared=file("widgets/PostApolloDateStepper.qml");
assert(shared.includes('import "tasks" as TaskFields'));
assert(shared.includes('import "tasks/TaskDateSegments.js" as Segments'));
assert.equal((shared.match(/TaskFields\.TaskDateSegment \{/g)||[]).length,3);
assert(shared.includes('Segments.setPart(base,part,value)'));
assert(shared.includes('Segments.step(base,part,direction)'));
assert(shared.includes('Segments.part(picker.dateValue,"month")'));
assert(shared.includes('Segments.part(picker.dateValue,"day")'));
assert(shared.includes('Segments.part(picker.dateValue,"year")'));
assert(shared.includes('signal dateEdited(string isoDate)'));
assert(shared.includes('property bool useUtcToday: false'));
assert(shared.includes('property string minDate: "0001-01-01"'));
assert(shared.includes('property string maxDate: "9999-12-31"'));
assert(shared.includes('if(dateWithinBounds(dateValue))return dateValue;'));
assert(shared.includes('if(dateWithinBounds(fallbackDate))return fallbackDate;'));
assert(shared.includes('return dateWithinBounds(minDate) ? minDate : "";'));
assert(shared.includes('const today = todayDate();'));
assert(shared.includes('if(dateValue!=="")dateEdited("");'));
assert(shared.includes('if(candidate !== dateValue)dateEdited(candidate);'));
assert(shared.includes('onLeftClicked: picker.setToday()'));
assert(shared.includes('onLeftClicked: picker.clearDate()'));
assert.equal((shared.match(/ActionButton \{/g)||[]).length,2);
assert(!shared.includes('Component.onCompleted:'));
assert(!shared.includes('Timer {'));
assert(!shared.includes('↑')&&!shared.includes('↓'),"Shared wrapper must reuse Tasks arrows, not redraw them");
for(const forbidden of ['Process {','FileView {','XMLHttpRequest','fetch(','WebSocket',
    'LocalStorage','Qt.openUrlExternally','writeFile(','onPaymentSent','Quickshell.Io'])
    assert(!shared.includes(forbidden),forbidden);

const banking=file("widgets/FinanceBankingProviderPane.qml");
assert.equal((banking.match(/PostApolloDateStepper \{/g)||[]).length,2);
for(const field of ['activityFromDate','activityToDate']) {
    assert(banking.includes('property string '+field+': ""'));
    assert(banking.includes('dateValue: providerPane.'+field));
    assert(banking.includes('providerPane.'+field+'=isoDate;'));
    assert(banking.includes('on'+field[0].toUpperCase()+field.slice(1)+'Changed: {'));
    assert(!banking.includes('id: '+field),"Old raw text inputs must be removed");
}
assert(banking.includes('minDate: "1900-01-01"'));
assert(banking.includes('maxDate: "2100-12-31"'));
assert(banking.includes('fromDate:activityFromDate,toDate:activityToDate'));
assert(banking.includes('providerPane.activityPageIndex=0;'));
assert(banking.includes('providerPane.clearSelectedEntry();'));
assert(banking.includes('CLEAR ACTIVITY DATE RANGE'));
assert(banking.includes('providerPane.filteredActivity.error'));
assert(banking.includes('providerPane.filteredActivity.accountBreakdown'));
assert(banking.includes('signal manualCorrectionRequested(var draft)'));
assert(banking.includes('signal manualDeletionRequested(var draft)'));
console.log("PostApolloDateStepper: actual Tasks arrows and civil date math, Today/Clear, bounds and Banking two-field reuse PASS");
