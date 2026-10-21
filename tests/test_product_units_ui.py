import subprocess
from pathlib import Path


def test_real_unit_formatters_render_quantities_and_package_content():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(['node', '-e', '''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c=vm.createContext({});
vm.runInContext(fs.readFileSync('web/app.js','utf8').split('let saleUnitsEnabled=false;')[0],c);
assert.equal(c.saleUnitLabel({sale_unit:'kg'}),'kg');
assert.equal(c.saleUnitLabel({sale_unit:'szt'}),'szt.');
assert.equal(c.saleUnitLabel({}),'szt.');
assert.equal(c.packageLabel({package_content:{amount_atoms:750,unit:'l'}}),' • zawartość: 0,75 l');
assert.equal(c.packageLabel({package_content:{amount_atoms:250,unit:'g'}}),' • zawartość: 250 g');
assert.equal(c.packageLabel({}), '');
assert(!c.saleUnitLabel({sale_unit:'<img src=x>'}).includes('<'));
'''], cwd=root, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
