const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
async function main(name){
 const source=fs.readFileSync('web/app.js','utf8'),elements={},calls=[],pending=[];
 const el=id=>elements[id]||(elements[id]={value:'',textContent:'',disabled:false});
 const ctx=vm.createContext({el,URLSearchParams,catalogOffset:0,catalogMore:false,catalogLoading:false,catalogPageSize:24,productRequest:1,sessionEpoch:1,
  api:path=>{calls.push(path);return new Promise((resolve,reject)=>pending.push({resolve,reject}))}});
 vm.runInContext(source.slice(source.indexOf('function resetCatalogView()'),source.indexOf('async function loadProducts()')),ctx);
 const item={id:1,farmer_id:2,name:'Fikcyjne warzywa',price_grosze:299,delivery_grosze:501,stock:10};
 const page=(offset=0,total=50,count=24)=>({offset,total,limit:24,items:Array.from({length:count},()=>({...item}))});
 if(name==='last')ctx.catalogOffset=48;
 if(name==='cap')ctx.catalogOffset=9984;
 if(name==='encoded')el('catalog-query').value='żółte & limit=1000';
 if(name==='long_query')el('catalog-query').value='x'.repeat(121);
 const first=ctx.catalogPage(1,1);
 if(name==='long_query'){assert.equal(await first,null);assert.equal(calls.length,0);assert.equal(ctx.catalogLoading,false);return}
 assert(ctx.catalogLoading);assert(el('catalog-next').disabled);
 const params=new URL(calls[0],'http://local.invalid').searchParams;
 assert.equal(params.get('limit'),'24');assert.equal(Number(params.get('offset')),ctx.catalogOffset);
 if(name==='encoded')assert.equal(params.get('q'),'żółte & limit=1000');
 if(name==='switch'){
  ctx.sessionEpoch++;ctx.resetCatalogView();pending[0].resolve(page());assert.equal(await first,null);
  assert.equal(el('catalog-status').textContent,'');assert.equal(ctx.catalogLoading,false);return;
 }
 if(name==='stale'){
  ctx.productRequest=2;ctx.catalogOffset=24;const second=ctx.catalogPage(2,1);pending[1].resolve(page(24));await second;
  const status=el('catalog-status').textContent;pending[0].resolve(page());assert.equal(await first,null);
  assert.equal(el('catalog-status').textContent,status);assert.match(status,/Strona 2/);assert.equal(ctx.catalogLoading,false);return;
 }
 if(name==='network'){pending[0].reject(Error('private-network-info'));assert.equal(await first,null);assert(!el('catalog-status').textContent.includes('private-network-info'));assert.equal(ctx.catalogLoading,false);return}
 let data=name==='last'?page(48,50,2):name==='empty'?page(0,0,0):name==='cap'?page(9984,10040):page();
 if(name==='wrong_offset')data.offset=1;
 if(name==='wrong_limit')data.limit=100;
 if(name==='too_many')data=page(0,50,25);
 if(name==='unsafe_total')data.total=Number.MAX_SAFE_INTEGER+1;
 if(name==='float_money')data.items[0].price_grosze=2.99;
 if(name==='boolean_stock')data.items[0].stock=true;
 if(name==='malformed')data=[];
 pending[0].resolve(data);const result=await first;
 if(['wrong_offset','wrong_limit','too_many','unsafe_total','float_money','boolean_stock','malformed'].includes(name)){
  assert.equal(result,null);assert.match(el('catalog-status').textContent,/Nie udało/);assert.equal(ctx.catalogLoading,false);assert(el('catalog-next').disabled);return;
 }
 assert.equal(result,data.items);assert.equal(ctx.catalogLoading,false);
 if(name==='cap'){assert(el('catalog-next').disabled);assert.match(el('catalog-status').textContent,/Zawęź/)}
 else assert.equal(el('catalog-next').disabled,['empty','last'].includes(name));
 assert.equal(el('catalog-previous').disabled,!['last','cap'].includes(name));
}
main(process.argv[2]).then(()=>process.stdout.write('PASS\n')).catch(e=>{console.error(e);process.exitCode=1});
