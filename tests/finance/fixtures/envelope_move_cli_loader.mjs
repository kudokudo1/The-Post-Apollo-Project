// Test-only ESM interception. The writer never imports a real Actual package
// in these isolated CLI tests and cannot connect to a financial server.
export function resolve(specifier,context,nextResolve) {
  if(specifier==="@actual-app/api")
    return {url:new URL("./envelope_move_cli_actual_stub.mjs",import.meta.url).href,
      shortCircuit:true};
  return nextResolve(specifier,context);
}
