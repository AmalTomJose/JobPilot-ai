import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {allowedReceiver, validPayload, APP_ORIGIN} from '../handoff.js';
import {readJobPage} from '../capture.js';
const nonce='11111111-1111-1111-1111-111111111111';
const payload={title:'Developer',company:'Example',url:'https://example.com/jobs/1',description:'Build software and maintain Python backend services for customers.'};
test('manifest grants no persistent page, cookie, or history access',()=>{
    const manifest=JSON.parse(readFileSync(new URL('../manifest.json',import.meta.url)));
    assert.equal(manifest.manifest_version,3);
    assert.equal(manifest.host_permissions,undefined);
    assert.equal(manifest.content_scripts,undefined);
    assert.deepEqual(manifest.permissions,['activeTab','scripting','storage','alarms']);
});
test('handoff requires correct origin, path, tab, frame, nonce and expiry',()=>{
    const record={nonce,tabId:7,expires:2000};
    const sender={url:APP_ORIGIN+'/jobs/capture',tab:{id:7},frameId:0};
    assert.equal(allowedReceiver(sender,record,nonce,1000),true);
    for(const changes of [{url:'https://evil.example/jobs/capture'},{url:'http://localhost:9999/jobs/capture'},
        {url:APP_ORIGIN+'/settings'},{tab:{id:8}},{frameId:1}]){
        assert.equal(allowedReceiver({...sender,...changes},record,nonce,1000),false);
    }
    assert.equal(allowedReceiver(sender,record,'wrong',1000),false);
    assert.equal(allowedReceiver(sender,record,nonce,2001),false);
});
test('payload rejects dangerous URLs, oversized text and missing fields',()=>{
    assert.equal(validPayload(payload),true);
    for(const changes of [{url:'javascript:alert(1)'},{url:'https://user:password@example.com/'},{description:'short'},
        {description:'x'.repeat(20001)},{title:'x'.repeat(256)},{company:null}]){
        assert.equal(validPayload({...payload,...changes}),false);
    }
});
test('LinkedIn is blocked before reading any page content',()=>{
    globalThis.location={hostname:'www.linkedin.com',protocol:'https:'};
    globalThis.document=new Proxy({}, {get(){throw new Error('Should not read content');}});
    assert.match(readJobPage().error,/disabled/);
});
test('selected job text is previewed without collecting the entire document',()=>{
    globalThis.location={hostname:'example.com',protocol:'https:',href:'https://example.com/jobs/1?utm_source=email#section'};
    globalThis.window={getSelection:()=>({toString:()=>payload.description})};
    globalThis.document={querySelectorAll:()=>[],querySelector:()=>({innerText:'Developer'})};
    const result=readJobPage();
    assert.equal(result.description,payload.description);
    assert.equal(result.url,'https://example.com/jobs/1');
    assert.equal(result.method,'Selected text');
});
test('no selection or job section produces guidance instead of copying page body',()=>{
    globalThis.location={hostname:'example.com',protocol:'https:',href:'https://example.com/jobs/1'};
    globalThis.window={getSelection:()=>({toString:()=>''})};
    globalThis.document={querySelectorAll:()=>[],querySelector:()=>null};
    assert.match(readJobPage().error,/Select only/);
});
