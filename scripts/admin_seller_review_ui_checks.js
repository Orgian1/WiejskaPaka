const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
async function main(name){
 class Element{
  constructor(tag='div',text=''){this.tag=tag;this.text=String(text);this.children=[];this.value='';this.disabled=false;this.isConnected=true}
  append(...items){for(const item of items){this.children.push(item);if(this.tag==='select'&&!this.value)this.value=item.value}}
  querySelectorAll(selector){const all=this.children.flatMap(n=>[n,...n.querySelectorAll('*')]);return selector==='*'?all:all.filter(n=>selector.split(',').includes(n.tag))}
  replaceChildren(){for(const child of this.querySelectorAll('*'))child.isConnected=false;this.children=[];this.text=''}
  setAttribute(){}
  set textContent(value){this.text=String(value);this.children=[]}
  get textContent(){return this.text+this.children.map(n=>n.textContent).join('')}
  set innerHTML(value){throw Error('Unsafe HTML insertion')}
 }
 const elements=new Map(),el=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id)},calls=[],pending=[];
 const c=vm.createContext({el,node:(...args)=>new Element(...args),URLSearchParams,role:'admin',token:'test-token',sessionEpoch:0,
 api:(...args)=>{calls.push(args);return new Promise((resolve,reject)=>pending.push({resolve,reject}))}});
 vm.runInContext(fs.readFileSync('web/admin-seller-review.js','utf8'),c);c.resetAdminSellerReview({role:'admin'});
 if(name==='non_admin'){c.role='rolnik';c.resetAdminSellerReview({role:'rolnik'});await el('admin-seller-refresh').onclick();assert.equal(calls.length,0);assert.equal(el('admin-seller-review').hidden,true);return}
 const profile={farmer_id:5,rules_version:'2026-10-draft',review_status:'pending',reviewed_at:null};
 const data={mode:'test',profiles:[profile],total:21,limit:20,offset:0,has_more:true};
 const first=el('admin-seller-refresh').onclick();assert.equal(calls.length,1);
 if(name==='stale_read'){c.sessionEpoch++;c.resetAdminSellerReview({role:'admin'})}
 if(name==='read_error')pending[0].reject(Error('Brak połączenia'));else pending[0].resolve(data);
 await first;
 if(name==='stale_read'){assert.equal(el('admin-seller-results').children.length,0);assert.equal(el('admin-seller-status').textContent,'');return}
 if(name==='read_error'){assert.match(el('admin-seller-status').textContent,/Brak połączenia/);assert.equal(el('admin-seller-refresh').disabled,false);return}
 const card=el('admin-seller-results').children[0],reason=card.querySelectorAll('textarea')[0],button=card.querySelectorAll('button')[0];
 assert.match(card.textContent,/Rolnik #5/);assert.equal(el('admin-seller-next').disabled,false);
 if(name==='pagination'){
   const next=el('admin-seller-next').onclick();assert.match(calls[1][0],/offset=20/);pending[1].resolve({...data,offset:20,has_more:false});await next;assert.equal(el('admin-seller-next').disabled,true);return;
 }
 reason.value=name==='short'?'ab':'Fikcyjne uzasadnienie';
 const write=button.onclick();
 if(name==='short'){await write;assert.equal(calls.length,1);assert.match(el('admin-seller-status').textContent,/3 do 500/);return}
 assert.equal(calls.length,2);assert.equal(reason.value,'');assert.equal(calls[1][2].expected_reviewed_at,null);assert.equal(calls[1][2].expected_review_status,'pending');
 await button.onclick();assert.equal(calls.length,2);
 if(name==='stale_write'){c.sessionEpoch++;c.role='rolnik';c.resetAdminSellerReview({role:'rolnik'})}
 if(name==='write_error')pending[1].reject(Error('Profil zmienił się'));else pending[1].resolve({review_status:'approved'});
 await write;
 assert.equal(el('admin-seller-results').children.length,0);assert.equal(reason.value,'');
 if(name==='stale_write'){assert.equal(el('admin-seller-status').textContent,'');assert.equal(el('admin-seller-review').hidden,true);return}
 assert.match(el('admin-seller-status').textContent,name==='write_error'?/mogła zostać zapisana/:/Decyzja testowa zapisana/);
 assert.equal(el('admin-seller-refresh').disabled,false);
 await button.onclick();assert.equal(calls.length,2);
}
main(process.argv[2]).then(()=>process.stdout.write('PASS\n')).catch(e=>{console.error(e);process.exitCode=1});
