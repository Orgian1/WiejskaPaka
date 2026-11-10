"""Regression tests for browser authentication request ordering."""
from pathlib import Path
import shutil
import subprocess
import pytest

APP = Path(__file__).resolve().parents[1] / 'web' / 'app.js'


def test_login_has_request_generation_guard():
    source = APP.read_text(encoding='utf-8')
    assert 'const attempt=++loginAttempt;const epoch=sessionEpoch' in source
    assert 'if(attempt!==loginAttempt||epoch!==sessionEpoch)return' in source
    logout=source.split("el('logout').onclick=",1)[1].split("el('new-product').onsubmit=",1)[0]
    assert 'loginAttempt++;sessionEpoch++;const logoutEpoch=sessionEpoch;' in logout
    assert 'token=null;logged(null);' in logout
    assert 'if(logoutEpoch===sessionEpoch)' in logout
    assert 'catch(e){if(attempt===loginAttempt){sessionEpoch++;token=null;logged(null)}throw e}' in source


def test_login_logout_race_with_mocked_browser():
    if not shutil.which('node'):
        pytest.skip('Node.js not installed')
    # Minimal DOM/fetch simulation: delayed login must never resurrect a session after logout.
    js = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{textContent:'',hidden:false,value:'',classList:{add(){},remove(){}},reset(){},replaceChildren(){},append(){},setAttribute(){},addEventListener(){},querySelectorAll(){return []},querySelector(){return element('mock-button')}});return elements.get(id)}
let resolveLogin;
const login=new Promise(resolve=>{resolveLogin=resolve});
const context={document:{getElementById:element,createElement:()=>({append(){},setAttribute(){}})},
 fetch:async(path)=>{if(path==='/auth/login')return login;return {ok:true,json:async()=>[]}},
 setTimeout:(fn,ms)=>{const timer=setTimeout(fn,ms);timer.unref?.();return timer},console};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const submit=element('auth').onsubmit({preventDefault(){}});
Promise.resolve().then(()=>{
 element('logout').onclick();
 resolveLogin({ok:true,json:async()=>({access_token:'OLD_TOKEN'})});
 return new Promise(r=>setTimeout(r,0));
}).then(()=>{
 assert.strictEqual(vm.runInContext('token',context),null);
 assert.strictEqual(element('identity').textContent,'Nie zalogowano');
}).catch(e=>{console.error(e);process.exitCode=1});
'''
    subprocess.run(['node', '-e', js, str(APP)], check=True, capture_output=True, text=True)
