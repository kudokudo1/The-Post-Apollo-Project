#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
const company=fs.readFileSync(path.join(root,"widgets/CompanyNetworkW.qml"),"utf8");
const coverage=fs.readFileSync(path.join(root,"widgets/CompanyCoveragePane.qml"),"utf8");
const controller=fs.readFileSync(path.join(root,"services/company/CompanyVectorSidecarController.qml"),"utf8");

test("Company publishes exact discovery namespace only on its existing native layer",()=>{
  assert.match(company,/WlrLayershell\.namespace:\s*"post-apollo-company-network"/);
  assert.equal((company.match(/WlrLayershell\.namespace:/g)||[]).length,1);
  assert.match(company,/WlrLayershell\.layer:\s*WlrLayer\.Overlay/);
  assert.match(company,/WlrLayershell\.keyboardFocus:\s*\n?\s*menuOpen \? WlrKeyboardFocus\.OnDemand : WlrKeyboardFocus\.None/);
  assert.match(company,/mask:\s*Region\s*\{/);
  assert.match(company,/visible:\s*true/);
});

test("namespace is not treated as trust or a compositor actor permission",()=>{
  assert.match(company,/This string is NOT authentication/);
  assert.match(company,/readonly property rect activeVectorViewportRect:/);
  assert.match(company,/readonly property bool activeVectorViewportValid:/);
  assert.match(coverage,/CompanyVectorSidecarController\s*\{/);
  assert.match(controller,/vectorRunner\.running=false/);
  for(const code of [company,coverage,controller]){
    assert.doesNotMatch(code,/WatchBridge\s*\{/);
    assert.doesNotMatch(code,/import PostApollo\.StageDirector/);
    assert.doesNotMatch(code,/wl_display_connect|stage_director_company_map_probe/);
  }
});
