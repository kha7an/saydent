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
    def __init__(self, filename='index.html'):
        super().__init__()
        self.elements = []
        self.feed((ROOT / filename).read_text())

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

    def test_external_services_require_a_link_click(self):
        for tag, attrs in self.elements:
            if tag != 'a':
                for key in ('src', 'href'):
                    self.assertFalse(urlsplit(attrs.get(key, '')).netloc, attrs)
        self.assertTrue(any(tag == 'a' and attrs.get('href', '').startswith('https://yandex.ru/maps/?rtext=')
                            for tag, attrs in self.elements))

    def test_external_links_are_safe(self):
        for tag, attrs in self.elements:
            if tag == 'a' and attrs.get('target') == '_blank':
                self.assertIn('noopener', attrs.get('rel', '').split())

    def test_prices_include_all_sections_and_preserve_service_conditions(self):
        class Prices(HTMLParser):
            def __init__(self):
                super().__init__()
                self.sections = []
                self.in_prices = False
                self.cell = None

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'section':
                    self.in_prices = attrs.get('id') == 'prices'
                if not self.in_prices:
                    return
                if tag == 'details':
                    self.sections.append([])
                if tag == 'tr':
                    self.row = []
                if tag in ('th', 'td'):
                    self.cell = ''

            def handle_data(self, data):
                if self.in_prices and self.cell is not None:
                    self.cell += data

            def handle_endtag(self, tag):
                if not self.in_prices:
                    return
                if tag in ('th', 'td'):
                    self.row.append(' '.join(self.cell.split()))
                    self.cell = None
                if tag == 'tr' and len(self.row) == 2:
                    self.sections[-1].append(self.row)
                if tag == 'section':
                    self.in_prices = False

        prices = Prices()
        prices.feed((ROOT / 'index.html').read_text())
        self.assertEqual([len(rows) for rows in prices.sections], [19, 20, 27, 38, 1])
        rows = [row for section in prices.sections for row in section]
        self.assertEqual(sum(price == '0 ₽' for _, price in rows), 3)
        self.assertIn(['Повторный прием,запланированный врачом', '0 ₽'], rows)
        self.assertIn(['Внутрикостная дентальная имплантация (операция All on 4)', '180 000 ₽'], rows)
        self.assertIn(['Восстановление зуба коронкой на имплантате Neobiotech(цирконевая коронка)', '34 900 ₽'], rows)
        self.assertIn(['Прицельный снимок', '300 ₽'], rows)
        self.assertTrue(all(price.endswith(' ₽') and price[:-2].replace(' ', '').isdigit()
                            for _, price in rows))

    def test_privacy_documents_are_linked_and_work_without_javascript(self):
        links = [attrs.get('href') for tag, attrs in self.elements if tag == 'a']
        self.assertGreaterEqual(links.count('privacy.html'), 3)
        self.assertIn('consent.html', links)
        self.assertFalse(any('data-policy' in attrs for _, attrs in self.elements))
        for filename in ('privacy.html', 'consent.html'):
            elements = Page(filename).elements
            self.assertEqual(sum(tag == 'h1' for tag, _ in elements), 1)
            self.assertFalse(any(tag == 'script' for tag, _ in elements))
            for tag, attrs in elements:
                for key in ('href', 'src'):
                    url = urlsplit(attrs.get(key, ''))
                    if not url.scheme and not url.netloc and url.path:
                        self.assertTrue((ROOT / unquote(url.path)).is_file())
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
    def test_cookie_notice_remembers_dismissal_and_handles_blocked_cookies(self):
        script = r"""
const assert = require('node:assert/strict');
const source = require('node:fs').readFileSync('script.js', 'utf8');
const block = source.slice(source.indexOf('  const cookieNotice ='), source.indexOf('  const appointmentForm ='));
for (const [cookies, hidden] of [['', false], ['other=1; saydent_cookie_notice=1', true], ['saydent_cookie_notice=10', false]]) {
  for (const protocol of ['http:', 'https:']) {
    const notice = {hidden: true}, button = {};
    const document = {cookie: cookies, querySelector: selector => selector === '#cookie-notice' ? notice : button};
    button.addEventListener = (type, handler) => { button.click = handler; };
    require('node:vm').runInNewContext(block, {document, window: {location: {protocol}}});
    assert.equal(notice.hidden, hidden);
    button.click();
    assert.equal(notice.hidden, true);
    assert.equal(document.cookie, 'saydent_cookie_notice=1; Max-Age=15552000; Path=/; SameSite=Lax' + (protocol === 'https:' ? '; Secure' : ''));
  }
}
const notice = {}, button = {addEventListener(type, handler) { this.click = handler; }};
const document = {querySelector: selector => selector === '#cookie-notice' ? notice : button,
  get cookie() { throw Error('blocked'); }, set cookie(value) { throw Error('blocked'); }};
require('node:vm').runInNewContext(block, {document, window: {location: {protocol: 'https:'}}});
assert.equal(notice.hidden, false);
button.click();
assert.equal(notice.hidden, true);
"""
        result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for frontend behavior checks')
    def test_submit_validates_and_waits_for_server_confirmation(self):
        script = r"""
(async () => {
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
    setSelectionRange(start, end) { this.selectionStart = start; this.selectionEnd = end; },
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
let now = 1000000, calls = 0, fail = false, nextId = 0;
const requestIds = [];
const fetch = async (url, options) => {
  calls++; assert.equal(url, '/api/appointments'); assert.equal(button.disabled, true);
  const body = JSON.parse(options.body); assert.equal(body.name, 'Анна'); assert.equal(body.consent, true);
  requestIds.push(body.request_id);
  if (fail) throw new TypeError('network');
  return {ok: true, json: async () => ({ok: true})};
};
const receipt = {hidden: true};
const receiptTitle = {focus() { focused = 'receipt-title'; }};
const document = {cookie: '', querySelector: selector => ({'#appointment-receipt': receipt, '#receipt-title': receiptTitle, '#appointment-form': form, '#appointment-submit': button, '#appointment-status': status, ...errors})[selector]};
function loadForm(abortSignal = AbortSignal) {
  receipt.hidden = true; button.hidden = true; form.noValidate = false;
  require('node:vm').runInNewContext(source.slice(source.indexOf('  const appointmentForm ='), source.indexOf('  const techDetails =')), {
    document, fetch, AbortSignal: abortSignal, Date: {now: () => now}, window: {crypto: {randomUUID: () => String(++nextId)}, location: {protocol: 'https:'}}
  });
}
loadForm();
assert.equal(button.hidden, false);
assert.equal(form.noValidate, true);
for (const [value, expected] of [['Ан12на', 'Анна'], ['Jean-Luc O’Neil', 'Jean-Luc O’Neil'], ['Анна ١２3', 'Анна '], ['123', '']]) {
  name.value = value;
  name.selectionStart = name.selectionEnd = value.length;
  name.input();
  assert.equal(name.value, expected);
}
name.value = 'Ан1на';
name.selectionStart = name.selectionEnd = 3;
name.input();
assert.equal(name.value, 'Анна');
assert.equal(name.selectionStart, 2);
assert.equal(errors['#appointment-name-error'].hidden, true);
for (const [value, expected] of [['+7abc (999) тест123-45-67', '+7 (999) 123-45-67'], ['letters!?@', ''], ['++7999+1234567', '+79991234567'], ['89991234567', '89991234567']]) {
  phone.value = value;
  phone.selectionStart = phone.selectionEnd = value.length;
  phone.input();
  assert.equal(phone.value, expected);
}
phone.value = '+7ab999';
phone.selectionStart = phone.selectionEnd = 4;
phone.input();
assert.equal(phone.value, '+7999');
assert.equal(phone.selectionStart, 2);
phone.value = '12'; phone.input();
assert.equal(errors['#appointment-phone-error'].hidden, true);
name.value = '   ';
await submit({preventDefault() { prevented++; }});
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
await submit({preventDefault() { prevented++; }});
assert.equal(prevented, 2);
assert.equal(receipt.hidden, false); assert.equal(focused, 'receipt-title');
assert.equal(calls, 1); assert.equal(button.disabled, false);
assert.equal(document.cookie, 'saydent_submitted=1; Max-Age=600; Path=/; SameSite=Lax; Secure');
await submit({preventDefault() {}});
assert.match(status.textContent, /уже заполнили/);
loadForm();
await submit({preventDefault() {}});
assert.match(status.textContent, /уже заполнили/);
// Model the browser expiring the cookie after ten minutes.
now += 600000; document.cookie = '';
await submit({preventDefault() {}});
assert.equal(receipt.hidden, false); assert.equal(focused, 'receipt-title');
Object.defineProperty(document, 'cookie', {get() { throw Error('blocked'); }, set() { throw Error('blocked'); }});
loadForm();
await submit({preventDefault() {}});
assert.equal(receipt.hidden, false); assert.equal(focused, 'receipt-title');
await submit({preventDefault() {}});
assert.match(status.textContent, /уже заполнили/);
now += 600000;
await submit({preventDefault() {}});
assert.equal(receipt.hidden, false); assert.equal(focused, 'receipt-title');
assert.equal(name.value, 'Анна');
phone.value = '12'; phone.input();
assert.equal(status.textContent, '');
assert.equal(phone.attributes['aria-invalid'], 'true');
now += 600000; fail = true;
loadForm({}); // Safari versions without AbortSignal.timeout must still send.
phone.value = '+7 999 123-45-67';
await submit({preventDefault() {}});
assert.match(status.textContent, /Не удалось подтвердить/);
assert.equal(receipt.hidden, true);
assert.equal(button.disabled, false);
assert.equal(name.value, 'Анна');
fail = false;
await submit({preventDefault() {}});
assert.equal(receipt.hidden, false); assert.equal(focused, 'receipt-title');
assert.equal(requestIds.at(-1), requestIds.at(-2));
assert.notEqual(requestIds[0], requestIds[1]);
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
        result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for frontend behavior checks')
    def test_accordions_keep_groups_separate_and_show_opened_price_category(self):
        script = r"""
