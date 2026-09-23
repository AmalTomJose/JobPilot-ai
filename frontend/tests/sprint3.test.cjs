const {test} = require('node:test');
const assert = require('node:assert/strict');
const {load} = require('./load-source.cjs');
const {toForm, toProfile, lines} = load('components/Profile/profile-form.ts');
const {profileService} = load('services/profile.service.ts');
const {default:api} = load('api/axios.ts');
const axios = require('axios');
global.localStorage = {getItem: () => 'synthetic-token', removeItem: () => {}};
global.window = {dispatchEvent: () => {}};
const draft = {
  contact: {name: null, email: 'alex@example.com', phone: null, location: null, links: []},
  summary: null, skills: ['C++', 'Node.js', 'CI/CD'],
  experience: [{title: 'Engineer', company: null, location: null, date_text: '2023 – Present', description: ['Built tools'], source_text: 'original experience'}],
  education: [{institution: null, degree: 'BSc', field_of_study: null, date_text: null, source_text: 'original education'}],
  projects: [{name: null, description: [], technologies: ['Python'], links: [], source_text: 'original project'}],
  unclassified_text: 'source header',
};

test('review starts unconfirmed, keeps unknown fields empty, and isolates source evidence', () => {
  const original = JSON.stringify(draft);
  const form = toForm(draft);
  assert.equal(form.confirmed, false);
  assert.equal(form.contact.name, '');
  form.contact.name = 'Corrected Name';
  form.experience[0].company = 'Corrected Company';
  const data = toProfile(form);
  assert.equal(data.contact.name, 'Corrected Name');
  assert.equal(data.experience[0].company, 'Corrected Company');
  assert.equal(data.contact.phone, null);
  assert.deepEqual(data.skills, ['C++', 'Node.js', 'CI/CD']);
  assert.ok(!('source_text' in data.experience[0]));
  assert.ok(!('source_text' in data.education[0]));
  assert.ok(!('source_text' in data.projects[0]));
  assert.ok(!('unclassified_text' in data));
  assert.ok(!('confirmed' in data));
  assert.equal(JSON.stringify(draft), original);
});

test('review supports adding and removing entries, multiline edits, and empty fields', () => {
  const form = toForm(draft);
  form.experience = [];
  form.projects.push({name: 'New Project', description: 'Built a tool\r\n\n Added tests ', technologies: 'React\nSQL', links: 'https://example.com'});
  form.contact.email = '  ';
  const data = toProfile(form);
  assert.equal(data.contact.email, null);
  assert.deepEqual(data.experience, []);
  assert.deepEqual(data.projects[1].description, ['Built a tool', 'Added tests']);
  assert.deepEqual(lines(' C#\n\nC++\n'), ['C#', 'C++']);
});

test('profile save sends the expected revision and reviewed data with authentication', async () => {
  const request = {source_resume_id: 7, expected_revision: 3, data: toProfile(toForm(draft))};
  api.defaults.adapter = async config => {
    assert.equal(config.method, 'put'); assert.equal(config.url, '/profile');
    assert.equal(config.headers.Authorization, 'Bearer synthetic-token');
    assert.deepEqual(JSON.parse(config.data), request);
    return {data: {...request, revision: 4}, status: 200, statusText: 'OK', headers: {}, config};
  };
  assert.equal((await profileService.save(request)).revision, 4);
});

test('only a missing profile becomes the empty state; network and permission errors remain errors', async () => {
  for (const status of [404, 401, 500]) {
    api.defaults.adapter = async config => { throw new axios.AxiosError('Request failed', 'ERR_BAD_RESPONSE', config, null, {status, data: {}, headers: {}, config}); };
    if (status === 404) assert.equal(await profileService.get(), null);
    else await assert.rejects(profileService.get(), error => error.response.status === status);
  }
});

test('stale save conflicts are passed back to the review form', async () => {
  api.defaults.adapter = async config => { throw new axios.AxiosError('Conflict', 'ERR_BAD_RESPONSE', config, null, {status: 409, data: {message: 'Reload latest'}, headers: {}, config}); };
  await assert.rejects(profileService.save({source_resume_id: 7, expected_revision: 0, data: toProfile(toForm(draft))}), error => error.response.status === 409);
});

test('confirmed profile display escapes resume markup and shows saved values', () => {
  const React = require('react');
  const {renderToStaticMarkup} = require('react-dom/server');
  const {default:Details} = load('components/Profile/ProfileDetails.tsx');
  const data = toProfile(toForm(draft));
  data.contact.name = '<script>alert(1)</script>';
  const html = renderToStaticMarkup(React.createElement(Details, {data}));
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('<script>'));
  assert.match(html, /Engineer/);
  assert.match(html, /Not provided/);
});
