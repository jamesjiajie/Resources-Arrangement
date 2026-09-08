// Keep the date rule aligned with backend.services.is_current_assignment.
export function isCurrentAssignment(item, date) {
  if (!["active", "planned", "blocked"].includes(item.status)) return false;
  if (!date) return true;
  if (item.start_date > date) return ["active", "blocked"].includes(item.status);
  return !item.end_date || item.end_date >= date;
}

export function resourceRisk(load, blocked = false) {
  return blocked ? "blocked" : load >= 110 ? "overloaded" : load >= 90 ? "tight" : load <= 35 ? "underused" : "normal";
}

export function buildResourceGraph({ members = [], projects = [], assignments = [], memberLoad = [], date = "" }) {
  const loads = new Map(memberLoad.map(p => [p.member_id, p]));
  const people = members.map((member, index) => {
    const work = assignments.filter(a => a.member_id === member.id);
    const current = work.filter(a => isCurrentAssignment(a, date));
    const load = loads.get(member.id);
    const allocated = load?.allocated_percent ?? current.reduce((sum, a) => sum + Number(a.allocation_percent || 0), 0);
    return { ...member, id: member.id, index, work, allocated, risk: load?.risk || resourceRisk(allocated, current.some(a => a.status === "blocked")), hours: load?.allocated_hours ?? allocated * Number(member.capacity_hours_week || 0) / 100 };
  });
  // Include members from assignments even if a partial response has no member catalog.
  const knownPeople = new Set(people.map(p => p.id));
  for (const a of assignments) {
    if (knownPeople.has(a.member_id)) continue;
    knownPeople.add(a.member_id);
    const work = assignments.filter(w => w.member_id === a.member_id);
    const current = work.filter(w => isCurrentAssignment(w, date));
    const allocated = current.reduce((sum, w) => sum + Number(w.allocation_percent || 0), 0);
    people.push({ id: a.member_id, name: a.member_name || String(a.member_id), role: a.member_role || "", index: people.length, work, allocated, hours: allocated * Number(a.capacity_hours_week || 0) / 100, capacity_hours_week: a.capacity_hours_week || 0, risk: resourceRisk(allocated, current.some(w => w.status === "blocked")) });
  }
  const projectMap = new Map(projects.map(p => [p.id, { ...p, work: [] }]));
  for (const a of assignments) {
    if (!projectMap.has(a.project_id)) projectMap.set(a.project_id, { id: a.project_id, name: a.project_name || String(a.project_id), status: "active", work: [] });
    projectMap.get(a.project_id).work.push(a);
  }
  const islands = [...projectMap.values()].map(project => {
    const ids = new Set(project.work.map(a => a.member_id));
    const participants = people.filter(p => ids.has(p.id)).sort((a, b) => b.allocated - a.allocated || a.name.localeCompare(b.name));
    const current = project.work.filter(a => isCurrentAssignment(a, date));
    return { ...project, people: participants, allocated: current.reduce((sum, a) => sum + Number(a.allocation_percent || 0), 0), average: participants.length ? participants.reduce((sum, p) => sum + p.allocated, 0) / participants.length : 0, blocked: current.filter(a => a.status === "blocked"), risky: participants.some(p => ["blocked", "overloaded", "tight"].includes(p.risk)) || current.some(a => a.status === "blocked") };
  }).sort((a, b) => b.people.length - a.people.length || a.name.localeCompare(b.name));
  return { people, islands };
}

export function sharedProjectLinks(islands) {
  const links = [];
  for (let i = 0; i < islands.length; i++) {
    const ids = new Set(islands[i].people.map(p => p.id));
    for (let j = i + 1; j < islands.length; j++) {
      const shared = islands[j].people.filter(p => ids.has(p.id));
      if (shared.length) links.push({ from: islands[i].id, to: islands[j].id, people: shared, risk: shared.some(p => ["overloaded", "blocked", "tight"].includes(p.risk)) });
    }
  }
  return links;
}

export function islandLayout(islands, spacing = 1) {
  const columns = Math.ceil(Math.sqrt(islands.length || 1));
  const rows = Math.ceil(islands.length / columns);
  return islands.map((p, i) => ({ id: p.id, x: ((i % columns) - (columns - 1) / 2) * 12 * spacing + (Math.floor(i / columns) % 2) * 2, z: (Math.floor(i / columns) - (rows - 1) / 2) * 11 * spacing, radius: Math.min(4.7, 3.4 + Math.sqrt(p.people.length) * .38) }));
}

export function demoResources(date) {
  const month = (date || new Date().toISOString().slice(0, 10)).slice(0, 7);
  const names = ["陈安", "李敏", "王越", "赵宁", "周清", "孙伟", "林涛", "刘洋"];
  const roles = ["后端工程师", "前端工程师", "测试工程师", "项目经理", "产品设计师", "后端工程师", "前端工程师", "运维工程师"];
  const members = names.map((name, i) => ({ id: i + 1, name, role: roles[i], capacity_hours_week: 40 }));
  const projects = ["资源排期系统", "客户门户改版", "数据同步服务", "交付与质量", "平台稳定性"].map((name, i) => ({ id: i + 1, name, status: "active" }));
  const rows = [[1, 1, 50, "API 服务与资源模型"], [2, 1, 30, "交互组件联调"], [3, 1, 35, "集成测试"], [4, 1, 40, "需求梳理与交付节奏"], [2, 2, 80, "Vue 工作台体验升级"], [5, 2, 60, "设计系统与页面规范"], [7, 2, 70, "前端组件实现"], [1, 3, 30, "同步服务技术预研"], [6, 3, 70, "数据管道开发"], [3, 4, 45, "回归测试计划"], [4, 4, 25, "交付协调"], [8, 5, 60, "服务监控与容量规划"], [6, 5, 30, "服务治理"]];
  const assignments = rows.map(([member_id, project_id, allocation_percent, task_name], i) => ({ id: `demo-${i}`, member_id, project_id, project_name: projects[project_id - 1].name, task_name, allocation_percent, start_date: `${month}-01`, end_date: "", status: i === 9 ? "blocked" : i === 1 ? "planned" : "active" }));
  return { members, projects, assignments, memberLoad: [] };
}
