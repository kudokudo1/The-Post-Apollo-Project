// Fictional finance child process, not a production FinanceW entrypoint.
// Input comes via stdin; never argv. Prints only non-sensitive status.
import {reserveM3d5b2DisposableIntent}
  from "../../../scripts/finance/simple_m3d5b2_disposable_transport.mjs";
let raw="";
for await(const chunk of process.stdin){
  raw+=chunk;
  if(raw.length>4096)throw Error("fixture-input-too-large");
}
const {sandboxRoot,command}=JSON.parse(raw);
const out=await reserveM3d5b2DisposableIntent({sandboxRoot,command});
process.stdout.write(JSON.stringify(out)+"\n");
