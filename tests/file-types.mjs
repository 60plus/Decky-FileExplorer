import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { test } from 'node:test';
const types = readFileSync(new URL('../fileexplorer/media_types.json', import.meta.url), 'utf8');
const source = readFileSync(new URL('../src/fileTypes.ts', import.meta.url), 'utf8').replace("import mediaTypes from '../fileexplorer/media_types.json';", `const mediaTypes = ${types};`);
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } }).outputText;
const { isText, openKind } = await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'));
test('text recognition covers configuration, code, subtitles and extensionless conventions', () => {
  for (const name of ['notes.txt','steam.vdf','app.acf','file.JSON','test.jsonc','settings.yaml','pyproject.toml','.env.local','README','LICENSE.md','Dockerfile.dev','Makefile','CMakeLists.txt','file.service','file.gd','file.rs','file.ps1','captions.srt','drawing.svg','.gitignore']) assert.ok(isText(name), name);
});
test('A never routes unknown or binary extensions into the text editor', () => {
  for (const name of ['game.exe','blob.bin','driver.dll','icon.ico','a.pdf','video.avi','database.db','file.unknown','text.txt.exe']) assert.equal(openKind({ name, directory: false, link: false }), null, name);
  for (const [name, kind] of [['a.txt','text'],['a.png','image'],['a.zip','archive'],['a.mp3','media'],['a.webm','media']]) assert.equal(openKind({name, directory:false, link:false}), kind);
  assert.equal(openKind({name:'link.txt',directory:false,link:true}), null);
  assert.equal(openKind({name:'folder.exe',directory:true,link:false}), 'folder');
});
