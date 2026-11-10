from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def test_remembered_locations_are_account_scoped_and_corrupt_storage_is_rejected():
    code=r'''
const vm=require('vm'),fs=require('fs'),assert=require('assert/strict');
const store=new Map(),els=new Map();
const el=id=>{if(!els.has(id))els.set(id,{value:'',textContent:'',addEventListener(){},replaceChildren(){}});return els.get(id);};
const context=vm.createContext({el,document:{querySelectorAll:()=>[]},sessionEpoch:1,role:'klient',
 coordinateText:x=>String(x),msg(){},act(){},location:{hash:''},
 localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)}});
vm.runInContext(fs.readFileSync('web/market-preferences.js','utf8'),context);
const run=s=>vm.runInContext(s,context);
run("refreshMarketPreferences({id:3,email:'one@example.invalid'})");
run('rememberNearbyLocation({latitude_e6:51210000,longitude_e6:16160000,radius_m:1000})');
assert.equal(store.size,1);assert.equal(JSON.parse([...store.values()][0]).location.lat,51210000);
run("refreshMarketPreferences({id:3,email:'two@example.invalid'})");
assert.equal(run('marketPreferences.location'),null);
run("refreshMarketPreferences({id:3,email:'one@example.invalid'})");
assert.equal(el('nearby-lat').value,'51210000');
run('forgetNearbyLocation()');assert.equal(JSON.parse([...store.values()][0]).location,null);
store.set('broken','not-json');assert.equal(run("readMarketPreferences('broken').location"),null);
store.set('broken',JSON.stringify({favorites:[1,1,-1,'2',null],location:{lat:999999999,lon:0,radius:1000}}));
assert.equal(run("JSON.stringify(readMarketPreferences('broken').favorites)"),'[1]');
assert.equal(run("readMarketPreferences('broken').location"),null);
run('refreshMarketPreferences(null)');assert.equal(run('marketOwner'),null);
'''
    result=subprocess.run(['node','-e',code],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
