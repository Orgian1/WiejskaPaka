const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
  constructor(tag='div',text=''){this.tag=tag;this.textContent=text;this.children=[];this.value='';this.hidden=false;this.disabled=false;this.isConnected=true;this.listeners={}}
  append(...nodes){this.children.push(...nodes)}
  replaceChildren(...nodes){this.children=[...nodes]}
  get firstChild(){return this.children[0]}
  setAttribute(){}
  reset(){this.value=''}
}
const fields=new Map(),el=id=>{if(!fields.has(id))fields.set(id,new Element());return fields.get(id)};
const rows=[1,2].map(id=>({order_id:id,shipment_id:'WPS-test',pickup_code:'WP-test',delivery_date:'2026-10-28',customer_from:720,customer_to:1080,agreed_from:720,agreed_to:960,state:'pending',revision:0,status:'oczekuje_na_platnosc_testowa',delivery_city:'Legnica',delivery_street:'Testowa 1',delivery_postal_code:'59-220',product_name:'Produkt '+id,quantity:2,total_grosze:400}));
const slot={id:'a'.repeat(32),city:'Legnica',postal_code:'59-220',weekday:2,from_time:'10:00',to_time:'16:00',active:true};
const calls=[],c=vm.createContext({el,node:(tag,text)=>new Element(tag,text),role:'rolnik',sessionEpoch:1,
  fetch:async()=>({ok:true,json:async()=>({enabled:false})}),money:n=>String(n),act:fn=>fn(),singleWrite:(_,b,fn)=>fn(),
  loadProducts:async()=>{},loadCart:async()=>{},loadOrders:async()=>{},loadDashboard:async()=>{},
  api:async(path,method='GET',body)=>{
    calls.push({path,method,body});
    if(path==='/address-delivery/requests/mine')return {items:rows,next_before:null};
    if(path==='/address-delivery/windows/mine'||path==='/farmers/7/delivery-windows')return {items:[slot]};
    throw Error('Unexpected request '+path);
  }});
const text=n=>[n.textContent,...n.children.map(text)].filter(Boolean).join(' ');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
vm.runInContext(fs.readFileSync('web/address-delivery.js','utf8'),c);
(async()=>{
  await tick();vm.runInContext('addressDeliveryEnabled=true',c);
  await c.loadAddressDeliveryViews();
  assert.equal(el('address-delivery-panel').hidden,false);
  assert.equal(el('delivery-requests').children.length,1); // One card per shipment.
  assert(text(el('delivery-requests')).includes('Produkt 1'));
  assert(text(el('delivery-requests')).includes('Produkt 2'));
  assert.equal(el('delivery-requests').children[0].children.filter(n=>n.tag==='button').length,2);
  c.role='klient';await c.loadAddressDeliveryViews();
  assert.equal(el('delivery-settings-tab').hidden,true);
  assert.equal(el('delivery-requests').children[0].children.filter(n=>n.tag==='button').length,0);
  const form=c.addressDeliveryFields(7);await tick();
  assert.throws(()=>form.payload());
  const input=label=>form.element.children.find(n=>n.tag==='label'&&n.textContent===label).children[0];
  input('Dostępne terminy sprzedawcy').value=slot.id;input('Data dostawy').value='2026-10-28';
  input('Mogę odebrać od godziny').value='12:00';input('Mogę odebrać do godziny').value='18:00';input('Numer telefonu').value='+48 500 100 200';
  assert.equal(form.payload().phone,'+48 500 100 200');assert.equal(form.payload().window_id,slot.id);
  let finish;c.api=()=>new Promise(resolve=>finish=resolve);
  const stale=c.loadAddressDeliveryViews();await tick();c.sessionEpoch++;c.role=null;c.resetAddressDeliveryViews();
  finish({items:rows,next_before:null});await stale;
  assert.equal(el('address-delivery-panel').hidden,true);
  assert.equal(el('delivery-requests').children.length,0);
  console.log('Delivery role views, private draft and stale response guards: PASS');
})().catch(error=>{console.error(error);process.exitCode=1});
