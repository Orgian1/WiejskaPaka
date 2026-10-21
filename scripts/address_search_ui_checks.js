const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function element(){return {value:'',hidden:true,disabled:false,required:true,textContent:'',children:[],listeners:{},
  append(item){this.children.push(item)},replaceChildren(){this.children=[]},
  addEventListener(event,handler){this.listeners[event]=handler}}}
const fields=new Map();
const el=id=>{if(!fields.has(id))fields.set(id,element());return fields.get(id)};
const requests=[];
const context=vm.createContext({el,node:()=>element(),sessionEpoch:1,AbortController,
  invalidateNearby(){},act:fn=>fn(),fetch:async(url,options)=>{
    if(url==='/address-search/config')return {ok:true,json:async()=>({enabled:true})};
    assert.equal(url,'/address-search');assert.equal(options.method,'POST');
    assert(!('Authorization' in options.headers));
    assert.equal(JSON.parse(options.body).city,'Legnica');
    return new Promise(resolve=>requests.push(resolve));
  }});
vm.runInContext(fs.readFileSync('web/nearby.js','utf8').split('function invalidateNearby(){')[0],context);
vm.runInContext(fs.readFileSync('web/address-search.js','utf8'),context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await tick();assert.equal(el('address-fields').hidden,false);
  assert.equal(el('nearby-manual-coordinates').hidden,true);
  el('address-city').value='Legnica';
  const stale=context.findAddress();await tick();
  el('address-city').listeners.input();
  requests.shift()({ok:true,json:async()=>({items:[{label:'Stary adres',latitude_e6:51000000,longitude_e6:16000000}]})});
  await stale;assert.equal(el('address-results').children.length,0);
  const current=context.findAddress();await tick();
  requests.shift()({ok:true,json:async()=>({items:[{label:'Wybrany adres',latitude_e6:51123456,longitude_e6:16123456,notice:'Orientacyjny punkt'}]})});
  await current;assert.equal(el('address-results').children.length,1);
  assert.equal(el('nearby-lat').value,''); // Never auto-select the first result.
  el('address-results').children[0].onclick();
  assert.equal(el('nearby-lat').value,'51,123456');
  el('nearby-geolocate').listeners.click();
  assert.equal(el('nearby-lat').value,'');assert.equal(el('nearby-lon').value,'');
  assert(!el('address-status').textContent.includes('Wybrano'));
  el('address-street').listeners.input();
  assert.equal(el('nearby-lat').value,'');assert.equal(el('nearby-lon').value,'');
  let stopped=false;el('nearby-form').listeners.submit({preventDefault(){},stopImmediatePropagation(){stopped=true}});
  assert(stopped);
  console.log('Address selection, invalidation and stale responses: PASS');
})().catch(error=>{console.error(error);process.exitCode=1});
