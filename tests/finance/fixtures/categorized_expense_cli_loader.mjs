// FICTIONAL CLI TEST ONLY. The writer cannot import @actual-app/api or
// connect to an Actual server in these tests.
export function resolve(specifier,context,nextResolve) {
  if(specifier==="@actual-app/api")
    return {url:new URL("./categorized_expense_cli_actual_stub.mjs",
      import.meta.url).href,shortCircuit:true};
  return nextResolve(specifier,context);
}