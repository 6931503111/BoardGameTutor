const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../../Code/index.html'), 'utf8');
const quizCode = html.slice(html.indexOf('function quiz(id)'), html.indexOf('const qa ='));

function render({ lessons = [], questions = [], completed = 0, admin = false }) {
    let output = '';
    const game = { id: 'new-game', st: lessons, qz: questions };
    const context = {
        G1: () => game, dn: () => completed, app: text => { output = text; },
        back: () => '', S: { ad: admin }, Q: {}, E: text => text,
        opts: () => '<button>คำตอบ</button>',
    };
    vm.createContext(context);
    vm.runInContext(quizCode, context);
    context.quiz(game.id);
    return output;
}
const questions = [{ c: 'คำถามทดสอบ', o: ['ก', 'ข'], a: 0, w: 'เฉลย' }];
test('questions remain accessible when an imported game has zero lessons', () => {
    assert.match(render({ questions }), /คำถามทดสอบ/);
});
test('existing lessons must be completed before starting a quiz', () => {
    assert.match(render({ lessons: [['บทเรียน', 'กฎ']], questions }), /เรียนบทเรียนให้ครบ/);
    assert.match(render({ lessons: [['บทเรียน', 'กฎ']], questions, completed: 1 }), /คำถามทดสอบ/);
});
test('missing questions show the real cause and link admins to the selected game', () => {
    const output = render({ admin: true });
    assert.match(output, /ยังไม่มีข้อสอบ/);
    assert.match(output, /#\/admin\/new-game/);
    assert.doesNotMatch(output, /เรียนบทเรียนให้ครบ/);
});
