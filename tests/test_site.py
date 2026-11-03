"""Static-site integrity checks; run with python3 -m unittest discover -s tests."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.feed((ROOT / 'index.html').read_text())

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.elements = Page().elements
        self.ids = [attrs['id'] for _, attrs in self.elements if 'id' in attrs]

    def test_unique_ids_and_reference_targets(self):
        self.assertEqual([key for key, count in Counter(self.ids).items() if count > 1], [])
        for _, attrs in self.elements:
            for key in ('aria-labelledby', 'aria-describedby', 'aria-controls', 'for'):
                for target in attrs.get(key, '').split():
                    self.assertIn(target, self.ids)
            if attrs.get('href', '').startswith('#'):
                self.assertIn(attrs['href'][1:], self.ids)

    def test_local_resources_exist_and_images_reserve_space(self):
        for tag, attrs in self.elements:
            for key in ('src', 'href'):
                url = urlsplit(attrs.get(key, ''))
                if url.scheme or url.netloc or not url.path:
                    continue
                resource = ROOT / unquote(url.path)
                self.assertTrue(resource.is_file(), str(resource))
                self.assertGreater(resource.stat().st_size, 0)
            if tag == 'img':
                self.assertTrue(attrs.get('alt'))
                self.assertGreater(int(attrs['width']), 0)
                self.assertGreater(int(attrs['height']), 0)

    def test_external_links_are_safe(self):
        for tag, attrs in self.elements:
            if tag == 'a' and attrs.get('target') == '_blank':
                self.assertIn('noopener', attrs.get('rel', '').split())

    def test_appointment_preview_fields_cannot_send_personal_data_without_js(self):
        self.assertTrue(any(tag == 'a' and attrs.get('href') == 'tel:+79509499325'
                            for tag, attrs in self.elements))
        inputs = {attrs['id']: attrs for tag, attrs in self.elements if tag == 'input'}
        for field in ('appointment-name', 'appointment-phone', 'appointment-consent'):
            self.assertIn('required', inputs[field])
            self.assertNotIn('name', inputs[field])
        self.assertNotIn('checked', inputs['appointment-consent'])
        submit = next(attrs for tag, attrs in self.elements if attrs.get('id') == 'appointment-submit')
        self.assertIn('hidden', submit)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for frontend behavior checks')
    def test_preview_submit_prevents_navigation_and_validates_without_sending(self):
        script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('script.js', 'utf8');
const html = fs.readFileSync('index.html', 'utf8');
const pattern = new RegExp('^(?:' + html.match(/id="appointment-phone"[^>]*pattern="([^"]+)"/)[1] + ')$', 'v');
for (const value of ['+7 (999) 123-45-67', '89991234567', '1234567890', '+123456789012345']) assert.ok(pattern.test(value), value);
for (const value of ['123456789', '+1234567890123456', '+7call9991234567', '++79991234567']) assert.ok(!pattern.test(value), value);
let submit, prevented = 0, focused;
const button = {hidden: true};
const status = {textContent: ''};
const errors = {};
function field(id, type) {
  errors['#' + id + '-error'] = {hidden: true, textContent: ''};
  return {id, type, value: '', checked: false, attributes: {},
    get validity() {
      const valueMissing = type === 'checkbox' ? !this.checked : !this.value;
      return {valueMissing, valid: !valueMissing && (type !== 'tel' || pattern.test(this.value))};
    },
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(type, handler) { this[type] = handler; },
    focus() { focused = id; }
  };
}
const name = field('appointment-name', 'text');
const phone = field('appointment-phone', 'tel');
const consent = field('appointment-consent', 'checkbox');
const form = {noValidate: false, querySelectorAll: () => [name, phone, consent], addEventListener(type, handler) {
  assert.equal(type, 'submit'); assert.equal(button.hidden, true); assert.equal(this.noValidate, false); submit = handler;
}};
require('node:vm').runInNewContext(source.slice(source.indexOf('  const appointmentForm ='), source.indexOf('  const techDetails =')), {
  document: {querySelector: selector => ({'#appointment-form': form, '#appointment-submit': button, '#appointment-status': status, ...errors})[selector]}
});
assert.equal(button.hidden, false);
assert.equal(form.noValidate, true);
phone.value = '12'; phone.input();
assert.equal(errors['#appointment-phone-error'].hidden, true);
name.value = '   ';
submit({preventDefault() { prevented++; }});
assert.equal(status.textContent, '');
assert.equal(focused, 'appointment-name');
assert.equal(errors['#appointment-name-error'].textContent, 'Укажите ваше имя.');
assert.match(errors['#appointment-phone-error'].textContent, /от 10 до 15/);
assert.match(errors['#appointment-consent-error'].textContent, /Подтвердите согласие/);
phone.value = ''; phone.input();
assert.equal(errors['#appointment-phone-error'].textContent, 'Укажите номер телефона.');
name.value = 'Анна'; name.input();
phone.value = '+7 999 123-45-67'; phone.input();
consent.checked = true; consent.change();
for (const input of [name, phone, consent]) {
  assert.equal(input.attributes['aria-invalid'], 'false');
  assert.equal(errors['#' + input.id + '-error'].hidden, true);
}
submit({preventDefault() { prevented++; }});
assert.equal(prevented, 2);
assert.match(status.textContent, /Отправка пока недоступна/);
assert.match(status.textContent, /950 949-93-25/);
assert.equal(name.value, 'Анна');
phone.value = '12'; phone.input();
assert.equal(status.textContent, '');
assert.equal(phone.attributes['aria-invalid'], 'true');
"""
        result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for frontend behavior checks')
    def test_comparison_reveals_before_and_after_at_range_limits(self):
        script = r"""
const assert = require('node:assert/strict');
const source = require('node:fs').readFileSync('script.js', 'utf8');
let input, reveal;
const range = {hidden: true, value: '50', parentElement: {style: {
  setProperty(name, value) { assert.equal(name, '--reveal'); reveal = value; }
}}, addEventListener(name, handler) { assert.equal(name, 'input'); input = handler; }};
require('node:vm').runInNewContext(source.slice(source.indexOf('  const comparisonRange ='), source.indexOf('  const reviewTrack =')), {
  document: {querySelector(selector) { assert.equal(selector, '#smile-comparison'); return range; }}
});
assert.equal(range.hidden, false);
for (const value of ['0', '50', '100']) { range.value = value; input(); assert.equal(reveal, value + '%'); }
"""
        result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)



if __name__ == '__main__':
    unittest.main()
