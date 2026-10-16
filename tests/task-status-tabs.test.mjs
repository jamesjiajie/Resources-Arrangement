import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = readFileSync(new URL('../frontend/src/App.vue', import.meta.url), 'utf8');
const filter = source.match(/const filteredLongTermTasks = computed\(\(\) => \{([\s\S]*?)\n\}\);/)[1];

test('task tabs partition statuses and keep search and filters inside the selected view', () => {
  const context = {
    taskSearch: { value: '' }, taskStatusFilter: { value: '' },
    taskView: { value: 'current' }, includeArchivedTasks: { value: false },
    longTermTasks: { value: ['planned', 'active', 'blocked', 'done', 'archived'].map((status, id) => ({ id, status, title: status, owner: 'Alice', category: '', notes: '' })) },
  };
  const ids = () => Array.from(vm.runInNewContext(`(() => {${filter}})()`, context), task => task.id);
  assert.deepEqual(ids(), [0, 1, 2]);
  context.taskStatusFilter.value = 'blocked';
  assert.deepEqual(ids(), [2]);
  context.taskView.value = 'completed';
  assert.deepEqual(ids(), [3]);
  context.includeArchivedTasks.value = true;
  assert.deepEqual(ids(), [3, 4]);
  context.taskSearch.value = 'archived';
  assert.deepEqual(ids(), [4]);
  context.taskSearch.value = 'missing';
  assert.deepEqual(ids(), []);
  context.taskSearch.value = '';
  context.taskView.value = 'current';
  context.taskStatusFilter.value = '';
  context.longTermTasks.value[1].status = 'done';
  assert.deepEqual(ids(), [0, 2]);
  context.taskView.value = 'completed';
  assert.deepEqual(ids(), [1, 3, 4]);
});
