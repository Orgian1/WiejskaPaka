"""Run real JS with controlled DOM/network/downloads. Not a Chromium substitute."""
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case',[
 'render_safe_original','logout_ignores_reply','detached_card_ignores_reply','latest_reply_wins',
 'legacy_has_no_invented_terms','error_is_generic','courier_cannot_request_record','private_json_download',
 'logout_blocks_download','shipment_one_delivery_and_point','button_prevents_duplicate_fetch','shipment_details_stale_guard',
])
def test_purchase_record_javascript_behaviour(case):
    result=subprocess.run(['node','scripts/purchase_record_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('helper,scenario',[
 ('shipmentFinancialHistoryButton','detached'),
 ('shipmentFinancialHistoryButton','role_changed'),
 ('shipmentFinancialHistoryButton','latest'),
 ('shipmentDetailsButton','detached'),
 ('shipmentDetailsButton','latest'),
])
def test_existing_shipment_panels_reject_stale_responses(helper,scenario):
    # Reuse the controlled DOM/fetch implementation but execute actual dashboard code.
    harness=(ROOT/'scripts/purchase_record_ui_checks.js').read_text().split('\nmain(process.argv[2]).catch',1)[0]
    harness+='''
async function additionalScenario(helper,scenario){
 const e=env(),c=e.c,card=e.card;c.el=()=>new e.Element();
 vm.runInContext(fs.readFileSync('web/dashboard.js','utf8'),c);
 const financial=helper==='shipmentFinancialHistoryButton';
 const data=label=>financial?{products_grosze:100,delivery_grosze:1,total_grosze:101,
   refund_grosze:0,delivery_consistent:true,orders:[{order_id:label,events:[]}]}:
   {items:[{product_id:label,quantity:1}],delivery_grosze:1,total_grosze:101};
 const first=c[helper]('WPS-1',card).onclick();await Promise.resolve();
 if(scenario==='latest'){
   const second=c[helper]('WPS-1',card).onclick();await Promise.resolve();
   e.pending[1].resolve(data('CURRENT'));await second;
   const rendered=card.textContent;assert(rendered.includes('CURRENT'));
   e.pending[0].resolve(data('STALE'));await first;
   assert.equal(card.textContent,rendered);assert(!card.textContent.includes('STALE'));
 }else{
   if(scenario==='detached')card.isConnected=false;
   else c.role='rolnik';
   e.pending[0].resolve(data('PRIVATE'));await first;
   assert.equal(card.children.length,0);
 }
}
additionalScenario(process.argv[1],process.argv[2]).catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',harness,helper,scenario],cwd=ROOT,capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
