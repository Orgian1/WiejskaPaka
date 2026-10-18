const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
async function main(name){
 const calls=[],pending=[],messages=[];let refreshes=0,active=true;
 const ctx=vm.createContext({el:()=>({}),node:()=>({isConnected:true,disabled:false}),role:'rolnik',crypto:{randomUUID:()=> 'private-id'},
   api:(...args)=>{calls.push(args);return new Promise((resolve,reject)=>pending.push({resolve,reject}))},
   act:async fn=>{try{await fn()}catch(e){messages.push(e.message)}},msg:m=>messages.push(m)});
 vm.runInContext(fs.readFileSync('web/dashboard.js','utf8'),ctx);
 ctx.loadDashboard=async()=>{refreshes++};
 const button=ctx.farmerTestSettlementButton(7,()=>active);
 if(name==='stale'){active=false;await button.onclick();assert.equal(calls.length,0);return}
 const first=button.onclick();assert.equal(calls.length,1);
 await button.onclick();assert.equal(calls.length,1);
 if(name==='switch_before_write'){active=false;ctx.role='klient'}
 pending[0].resolve({state:name==='already_done'?'completed_test':name==='invalid'?'refunded_test':'paid_test'});
 await new Promise(r=>setImmediate(r));
 if(name==='switch_before_write'){await first;assert.equal(calls.length,1);assert.equal(refreshes,0);return}
 if(name==='already_done'){await first;assert.equal(calls.length,1);assert.equal(refreshes,1);return}
 if(name==='invalid'){await first;assert.equal(calls.length,1);assert.equal(refreshes,0);assert.match(messages[0],/nie jest gotowa/);return}
 assert.equal(calls.length,2);assert.equal(calls[1][0],'/test/payments/7/events');assert.equal(calls[1][2].event_type,'order_completed_test');
 if(name==='switch_after_write'){active=false;ctx.role='klient'}
 if(name==='unknown_response')pending[1].reject(Error('Lost response'));else pending[1].resolve({state:'completed_test'});
 await first;
 if(name==='switch_after_write'){assert.equal(messages.length,0);assert.equal(refreshes,0);return}
 if(name==='unknown_response'){
   const retry=button.onclick();pending[2].resolve({state:'completed_test'});await retry;
   assert.equal(calls.length,3);assert.equal(refreshes,1);assert.equal(calls.filter(c=>c[1]==='POST').length,1);return;
 }
 assert.equal(refreshes,1);assert.match(messages[0],/Nie wykonano przelewu/);assert.equal(button.disabled,false);
}
main(process.argv[2]).then(()=>process.stdout.write('PASS\n')).catch(e=>{console.error(e);process.exitCode=1});
