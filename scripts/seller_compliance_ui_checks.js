const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
async function main(name){
 const elements=new Map(),calls=[],pending=[];
 const el=id=>{if(!elements.has(id))elements.set(id,{textContent:'',disabled:false,checked:false,hidden:false});return elements.get(id)};
 const c=vm.createContext({el,sessionEpoch:0,role:'rolnik',token:'token',api:(...args)=>{calls.push(args);return new Promise((resolve,reject)=>pending.push({resolve,reject}))}});
 vm.runInContext(fs.readFileSync('web/seller-compliance.js','utf8'),c);
 c.resetSellerComplianceView({role:'rolnik'});
 const status={completed_transaction_count:20,profile_reminder_threshold:20,profile_reminder_due:true,rules_acknowledged:false,rules_version:null,current_rules_version:'2026-10-draft',review_status:'not_started'};
 if(name==='anonymous'||name==='buyer'){
   c.role=name==='buyer'?'klient':null;c.token=name==='buyer'?'token':null;
   c.resetSellerComplianceView(c.role?{role:c.role}:null);await el('seller-compliance-refresh').onclick();
   assert.equal(calls.length,0);assert.equal(el('seller-compliance').hidden,true);return;
 }
 await el('seller-rules-submit').onclick();assert.equal(calls.length,0);
 const first=el('seller-compliance-refresh').onclick();assert.equal(calls.length,1);
 assert.equal(el('seller-rules-submit').disabled,true);
 if(name==='duplicate'){await el('seller-compliance-refresh').onclick();assert.equal(calls.length,1)}
 if(['switch','logout'].includes(name)){
   c.sessionEpoch++;c.role=name==='switch'?'rolnik':null;c.token=c.role?'new-token':null;
   c.resetSellerComplianceView(c.role?{role:c.role}:null);
 }
 if(name==='error')pending[0].reject(Error('Brak połączenia'));
 else pending[0].resolve({...status,completed_transaction_count:name==='invalid'?1.5:20});
 await first;
 if(['switch','logout'].includes(name)){assert.equal(el('seller-compliance-status').textContent,'');assert.equal(el('seller-rules-submit').disabled,true);return}
 if(name==='error'||name==='invalid'){
   assert.match(el('seller-compliance-status').textContent,name==='error'?/Brak połączenia/:/Nieprawidłowa/);
   assert.equal(el('seller-rules-submit').disabled,true);assert.equal(el('seller-compliance-refresh').disabled,false);return;
 }
 assert.match(el('seller-compliance-status').textContent,/Zakończone transakcje: 20/);
 assert.match(el('seller-compliance-status').textContent,/przypomnienie/);
 assert.equal(el('seller-rules-submit').disabled,true);
 el('seller-rules-check').checked=true;el('seller-rules-check').onchange();
 assert.equal(el('seller-rules-submit').disabled,false);
 const ack=el('seller-rules-submit').onclick();assert.equal(calls.length,2);
 assert.equal(calls[1][0],'/farmers/me/compliance/acknowledge');assert.equal(calls[1][1],'POST');
 assert.equal(JSON.stringify(calls[1][2]),JSON.stringify({rules_version:'2026-10-draft',accepted:true}));
 await el('seller-rules-submit').onclick();assert.equal(calls.length,2);
 if(name==='ack_switch'){c.sessionEpoch++;c.resetSellerComplianceView({role:'rolnik'})}
 if(name==='ack_error')pending[1].reject(Error('Brak połączenia'));
 else pending[1].resolve({...status,rules_acknowledged:true,rules_version:'2026-10-draft',review_status:'pending'});
 await ack;
 if(name==='ack_switch'){assert.equal(el('seller-compliance-status').textContent,'');return}
 if(name==='ack_error')assert.match(el('seller-compliance-status').textContent,/mogło zostać zapisane/);
 else assert.match(el('seller-compliance-status').textContent,/Zasady demo potwierdzone/);
 assert.equal(el('seller-rules-check').checked,false);assert.equal(el('seller-rules-submit').disabled,true);
}
main(process.argv[2]).then(()=>process.stdout.write('PASS\n')).catch(e=>{console.error(e);process.exitCode=1});
