"""Actual logout handler clears locally first and reports failed server revocation."""
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('outcome',['success','already_revoked','server_error','network_error','switch_success','switch_error','no_token'])
def test_logout_feedback_and_account_switch(outcome):
    script=r'''
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const outcome=process.argv[1],source=fs.readFileSync('web/app.js','utf8'),elements=new Map(),messages=[],calls=[];let action,pending;
const el=id=>{if(!elements.has(id))elements.set(id,{});return elements.get(id)};
const c=vm.createContext({el,token:outcome==='no_token'?null:'old-token',sessionEpoch:0,loginAttempt:0,
 logged:user=>assert.equal(user,null),msg:t=>messages.push(t),act:fn=>{action=Promise.resolve().then(fn)},
 fetch:(...args)=>{calls.push(args);return new Promise((resolve,reject)=>pending={resolve,reject})}});
const segment=source.split("el('logout').onclick=",2)[1].split("el('new-product').onsubmit=",1)[0];
vm.runInContext("el('logout').onclick="+segment,c);
async function main(){
 el('logout').onclick();await Promise.resolve();assert.equal(c.token,null);assert.equal(c.sessionEpoch,1);
 assert.match(messages[0],/na tym urządzeniu/);
 if(outcome==='no_token'){await action;assert.equal(calls.length,0);return}
 assert.equal(calls[0][0],'/auth/logout');assert.equal(calls[0][1].headers.Authorization,'Bearer old-token');
 assert.equal(calls[0][1].cache,'no-store');
 if(outcome.startsWith('switch')){c.sessionEpoch++;c.token='new-token'}
 if(outcome==='network_error'||outcome==='switch_error')pending.reject(Error('offline'));
 else pending.resolve({ok:outcome==='success'||outcome==='switch_success',status:outcome==='already_revoked'?401:outcome==='server_error'?500:200});
 await action;
 if(outcome==='network_error'||outcome==='server_error'){assert.equal(messages.length,2);assert.match(messages[1],/Nie potwierdzono/)}
 else assert.equal(messages.length,1);
 assert.equal(c.token,outcome.startsWith('switch')?'new-token':null);
}
main().catch(e=>{console.error(e);process.exitCode=1});
'''
    r=subprocess.run(['node','-e',script,outcome],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert r.returncode==0,r.stdout+r.stderr
