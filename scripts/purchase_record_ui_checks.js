const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function env(){
 const pending=[],calls=[],downloads=[],urls=[],revoked=[],timers=[];
 class Element{
  constructor(tag='div',text=''){this.tag=tag;this.text=text;this.children=[];this.dataset={};this.isConnected=true;this.disabled=false;}
  append(...items){for(const item of items){item.parent=this;this.children.push(item);}}
  querySelector(selector){const key=selector.match(/\[data-([^\]]+)\]/)?.[1]?.replace(/-([a-z])/g,(_,x)=>x.toUpperCase());return this.children.find(n=>n.dataset[key])||null;}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(n=>n!==this);this.isConnected=false;}
  click(){downloads.push({filename:this.download,url:this.href});}
  set textContent(v){this.text=String(v);this.children=[];}
  get textContent(){return this.text+this.children.map(n=>n.textContent).join('');}
  set innerHTML(v){throw Error('Unsafe HTML');}
 }
 const body=new Element('body');
 const c=vm.createContext({console,sessionEpoch:0,role:'klient',node:(tag,text='')=>new Element(tag,text),
  money:n=>String(n)+' gr',api:path=>{calls.push(path);return new Promise((resolve,reject)=>pending.push({resolve,reject}));},
  document:{body,createElement:tag=>new Element(tag)},URL:{createObjectURL:blob=>{urls.push(blob);return 'blob:private-'+urls.length;},revokeObjectURL:url=>revoked.push(url)},Blob,
  setTimeout:fn=>timers.push(fn),act:fn=>Promise.resolve().then(fn)});
 vm.runInContext(fs.readFileSync('web/app.js','utf8').split('let saleUnitsEnabled=false;')[0],c);
 vm.runInContext(fs.readFileSync('web/purchase-records.js','utf8'),c);
 const original={product:{id:1,name:'<img src=x onerror=alert(1)>',unit_price_grosze:199},quantity:2,subtotal_grosze:398,delivery_grosze:501,total_grosze:899,
  ordered_at:'2026-10-16T10:00:00+00:00',reservation_expires_at:'2026-10-16T10:30:00+00:00',pickup_point:{id:1,name:'Stary punkt',city:'Opole',street:'Pierwotna 1',opening_hours:'9–17'}};
 const order={order_id:1,pickup_code:'WP-1',notice:'Zapis testowy',original_available:true,original,current:{status:'anulowane_testowo',payment_state_test:'refunded_test',refund_grosze:899}};
 return {c,card:new Element(),pending,calls,downloads,urls,revoked,timers,order,Element};
}
async function main(name){
 const e=env(),{c,card,pending}=e;
 switch(name){
 case 'render_safe_original':{
  const p=c.showPurchaseRecord('order',1,card);pending[0].resolve(e.order);await p;
  assert.match(card.textContent,/<img src=x/);assert.match(card.textContent,/Pierwotna 1/);assert.match(card.textContent,/899 gr/);break;}
 case 'logout_ignores_reply':{
  const p=c.showPurchaseRecord('order',1,card);c.sessionEpoch++;c.role='rolnik';pending[0].resolve(e.order);await p;assert.equal(card.children.length,0);break;}
 case 'detached_card_ignores_reply':{
  const p=c.showPurchaseRecord('order',1,card);card.isConnected=false;pending[0].resolve(e.order);await p;assert.equal(card.children.length,0);break;}
 case 'latest_reply_wins':{
  const p1=c.showPurchaseRecord('order',1,card),p2=c.showPurchaseRecord('order',1,card);
  pending[1].resolve({...e.order,notice:'NOWE'});await p2;pending[0].resolve({...e.order,notice:'STARE'});await p1;
  assert.match(card.textContent,/NOWE/);assert(!card.textContent.includes('STARE'));assert.equal(card.children.length,1);break;}
 case 'legacy_has_no_invented_terms':{
  const p=c.showPurchaseRecord('order',1,card);pending[0].resolve({...e.order,original_available:false,original:null});await p;
  assert.match(card.textContent,/Brak archiwalnego/);assert(!card.textContent.includes('Pierwotna 1'));break;}
 case 'error_is_generic':{
  const p=c.showPurchaseRecord('order',1,card);pending[0].reject(Error('private server detail'));await p;
  assert.match(card.textContent,/Nie udało się/);assert(!card.textContent.includes('private'));break;}
 case 'courier_cannot_request_record':
  c.role='dostawca';await c.showPurchaseRecord('order',1,card);assert.equal(e.calls.length,0);break;
 case 'private_json_download':{
  const p=c.showPurchaseRecord('order',1,card,true);pending[0].resolve(e.order);await p;
  assert.equal(e.downloads.length,1);assert.equal(e.downloads[0].filename,'WiejskaPaka_zapis_order_1.json');
  const payload=JSON.parse(await e.urls[0].text());assert.equal(payload.original.product.unit_price_grosze,199);
  assert.equal(card.children.length,0);e.timers.forEach(fn=>fn());assert.equal(e.revoked[0],'blob:private-1');break;}
 case 'logout_blocks_download':{
  const p=c.showPurchaseRecord('order',1,card,true);c.sessionEpoch++;pending[0].resolve(e.order);await p;assert.equal(e.downloads.length,0);break;}
 case 'shipment_one_delivery_and_point':{
  const p=c.showPurchaseRecord('shipment','WPS-1',card);
  pending[0].resolve({notice:'TEST',original_available:true,original:{products_grosze:1000,delivery_grosze:501,total_grosze:1501},orders:[e.order,{...e.order,order_id:2,pickup_code:'WP-2'}]});await p;
  assert.match(card.textContent,/jedna dostawa: 501 gr/);assert.equal(card.textContent.split('Punkt przy zakupie:').length-1,1);break;}
 case 'button_prevents_duplicate_fetch':{
  const controls=c.purchaseRecordControls('order',1,card),button=controls.children[0];
  const p1=button.onclick();await Promise.resolve();const p2=button.onclick();await Promise.resolve();assert.equal(e.calls.length,1);
  pending[0].resolve(e.order);await Promise.all([p1,p2]);assert.equal(button.disabled,false);break;}
 case 'shipment_details_stale_guard':{
  // Execute the actual existing dashboard helper as well as the new record UI.
  c.el=()=>new e.Element();c.dashboardButton=(label,action)=>({action});c.node=(tag,text='')=>new e.Element(tag,text);
  vm.runInContext(fs.readFileSync('web/dashboard.js','utf8'),c);
  const button=c.shipmentDetailsButton('WPS-1',card);const p=button.onclick();await Promise.resolve();c.sessionEpoch++;
  pending[0].resolve({items:[],delivery_grosze:501,total_grosze:899});await p;assert.equal(card.children.length,0);break;}
 default:throw Error('Unknown scenario');
 }
 process.stdout.write(name+': PASS\n');
}
main(process.argv[2]).catch(error=>{console.error(error);process.exitCode=1;});
