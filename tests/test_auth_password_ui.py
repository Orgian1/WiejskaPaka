"""Execute the actual auth handlers; submitted secrets leave the DOM immediately."""
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('kind',['login','register'])
@pytest.mark.parametrize('failure',[False,True])
def test_auth_clears_password_field_before_response(kind,failure):
    script=r'''
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const kind=process.argv[1],failure=process.argv[2]==='true',source=fs.readFileSync('web/app.js','utf8');
const elements=new Map(),pending=[],calls=[];let action;
const el=id=>{if(!elements.has(id))elements.set(id,{value:id==='password'?'Synthetic-submit-password!':id==='role'?'klient':'test@example.invalid'});return elements.get(id)};
const c=vm.createContext({el,sessionEpoch:0,loginAttempt:0,token:null,
 api:(...args)=>{calls.push(args);if(args[0]==='/auth/me')return Promise.resolve({id:1,role:'klient'});return new Promise((resolve,reject)=>pending.push({resolve,reject}))},
 act:fn=>{action=Promise.resolve().then(fn);action.catch(()=>{})},
 singleWrite:(_k,_button,fn)=>fn(),logged:()=>{},msg:()=>{}});
const segment=kind==='login'?source.split("el('auth').onsubmit=",2)[1].split('// Prevent repeated submissions',1)[0]:
 source.split("el('register').onclick=",2)[1].split("el('logout').onclick=",1)[0];
vm.runInContext("el('"+(kind==='login'?'auth':'register')+"')."+(kind==='login'?'onsubmit':'onclick')+'='+segment,c);
async function main(){
 el(kind==='login'?'auth':'register')[kind==='login'?'onsubmit':'onclick']({preventDefault(){}});await Promise.resolve();
 assert.equal(calls.length,1);assert.equal(calls[0][2].password,'Synthetic-submit-password!');assert.equal(el('password').value,'');
 if(failure)pending[0].reject(Error('Denied'));
 else pending[0].resolve(kind==='login'?{access_token:'new-memory-token'}:{id:1});
 try{await action;if(failure)throw Error('Expected rejection')}catch(error){if(!failure)throw error;assert.equal(error.message,'Denied')}
 assert.equal(el('password').value,'');
 if(kind==='login'&&!failure)assert.equal(calls[1][0],'/auth/me');
}
main().catch(e=>{console.error(e);process.exitCode=1});
'''
    r=subprocess.run(['node','-e',script,kind,str(failure).lower()],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert r.returncode==0,r.stdout+r.stderr
