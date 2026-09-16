const { test, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

// Compile application TS in memory so the existing Node test runner can exercise
// real schemas, API interceptors, and services without another test dependency.
const cache = new Map();
function loadSource(relative) {
  const filename = path.resolve(__dirname, '../src', relative);
  if (cache.has(filename)) return cache.get(filename).exports;
  const source = fs.readFileSync(filename, 'utf8').replace('import.meta.env.VITE_API_URL', '"http://test.invalid"');
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true, target: ts.ScriptTarget.ES2022 } }).outputText;
  const mod = new Module(filename, module);
  cache.set(filename, mod);
  mod.filename = filename;
  mod.paths = Module._nodeModulePaths(path.dirname(filename));
  const nativeRequire = mod.require.bind(mod);
  mod.require = name => {
    if (!name.startsWith('.')) return nativeRequire(name);
    const target = path.resolve(path.dirname(filename), name);
    const resolved = [target, `${target}.ts`, `${target}.tsx`].find(file => fs.existsSync(file) && fs.statSync(file).isFile());
    return loadSource(path.relative(path.resolve(__dirname, '../src'), resolved));
  };
  mod._compile(code, filename);
  return mod.exports;
}
let store;
let events;
beforeEach(() => {
  store = new Map();
  events = [];
  global.localStorage = {getItem:key=>store.get(key) ?? null, setItem:(key,value)=>store.set(key,value),removeItem:key=>store.delete(key)};
  global.window = {dispatchEvent:event=>{events.push(event.type);return true;}};
});
const axios = require('axios');
const {default: api, apiError} = loadSource('api/axios.ts');
const {authService} = loadSource('services/auth.service.ts');
const {loginSchema,registerSchema} = loadSource('schemas/auth.schema.ts');
function reject401(config) {
  return Promise.reject(new axios.AxiosError('Unauthorized','ERR_BAD_REQUEST',config,null,{status:401,data:{message:'Invalid email or password'},headers:{},config,statusText:'Unauthorized'}));
}

test('failed login preserves the form session and does not dispatch session expiry', async () => {
  store.set('access_token','existing-token');
  api.defaults.adapter = reject401;
  await assert.rejects(authService.login({email:'test@example.com',password:'incorrect'}));
  assert.equal(store.get('access_token'),'existing-token');
  assert.deepEqual(events,[]);
});

test('protected 401 clears the token and notifies the auth provider', async () => {
  store.set('access_token','expired-token');
  api.defaults.adapter = reject401;
  await assert.rejects(authService.getCurrentUser());
  assert.equal(store.has('access_token'),false);
  assert.deepEqual(events,['session-expired']);
});

test('temporary network failures preserve the session token', async () => {
  store.set('access_token','saved-token');
  api.defaults.adapter = config => Promise.reject(new axios.AxiosError('Network Error','ERR_NETWORK',config));
  await assert.rejects(authService.getCurrentUser());
  assert.equal(store.get('access_token'),'saved-token');
  assert.deepEqual(events,[]);
});

test('authenticated requests carry the bearer token', async () => {
  store.set('access_token','sample-token');
  api.defaults.adapter = async config => {
    assert.equal(config.headers.Authorization,'Bearer sample-token');
    return {data:{id:1,name:'Alex',email:'alex@example.com'},status:200,statusText:'OK',headers:{},config};
  };
  assert.equal((await authService.getCurrentUser()).name,'Alex');
});

test('registration sends only backend fields and returns the server result', async () => {
  api.defaults.adapter = async config => {
    assert.deepEqual(JSON.parse(config.data),{name:'Alex',email:'alex@example.com',password:'safe-password'});
    return {data:{message:'Created',user:{id:1,name:'Alex',email:'alex@example.com'}},status:201,statusText:'Created',headers:{},config};
  };
  const response = await authService.register({name:'Alex',email:'alex@example.com',password:'safe-password',confirmPassword:'safe-password'});
  assert.equal(response.message,'Created');
});

test('form validation rejects mismatches, invalid emails, and overlong passwords', () => {
  const data = {name:'Alex',email:'alex@example.com',password:'password123',confirmPassword:'password123'};
  assert.equal(registerSchema.safeParse(data).success,true);
  assert.equal(registerSchema.safeParse({...data,confirmPassword:'different'}).success,false);
  assert.equal(registerSchema.safeParse({...data,name:'x'.repeat(101)}).success,false);
  assert.equal(registerSchema.safeParse({...data,name:'   '}).success,false);
  assert.equal(loginSchema.safeParse({email:'invalid',password:'password123'}).success,false);
  assert.equal(loginSchema.safeParse({email:data.email,password:'x'.repeat(129)}).success,false);
});

test('API errors surface safe server messages and useful connection feedback', () => {
  assert.equal(apiError(new axios.AxiosError('Oops',null,null,null,{data:{message:'Only PDF files are allowed'}})),'Only PDF files are allowed');
  assert.match(apiError(new axios.AxiosError('Network Error','ERR_NETWORK')),/reach the server/);
  assert.equal(apiError(new Error('internal detail'),'Try again'),'Try again');
});

test('login renders a masked password and accessible labels', () => {
  const React = require('react');
  const {renderToStaticMarkup} = require('react-dom/server');
  const {MemoryRouter} = require('react-router-dom');
  const {AuthContext} = loadSource('contexts/auth-context.ts');
  const {default:LoginForm} = loadSource('components/auth/LoginForm.tsx');
  const html = renderToStaticMarkup(React.createElement(MemoryRouter,null,
    React.createElement(AuthContext.Provider,{value:{login:()=>{}}},React.createElement(LoginForm))));
  assert.match(html,/type="password"/);
  assert.match(html,/autoComplete="current-password"/);
  assert.match(html,/for="login-email"/);
});


test('a stale protected request cannot sign out a newly authenticated session', async () => {
  store.set('access_token','old-token');
  api.defaults.adapter = config => {
    store.set('access_token','new-token');
    return reject401(config);
  };
  await assert.rejects(authService.getCurrentUser());
  assert.equal(store.get('access_token'),'new-token');
  assert.deepEqual(events,[]);
});
