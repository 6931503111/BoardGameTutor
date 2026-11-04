const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup(texts, { scanText = 'ข้อความภาษาไทยที่อ่านได้จากภาพ และกติกาการเล่นเกมสำหรับตรวจสอบ '.repeat(2), onRecognize } = {}) {
    const calls = { recognized: 0, terminated: 0, destroyed: 0, cleaned: 0 };
    const pages = texts.map(text => ({
        getTextContent: async () => ({ items: [{ str: text, hasEOL: true }] }),
        getViewport: ({ scale }) => ({ width: 600 * scale, height: 800 * scale }),
        render: () => ({ promise: Promise.resolve(), cancel() {} }),
        cleanup: () => calls.cleaned++,
    }));
    const worker = {
        recognize: async () => { calls.recognized++; onRecognize?.(); return { data: { text: scanText } }; },
        terminate: async () => { calls.terminated++; },
    };
    const pdfjs = {
        GlobalWorkerOptions: {},
        getDocument: () => ({
            promise: Promise.resolve({ numPages: texts.length, getPage: async n => pages[n - 1] }),
            destroy: async () => { calls.destroyed++; },
        }),
    };
    const context = {
        window: { Tesseract: { createWorker: async () => worker } },
        document: { createElement: () => ({ getContext: () => ({}) }) },
        pdfjs, DOMException, Uint8Array,
    };
    vm.createContext(context);
    const source = fs.readFileSync(path.join(__dirname, '../../Code/pdf-ocr.js'), 'utf8')
        .replace("import(PDF_BASE + '/pdf.min.mjs')", 'Promise.resolve(pdfjs)');
    vm.runInContext(source, context);
    return { read: context.window.readPdfWithOcr, calls, file: { size: 100, arrayBuffer: async () => new ArrayBuffer(8) } };
}

test('mixed PDFs retain text pages and OCR scanned pages in original order', async () => {
    const original = 'กติกาหน้าแรกที่มีข้อความพร้อมใช้งานแล้ว '.repeat(4);
    const env = setup([original, '']);
    const result = await env.read(env.file);
    assert.ok(result.startsWith('[หน้า 1]\n' + original.trim()));
    assert.ok(result.includes('[หน้า 2]\nข้อความภาษาไทย'));
    assert.equal(env.calls.recognized, 1);
    assert.equal(env.calls.cleaned, 2);
    assert.equal(env.calls.terminated, 1);
    assert.equal(env.calls.destroyed, 1);
});

test('force OCR bypasses an existing but defective text layer', async () => {
    const env = setup(['garbled text layer '.repeat(10)]);
    const result = await env.read(env.file, { forceOcr: true });
    assert.ok(!result.includes('garbled'));
    assert.equal(env.calls.recognized, 1);
});

test('cancelled OCR never returns partial text and releases its resources', async () => {
    const controller = new AbortController();
    const env = setup([''], { onRecognize: () => controller.abort() });
    await assert.rejects(env.read(env.file, { signal: controller.signal }), { name: 'AbortError' });
    assert.ok(env.calls.terminated >= 1);
    assert.equal(env.calls.destroyed, 1);
});

test('oversized scans and unreadable results report actionable errors', async () => {
    const large = setup(Array(41).fill(''));
    await assert.rejects(large.read(large.file), /40/);
    assert.equal(large.calls.recognized, 0);
    assert.equal(large.calls.destroyed, 1);
    const empty = setup([''], { scanText: '' });
    await assert.rejects(empty.read(empty.file), /ไม่เพียงพอ/);
    assert.equal(empty.calls.terminated, 1);
});

async function importFromUi(status, force = false) {
    const file = { name: 'scanned.pdf', size: 200 };
    const elements = {
        '#aiGamePdf': { files: [file] }, '#forcePdfOcr': { checked: force },
        '#generatePdfGameButton': { dataset: { defaultText: 'อ่าน PDF' } },
        '#pdfTextPreview': {}, '#pdfReadStatus': {},
    };
    const calls = { ocr: 0, requests: 0 };
    const context = {
        $: key => elements[key], API_BASE: 'http://localhost', ADMIN_TOKEN: 'test',
        AbortController, DOMException, FormData: class { append() {} },
        E: text => text, msg() {},
        fetch: async () => { calls.requests++; return { ok: status === 200, status, json: async () => ({ text: 'ข้อความปกติ', detail: status === 422 ? 'ต้องใช้ OCR' : 'เซสชันหมดอายุ' }) }; },
        readPdfWithOcr: async received => { assert.equal(received, file); calls.ocr++; return 'ข้อความที่อ่านจากภาพ'; },
    };
    vm.createContext(context);
    const html = fs.readFileSync(path.join(__dirname, '../../Code/index.html'), 'utf8');
    vm.runInContext(html.slice(html.indexOf('let PDF_OCR_ABORT='), html.indexOf('async function generateGameDraftFromPdfText()')), context);
    await context.generateGameDraftFromPdf();
    return { elements, calls };
}

test('PDF upload automatically falls back to OCR and shows editable text before generating', async () => {
    const { elements, calls } = await importFromUi(422);
    assert.equal(calls.ocr, 1);
    assert.match(elements['#pdfTextPreview'].innerHTML, /ข้อความที่อ่านจากภาพ/);
    assert.match(elements['#pdfTextPreview'].innerHTML, /pdfCorrectedText/);
    assert.equal(elements['#generatePdfGameButton'].disabled, false);
});

test('authorization errors do not start OCR', async () => {
    const { elements, calls } = await importFromUi(401);
    assert.equal(calls.ocr, 0);
    assert.match(elements['#pdfTextPreview'].textContent, /เซสชันหมดอายุ/);
});

test('force OCR works without text extraction while ordinary text avoids OCR', async () => {
    const forced = await importFromUi(200, true);
    assert.equal(forced.calls.requests, 0);
    assert.equal(forced.calls.ocr, 1);
    const normal = await importFromUi(200);
    assert.equal(normal.calls.ocr, 0);
    assert.match(normal.elements['#pdfTextPreview'].innerHTML, /ข้อความปกติ/);
});
