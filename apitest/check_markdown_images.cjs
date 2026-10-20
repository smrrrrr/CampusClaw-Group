// Uses the real Markdown parser and the frontend normalizer; no browser or network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');
const frontend = createRequire(path.resolve('frontend/package.json'));
const ts = frontend('typescript');
const source = fs.readFileSync('frontend/lib/markdown-images.ts', 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const loaded = { exports: {} };
new Function('exports', 'module', compiled)(loaded.exports, loaded);
const normalize = loaded.exports.normalizeMarkdownImagePaths;

async function main() {
  const React = frontend('react');
  const { renderToStaticMarkup } = frontend('react-dom/server');
  const { default: Markdown } = await import(pathToFileURL(frontend.resolve('react-markdown')).href);
  const renderedImages = text => {
    const images = [];
    const html = renderToStaticMarkup(React.createElement(Markdown, {
      components: { img: ({ src, alt }) => { images.push(src); return React.createElement('img', { src, alt }); } },
      children: text,
    }));
    return { images, html };
  };
  const destination = 'sources/1/第一章 空间立体几何.assets/ex01-original.png';
  const raw = `![SV-EX-01 原题图](${destination})`;
  assert.equal(renderedImages(raw).images.length, 0, 'reproduces the screenshot: whitespace prevents Markdown image parsing');
  const fixed = normalize(raw);
  const result = renderedImages(fixed);
  assert.equal(result.images.length, 1);
  assert.equal(decodeURIComponent(result.images[0]), destination);
  assert.match(result.html, /<img /);
  assert(!result.html.includes('![SV-EX-01'));
  assert.equal(normalize(fixed), fixed, 'already encoded URL is not double encoded');
  const code = '```md\n' + raw + '\n```\n`' + raw + '`';
  assert.equal(normalize(code), code);
  assert.equal(renderedImages(normalize(code)).images.length, 0);
  const titled = `![原图](${destination} "题图说明")`;
  assert.equal(renderedImages(normalize(titled)).images.length, 1);
  const angle = `![原图](<${destination}>)`;
  assert.equal(normalize(angle), angle);
  assert.equal(renderedImages(normalize(angle)).images.length, 1);
  const ascii = '![plain](sources/2/simple.png)';
  assert.equal(normalize(ascii), ascii);
  const text = '$x^2+1$\n\n' + raw + '\n\n' + ascii;
  assert.equal(renderedImages(normalize(text)).images.length, 2);
  assert(normalize(text).startsWith('$x^2+1$'));
  console.log('Markdown image parser regression: 14 assertions passed; raw whitespace failure reproduced and fixed.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
