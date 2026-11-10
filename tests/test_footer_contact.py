"""Public footer navigation and a contact form without mail delivery yet."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids
            self.ids[attrs['id']] = (tag, attrs)


def test_footer_links_share_public_form_with_disabled_delivery():
    parsed = Elements()
    html = (ROOT/'web/index.html').read_text()
    parsed.feed(html)
    for link in ('footer-contact-link', 'footer-report-link'):
        assert parsed.ids[link][1]['href'] == '#contact-section'
    assert 'hidden' not in parsed.ids['contact-section'][1]
    assert parsed.ids['contact-form'][1]['method'] == 'post'
    assert 'disabled' in parsed.ids['contact-submit'][1]
    assert parsed.ids['contact-email'][1]['type'] == 'email'
    assert parsed.ids['contact-message'][1]['maxlength'] == '4000'
    assert html.index('id="contact-section"') < html.index('</main>') < html.index('class="site-footer"')


def test_topic_switch_keeps_draft_and_submit_never_sends_or_claims_success():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const handlers={},links=['contact','problem'].map(type=>({dataset:{contactTopic:type},
  addEventListener(name,fn){this[name]=fn;}}));
const nodes={'contact-form':{addEventListener:(type,fn)=>handlers[type]=fn},
 'contact-topic':{value:'contact'},'contact-status':{textContent:''},
 'contact-heading':{focus(){this.focused=true;}}};
const document={getElementById:id=>nodes[id],querySelectorAll:()=>links};
const ctx={document,fetch(){throw Error('Unexpected network request');},
 localStorage:{setItem(){throw Error('Unexpected persistence');}}};
vm.runInNewContext(fs.readFileSync('web/contact.js','utf8'),ctx);
links[1].click();assert.equal(nodes['contact-topic'].value,'problem');
assert.equal(nodes['contact-heading'].focused,true);
links[0].click();assert.equal(nodes['contact-topic'].value,'contact');
let prevented=false;handlers.submit({preventDefault(){prevented=true;}});
assert.equal(prevented,true);
assert.match(nodes['contact-status'].textContent,/nie została wysłana/);
'''
    result = subprocess.run(['node', '-e', script], cwd=ROOT,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout+result.stderr
