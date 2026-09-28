const {test} = require('node:test');
const assert = require('node:assert/strict');
const {load} = require('./load-source.cjs');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {MemoryRouter} = require('react-router-dom');
const {matchService} = load('services/match.service.ts');
const {default: MatchCard} = load('pages/Matches/MatchCard.tsx');
const {default: api} = load('api/axios.ts');
const axios = require('axios');
global.localStorage = {getItem: () => 'synthetic-token'};
const base = {job_id: 7, title: 'Developer', company: 'Example', job_status: 'saved', state: 'current', score: 50, matched_skills: [{job_skill: 'PostgreSQL', profile_skill: 'Postgres'}], missing_skills: ['Python'], reason: null, computed_at: '2026-09-25T10:00:00', profile_revision: 1, job_revision: 1, matcher_version: 'test'};
const render = changes => renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(MatchCard, {item: {...base, ...changes}})));

test('matching requests use authentication and explicit POST for computation', async () => {
  const calls = [];
  api.defaults.adapter = async config => {calls.push(config); return {data: {}, status: 200, statusText: 'OK', headers: {}, config};};
  await matchService.list(true, 20); await matchService.run();
  assert.equal(calls[0].headers.Authorization, 'Bearer synthetic-token');
  assert.equal(calls[0].url, '/matches'); assert.equal(calls[0].params.offset, 20); assert.equal(calls[0].params.include_archived, true);
  assert.equal(calls[1].url, '/matches/run'); assert.equal(calls[1].method, 'post');
});
test('zero overlap is a real score while missing data has no score', () => {
  assert.match(render({score: 0, matched_skills: []}), /0%/);
  const unknown = render({score: null, reason: 'job_skills_missing', matched_skills: [], missing_skills: []});
  assert.match(unknown, /Not enough information/); assert.doesNotMatch(unknown, /0%/);
});
test('outdated scores are not displayed as current percentages', () => {
  const html = render({state: 'outdated'});
  assert.match(html, /Outdated/); assert.match(html, /previous check/); assert.doesNotMatch(html, /50%/);
});
test('matching explains alias evidence, links jobs, and escapes imported content', () => {
  const html = render({title: '<script>unsafe</script>'});
  assert.match(html, /Your profile: Postgres/); assert.match(html, /1 of 2 unique listed skills/);
  assert.match(html, /href="\/jobs\/7"/); assert.doesNotMatch(html, /<script>/);
});
test('pending jobs do not claim a computed score or missing skills', () => {
  const html = render({state: 'pending', score: null, matched_skills: [], missing_skills: []});
  assert.match(html, /Not checked/); assert.doesNotMatch(html, /All listed skills are covered/);
});
test('a conflicting run is exposed for retry', async () => {
  api.defaults.adapter = async config => {throw new axios.AxiosError('Conflict', 'ERR_BAD_RESPONSE', config, null, {status: 409, data: {message: 'Try again'}, headers: {}, config});};
  await assert.rejects(matchService.run(), error => error.response.status === 409);
});
