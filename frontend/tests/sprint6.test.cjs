const {test} = require('node:test');
const assert = require('node:assert/strict');
const {load} = require('./load-source.cjs');
const {emailService} = load('services/email.service.ts');
const {default: api} = load('api/axios.ts');
global.localStorage = {getItem: () => 'synthetic-token'};

test('Gmail actions authenticate and bind OAuth to the browser cookie', async () => {
  const calls = [];
  api.defaults.adapter = async config => {calls.push(config); return {data: {}, status: 200, statusText: 'OK', headers: {}, config};};
  await emailService.connect();
  await emailService.select({label_id: 'Label_Jobs', import_since: '2026-01-01', auto_sync: false});
  await emailService.sync();
  await emailService.disconnect();
  assert.ok(calls.every(call => call.headers.Authorization === 'Bearer synthetic-token'));
  assert.equal(calls[0].withCredentials, true);
  assert.equal(calls[0].method, 'post');
  assert.deepEqual(JSON.parse(calls[1].data), {label_id: 'Label_Jobs', import_since: '2026-01-01', auto_sync: false});
  assert.equal(calls[2].timeout, 120000);
  assert.equal(calls[3].method, 'delete');
  assert.ok(calls.every(call => !call.url.includes('synthetic-token')));
});

test('Gmail history pages and status remain separate from private message bodies', async () => {
  const calls = [];
  api.defaults.adapter = async config => {calls.push(config); return {data: {}, status: 200, statusText: 'OK', headers: {}, config};};
  await emailService.status(); await emailService.messages(20); await emailService.runs();
  assert.equal(calls[0].url, '/email/gmail');
  assert.deepEqual(calls[1].params, {limit: 20, offset: 20});
  assert.equal(calls[2].url, '/email/gmail/runs');
});
