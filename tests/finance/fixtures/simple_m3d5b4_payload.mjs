// Pure fictional Actual-style snapshot, never imported by product code.
import {createHash} from "node:crypto";
import {normalizeSnapshot} from "../../../scripts/finance/actual_readonly.mjs";
export const url="http://127.0.0.1:5006";
export const syncId="fictional-m3d5b4-sync-9876";
export const sourceKey=createHash("sha256")
  .update(url+"\0"+syncId).digest("hex");
export const sourceOptions={
  readerEndpoint:url,writerEndpoint:url,writerSourceKey:sourceKey
};
export function makeView(){
  const month="2026-11";
  const snapshot=normalizeSnapshot({
    month,budget:{toBudget:12000,categoryGroups:[
      {id:"needs",name:"Needs",is_income:false,hidden:false,categories:[
        {id:"groceries",name:"Groceries",hidden:false,
          budgeted:10000,balance:7500,spent:-2500}
      ]}
    ]},
    accounts:[{id:"fictional-checking",name:"Checking",offbudget:false,closed:false}],
    balances:new Map([["fictional-checking",42000]]),
    transactionSets:new Map([["fictional-checking",[]]]),payees:[]
  });
  snapshot.sourceKey=sourceKey;
  const candidate={action:"create",editing:false,direction:"expense",
    sourceKey,month,accountId:"fictional-checking",date:"2026-11-25",
    description:"Imaginary Groceries",amountCents:-1250};
  const proposal={ok:true,readOnly:true,writeAllowed:false,savesToActual:false,
    sourceKey,month,accountId:"fictional-checking",
    date:"2026-11-25",description:"Imaginary Groceries",
    expenseAmountCents:-1250,categoryId:"groceries",
    categoryName:"Groceries",groupId:"needs",groupName:"Needs",
    availableBeforeCents:7500,spentBeforeCents:-2500,
    estimatedAvailableAfterCents:6250,estimatedSpentAfterCents:-3750,
    estimatedOverspent:false,toBudgetAfterCents:null};
  return {snapshot,candidate,proposal,selectedCategoryId:"groceries"};
}
