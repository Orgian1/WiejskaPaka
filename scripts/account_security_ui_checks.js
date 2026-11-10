const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
async function main(name){
 const elements=new Map(),pending=[],calls=[],messages=[];let logged=null;
 const el=id=>{if(!elements.has(id))elements.set(id,{value:'',disabled:false,hidden:false,reset(){for(const key of ['current-password','next-password','repeat-password'])el(key).value=''}});return elements.get(id)};
 const c=vm.createContext({console,el,sessionEpoch:0,role:'klient',token:'memory-only-token',loginAttempt:0,
  msg:t=>messages.push(t),logged:user=>{logged=user;c.resetPasswordChangeView(user)},
  api:(...args)=>{calls.push(args);return new Promise((resolve,reject)=>pending.push({resolve,reject}))},
  localStorage:{setItem(){throw Error('Storage forbidden')}},sessionStorage:{setItem(){throw Error('Storage forbidden')}}});
 vm.runInContext(fs.readFileSync('web/account-security.js','utf8'),c);
 c.resetPasswordChangeView({id:1});assert.equal(el('account-security').hidden,false);
 el('current-password').value='Old-private-synthetic-password!';
 el('next-password').value='New-private-synthetic-password!';el('repeat-password').value=el('next-password').value;
 if(name==='mismatch')el('repeat-password').value='Different-private-password!';
 if(name==='too_short'){el('next-password').value='short';el('repeat-password').value='short'}
 if(name==='same'){el('next-password').value=el('current-password').value;el('repeat-password').value=el('current-password').value}
 const first=el('change-password').onsubmit({preventDefault(){}});
 assert.equal(el('current-password').value,'');assert.equal(el('next-password').value,'');assert.equal(el('repeat-password').value,'');
 if(['mismatch','too_short','same'].includes(name)){await first;assert.equal(calls.length,0);assert(messages.length);return}
 assert.equal(calls.length,1);assert.equal(calls[0][0],'/auth/change-password');assert.equal(calls[0][1],'POST');
 if(name==='duplicate'){await el('change-password').onsubmit({preventDefault(){}});assert.equal(calls.length,1)}
 if(name==='account_switch'){c.sessionEpoch++;c.token='new-account-token';c.resetPasswordChangeView({id:2})}
 if(name==='logout'){c.sessionEpoch++;c.token=null;c.resetPasswordChangeView(null)}
 if(name==='error')pending[0].reject(Error('Nieprawidłowe obecne hasło.'));
 else pending[0].resolve({changed:true,reauthentication_required:true});
 await first;
 if(name==='error'){assert.equal(c.token,'memory-only-token');assert.equal(el('change-password-submit').disabled,false);assert.match(messages[0],/Nieprawidłowe/);return}
 if(name==='account_switch'){assert.equal(c.token,'new-account-token');assert.equal(messages.length,0);return}
 if(name==='logout'){assert.equal(messages.length,0);return}
 assert.equal(c.token,null);assert.equal(c.sessionEpoch,1);assert.equal(logged,null);
 assert.equal(el('account-security').hidden,true);assert.match(messages[0],/Wszystkie sesje/);
}
main(process.argv[2]).then(()=>process.stdout.write('PASS\n')).catch(e=>{console.error(e);process.exitCode=1});
