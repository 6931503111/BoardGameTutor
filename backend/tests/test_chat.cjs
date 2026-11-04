const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../../Code/index.html'), 'utf8');
const askCode = html.slice(html.indexOf('async function ask()'), html.indexOf('/* ข้อมูลผู้ใช้'));
const resetCode = html.split('\n').find(line => line.includes('const nc ='));

function setup() {
    const requests = [], input = { value: '' }, saved = [];
    const S = { lg: 'a', cv: {}, cfg: { demo: 0 }, rt: [] };
    const games = [{ id: 'a' }, { id: 'b' }];
    const context = {
        S, CHAT_REQUESTS: new Map(), API_BASE: 'http://localhost', ADMIN_TOKEN: '',
        G1: id => games.find(g => g.id === id), $: () => input,
        knowledgeVersion: game => game.source_text || 'initial',
        save: () => saved.push(true), draw() {}, msg() {}, ai() {},
        AbortController, performance: { now: () => 10 }, setTimeout: () => 1, clearTimeout() {},
        fetch: (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject })),
    };
    vm.createContext(context);
    vm.runInContext(askCode + '\n' + resetCode + '\nthis.reset = nc;', context);
    return { context, S, input, requests, saved, games };
}
const reply = (gameId, text) => ({ ok: true, json: async () => ({ game_id: gameId, status: 'answered', answer: text, sources: [{ id: 'R1', title: 'กฎ', kind: 'กฎ', content: 'ต้นฉบับ' }] }) });

test('sends selected game, relevant conversation and source identifiers', async () => {
    const env = setup();
    env.S.cv.a = [{ r: 'u', t: 'Nope คืออะไร' }, { r: 'a', t: 'คำตอบเก่า', sources: [{ id: 'R1' }], status: 'answered' }];
    env.input.value = 'ขอตัวอย่างเพิ่ม';
    const pending = env.context.ask();
    const request = env.requests[0];
    assert.equal(request.url, 'http://localhost/api/games/a/ask');
    const body = JSON.parse(request.options.body);
    assert.equal(body.history[0].content, 'Nope คืออะไร');
    assert.deepEqual(body.history[1].source_ids, ['R1']);
    request.resolve(reply('a', 'คำตอบใหม่'));
    await pending;
    assert.equal(env.S.cv.a.at(-1).sources[0].content, 'ต้นฉบับ');
});

test('switching games during a request keeps both conversations separate', async () => {
    const env = setup();
    env.input.value = 'คำถาม A';
    const first = env.context.ask();
    env.S.lg = 'b';env.input.value = 'คำถาม B';
    const second = env.context.ask();
    env.requests[0].resolve(reply('a', 'ตอบ A'));
    await first;
    assert.equal(env.S.cv.a.at(-1).t, 'ตอบ A');
    assert.equal(env.S.cv.b.length, 1);
    env.requests[1].resolve(reply('b', 'ตอบ B'));
    await second;
    assert.equal(env.S.cv.b.at(-1).t, 'ตอบ B');
    assert.equal(JSON.parse(env.requests[1].options.body).history.length, 0);
});

test('new conversation ignores a late reply from the cleared conversation', async () => {
    const env = setup();env.input.value = 'คำถาม';
    const pending = env.context.ask();
    env.context.reset();
    assert.equal(env.requests[0].options.signal.aborted, true);
    env.requests[0].resolve(reply('a', 'คำตอบที่มาช้า'));
    await pending;
    assert.equal(env.S.cv.a, undefined);
});

test('repeated submit is ignored and a failed service leaves a readable error', async () => {
    const env = setup();env.input.value = 'คำถาม';
    const pending = env.context.ask();
    env.input.value = 'ส่งซ้ำ';await env.context.ask();
    assert.equal(env.requests.length, 1);
    env.requests[0].resolve({ ok: false, status: 502, json: async () => ({ detail: 'กรุณาเปิด Ollama' }) });
    await pending;
    assert.equal(env.S.cv.a.at(-1).status, 'error');
    assert.match(env.S.cv.a.at(-1).t, /Ollama/);
    assert.equal(env.context.CHAT_REQUESTS.size, 0);
});

test('updated manuals exclude stale answers from the model context', async () => {
    const env=setup();env.games[0].source_text='new manual';
    env.S.cv.a=[{r:'u',t:'คำถามเก่า',kb:'old manual'},{r:'a',t:'คำตอบเก่า',kb:'old manual',sources:[{id:'M1'}]}];
    env.input.value='คำถามใหม่';const pending=env.context.ask();
    assert.equal(JSON.parse(env.requests[0].options.body).history.length,0);
    env.requests[0].resolve(reply('a','คำตอบใหม่'));await pending;
    assert.equal(env.S.cv.a.at(-1).kb,'new manual');
    assert.equal(env.S.cv.a[1].t,'คำตอบเก่า');
});
