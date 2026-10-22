// Test-only ESM interception. Never imports a real Actual package.
export function resolve(specifier, context, nextResolve) {
  if (specifier === "@actual-app/api") {
    return {url: new URL("./write_cli_actual_stub.mjs", import.meta.url).href,
      shortCircuit: true};
  }
  return nextResolve(specifier, context);
}
