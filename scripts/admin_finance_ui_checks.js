const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
async function main(name){
  let active=true,clicked=0,removed=0,revoked=0,created=0;const calls=[],pending=[];
  const link={click:()=>clicked++,remove:()=>removed++};
  const ctx=vm.createContext({el:()=>({}),sessionEpoch:1,role:'admin',token:'private-test-token',
    fetch:(...args)=>{calls.push(args);return new Promise((resolve,reject)=>pending.push({resolve,reject}))},
    URL:{createObjectURL:()=>{created++;return 'blob:private-test'},revokeObjectURL:url=>{assert.equal(url,'blob:private-test');revoked++}},
    document:{createElement:()=>link,body:{append:()=>{}}},setTimeout:fn=>fn()});
  vm.runInContext(fs.readFileSync('web/dashboard.js','utf8'),ctx);
  const month='2026-10',report={month,report_type:'test_operational_snapshot_not_accounting',eligible_order_count:2,products_grosze:648,delivery_grosze:501,gross_order_grosze:1149,platform_commission_grosze:97,seller_due_grosze:1052,payment_success_event_order_count:4,refund_event_order_count:1};
  if(name==='summary'){
    const lines=Array.from(ctx.adminFinanceSummaryLines(report,month));
    assert.match(lines[0],/pozycje.*: 2/);assert.match(lines[1],/6,48 zł.*5,01 zł.*11,49 zł/);assert.match(lines[2],/0,97 zł.*10,52 zł/);
    assert.match(lines[3],/miesiącu: 4.*testowym: 1/);assert.match(lines[4],/Nie jest dokumentem księgowym/);return;
  }
  if(name==='maximum'){
    Object.assign(report,{products_grosze:Number.MAX_SAFE_INTEGER,delivery_grosze:0,gross_order_grosze:Number.MAX_SAFE_INTEGER,platform_commission_grosze:0,seller_due_grosze:Number.MAX_SAFE_INTEGER});
    assert.match(ctx.adminFinanceSummaryLines(report,month)[1],/90071992547409,91 zł/);return;
  }
  const mutations={wrong_month:['month','2026-09'],unsafe:['products_grosze',Number.MAX_SAFE_INTEGER+1],float:['delivery_grosze',0.5],negative:['seller_due_grosze',-1],boolean:['refund_event_order_count',true],wrong_type:['report_type','accounting'],inconsistent:['gross_order_grosze',10],missing:['eligible_order_count',undefined]};
  if(mutations[name]){const [key,value]=mutations[name];report[key]=value;assert.throws(()=>ctx.adminFinanceSummaryLines(report,month));return}
  if(name==='invalid_month'){await assert.rejects(ctx.downloadAdminFinanceCsv('../private',()=>active));assert.equal(calls.length,0);return}
  if(name==='logged_out'){ctx.token=null;await ctx.downloadAdminFinanceCsv(month,()=>active);assert.equal(calls.length,0);return}
  const result=ctx.downloadAdminFinanceCsv(month,()=>active);
  assert.equal(calls.length,1);assert.equal(calls[0][0],'/test/admin/finance/monthly/2026-10/export.csv');
  assert.equal(calls[0][1].headers.Authorization,'Bearer private-test-token');assert.equal(calls[0][1].cache,'no-store');
  let blobResolve;
  if(name==='stale_network_error'){active=false;pending[0].reject(Error('network failed'));await result;assert.equal(created,0);return}
  if(name==='network_error'){const rejected=assert.rejects(result);pending[0].reject(Error('network failed'));await rejected;assert.equal(created,0);return}
  if(name==='switched_session')ctx.sessionEpoch++;
  if(name==='changed_month')active=false;
  const response={ok:name!=='http_error',headers:{get:()=>name==='wrong_format'?'text/html':'text/csv; charset=utf-8'},blob:()=>new Promise(resolve=>{blobResolve=resolve})};
  const checked=['http_error','wrong_format'].includes(name)?assert.rejects(result):result;
  pending[0].resolve(response);await new Promise(resolve=>setImmediate(resolve));
  if(['switched_session','changed_month','http_error','wrong_format'].includes(name)){await checked;assert.equal(created,0);return}
  if(name==='switched_during_blob')ctx.sessionEpoch++;
  blobResolve({});await checked;
  if(name==='switched_during_blob'){assert.equal(created,0);return}
  assert.equal(clicked,1);assert.equal(removed,1);assert.equal(revoked,1);assert.equal(link.download,'wiejskapaka-test-2026-10.csv');
}
main(process.argv[2]).then(()=>process.stdout.write('PASS\n')).catch(error=>{console.error(error);process.exitCode=1});
