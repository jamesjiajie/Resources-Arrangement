const activeStatuses = new Set(["active", "planned", "blocked"]);

export function isCurrentAssignment(item, date) {
  if (!activeStatuses.has(item.status)) return false;
  if (!date) return true;
  if (item.start_date && item.start_date > date) return item.status !== "planned";
  return !item.end_date || item.end_date >= date;
}

export function buildCommandBoard({ members = [], assignments = [], memberLoad = [], currentDate = "" }) {
  const current = assignments.filter((item) => isCurrentAssignment(item, currentDate));
  const snapshotDate = assignments.map((item) => item.end_date || item.start_date || "").sort().at(-1) || "";
  const snapshot = current.length ? [] : assignments.filter((item) => isCurrentAssignment(item, snapshotDate));
  const source = current.length ? current : snapshot;
  const loads = new Map(memberLoad.map((item) => [String(item.member_id), item]));
  const memberMap = new Map(members.map((item) => [String(item.id), item]));
  const people = [...new Set(source.map((item) => String(item.member_id)))].map((id) => {
    const assignmentsForPerson = source.filter((item) => String(item.member_id) === id);
    const load = current.length ? loads.get(id) : null;
    const member = memberMap.get(id);
    const allocated = load?.allocated_percent ?? assignmentsForPerson.reduce((sum, item) => sum + Number(item.allocation_percent || 0), 0);
    return {
      id,
      name: load?.name || member?.name || assignmentsForPerson[0]?.member_name || "未命名成员",
      role: load?.role || member?.role || assignmentsForPerson[0]?.role || "未填写角色",
      allocated: Math.round(allocated),
      risk: load?.risk || (assignedRisk(assignmentsForPerson, allocated)),
      assignments: assignmentsForPerson,
    };
  }).sort((a, b) => b.allocated - a.allocated);
  const projects = [...new Map(source.map((item) => [String(item.project_id || item.project_name), {
    id: String(item.project_id || item.project_name), name: item.project_name || "未命名项目",
  }])).values()].map((project) => {
    const items = source.filter((item) => String(item.project_id || item.project_name) === project.id);
    return { ...project, assignments: items, people: new Set(items.map((item) => String(item.member_id))).size, risk: items.some((item) => item.status === "blocked") };
  });
  return { people, projects, assignments: source, usingHistoricalSnapshot: !current.length && snapshot.length > 0, snapshotDate };
}

function assignedRisk(assignments, allocated) {
  if (assignments.some((item) => item.status === "blocked")) return "blocked";
  if (allocated > 100) return "overloaded";
  if (allocated >= 85) return "tight";
  return "normal";
}
