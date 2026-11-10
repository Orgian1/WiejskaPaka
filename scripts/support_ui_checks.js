const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
async function main(chosen){
 const pool=[],elements={},calls=[],pending=[],errors=[];
 class N{
  constructor(tag,text=''){this.tag=tag;this.textContent=text;this.value='';this.children=[];this.dataset={};this.isConnected=true;pool.push(this)}
  append(...nodes){this.children.push(...nodes);if(this.tag==='select'&&!this.value)this.value=nodes[0]?.value||''}
  prepend(...nodes){this.children.unshift(...nodes)}
  replaceChildren(...nodes){this.children=nodes}
  querySelectorAll(){return this.children.flatMap(n=>[n,...n.querySelectorAll()])}
  querySelector(){return this.querySelectorAll().find(n=>n.dataset.supportPrivate)||null}
  setAttribute(){} focus(){} remove(){this.isConnected=false}
 }
 const el=id=>elements[id]||(elements[id]=new N('div'));
 el('support-list').dataset.supportPrivate='true';el('support-detail').dataset.supportPrivate='true';
 const ctx=vm.createContext({el,node:(tag,text)=>new N(tag,text),document:{querySelectorAll:()=>pool.filter(n=>n.dataset.supportPrivate)},sessionEpoch:1,role:'klient',token:'private-token',URLSearchParams,crypto:{randomUUID:()=> 'stable-test-request'},
  act:async fn=>{try{await fn()}catch(e){errors.push(e.message)}},api:(...args)=>{calls.push(args);if(args[0].startsWith('/test/support/cases?')&&!chosen.startsWith('list_'))return Promise.resolve({mode:'test',cases:[],limit:20,offset:0,has_more:false});return new Promise((resolve,reject)=>pending.push({resolve,reject}))}});
 vm.runInContext(fs.readFileSync('web/support-cases.js','utf8'),ctx);
 const cid='a'.repeat(32),data={mode:'test',case:{id:cid,status:'new',revision:1,description:'Fikcyjny opis prywatny'},events:[],has_older_events:false,notice:'TEST'};
 if(chosen==='draft_clear'){
  const input=new N('textarea');input.value='private draft';el('support-detail').append(input);ctx.resetSupportView(null);
  assert.equal(input.value,'');assert.equal(el('support-detail').children.length,0);assert(el('support-section').hidden);return;
 }
 if(chosen.startsWith('list_')){
  const first=ctx.loadSupportCases();
  if(chosen==='list_switch'){ctx.sessionEpoch++;ctx.resetSupportView(null);pending[0].resolve({mode:'test',cases:[],limit:20,offset:0,has_more:false});await first;assert.equal(el('support-status').textContent,'');return}
  const second=ctx.loadSupportCases();pending[1].resolve({mode:'test',cases:[],limit:20,offset:0,has_more:false});await second;
  pending[0].resolve({mode:'test',cases:[{id:cid,category:'product',status:'new',kind:'order',target_id:'private-old-order'}],limit:20,offset:0,has_more:false});await first;
  assert.equal(el('support-list').children.length,0);assert.match(el('support-status').textContent,/Brak zgłoszeń/);return;
 }
 if(chosen==='history_switch'||chosen==='history_replaced'){
  const first=ctx.loadSupportCase(cid);
  pending[0].resolve({...data,events:[{revision:21,actor_role:'klient',created_at:'2026-10-18',message:'Test',status_after:'new'}],has_older_events:true});await first;
  const older=pool.find(n=>n.textContent==='Pokaż wcześniejsze wpisy');
  if(chosen==='history_switch'){ctx.sessionEpoch++;ctx.resetSupportView(null)}
  else {const next=ctx.loadSupportCase('b'.repeat(32));pending[1].resolve(data);await next}
  const count=calls.length;const result=older.onclick();assert.equal(calls.length,count,'An obsolete history control must not send a request in a different view or session');await result;return;
 }
 if(chosen==='detail_switch'){
  const result=ctx.loadSupportCase(cid);ctx.sessionEpoch++;ctx.resetSupportView(null);pending[0].resolve(data);await result;assert.equal(el('support-detail').children.length,0);return;
 }
 const card=new N('article'),button=ctx.supportCreateButton('order',7,card);await button.onclick();
 const text=pool.find(n=>n.tag==='textarea'),submit=pool.find(n=>n.textContent==='Wyślij zgłoszenie testowe');text.value='Fikcyjny opis testowy zakupu';
 const result=submit.onclick();assert.equal(calls.length,1);await submit.onclick();assert.equal(calls.length,1);
 if(chosen==='create_switch'){
  ctx.sessionEpoch++;ctx.resetSupportView(null);pending[0].resolve(data);await result;assert.equal(text.value,'');assert.equal(calls.length,1);return;
 }
 if(chosen==='create_retry'){
  pending[0].reject(Error('Lost response'));await result;
  const retry=submit.onclick();assert.equal(calls[0][2].request_id,calls[1][2].request_id);pending[1].resolve(data);await retry;
 }else{pending[0].resolve(data);await result}
 assert.equal(text.value,'');assert.equal(submit.disabled,false);assert.equal(errors.length,0);
}
main(process.argv[2]).then(()=>process.stdout.write('PASS\n')).catch(e=>{console.error(e);process.exitCode=1});
