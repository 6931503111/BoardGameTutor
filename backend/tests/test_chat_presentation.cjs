const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../../Code/index.html'),'utf8');
const code=html.slice(html.indexOf('function chatAnswerText('),html.indexOf('const draw ='));
const escape=text=>String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const context={E:escape,ruleText:text=>`<p>${escape(text)}</p>`};
vm.createContext(context);
vm.runInContext(code+'\nthis.render=bub;',context);

test('unconfirmed replies are labelled clearly and keep complete sources folded',()=>{
 const output=context.render({r:'a',status:'excerpt',t:'ยังยืนยันไม่ได้',sources:[
  {id:'M11',kind:'บันทึกตรวจเทียบคู่มือ',title:'คู่มือ หน้า 4',content:'กฎฉบับเต็ม',edition:'Base'},
  {id:'R1',kind:'กฎ',title:'กฎอีกหัวข้อ',content:'ข้อยกเว้นฉบับเต็ม'}]});
 assert.match(output,/ยังยืนยันคำตอบไม่ได้/);
 assert.match(output,/<details class="src"><summary>ดูกฎอ้างอิง \(2 แหล่ง\)<\/summary>/);
 assert.doesNotMatch(output,/<details[^>]*\bopen\b/);
 assert.doesNotMatch(output,/M11|อ้างอิง R1/);
 assert.match(output,/กฎฉบับเต็ม/);
 assert.match(output,/ข้อยกเว้นฉบับเต็ม/);
});

test('old saved fallback pastes no longer look like answers to the new question',()=>{
 const output=context.render({r:'a',status:'excerpt',t:'พบกฎที่เกี่ยวข้องดังนี้:\nคำถาม: คำถามก่อนหน้า\nคำตอบ: ข้อสรุปเก่า',sources:[]});
 assert.doesNotMatch(output,/คำถามก่อนหน้า|ข้อสรุปเก่า/);
 assert.match(output,/ยังยืนยัน/);
 const demo=context.render({r:'a',status:'excerpt',demo:true,t:'ข้อความสาธิตต้นฉบับ',sources:[]});
 assert.match(demo,/โหมดสาธิต/);
 assert.match(demo,/ข้อความสาธิตต้นฉบับ/);
});

test('legacy chat timeouts no longer ask users to split a manual',()=>{
 const output=context.render({r:'a',e:1,status:'error',t:'Ollama ใช้เวลานานเกินไป กรุณาลองแบ่งคู่มือเป็นส่วนย่อย'});
 assert.doesNotMatch(output,/แบ่งคู่มือ/);
 assert.match(output,/ตรวจคำตอบไม่ทัน/);
 assert.match(output,/err/);
});

test('question and reference HTML remain escaped and unsafe links are omitted',()=>{
 const output=context.render({r:'a',status:'answered',t:'<script>alert(1)</script>',sources:[
  {title:'<img src=x onerror=alert(1)>',excerpt:'<script>quote</script>',content:'<svg onload=alert(1)>',url:'javascript:alert(1)'}]});
 assert.doesNotMatch(output,/<script>|<img|<svg|href="javascript:/);
 assert.match(output,/&lt;script&gt;/);
});

test('selected proof appears before the complete reference when expanded',()=>{
 const output=context.render({r:'a',status:'answered',t:'ได้ครับ',sources:[
  {title:'Manual',excerpt:'Selected evidence.',content:'Complete manual text.'}]});
 assert.ok(output.indexOf('Selected evidence.')<output.indexOf('Complete manual text.'));
 assert.match(output,/ประโยคที่ใช้ตัดสิน/);
 assert.match(output,/ข้อความหัวข้อเต็ม/);
});
