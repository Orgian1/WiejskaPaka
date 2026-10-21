const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
  constructor(tag='div',text=''){this.tag=tag;this.textContent=text;this.children=[];this.value='';this.hidden=false;this.disabled=false;}
  append(...nodes){this.children.push(...nodes)} replaceChildren(...nodes){this.children=[...nodes]}
  get firstChild(){return this.children[0]} reset(){el('seller-public-login').value=''}
}
const fields=new Map(),el=id=>{if(!fields.has(id))fields.set(id,new Element());return fields.get(id)};
el('catalog-query-label').append(new Element('text','Nazwa produktu '));
const row={farmer_id:7,login:'warzywa_marka',farm_name:'Łąka',city:'Legnica'};
const c=vm.createContext({el,node:(tag,text)=>new Element(tag,text),role:'klient',sessionEpoch:1,
  catalogSellerId:null,catalogOffset:0,productRequest:0,URLSearchParams,
  fetch:async()=>({ok:true,json:async()=>({enabled:false})}),act:fn=>fn(),singleWrite:(_,b,fn)=>fn(),loadProducts:async()=>{},
  api:async()=>({items:[row],total:1,limit:24,offset:0})});
const tick=()=>new Promise(r=>setImmediate(r));
vm.runInContext(fs.readFileSync('web/seller-search.js','utf8'),c);
(async()=>{
  await tick();vm.runInContext('sellerSearchEnabled=true',c);el('catalog-search-mode').value='seller';
  await c.loadSellerDirectory();assert.equal(el('seller-results').children.length,1);
  const card=el('seller-results').children[0];assert.equal(card.children[0].textContent,'@warzywa_marka');
  card.children.find(n=>n.tag==='button').onclick();assert.equal(c.catalogSellerId,7);
  assert.equal(el('catalog-search-mode').value,'product');assert.equal(el('catalog-seller-filter').hidden,false);
  let finish;c.api=()=>new Promise(resolve=>finish=resolve);el('catalog-search-mode').value='seller';
  const stale=c.loadSellerDirectory();await tick();el('catalog-search-mode').value='product';
  finish({items:[row],total:1,limit:24,offset:0});await stale;assert.equal(el('seller-results').children.length,0);
  c.role='rolnik';el('seller-public-login').value='';
  const privateRead=c.loadSellerLoginEditor();await tick();assert.equal(el('seller-login-panel').hidden,true);
  c.sessionEpoch++;c.role='klient';c.resetSellerDirectory();finish({login:'previous_account'});await privateRead;
  assert.equal(el('seller-public-login').value,'');assert.equal(el('seller-login-panel').hidden,true);
  assert.equal(c.catalogSellerId,null);
  console.log('Seller selection, stale mode response and account isolation: PASS');
})().catch(error=>{console.error(error);process.exitCode=1});
