const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('web/password-reset.js','utf8');
const chosen=process.argv[2],secret='R'.repeat(43),nodes={};
for(const id of ['password-reset-section','reset-status','reset-token','reset-email','reset-new-password','reset-repeat-password','request-reset-submit','confirm-reset-submit','request-password-reset','confirm-password-reset']){
  nodes[id]={hidden:true,value:'',disabled:false,textContent:'',reset(){
    const ids=id==='request-password-reset'?['reset-email']:['reset-token','reset-new-password','reset-repeat-password'];
    for(const input of ids)nodes[input].value='';
  }};
}
let calls=[],urlRemoved=false,loggedOut=0,finish;
const ctx=vm.createContext({el:id=>nodes[id],location:{hash:'#reset-token='+secret,pathname:'/',search:''},
  history:{replaceState(a,b,url){assert.equal(url,'/');urlRemoved=true}},sessionEpoch:0,loginAttempt:0,token:'session',
  logged(user){assert.equal(user,null);loggedOut++},
  fetch:async(path,options)=>{
    calls.push({path,options});
    if(path.endsWith('/options'))return {ok:true,json:async()=>({enabled:chosen!=='disabled'})};
    if(chosen==='network')throw Error('network');
    if(chosen==='duplicate'||chosen==='account_switch')return new Promise(resolve=>{finish=()=>resolve({ok:true,json:async()=>({changed:true,reauthentication_required:true})})});
    return {ok:true,json:async()=>({changed:true,reauthentication_required:true})};
  }});
(async()=>{
  await vm.runInContext(script,ctx);
  assert(urlRemoved);assert.equal(ctx.location.hash.includes(secret),true); // browser stub doesn't mutate hash
  if(chosen==='disabled'){
    assert(nodes['password-reset-section'].hidden);assert.equal(nodes['reset-token'].value,'');return;
  }
  assert.equal(nodes['password-reset-section'].hidden,false);
  assert.equal(nodes['reset-token'].value,secret);
  if(chosen==='request'){
    nodes['reset-email'].value='synthetic@example.invalid';
    await nodes['request-password-reset'].onsubmit({preventDefault(){}});
    assert.equal(calls.length,2);assert.equal(nodes['reset-email'].value,'');
    assert(nodes['reset-status'].textContent.startsWith('Jeśli adres'));
    assert.equal(calls[1].options.credentials,'omit');assert(!JSON.stringify(calls[1]).includes(secret));return;
  }
  nodes['reset-new-password'].value='New-synthetic-password!';
  nodes['reset-repeat-password'].value=chosen==='mismatch'?'Other-password!':'New-synthetic-password!';
  const promise=nodes['confirm-password-reset'].onsubmit({preventDefault(){}});
  if(chosen==='duplicate'){
    await nodes['confirm-password-reset'].onsubmit({preventDefault(){}});assert.equal(calls.length,2);finish();
  }
  if(chosen==='account_switch'){ctx.sessionEpoch++;finish()}
  await promise;
  if(chosen==='mismatch'){assert.equal(calls.length,1);assert.equal(loggedOut,0);return}
  assert.equal(nodes['reset-token'].value,'');assert.equal(nodes['reset-new-password'].value,'');
  assert.equal(nodes['confirm-reset-submit'].disabled,false);
  assert.equal(calls[1].options.credentials,'omit');assert.equal(calls[1].options.referrerPolicy,'no-referrer');
  if(chosen==='account_switch'){assert.equal(loggedOut,0);assert.equal(ctx.token,'session');return}
  if(chosen==='network'){assert.equal(loggedOut,0);assert(nodes['reset-status'].textContent.includes('sprawdź logowanie'));return}
  assert.equal(loggedOut,1);assert.equal(ctx.token,null);assert(nodes['reset-status'].textContent.includes('Hasło zmienione'));
})().catch(error=>{console.error(error);process.exitCode=1});
