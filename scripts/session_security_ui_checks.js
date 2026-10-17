const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
async function main(name){
 const elements=new Map(),calls=[],pending=[],messages=[];
 const el=id=>{if(!elements.has(id))elements.set(id,{textContent:'',disabled:false});return elements.get(id)};
 const c=vm.createContext({console,el,sessionEpoch:0,role:'klient',token:'old-token',loginAttempt:0,
  logged:user=>c.resetSessionSecurityView(user),msg:t=>messages.push(t),
  api:(...args)=>{calls.push(args);return new Promise((resolve,reject)=>pending.push({resolve,reject}))},
  localStorage:{setItem(){throw Error('Forbidden storage')}},sessionStorage:{setItem(){throw Error('Forbidden storage')}}});
 vm.runInContext(fs.readFileSync('web/session-security.js','utf8'),c);c.resetSessionSecurityView({id:1});
 const action=name==='all'||name==='all_switch'?'sessions-logout-all':name==='others'?'sessions-logout-others':'sessions-refresh';
 if(name==='anonymous'){c.token=null;await el(action).onclick();assert.equal(calls.length,0);return}
 const first=el(action).onclick();assert.equal(calls.length,1);
 const expected=action==='sessions-refresh'?'/auth/sessions':action==='sessions-logout-all'?'/auth/logout-all':'/auth/logout-others';
 assert.equal(calls[0][0],expected);assert.equal(calls[0][1],action==='sessions-refresh'?'GET':'POST');
 if(name==='duplicate'){await el('sessions-logout-all').onclick();assert.equal(calls.length,1)}
 if(['account_switch','all_switch','new_request'].includes(name)){c.sessionEpoch++;c.token='new-token';c.resetSessionSecurityView({id:2})}
 if(name==='logout'){c.sessionEpoch++;c.token=null;c.resetSessionSecurityView(null)}
 if(name==='new_request'){
   const second=el('sessions-refresh').onclick();pending[1].resolve({active_sessions:9,other_sessions:8});await second;
 }
 if(name==='error')pending[0].reject(Error('Brak połączenia'));
 else pending[0].resolve(action==='sessions-refresh'?{active_sessions:name==='invalid'?1.5:3,other_sessions:2}:{ok:true,other_sessions:0});
 await first;
 if(['account_switch','all_switch','logout'].includes(name)){assert.equal(el('sessions-status').textContent,'');assert.equal(c.token,name==='logout'?null:'new-token');assert.equal(messages.length,0);return}
 if(name==='new_request'){assert.match(el('sessions-status').textContent,/9/);return}
 if(name==='error'){assert.match(el('sessions-status').textContent,/Brak połączenia/);assert.equal(el('sessions-refresh').disabled,false);return}
 if(name==='invalid'){assert.match(el('sessions-status').textContent,/Nieprawidłowa/);return}
 if(name==='all'){assert.equal(c.token,null);assert.equal(c.sessionEpoch,1);assert.equal(el('sessions-status').textContent,'');assert.equal(el('sessions-refresh').disabled,true);assert.equal(messages.length,1);return}
 if(name==='others'){assert.equal(c.token,'old-token');assert.match(el('sessions-status').textContent,/Bieżąca sesja/)}
 else assert.match(el('sessions-status').textContent,/Aktywne sesje: 3/);
 assert.equal(el('sessions-refresh').disabled,false);
}
main(process.argv[2]).then(()=>process.stdout.write('PASS\n')).catch(e=>{console.error(e);process.exitCode=1});
