const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const cache = new Map();
function load(relative) {
  const filename = path.resolve(__dirname, '../src', relative);
  if(cache.has(filename)) return cache.get(filename).exports;
  const source = fs.readFileSync(filename,'utf8').replace('import.meta.env.VITE_API_URL','"http://test.invalid"');
  const mod = new Module(filename,module);
  cache.set(filename,mod);
  mod.filename=filename;
  mod.paths=Module._nodeModulePaths(path.dirname(filename));
  const original=mod.require.bind(mod);
  mod.require=name=>{
    if(!name.startsWith('.')) return original(name);
    const target=path.resolve(path.dirname(filename),name);
    const resolved=[target,target+'.ts',target+'.tsx'].find(file=>fs.existsSync(file)&&fs.statSync(file).isFile());
    return load(path.relative(path.resolve(__dirname,'../src'),resolved));
  };
  mod._compile(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,filename);
  return mod.exports;
}
module.exports = {load};
