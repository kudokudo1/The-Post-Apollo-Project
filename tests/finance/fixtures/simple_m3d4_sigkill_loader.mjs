// M3d4 disposable CI-only loader. It pauses the M3b policy function at an
// exact checkpoint so the parent can SIGKILL the real writer process.
// No production file is edited. A modified in-memory module is used only in
// the child launched with --experimental-loader by the CI-only harness.
const target="/scripts/finance/categorized_expense_guard.mjs";
const markerAttempt="  await recordAttempt(cmd);";
const markerAdd="  await api.sync();";
const pause=point=>`  {
    if (process.env.FINANCEW_M3D4_POINT !== "${point}")
      throw new Error("m3d4-disposable-checkpoint-mismatch");
    const path = process.env.FINANCEW_M3D4_BARRIER;
    if (typeof path !== "string" || !path.endsWith("/m3d4-barrier"))
      throw new Error("m3d4-invalid-barrier");
    const { writeFile } = await import("node:fs/promises");
    await writeFile(path, "${point}\\n", {flag:"wx",mode:0o600});
    // Hold a Node event-loop handle. Only the CI parent issues SIGKILL.
    await new Promise(() => { setInterval(() => {}, 1000); });
  }`;
export async function load(url,context,nextLoad){
  const result=await nextLoad(url,context);
  if(!url.endsWith(target))return result;
  if(process.env.GITHUB_ACTIONS!=="true" || process.env.CI!=="true"
     || process.env.FINANCEW_DISPOSABLE_TEST!=="yes")
    throw new Error("m3d4-CI-only-loader");
  const point=process.env.FINANCEW_M3D4_POINT;
  if(point!=="after-attempt" && point!=="after-add")
    throw new Error("m3d4-invalid-checkpoint");
  const source=typeof result.source==="string" ? result.source
    : Buffer.from(result.source).toString("utf8");
  const original=point==="after-attempt"?markerAttempt:markerAdd;
  if(source.indexOf(original)<0 || source.indexOf(original)!==source.lastIndexOf(original))
    throw new Error("m3d4-expected-single-policy-checkpoint");
  const replacement=point==="after-attempt"
    ? original+"\n"+pause(point)
    : pause(point)+"\n"+original;
  return {...result,source:source.replace(original,replacement)};
}
