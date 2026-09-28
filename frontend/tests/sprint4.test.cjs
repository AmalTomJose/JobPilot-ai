const {test} = require('node:test');
const assert = require('node:assert/strict');
const {load} = require('./load-source.cjs');
const {jobToForm, formToJob, blankJob} = load('components/Jobs/job-form.ts');
const {jobService} = load('services/job.service.ts');
const {authService} = load('services/auth.service.ts');
const {default:api} = load('api/axios.ts');
const axios = require('axios');
global.localStorage = {getItem:()=> 'synthetic-token'};
const ok = (config,data) => ({data,status:200,statusText:'OK',headers:{},config});

test('unknown job fields stay empty and reviewed data excludes extraction evidence',()=>{
  const input = {...blankJob,title:'Original',skills:['C++','SQL'],raw_text:'immutable source'};
  const form = jobToForm(input);
  assert.equal(form.confirmed,false);
  assert.equal(form.company,'');
  form.title=' Corrected '; form.skills='C++\r\nSQL\n\nReact';
  const output = formToJob(form);
  assert.equal(output.title,'Corrected');assert.equal(output.location,null);
  assert.deepEqual(output.skills,['C++','SQL','React']);
  assert.ok(!('raw_text' in output));assert.ok(!('confirmed' in output));assert.ok(!('status' in output));
  assert.equal(input.title,'Original');
});

test('email intake sends exact original text with authentication',async()=>{
  const text='  Title: Engineer\r\n\nCompany: Example  ';
  api.defaults.adapter=async config=>{
    assert.equal(config.url,'/jobs/imports');assert.equal(config.method,'post');
    assert.equal(config.headers.Authorization,'Bearer synthetic-token');
    assert.equal(JSON.parse(config.data).raw_text,text);return ok(config,{id:7});
  };
  assert.equal((await jobService.importEmail(text)).id,7);
});

test('review save includes import ID and edits include expected revision',async()=>{
  const calls=[];
  api.defaults.adapter=async config=>{calls.push({url:config.url,method:config.method,data:JSON.parse(config.data)});return ok(config,{id:3});};
  await jobService.create({...blankJob,title:'Engineer'},7);
  await jobService.update(3,{...blankJob,title:'Edited'},2,'archived');
  assert.equal(calls[0].data.import_id,7);assert.equal(calls[0].method,'post');
  assert.equal(calls[1].url,'/jobs/3');assert.equal(calls[1].data.expected_revision,2);assert.equal(calls[1].data.status,'archived');
  assert.ok(!('import_id' in calls[1].data));
});

test('inbox forwards filters and pagination and source retrieval is separate',async()=>{
  const calls=[];api.defaults.adapter=async config=>{calls.push(config);return ok(config,{items:[],total:0});};
  await jobService.list({q:'Backend',status:'saved',source:'email',work_mode:'remote',limit:20,offset:20});
  await jobService.imports(10);await jobService.get(3);await jobService.getImport(7);
  assert.equal(calls[0].params.offset,20);assert.equal(calls[0].params.work_mode,'remote');
  assert.equal(calls[1].params.offset,10);assert.equal(calls[2].url,'/jobs/3');assert.equal(calls[3].url,'/jobs/imports/7');
});

test('duplicate save returns the existing job reference without hiding the conflict',async()=>{
  api.defaults.adapter=async config=>{throw new axios.AxiosError('Conflict','ERR_BAD_RESPONSE',config,null,{status:409,data:{details:{duplicate:{id:8,title:'Existing'}}},headers:{},config});};
  await assert.rejects(jobService.create({...blankJob,title:'Engineer'},null),error=>error.response.status===409 && error.response.data.details.duplicate.id===8);
});

test('sign-in does not log submitted credentials',async()=>{
  const calls=[];const original=console.log;
  api.defaults.adapter=async config=>ok(config,{access_token:'test'});
  console.log=(...values)=>calls.push(values);
  try {await authService.login({email:'synthetic@example.com',password:'synthetic-password'});} finally {console.log=original;}
  assert.deepEqual(calls,[]);
});
