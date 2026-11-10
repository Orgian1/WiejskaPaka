"""Regresja: stary timer nie może ukryć nowego komunikatu UI."""
from pathlib import Path
import subprocess
import shutil
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_notice_timeout_does_not_hide_newer_message():
    if not shutil.which('node'):
        pytest.skip('Node.js niedostępny')
    js = (ROOT / 'web/app.js').read_text(encoding='utf-8')
    start = js.index('let noticeVersion = 0;')
    end = js.index('async function api(', start)
    source = js[start:end]
    runner = r'''
const assert = require('node:assert/strict');
let seq=0;
const timers=new Map();
const notice={textContent:'',visible:false,classList:{add(k){assert.equal(k,'show');notice.visible=true},remove(k){assert.equal(k,'show');notice.visible=false}}};
const el=id=>{assert.equal(id,'notice');return notice};
const setTimeout=(cb,delay)=>{assert.equal(delay,6500);const id=++seq;timers.set(id,cb);return id};
const clearTimeout=id=>timers.delete(id);
''' + source + r'''
msg('Pierwszy');
assert.equal(notice.textContent,'Pierwszy');
assert.equal(notice.visible,true);
const first=seq;
msg('Drugi');
assert.equal(notice.textContent,'Drugi');
assert.equal(timers.has(first),true);
timers.get(first)();
assert.equal(notice.visible,true);
assert.equal(notice.visible,true);
for(const cb of [...timers.values()])cb();
assert.equal(notice.visible,false);
assert.equal(noticeVersion,2);
msg('Trzeci');
assert.equal(notice.visible,true);
'''
    result = subprocess.run(['node', '-e', runner], cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