const assert = require('node:assert/strict');
const source = require('node:fs').readFileSync('script.js', 'utf8');
const groups = ['[data-tech]', '.price-accordion details'].map(selector =>
  [0, 1, 2].map(index => {
    const summary = {
      scrolls: 0,
      addEventListener(type, handler) { assert.equal(type, 'click'); this.click = handler; },
      scrollIntoView(options) {
        assert.equal(selector, '.price-accordion details');
        assert.equal(options.block, 'start');
        assert.equal(options.behavior, 'instant');
        assert.equal(groups[1].filter(detail => detail.open).length, 1);
        this.scrolls++;
      }
    };
    return {open: index === 0, querySelector: () => summary};
  })
);
require('node:vm').runInNewContext(source.slice(source.indexOf('  const techDetails ='), source.indexOf('  const comparisonRange =')), {
  document: {querySelectorAll: selector => groups[selector === '[data-tech]' ? 0 : 1]},
  window: {
    scrollBy() { assert.fail('Accordion must not scroll the page'); },
    scrollTo() { assert.fail('Accordion must not scroll the page'); }
  }
});
for (const [groupIndex, details] of groups.entries()) {
  const other = groups[1 - groupIndex];
  const unchanged = other.map(detail => detail.open);
  for (const index of [1, 2, 0, 0]) {
    const summary = details[index].querySelector();
    const opening = !details[index].open;
    const scrolls = summary.scrolls;
    let prevented = false;
    summary.click({preventDefault() { prevented = true; }});
    assert.ok(prevented);
    assert.deepEqual(details.map(d => d.open), details.map((d, i) => opening && i === index));
    assert.deepEqual(other.map(detail => detail.open), unchanged);
    assert.equal(summary.scrolls, scrolls + Number(groupIndex === 1 && opening));
  }
}
"""
        result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for frontend behavior checks')
    def test_reviews_navigate_all_cards_and_track_manual_scroll(self):
        script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('script.js', 'utf8');
const html = fs.readFileSync('index.html', 'utf8');
const count = [...html.matchAll(/class="review-card"/g)].length;
assert.equal(count, 5);
assert.match(html, /class="review-position"[^\n]*<span>05<\/span>/);
for (const width of [390, 1280]) {
  const cardWidth = width * .65, gap = 24;
  const cards = Array.from({length: count}, (_, i) => ({offsetLeft: 56 + i * (cardWidth + gap)}));
  const current = {}, line = {style: {setProperty(name, value) { this[name] = value; }}};
  const controls = Object.fromEntries(['#review-prev', '#review-next'].map(key => [key, {
    addEventListener(type, handler) { this[type] = handler; }
  }]));
  const track = {children: cards, clientWidth: width, scrollWidth: count * cardWidth + (count - 1) * gap, scrollLeft: 0,
    scrollTo({left, behavior}) { assert.equal(behavior, 'instant'); this.scrollLeft = Math.min(left, this.scrollWidth - width); },
    addEventListener(type, handler) { this[type] = handler; }
  };
  require('node:vm').runInNewContext(source.slice(source.indexOf('  const reviewTrack ='), source.indexOf("  if ('IntersectionObserver'")), {
    reducedMotion: {matches: true},
    document: {querySelector: selector => ({'.review-track': track, '#review-current': current, '.review-position-line': line, ...controls})[selector]}
  });
  for (let i = 1; i <= count; i++) {
    controls['#review-next'].click(); track.scroll();
    assert.equal(current.textContent, String(i % count + 1).padStart(2, '0'));
  }
  controls['#review-prev'].click(); track.scroll();
  assert.equal(current.textContent, '05');
  assert.equal(line.style['--progress'], '50%');
  for (let i = 0; i < count; i++) {
    track.scrollLeft = Math.min(cards[i].offsetLeft - cards[0].offsetLeft, track.scrollWidth - width);
    track.scroll();
    assert.equal(current.textContent, String(i + 1).padStart(2, '0'));
  }
}
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
