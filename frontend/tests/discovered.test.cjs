const {test}=require('node:test');
const assert=require('node:assert/strict');
const {load}=require('./load-source.cjs');
const {discoveredService}=load('services/discovered.service.ts');
const {default:api}=load('api/axios.ts');
global.localStorage={getItem:()=> 'test-token'};
test('viewing discoveries does not approve; approval, dismissal and backfill are explicit authenticated writes',async()=>{
 const calls=[];
 api.defaults.adapter=async config=>{calls.push(config);return {data:{},status:200,statusText:'OK',headers:{},config};};
 await discoveredService.list('dismissed',20);
 await discoveredService.get(12);
 assert.ok(calls.every(call=>call.method==='get'));
 await discoveredService.status(12,'pending');
 await discoveredService.approve(12,{title:'Reviewed developer'});
 await discoveredService.backfill(100);
 assert.deepEqual(calls.map(call=>[call.method,call.url]),[
  ['get','/jobs/discovered'],['get','/jobs/discovered/12'],['patch','/jobs/discovered/12'],
  ['post','/jobs/discovered/12/approve'],['post','/jobs/discovered/backfill']]);
 assert.deepEqual(calls[0].params,{status:'dismissed',offset:20});
 assert.equal(JSON.parse(calls[3].data).title,'Reviewed developer');
 assert.equal(calls[4].params.after_id,100);
 assert.ok(calls.every(call=>call.headers.Authorization==='Bearer test-token'));
});
test('source filter and URL lookup reach the discovery API',async()=>{
 const calls=[];
 api.defaults.adapter=async config=>{calls.push(config);return {data:[],status:200,statusText:'OK',headers:{},config};};
 await discoveredService.list('pending',20,'indeed');
 await discoveredService.lookup('https://www.indeed.com/viewjob?jk=abcdef1234567890');
 assert.deepEqual(calls[0].params,{status:'pending',offset:20,site:'indeed'});
 assert.equal(calls[1].url,'/jobs/discovered/lookup');
 assert.equal(calls[1].params.url,'https://www.indeed.com/viewjob?jk=abcdef1234567890');
});
