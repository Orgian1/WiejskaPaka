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
    assert parsed.ids['contact-disclosure'][0]=='details'
    assert 'open' not in parsed.ids['contact-disclosure'][1]
    assert parsed.ids['footer-contact-toggle'][0]=='summary'
    assert 'footer-contact-link' not in parsed.ids and 'footer-report-link' not in parsed.ids
    assert parsed.ids['contact-form'][1]['method']=='post'
    assert 'disabled' in parsed.ids['contact-submit'][1]
    assert parsed.ids['contact-email'][1]['type']=='email'
    assert parsed.ids['contact-message'][1]['maxlength']=='4000'
    assert html.index('</main>')<html.index('class="site-footer"')<html.index('id="contact-section"')


def test_topic_switch_keeps_draft_and_submit_never_sends_or_claims_success():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const handlers={},nodes={'contact-form':{reset(){nodes['contact-topic'].value='contact'},addEventListener:(type,fn)=>handlers[type]=fn},
'contact-topic':{value:'contact'},'contact-status':{textContent:''},'contact-disclosure':{open:false,addEventListener:(type,fn)=>handlers[type]=fn}};
const ctx={document:{getElementById:id=>nodes[id]},fetch(){throw Error('Unexpected network request')},localStorage:{setItem(){throw Error('Unexpected persistence')}}};
vm.runInNewContext(fs.readFileSync('web/contact.js','utf8'),ctx);
nodes['contact-topic'].value='problem';nodes['contact-disclosure'].open=true;handlers.toggle();
assert.equal(nodes['contact-topic'].value,'problem');
let prevented=false;handlers.submit({preventDefault(){prevented=true}});
assert(prevented);assert.match(nodes['contact-status'].textContent,/nie została wysłana/);
ctx.resetContactView();assert.equal(nodes['contact-disclosure'].open,false);assert.equal(nodes['contact-topic'].value,'contact');
'''
    result = subprocess.run(['node', '-e', script], cwd=ROOT,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout+result.stderr
