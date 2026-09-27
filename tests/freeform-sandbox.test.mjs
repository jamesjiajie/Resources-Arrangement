import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';
import { compile } from '@vue/compiler-dom';
import * as Vue from 'vue';

const source = readFileSync(new URL('../frontend/src/components/FreeformSandbox.vue', import.meta.url), 'utf8');

test('both new buttons discard the click event', () => {
  const buttons = source.match(/<button\b[^>]*@click="createSandbox[^"]*"[^>]*>[\s\S]*?<\/button>/g);
  assert.equal(buttons.length, 2);
  for (const button of buttons) {
    const render = new Function('Vue', compile(button).code)(Vue);
    let received;
    const vnode = render({ createSandbox: (...args) => { received = args; } }, []);
    vnode.props.onClick({ isTrusted: true });
    assert.deepEqual(received, []);
  }
});

test('API errors display validation text and preserve the HTTP status', async () => {
  const apiSource = source.slice(source.indexOf('async function api('), source.indexOf('\nasync function refreshList'));
  const cases = [
    [{ detail: [{ loc: ['body', 'title'], msg: 'Field required' }] }, 422, 'body.title：Field required'],
    [{ detail: { msg: '无效沙盘' } }, 400, '无效沙盘'],
    [{ detail: '版本冲突' }, 409, '版本冲突'],
    [{ detail: {} }, 500, '请求失败（HTTP 500）'],
    [null, 502, '请求失败（HTTP 502）'],
  ];
  for (const [body, status, message] of cases) {
    const api = runInNewContext(`${apiSource}\napi`, {
      fetch: async () => ({ ok: false, status, json: async () => {
        if (body === null) throw new SyntaxError('Not JSON');
        return body;
      } }),
    });
    await assert.rejects(api(''), error => error.message === message && error.status === status);
  }
});
