'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const storage=new Map(),notices=[],calls=[];
const context=vm.createContext({token:null,role:'klient',checkoutOwner:1,sessionEpoch:1,
 crypto:require('crypto').webcrypto,sessionStorage:{getItem:k=>storage.has(k)?storage.get(k):null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
 el:()=>null,msg:text=>notices.push(text),api:async(...args)=>{calls.push(args);return {outcome:'released'};}});
vm.runInContext(fs.readFileSync('web/wallet.js','utf8'),context);
vm.runInContext("refreshWallet=async()=>{};token='synthetic-token'",context);
const run=source=>vm.runInContext(source,context),key=run("walletIntentKey(1,'topup')");
const original={amount_grosze:10000,request_key:'original-intent-001'};
async function main(){
 const which=process.argv[2];
 if(which==='malformed'){
  storage.set(key,'{invalid');assert.throws(()=>run("walletIntent(1,'topup',5000)"));assert.equal(storage.get(key),'{invalid');
 }else if(which==='invalid_amount'){
  for(const amount of [true,0,-1,1.5,100000001]){storage.set(key,JSON.stringify({...original,amount_grosze:amount}));assert.throws(()=>run("walletIntent(1,'topup',5000)"));}
 }else if(which==='extra_fields'){
  storage.set(key,JSON.stringify({...original,pin:'never-copy',user_id:9}));
  assert.deepEqual(JSON.parse(JSON.stringify(run("readWalletIntent(1,'topup')"))),original);
 }else if(which==='changed_amount'){
  storage.set(key,JSON.stringify(original));assert.throws(()=>run("walletIntent(1,'topup',5000)"));assert.equal(storage.get(key),JSON.stringify(original));
 }else if(which==='late_clear'){
  storage.set(key,JSON.stringify({...original,request_key:'new-intent-000002'}));run("clearWalletIntent(1,'topup','original-intent-001')");assert.ok(storage.has(key));
  run("clearWalletIntent(1,'topup','new-intent-000002')");assert.equal(storage.has(key),false);
 }else if(which==='other_active'){
  storage.set(key,JSON.stringify(original));run("walletBusy=true;walletActiveIntent={owner:1,kind:'withdraw',request_key:'different-request-01'}");
  await run("recoverWalletIntent(1,'topup',()=>true,{disabled:false})");assert.equal(calls.length,0);assert.equal(run('walletBusy'),true);
 }else if(which==='matching_active'){
  storage.set(key,JSON.stringify(original));run("walletBusy=true;walletActiveIntent={owner:1,kind:'topup',request_key:'original-intent-001'}");
  await run("recoverWalletIntent(1,'topup',()=>true,{disabled:false})");assert.equal(calls.length,1);assert.equal(storage.has(key),false);assert.equal(run('walletBusy'),false);assert.equal(run('walletVersion'),1);
 }else if(which==='invalid_reply'){
  storage.set(key,JSON.stringify(original));context.api=async()=>({outcome:'unknown'});
  await run("recoverWalletIntent(1,'topup',()=>true,{disabled:false})");assert.ok(storage.has(key));assert.equal(run('walletVersion'),0);
 }else if(which==='account_switch'){
  storage.set(key,JSON.stringify(original));let resolve;context.api=()=>new Promise(r=>{resolve=r;});
  const pending=run("recoverWalletIntent(1,'topup',()=>walletVersion===0,{disabled:false})");assert.equal(run('walletRecovering'),true);
  run('sessionEpoch++;resetWalletView();walletRecovering=true');resolve({outcome:'released'});await pending;
  assert.ok(storage.has(key));assert.equal(run('walletRecovering'),true);
 }else if(which==='withdraw_mapping'){
  storage.set(run("walletIntentKey(1,'withdraw')"),JSON.stringify(original));
  await run("recoverWalletIntent(1,'withdraw',()=>true,{disabled:false})");assert.equal(calls[0][2].kind,'withdrawal');assert.equal('pin' in calls[0][2],false);
 }else throw Error('Unknown case');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
