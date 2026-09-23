const {test} = require('node:test');
const assert = require('node:assert/strict');
const {load} = require('./load-source.cjs');
global.localStorage={getItem:()=> 'synthetic-token'};
const {default:api}=load('api/axios.ts');
const {resumeService}=load('services/resume.service.ts');

test('history uses authenticated summary endpoint', async()=>{
  api.defaults.adapter=async config=>{
    assert.equal(config.url,'/resume');
    assert.equal(config.headers.Authorization,'Bearer synthetic-token');
    return {data:[{id:7,file_name:'sample.pdf'}],status:200,statusText:'OK',headers:{},config};
  };
  assert.equal((await resumeService.list())[0].id,7);
});

test('source and saved parse use distinct retrieval endpoints', async()=>{
  const visited=[];
  api.defaults.adapter=async config=>{visited.push(config.url);return {data:{id:7},status:200,statusText:'OK',headers:{},config};};
  await resumeService.get(7);
  await resumeService.getParse(7);
  assert.deepEqual(visited,['/resume/7','/resume/7/parse']);
});

test('parsing requests reuse by default and explicitly force rebuilding', async()=>{
  const forces=[];
  api.defaults.adapter=async config=>{
    assert.equal(config.url,'/resume/7/parse');
    assert.equal(config.method,'post');
    forces.push(config.params.force);
    return {data:{status:'completed',draft_data:{skills:['Python']}},status:200,statusText:'OK',headers:{},config};
  };
  assert.deepEqual((await resumeService.parse(7)).draft_data.skills,['Python']);
  await resumeService.parse(7,true);
  assert.deepEqual(forces,[false,true]);
});

test('failed parse result is preserved for UI retry rather than treated as a draft', async()=>{
  api.defaults.adapter=async config=>({data:{status:'failed',draft_data:null,error_message:'Retry parsing'},status:200,statusText:'OK',headers:{},config});
  const result=await resumeService.parse(7);
  assert.equal(result.status,'failed');
  assert.equal(result.draft_data,null);
});

test('history panel starts without exposing an old draft',()=>{
  const React=require('react');
  const {renderToStaticMarkup}=require('react-dom/server');
  const {default:Panel}=load('components/ResumeUpload/ResumeDraftPanel.tsx');
  const html=renderToStaticMarkup(React.createElement(Panel,{selectedId:null,onSelect:()=>{},refreshKey:0}));
  assert.match(html,/Loading saved resumes/);
  assert.doesNotMatch(html,/Draft saved\./);
});
