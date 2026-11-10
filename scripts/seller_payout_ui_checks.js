const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const context=vm.createContext({el:()=>({})});
vm.runInContext(fs.readFileSync('web/dashboard.js','utf8'),context);
const report={eligible_grosze:181254,pending_grosze:181254,paid_out_grosze:999,platform_commission_earned_grosze:12345,platform_commission_paid_out_grosze:50,eligible_orders:2,paid_orders:1,next_weekly_payout_date:'2026-10-19',orders:[]};
const chosen=process.argv[2];
if(chosen==='zero'){for(const key of Object.keys(report))if(typeof report[key]==='number')report[key]=0}
if(chosen==='maximum'){report.eligible_grosze=report.pending_grosze=Number.MAX_SAFE_INTEGER}
const mutations={float:['eligible_grosze',1.5],boolean:['paid_orders',true],negative:['paid_out_grosze',-1],unsafe:['eligible_grosze',Number.MAX_SAFE_INTEGER+1],string:['eligible_grosze','100'],invalid_date:['next_weekly_payout_date','2026-02-30'],injected_date:['next_weekly_payout_date','<img src=x>'],mismatch:['pending_grosze',7],bad_commission:['platform_commission_paid_out_grosze',99999],missing:['eligible_orders',undefined]};
if(mutations[chosen]){const [key,value]=mutations[chosen];report[key]=value;assert.throws(()=>context.sellerPayoutSummaryLines(report));process.stdout.write('PASS\n');process.exit(0)}
const lines=Array.from(context.sellerPayoutSummaryLines(report));
assert.equal(lines.length,6);assert.match(lines[4],/19\.10\.2026/);assert.match(lines[5],/Nie wykonano przelewu/);
if(chosen==='maximum')assert.match(lines[0],/90071992547409,91 zł/);
else if(chosen==='zero'){assert.match(lines[0],/0,00 zł/);assert.match(lines[0],/pozycje zamówień: 0/)}
else {assert.match(lines[0],/1812,54 zł/);assert.match(lines[0],/pozycje zamówień: 2/);assert.match(lines[1],/9,99 zł/);assert.match(lines[2],/123,45 zł/)}
assert(!lines.join(' ').includes('eligible_grosze'));
process.stdout.write('PASS\n');
