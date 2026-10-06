import {test} from 'node:test';
import assert from 'node:assert/strict';

test('background hands a preview to only its destination tab, once, then deletes it',async()=>{
    const store={}; const handlers={}; let destination='';
    globalThis.chrome={
        runtime:{id:'a'.repeat(32),getURL:path=>'chrome-extension://'+'a'.repeat(32)+'/'+path,
            onMessage:{addListener:fn=>handlers.internal=fn},onMessageExternal:{addListener:fn=>handlers.external=fn}},
        storage:{session:{
            get:async key=>key===null?{...store}:{[key]:store[key]},
            set:async values=>Object.assign(store,values),
            remove:async keys=>{for(const key of Array.isArray(keys)?keys:[keys])delete store[key];}
        }},
        tabs:{create:async()=>({id:17}),update:async(id,value)=>{destination=value.url;},
            onRemoved:{addListener:fn=>handlers.removed=fn}},
        alarms:{create:()=>{},onAlarm:{addListener:fn=>handlers.alarm=fn}}
    };
    await import('../background.js');
    const payload={title:'Engineer',company:'Example',url:'https://example.com/jobs/1',description:'Build Python services with PostgreSQL and collaborate with a small engineering team.'};
    const send=(handler,message,sender)=>new Promise(resolve=>handler(message,sender,resolve));
    const result=await send(handlers.internal,{type:'send',payload},{id:chrome.runtime.id,url:chrome.runtime.getURL('popup.html')});
    assert.equal(result.ok,true);
    assert.ok(destination.startsWith('http://localhost:5173/jobs/capture#'));
    assert.ok(!destination.includes('Python'));
    const nonce=Object.keys(store)[0];
    const sender={url:'http://localhost:5173/jobs/capture',frameId:0,tab:{id:17}};
    const refused=await send(handlers.external,{type:'claim',nonce},{...sender,tab:{id:18}});
    assert.ok(refused.error);
    assert.ok(store[nonce]);
    const claimed=await send(handlers.external,{type:'claim',nonce},sender);
    assert.deepEqual(claimed.payload,payload);
    assert.equal(Object.keys(store).length,0);
    const replay=await send(handlers.external,{type:'claim',nonce},sender);
    assert.ok(replay.error);
    assert.equal(handlers.internal({type:'send',payload},{id:chrome.runtime.id,url:'https://evil.example'},()=>{}),undefined);
});
