const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync('web/nearby.js','utf8');
function env(){
  const elements=new Map(),calls=[],pending=[],geoCalls=[];
  class Element{
    constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.hidden=false;this.disabled=false;this.checked=false;this.text='';this.attributes={};}
    set textContent(t){this.text=String(t);this.children=[];}
    get textContent(){return this.text+this.children.map(c=>c.textContent).join('');}
    set innerHTML(_){throw Error('Unsafe HTML rendering');}
    append(...children){this.children.push(...children);if(this.tag==='select'&&!this.value&&children[0])this.value=children[0].value;}
    replaceChildren(...children){this.children=children;this.text='';if(this.tag==='select')this.value='';}
    setAttribute(k,v){this.attributes[k]=v;}
    reset(){for(const [id,e] of elements){if((this===el('nearby-form')&&id.startsWith('nearby-'))||(this===el('point-edit-form')&&id.startsWith('point-edit-'))){e.value='';e.checked=false;}}el('nearby-radius').value='1000';}
  }
  function el(id){if(!elements.has(id))elements.set(id,new Element(id.includes('select')?'select':'div'));return elements.get(id);}
  const storage=new Proxy({},{get(){throw Error('No browser persistence allowed');}});
  const context=vm.createContext({console,AbortController,sessionEpoch:0,role:'klient',document:{getElementById:el},el,
    node:(tag,text='')=>{const n=new Element(tag);n.textContent=text;return n;},
    money:gr=>String(gr)+' gr',parseGrosze:s=>{if(!/^\d+(,\d{1,2})?$/.test(s))throw Error('money');return Number(s.replace(',','.'))*100;},
    fetch:(path,options)=>{calls.push({path,options});return new Promise(resolve=>pending.push(resolve));},
    api:async(...args)=>{calls.push({api:args});return [];},loadCart:async()=>{},loadFarmer:async()=>{},msg:()=>{},requireResolvedCheckout:()=>{},
    act:fn=>Promise.resolve().then(fn),singleWrite:async(key,button,fn)=>fn(),
    navigator:{geolocation:{getCurrentPosition:(...args)=>geoCalls.push(args)}},localStorage:storage,sessionStorage:storage});
  vm.runInContext(fs.readFileSync('web/app.js','utf8').split('let saleUnitsEnabled=false;')[0],context);
  vm.runInContext(code,context);el('nearby-lat').value='52';el('nearby-lon').value='16';el('nearby-radius').value='1000';
  const result=(name='<img src=x onerror=alert(1)>')=>({ok:true,json:async()=>({items:[{distance_m:12,distance_bucket_m:100,product:{id:1,name,price_grosze:199,stock:10},pickup_point:{id:2,name:'Punkt',city:'Opole',street:'Polna 1',opening_hours:'9-17'}}],has_more:false})});
  return {context,el,calls,pending,geoCalls,result,run:s=>vm.runInContext(s,context)};
}
async function main(name){
 const e=env(),{context:c,el,run}=e;
 switch(name){
 case 'coordinate_precision':
  assert.equal(run("coordinateE6('-0,000001',90)"),-1);assert.equal(run("coordinateE6('+180.000000',180)"),180000000);
  assert.equal(run("coordinateE6('52,229676',90)"),52229676);assert.equal(run('coordinateText(-1)'),'-0,000001');
  for(const x of ['1e2','Infinity','NaN','90.000001','1.1234567','', '0x10'])assert.throws(()=>c.coordinateE6(x,90));break;
 case 'location_requires_click':
  assert.equal(e.geoCalls.length,0);el('nearby-geolocate').onclick();assert.equal(e.geoCalls.length,1);
  e.geoCalls[0][1]({code:1,message:'raw secret location error'});assert.match(el('nearby-status').textContent,/Nie udzielono zgody/);assert(!el('nearby-status').textContent.includes('raw'));break;
 case 'public_query_private_body':{
  const p=c.searchNearby();assert.equal(e.calls.length,1);const call=e.calls[0];
  assert.equal(call.path,'/marketplace/nearby');assert.equal(call.options.method,'POST');assert.equal(call.options.cache,'no-store');
  assert.equal(call.options.headers.Authorization,undefined);assert.equal(JSON.parse(call.options.body).latitude_e6,52000000);
  e.pending[0](e.result());await p;assert.match(el('nearby-results').textContent,/<img src=x/);assert.equal(el('nearby-results').children.length,1);break;}
 case 'latest_request_wins':{
  const p1=c.searchNearby();el('nearby-query').value='drugie';const p2=c.searchNearby();
  e.pending[1](e.result('DRUGIE'));await p2;e.pending[0](e.result('PIERWSZE'));await p1;
  assert.match(el('nearby-results').textContent,/DRUGIE/);assert(!el('nearby-results').textContent.includes('PIERWSZE'));break;}
 case 'input_invalidates_response':{
  const p=c.searchNearby();el('nearby-lat').value='53';el('nearby-form').oninput();e.pending[0](e.result());await p;
  assert.equal(el('nearby-results').children.length,0);assert.equal(el('nearby-submit').disabled,false);break;}
 case 'logout_clears_coordinates':
  el('nearby-geolocate').onclick();c.sessionEpoch++;c.resetNearbySearch();e.geoCalls[0][0]({coords:{latitude:51,longitude:17}});
  assert.equal(el('nearby-lat').value,'');assert.equal(el('nearby-lon').value,'');assert.equal(e.calls.length,0);break;
 case 'reset_aborts_pending_response':{
  const p=c.searchNearby();c.resetNearbySearch();assert.equal(e.calls[0].options.signal.aborted,true);e.pending[0](e.result());await p;
  assert.equal(el('nearby-results').children.length,0);assert.equal(el('nearby-next').hidden,true);break;}
 case 'stale_cart_button_cannot_write':{
  const p=c.searchNearby();e.pending[0](e.result());await p;
  const card=el('nearby-results').children[0],button=card.children.find(n=>n.tag==='button');assert(button);
  c.sessionEpoch++;c.role='rolnik';await button.onclick();assert.equal(e.calls.filter(x=>x.api).length,0);break;}
 case 'point_owner_switch_clears_old_result':{
  c.role='rolnik';let resolve;c.api=()=>new Promise(r=>resolve=r);const p=c.loadPointEditor();
  c.sessionEpoch++;c.role='klient';c.refreshNearbyRole();resolve([{id:1,name:'Private old account point',active:1}]);await p;
  assert.equal(el('point-location-panel').hidden,true);assert.equal(el('point-edit-select').children.length,0);break;}
 case 'point_edit_coordinates_atomic':{
  c.role='rolnik';c.api=async(...args)=>{e.calls.push({api:args});return args[0]==='/farmers/me/pickup-points'?[{id:8,name:'Punkt',city:'Opole',street:'Polna 1',opening_hours:'9-17',active:1,latitude_e6:52000000,longitude_e6:16000000}]:{};};
  await c.loadPointEditor();el('point-edit-clear-coordinates').checked=true;await c.savePointEditor();
  const call=e.calls.find(x=>x.api&&x.api[1]==='PUT');assert(call);assert.equal(call.api[0],'/pickup-points/8');
  assert.equal(call.api[2].clear_coordinates,true);assert.equal(call.api[2].latitude_e6,undefined);assert.equal(call.api[2].active,true);break;}
 case 'price_range_blocks_fetch':
  el('nearby-min-price').value='2';el('nearby-max-price').value='1';await assert.rejects(()=>c.searchNearby());assert.equal(e.calls.length,0);break;
 case 'error_and_retry':{
  const p=c.searchNearby();e.pending[0]({ok:false,json:async()=>({detail:'Błąd kontrolowany'})});await p;
  assert.equal(el('nearby-status').textContent,'Błąd kontrolowany');assert.equal(el('nearby-submit').disabled,false);
  const p2=c.searchNearby();e.pending[1](e.result('OK'));await p2;assert.match(el('nearby-results').textContent,/OK/);break;}
 default:throw Error('Unknown case');
 }
 process.stdout.write(name+': PASS\n');
}
main(process.argv[2]).catch(error=>{console.error(error);process.exitCode=1;});
