// Actual browser source with controlled DOM/network/time. Not a Chromium test.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function env(){
 const pending=[],calls=[],views=[],timers=new Map(),events={};let serial=0;
 class Element{
  constructor(tag,text=''){this.tag=tag;this.text=text;this.children=[];this.dataset={};this.value='';this.disabled=false;this.isConnected=true;}
  append(...nodes){this.children.push(...nodes)}
  replaceChildren(...nodes){this.text='';this.children=[...nodes]}
  querySelectorAll(selector){return this.children.flatMap(n=>[...(n.tag===selector?[n]:[]),...n.querySelectorAll(selector)])}
  setAttribute(key,value){this[key]=value}
  focus(){this.focused=true}
  set textContent(value){this.text=String(value);this.children=[]}
  get textContent(){return this.text+this.children.map(n=>n.textContent).join('')}
  set innerHTML(_){throw Error('Unsafe HTML')}
 }
 const document={hidden:false,querySelectorAll:()=>views,addEventListener:(name,fn)=>events[name]=fn};
 const c=vm.createContext({console,sessionEpoch:0,role:'klient',document,
  addEventListener:(name,fn)=>events[name]=fn,
  node:(tag,text='')=>new Element(tag,text),
  api:(...args)=>{calls.push(args);return new Promise((resolve,reject)=>pending.push({resolve,reject}))},
  localStorage:{setItem(){throw Error('Sensitive storage')}},sessionStorage:{setItem(){throw Error('Sensitive storage')}},
  setTimeout:(fn,ms)=>{const id=++serial;timers.set(id,{fn,ms});return id},clearTimeout:id=>timers.delete(id)});
 vm.runInContext(fs.readFileSync('web/pin-recovery.js','utf8'),c);
 function open(kind='order',id=7){const host=c.pinRecoveryControls(kind,id);views.push(host);host.children[0]?.onclick();return host}
 function form(host){return host.children[0]}
 function submit(host,password='Synthetic-reauth-password'){const f=form(host);f.querySelectorAll('input')[0].value=password;return f.onsubmit({preventDefault(){}})}
 function expire(ms){for(const [id,t] of [...timers])if(t.ms===ms){timers.delete(id);t.fn()}}
 return {c,open,form,submit,expire,pending,calls,events,document};
}
const response={mode:'test',pin_test_only:'012345',order_ids:[7],shipment_id:null};
async function main(name){
 const e=env();
 if(name==='non_client'){e.c.role='rolnik';const host=e.open();assert.equal(host.children.length,0);assert.equal(e.calls.length,0);return}
 const host=e.open(name==='shipment_route'?'shipment':'order',name==='shipment_route'?'WPS/A ?':7);
 if(name==='blank'){await e.submit(host,'');assert.equal(e.calls.length,0);assert.match(host.textContent,/Podaj hasło/);return}
 const first=e.submit(host);
 assert.equal(e.form(host).querySelectorAll('input')[0].value,'');
 assert.deepEqual(e.calls[0].slice(0,2),[name==='shipment_route'?'/shipments/WPS%2FA%20%3F/recover-pin-test':'/orders/7/recover-pin-test','POST']);
 assert.equal(e.calls[0][2].password,'Synthetic-reauth-password');
 if(name==='duplicate'){await e.submit(host);assert.equal(e.calls.length,1)}
 if(name==='cancel'){e.form(host).children.find(n=>n.tag==='button'&&n.type==='button').onclick()}
 if(name==='logout'){e.c.sessionEpoch++;e.c.role=null;e.c.resetPinRecoveryViews()}
 if(name==='role_changed')e.c.role='rolnik';
 if(name==='detached')host.isConnected=false;
 if(name==='hidden'){e.document.hidden=true;e.events.visibilitychange()}
 if(name==='pagehide')e.events.pagehide();
 if(name==='stalled_timeout')e.expire(30000);
 if(name==='password_error'){
  e.pending[0].reject(Error('Nieprawidłowe hasło.'));await first;
  assert(!host.textContent.includes('012345'));assert.match(host.textContent,/Nieprawidłowe/);
  const second=e.submit(host);e.pending[1].resolve(response);await second;assert(host.textContent.includes('012345'));return;
 }
 e.pending[0].resolve(name==='invalid_pin'?{...response,pin_test_only:'<img src=x>'}:response);await first;
 if(['cancel','logout','role_changed','detached','hidden','pagehide','stalled_timeout'].includes(name)){
  assert(!host.textContent.includes('012345'));return;
 }
 if(name==='invalid_pin'){assert(!host.textContent.includes('<img'));assert.match(host.textContent,/bezpiecznie/);return}
 assert.match(host.textContent,/PIN TESTOWY: 012345/);
 if(name==='timeout'){const previous=e.form(host);e.expire(30000);assert(!previous.textContent.includes('012345'));assert(!host.textContent.includes('012345'));assert.match(host.textContent,/Odzyskaj PIN/)}
 if(name==='hide_after_reveal'){e.document.hidden=true;e.events.visibilitychange();assert(!host.textContent.includes('012345'))}
 if(name==='superseded'){
  e.c.resetPinRecoveryViews();host.children[0].onclick();const second=e.submit(host);e.pending[1].resolve({...response,pin_test_only:'654321'});await second;
  assert(host.textContent.includes('654321'));assert(!host.textContent.includes('012345'));
 }
}
main(process.argv[2]).then(()=>process.stdout.write(process.argv[2]+': PASS\n')).catch(error=>{console.error(error);process.exitCode=1});
