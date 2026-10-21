const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
  constructor(tag,text=''){this.tag=tag;this.textContent=text;this.children=[];this.value='';this.disabled=false;this.open=false;}
  append(...children){this.children.push(...children)} replaceChildren(...children){this.children=children}
  setAttribute(){} addEventListener(){} scrollIntoView(){} remove(){this.removed=true}
  showModal(){this.open=true} close(){this.open=false}
  querySelectorAll(tag){return this.children.flatMap(child=>[...(child.tag===tag?[child]:[]),...child.querySelectorAll(tag)])}
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const product={id:1,farmer_id:7,name:'Marchew',stock:10,price_grosze:200};
const other={...product,id:2,name:'Pomidory'};
const fields=new Map(),el=id=>{if(!fields.has(id))fields.set(id,new Element('div'));return fields.get(id)};
const document={body:new Element('body'),createElement:tag=>new Element(tag)};
const writes=[];let saved=[{product_id:1,quantity:3}];
const c=vm.createContext({document,el,node:(tag,text)=>new Element(tag,text),role:'klient',sessionEpoch:1,URLSearchParams,
  saleUnitLabel:()=> 'kg',packageLabel:()=>'',money:n=>String(n),act:fn=>fn(),requireResolvedCheckout:()=>{},loadCart:async()=>{},
  api:async(path,method,body)=>{
    if(path.startsWith('/catalog/search?')){assert.equal(new URLSearchParams(path.split('?')[1]).get('farmer_id'),'7');return {items:[product,other],total:2,offset:0,limit:24}}
    if(method==='PUT'){writes.push(body);saved=saved.filter(x=>x.product_id!==body.product_id).concat(body);return {};}
    return {items:saved};
  }});
vm.runInContext(fs.readFileSync('web/same-package.js','utf8'),c);
(async()=>{
  const pending=c.offerSamePackage(product,2,true);await tick();
  let dialog=document.body.children.at(-1),list=dialog.children.find(x=>x.id==='same-package-products');
  assert.equal(list.children.length,1);assert.equal(list.children[0].children[0].textContent,'Pomidory');
  assert.equal(writes.length,0,'Opening recommendations must not place an order or change a cart');
  await list.children[0].children.at(-1).onclick();
  assert.equal(writes.length,2);assert.deepEqual(JSON.parse(JSON.stringify(writes)),[{product_id:1,quantity:5},{product_id:2,quantity:1}]);
  dialog.children.find(x=>x.id==='same-package-done').onclick();assert.equal(await pending,false,'Use one cart checkout instead of a second direct order');
  const skipped=c.offerSamePackage(product,1,true);await tick();dialog=document.body.children.at(-1);
  dialog.children.find(x=>x.id==='same-package-done').onclick();assert.equal(await skipped,true);assert.equal(writes.length,2);
  let respond;c.api=()=>new Promise(resolve=>respond=resolve);
  const stale=c.offerSamePackage(product,1,true);await tick();c.sessionEpoch++;c.resetPackageOffer();assert.equal(await stale,false);
  respond({items:[product,other],total:2,offset:0,limit:24});await tick();assert.equal(writes.length,2);
  assert.equal(document.body.children.at(-1).removed,true);
  console.log('Same seller, existing quantities, one checkout, skip and stale account: PASS');
})().catch(error=>{console.error(error);process.exitCode=1});
