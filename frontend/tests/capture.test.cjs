const {test}=require('node:test');
const assert=require('node:assert/strict');
const {load}=require('./load-source.cjs');
const {captureService}=load('services/capture.service.ts');
const {validCapture,receivePreview}=load('services/extension-handoff.ts');
const {default:api}=load('api/axios.ts');
global.localStorage={getItem:()=> 'test-token'};
const capture={title:'Developer',company:'Example',url:'https://example.com/jobs/1',description:'Build reliable Python backend services and collaborate with the engineering team.'};
test('preview, save draft and save job use separate authenticated actions',async()=>{
    const calls=[];
    api.defaults.adapter=async config=>{calls.push(config);return {data:{},status:200,statusText:'OK',headers:{},config};};
    await captureService.preview(capture);
    assert.equal(calls.length,1);
    assert.equal(calls[0].url,'/jobs/capture/preview');
    await captureService.saveDraft(capture,{title:'Reviewed'});
    await captureService.save({title:'Reviewed'});
    assert.deepEqual(calls.map(call=>call.url),['/jobs/capture/preview','/jobs/capture/drafts','/jobs/capture/save']);
    assert.ok(calls.every(call=>call.headers.Authorization==='Bearer test-token'));
    assert.equal(JSON.parse(calls[1].data).draft_data.title,'Reviewed');
});
test('browser handoff validates untrusted page data',()=>{
    assert.equal(validCapture(capture),true);
    assert.equal(validCapture({...capture,url:'javascript:alert(1)'}),false);
    assert.equal(validCapture({...capture,description:'x'.repeat(20001)}),false);
});
test('missing extension and malformed handoff fail without API calls',async()=>{
    global.window={};
    await assert.rejects(receivePreview('#extension=wrong'),/Invalid/);
    await assert.rejects(receivePreview('#extension='+'a'.repeat(32)+'&handoff=11111111-1111-1111-1111-111111111111'),/Chrome/);
});
test('valid handoff reads a single payload and never obtains a login token',async()=>{
    const requests=[];
    global.window={setTimeout,clearTimeout,chrome:{runtime:{sendMessage(id,message,callback){requests.push({id,message});callback({payload:capture});}}}};
    assert.deepEqual(await receivePreview('#extension='+'a'.repeat(32)+'&handoff=11111111-1111-1111-1111-111111111111'),capture);
    assert.deepEqual(requests[0].message,{type:'claim',nonce:'11111111-1111-1111-1111-111111111111'});
});
