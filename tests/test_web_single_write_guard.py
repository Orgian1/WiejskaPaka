"""Real Node.js behavior test: repeated clicks must not repeat mutations."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_single_write_guards_pending_request_and_recovers_after_error():
    if not shutil.which('node'):
        pytest.skip('Node.js unavailable')
    js = (ROOT / 'web/app.js').read_text(encoding='utf-8')
    snippet = js[js.index('const pendingWrites = new Set();'):js.index("el('register').onclick=", js.index('const pendingWrites = new Set();'))]
    runner = r'''
const assert = require('node:assert/strict');
''' + snippet + r'''
(async()=>{
  let resolve;
  const button={disabled:false};
  let calls=0;
  const task=()=>{calls++;return new Promise(r=>resolve=r)};
  const first=singleWrite('save',button,task);
  assert.equal(button.disabled,true);
  await singleWrite('save',button,task);
  assert.equal(calls,1);
  resolve();await first;
  assert.equal(button.disabled,false);
  assert.equal(pendingWrites.size,0);
  await assert.rejects(singleWrite('save',button,async()=>{throw Error('network')}),/network/);
  assert.equal(button.disabled,false);
  assert.equal(pendingWrites.size,0);
  await singleWrite('save',button,async()=>{calls++});
  assert.equal(calls,2);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result = subprocess.run(['node', '-e', runner], cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_mutating_forms_use_single_write_guard():
    js = (ROOT / 'web/app.js').read_text(encoding='utf-8')
    for key in ('register', 'new-product', 'profile-form', 'point-form'):
        assert f"singleWrite('{key}'" in js
    assert "querySelector('button')" in js
