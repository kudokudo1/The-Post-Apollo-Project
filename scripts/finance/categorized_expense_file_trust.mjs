// FinanceW Simple M3b security-revise // Linux descriptor-anchored trust boundary.
// Every path component opens without symlink following and is verified with
// fstat. Children are opened through /proc/self/fd/<parent fd> so a path-swap
// between validating a directory and opening its child cannot redirect access.
// Do not use this helper outside the dormant categorized writer without review.
import {open,mkdir} from "node:fs/promises";
import {constants as fsConstants} from "node:fs";
import {dirname,isAbsolute,resolve} from "node:path";

const DIR_FLAGS=fsConstants.O_RDONLY|fsConstants.O_DIRECTORY
  |fsConstants.O_NOFOLLOW|fsConstants.O_NONBLOCK;
const FILE_FLAGS=fsConstants.O_RDONLY|fsConstants.O_NOFOLLOW
  |fsConstants.O_NONBLOCK;
const uid=typeof process.getuid==="function"?process.getuid():null;
export class FinanceFileTrustRefusal extends Error {
  constructor(code){super(code);this.code=code;}
}
const refuse=code=>{throw new FinanceFileTrustRefusal(code);};
function childPath(dir,name){
  if(typeof name!=="string" || !/^[A-Za-z0-9._-]+$/.test(name)
      ||name==="." ||name==="..")refuse("unsafe-path-component");
  return "/proc/self/fd/"+dir.fd+"/"+name;
}
function checkDir(st,{privateLeaf=false}={}){
  if(!st.isDirectory() || uid===null || (st.uid!==uid && st.uid!==0))
    refuse("untrusted-directory");
  const writable=(st.mode & 0o022)!==0;
  // Linux /tmp and /var/tmp: root-owned sticky directories protect named
  // entries from other users despite world-writable directory permissions.
  const safeSticky=st.uid===0 && (st.mode & 0o1000)!==0;
  if(writable && !safeSticky)refuse("untrusted-directory");
  if(privateLeaf && (st.uid!==uid || (st.mode & 0o077)!==0))
    refuse("untrusted-private-directory");
}
function checkFile(st){
  if(!st.isFile() || uid===null || st.uid!==uid || st.nlink!==1
      ||(st.mode & 0o077)!==0 || st.size>8192)
    refuse("unsafe-private-file");
}
// Walk from the root, using each just-opened parent descriptor. Never follow
// an intermediate symlink. Create only missing components below trusted roots.
// Callers own the returned open directory and must close it.
export async function openTrustedDirectory(path,{create=false,privateLeaf=false}={}){
  if(typeof path!=="string" || !isAbsolute(path) || resolve(path)!==path)
    refuse("unsafe-directory-path");
  let handle=await open("/",DIR_FLAGS);
  try {
    checkDir(await handle.stat());
    const parts=path.split("/").filter(Boolean);
    if(privateLeaf && parts.length===0)refuse("unsafe-directory-path");
    for(let i=0;i<parts.length;i++){
      const candidate=childPath(handle,parts[i]);
      if(create){
        try{await mkdir(candidate,{mode:0o700});}
        catch(e){if(e?.code!=="EEXIST")throw e;}
      }
      const next=await open(candidate,DIR_FLAGS);
      try{checkDir(await next.stat(),{
        privateLeaf:privateLeaf && i===parts.length-1
      });}
      catch(e){await next.close();throw e;}
      await handle.close();
      handle=next;
    }
    return handle;
  } catch(error) {
    await handle.close();
    throw error;
  }
}
export function dirEntryPath(dir,name){return childPath(dir,name);}
export async function readPrivateEntry(dir,name){
  const handle=await open(childPath(dir,name),FILE_FLAGS);
  try{
    checkFile(await handle.stat());
    return (await handle.readFile("utf8")).trim();
  }finally{await handle.close();}
}
export async function readTrustedPrivateFile(path){
  const dir=await openTrustedDirectory(dirname(path),{privateLeaf:true});
  try {
    return await readPrivateEntry(dir,path.slice(dirname(path).length+1));
  }finally{await dir.close();}
}
