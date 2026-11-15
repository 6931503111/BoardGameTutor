const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../../Code/index.html'),'utf8');
const code=html.slice(html.indexOf('let REVIEW_SOURCES='),html.indexOf('async function saveManual()'));
function setup(){
 const fields={},committed=[],messages=[],requests=[];
 for(const key of ['reviewGame','reviewSource','reviewEvidence','reviewQuote','reviewQuestion','reviewAnswer','reviewAliases','reviewConfirmed'])fields[key]={value:'',checked:false,innerHTML:''};
 fields.reviewGame.value='a';
 const context={API_BASE:'http://localhost',ADMIN_TOKEN:'test',V:key=>fields[key].value.trim(),$:selector=>fields[selector.slice(1)],E:text=>text,
  G1:id=>({id}),admin(){},msg:text=>messages.push(text),commitGame:async game=>committed.push(game),
  fetch:()=>new Promise(resolve=>requests.push(resolve))};
 vm.createContext(context);vm.runInContext(code,context);
 return {context,fields,committed,messages,requests};
}
test('changing games cannot save evidence loaded for a different game',async()=>{
 const env=setup(),loading=env.context.loadReviewSources();
 env.requests[0]({ok:true,json:async()=>({sources:[{id:'R1',content:'ข้อความกฎที่ตรวจแล้ว'}]})});await loading;
 env.fields.reviewSource.value='R1';env.fields.reviewQuestion.value='คำถามเกี่ยวกับกฎ';env.fields.reviewAnswer.value='คำตอบที่ตรวจแล้วและอ้างอิงจากกฎ';env.fields.reviewQuote.value='ข้อความกฎ';env.fields.reviewConfirmed.checked=true;
 env.fields.reviewGame.value='b';await env.context.saveReviewedAnswer();
 assert.equal(env.committed.length,0);
});
test('late source response does not populate the newly selected game',async()=>{
 const env=setup(),loading=env.context.loadReviewSources();
 env.fields.reviewGame.value='b';env.context.clearReviewSources();
 env.requests[0]({ok:true,json:async()=>({sources:[{id:'R1',content:'กฎของเกมเก่า'}]})});await loading;
 assert.equal(env.fields.reviewSource.innerHTML,'');assert.equal(env.fields.reviewEvidence.value,'');
});
test('a reviewed answer requires an exact quote and explicit inspection',async()=>{
 const env=setup(),loading=env.context.loadReviewSources();
 env.requests[0]({ok:true,json:async()=>({sources:[{id:'R1',content:'ข้อความกฎที่ตรวจแล้ว'}]})});await loading;
 Object.assign(env.fields.reviewSource,{value:'R1'});env.fields.reviewQuestion.value='คำถามเกี่ยวกับกฎ';env.fields.reviewAnswer.value='คำตอบที่ตรวจแล้วและอ้างอิงจากกฎ';env.fields.reviewQuote.value='ข้อความกฎ';
 await env.context.saveReviewedAnswer();assert.equal(env.committed.length,0);
 env.fields.reviewConfirmed.checked=true;env.fields.reviewQuote.value='ข้อความที่ไม่มีในกฎ';
 await env.context.saveReviewedAnswer();assert.equal(env.committed.length,0);
 env.fields.reviewQuote.value='ข้อความกฎ';await env.context.saveReviewedAnswer();
 assert.equal(env.committed[0].verified_qa[0].reviewed,true);
});
