// Isolated test-only Actual interception. No network or real budget.
export function resolve(specifier,context,nextResolve) {
  if(specifier==="@actual-app/api")return {
    url:new URL("./category_cli_stub.mjs",import.meta.url).href,
    shortCircuit:true
  };
  return nextResolve(specifier,context);
}
