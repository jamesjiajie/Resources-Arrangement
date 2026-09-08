import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildResourceGraph, demoResources, isCurrentAssignment, sharedProjectLinks, islandLayout } from '../frontend/src/lib/resourceSandbox.js';

test('date boundaries match backend behavior, including future active work', () => {
  const a = { status: 'planned', start_date: '2026-08-01', end_date: '2026-08-31' };
  assert.equal(isCurrentAssignment(a, '2026-08-31'), true);
  assert.equal(isCurrentAssignment(a, '2026-09-01'), false);
  assert.equal(isCurrentAssignment(a, '2026-07-01'), false);
  assert.equal(isCurrentAssignment({ ...a, status: 'active' }, '2026-07-01'), true);
  assert.equal(isCurrentAssignment({ ...a, status: 'done' }, '2026-08-20'), false);
  assert.equal(isCurrentAssignment({ ...a, end_date: null }, '2026-09-08'), true);
});

test('all members and work survive grouping, links represent actual shared members', () => {
  const data = demoResources('2026-09-08');
  const graph = buildResourceGraph({ ...data, date: '2026-09-08' });
  assert.equal(graph.people.length, 8);
  assert.equal(graph.islands.reduce((sum, p) => sum + p.work.length, 0), 13);
  const li = graph.people.find(p => p.name === '李敏');
  assert.equal(li.allocated, 110);
  assert.equal(li.hours, 44);
  assert.equal(li.risk, 'overloaded');
  const links = sharedProjectLinks(graph.islands);
  assert.ok(links.some(l => l.people.some(p => p.id === li.id)));
  for (const l of links) for (const p of l.people) {
    assert.ok(graph.islands.find(i => i.id === l.from).people.some(m => m.id === p.id));
    assert.ok(graph.islands.find(i => i.id === l.to).people.some(m => m.id === p.id));
  }
});

test('API load is authoritative; expired work remains inspectable and has no current risk', () => {
  const data = { members: [{ id: 1, name: 'A', capacity_hours_week: 40 }], projects: [{ id: 1, name: 'Old project' }, { id: 2, name: 'Empty project' }], assignments: [{ id: 1, member_id: 1, project_id: 1, allocation_percent: 150, status: 'blocked', start_date: '2026-08-01', end_date: '2026-08-31' }], memberLoad: [{ member_id: 1, allocated_percent: 0, allocated_hours: 0, risk: 'underused' }], date: '2026-09-08' };
  const graph = buildResourceGraph(data);
  assert.equal(graph.islands.length, 2);
  assert.equal(graph.islands[0].work.length, 1);
  assert.equal(graph.islands[0].allocated, 0);
  assert.equal(graph.islands[0].risky, false);
  assert.equal(graph.people[0].allocated, 0);
  assert.equal(sharedProjectLinks(graph.islands).length, 0);
});

test('empty, partial and large projects do not omit members or create invalid positions', () => {
  assert.deepEqual(buildResourceGraph({}), { people: [], islands: [] });
  const assignments = Array.from({ length: 25 }, (_, i) => ({ id: i, member_id: i, member_name: `Person ${i}`, project_id: 1, status: 'active', allocation_percent: 20 }));
  const graph = buildResourceGraph({ assignments, date: '2026-09-08' });
  assert.equal(graph.islands[0].people.length, 25);
  for (const p of islandLayout(graph.islands)) assert.ok([p.x, p.z, p.radius].every(Number.isFinite));
});
