from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_old_promotion_responses_do_not_restore_previous_seller_after_logout():
    code = r'''
const vm=require('vm'),fs=require('fs'),assert=require('assert/strict');
const elements=new Map(), pending=[];
const el=id=>{if(!elements.has(id))elements.set(id,{hidden:false,disabled:false,value:'',textContent:'',children:[],reset(){this.value=''},replaceChildren(){this.children=[]},append(x){this.children.push(x)}});return elements.get(id)};
const context=vm.createContext({el,sessionEpoch:1,role:'rolnik',api:()=>new Promise(resolve=>pending.push(resolve)),
 node:(tag,text)=>({tag,text}),act:f=>f(),loadFarmer:()=>{throw Error('Old redemption must not refresh another account')}});
const run=s=>vm.runInContext(s,context);
vm.runInContext(fs.readFileSync('web/pickup-promotion.js','utf8'),context);
const data={enabled:true,active:true,redeemed:true,expired:false,remaining:2,covered_point_ids:[1]};
(async()=>{
 const old=run("loadPickupPromotion([{id:1,name:'Previous seller point'}])");
 run("sessionEpoch++;role=null;resetPickupPromotion()");
 pending.shift()(data);await old;
 assert.equal(el('pickup-promotion').hidden,true);
 assert.equal(el('pickup-promo-status').textContent,'');
 assert.equal(el('pickup-promo-points').children.length,0);
 run("sessionEpoch++;role='rolnik';resetPickupPromotion()");
 el('pickup-promo-code').value='WIEJSKAPAKA';
 el('pickup-promo-form').onsubmit({preventDefault(){}});
 assert.equal(el('pickup-promo-submit').disabled,true);
 run("sessionEpoch++;role='klient';resetPickupPromotion()");
 el('pickup-promo-code').value='new account draft';
 pending.shift()(data);await new Promise(resolve=>setTimeout(resolve,0));
 assert.equal(el('pickup-promo-code').value,'new account draft');
 assert.equal(el('pickup-promotion').hidden,true);
})().catch(error=>{console.error(error);process.exitCode=1});
'''
    result = subprocess.run(['node','-e',code],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode == 0, result.stdout+result.stderr
