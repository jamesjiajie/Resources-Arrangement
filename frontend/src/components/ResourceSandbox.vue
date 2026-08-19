<template>
  <section class="sandbox-view">
    <div class="sandbox-toolbar">
      <label>
        <span>{{ copy.scope }}</span>
        <select v-model="projectFilter">
          <option value="">{{ copy.allProjects }}</option>
          <option v-for="project in availableProjects" :key="project" :value="project">{{ project }}</option>
        </select>
      </label>
      <div class="sandbox-search">
        <Search :size="17" />
        <input v-model.trim="query" :placeholder="copy.search" />
      </div>
      <div class="view-switch" :aria-label="copy.viewMode">
        <button type="button" :class="{ active: mode === 'graph' }" @click="mode = 'graph'">
          <Network :size="17" />
        </button>
        <button type="button" :class="{ active: mode === 'list' }" @click="mode = 'list'">
          <List :size="17" />
        </button>
      </div>
    </div>

    <div v-if="usingDemo" class="demo-notice">
      <Info :size="16" />
      <span>{{ copy.demoNotice }}</span>
    </div>

    <div class="sandbox-grid" :class="{ 'list-mode': mode === 'list' }">
      <section class="relationship-stage">
        <div class="stage-heading">
          <strong>{{ copy.people }}（{{ filteredPeople.length }}）</strong>
          <strong>{{ copy.tasks }} / {{ copy.projects }}（{{ visibleAssignmentCount }}）</strong>
        </div>

        <div v-if="filteredPeople.length" class="relationship-rows">
          <article
            v-for="person in filteredPeople"
            :key="person.member_id"
            class="relationship-row"
            :class="{ selected: selectedPerson?.member_id === person.member_id }"
          >
            <button class="person-card" type="button" @click="selectedId = person.member_id">
              <img :src="person.avatar" :alt="person.name" />
              <span class="person-copy">
                <strong>{{ person.name }}</strong>
                <small>{{ person.role || copy.noRole }}</small>
                <b :class="person.risk">{{ Math.round(person.allocated_percent) }}%</b>
                <em>{{ person.allocated_hours }} / {{ person.capacity_hours_week }} {{ copy.hours }}</em>
              </span>
            </button>

            <div class="connection-stack" aria-hidden="true">
              <div v-for="assignment in person.assignments" :key="assignment.id" class="connection-item">
                <i :class="connectionClass(assignment)" :style="{ height: lineHeight(assignment.allocation_percent) + 'px' }"></i>
                <b>{{ Math.round(assignment.allocation_percent) }}%</b>
              </div>
              <div v-if="!person.assignments.length" class="connection-empty">{{ copy.noCurrentWork }}</div>
            </div>

            <div class="task-stack">
              <button
                v-if="person.assignments[0]"
                type="button"
                class="task-card"
                :class="person.assignments[0].status"
                @click="selectAssignment(person, person.assignments[0])"
              >
                <span class="project-line">
                  <FolderKanban :size="15" />
                  {{ person.assignments[0].project_name }}
                  <em :class="person.assignments[0].status">{{ statusLabel(person.assignments[0].status) }}</em>
                </span>
                <strong>{{ person.assignments[0].task_name }}</strong>
                <small>{{ copy.period }} {{ person.assignments[0].start_date }} — {{ person.assignments[0].end_date || copy.ongoing }}</small>
              </button>
              <div v-if="!person.assignments.length" class="task-empty">
                <CircleOff :size="18" />
                {{ copy.noCurrentWork }}
              </div>
            </div>
          </article>
        </div>

        <div v-else class="sandbox-empty">
          <SearchX :size="28" />
          <strong>{{ copy.noResults }}</strong>
          <span>{{ copy.tryAnother }}</span>
        </div>

        <footer class="sandbox-legend">
          <div>
            <strong>{{ copy.lineWeight }}</strong>
            <span><i class="weight thick"></i>≥ 60%</span>
            <span><i class="weight medium"></i>30%–59%</span>
            <span><i class="weight thin"></i>&lt; 30%</span>
          </div>
          <div>
            <strong>{{ copy.status }}</strong>
            <span><i class="dot overload"></i>{{ copy.overloaded }}</span>
            <span><i class="dot risk"></i>{{ copy.atRisk }}</span>
            <span><i class="dot normal"></i>{{ copy.normal }}</span>
          </div>
        </footer>
      </section>

      <aside v-if="selectedPerson" class="detail-panel">
        <div class="detail-head">
          <img :src="selectedPerson.avatar" :alt="selectedPerson.name" />
          <div>
            <strong>{{ selectedPerson.name }}</strong>
            <span>{{ selectedPerson.role || copy.noRole }}</span>
            <em :class="selectedPerson.risk">{{ riskLabel(selectedPerson.risk) }}</em>
          </div>
        </div>

        <section class="capacity-overview">
          <h3>{{ copy.capacityOverview }}</h3>
          <div class="capacity-chart">
            <svg viewBox="0 0 92 92" role="img" :aria-label="`${Math.round(selectedPerson.allocated_percent)}%`">
              <circle cx="46" cy="46" r="36" class="ring-track" />
              <circle
                cx="46"
                cy="46"
                r="36"
                class="ring-value"
                :class="selectedPerson.risk"
                :style="{ strokeDasharray: `${Math.min(selectedPerson.allocated_percent, 100) * 2.262} 226.2` }"
              />
            </svg>
            <strong>{{ Math.round(selectedPerson.allocated_percent) }}<small>%</small></strong>
          </div>
          <div class="capacity-numbers">
            <strong>{{ selectedPerson.allocated_hours }} / {{ selectedPerson.capacity_hours_week }} {{ copy.hours }}</strong>
            <span>{{ copy.plannedHours }}</span>
            <strong>{{ Math.max(0, selectedPerson.capacity_hours_week - selectedPerson.allocated_hours).toFixed(1) }} {{ copy.hours }}</strong>
            <span>{{ copy.availableHours }}</span>
          </div>
        </section>

        <section class="related-work">
          <h3>{{ copy.relatedWork }}（{{ selectedPerson.assignments.length }}）</h3>
          <button
            v-for="assignment in selectedPerson.assignments"
            :key="assignment.id"
            type="button"
            :class="{ active: selectedAssignment?.id === assignment.id }"
            @click="selectedAssignment = assignment"
          >
            <span><i :class="connectionClass(assignment)"></i>{{ assignment.project_name }}</span>
            <strong>{{ assignment.task_name }}</strong>
            <b>{{ Math.round(assignment.allocation_percent) }}%</b>
          </button>
        </section>

        <section v-if="riskAssignments.length" class="risk-note">
          <h3>{{ copy.riskNotes }}（{{ riskAssignments.length }}）</h3>
          <div>
            <AlertTriangle :size="18" />
            <p>
              <strong>{{ riskAssignments[0].task_name }}</strong>
              <span>{{ riskMessage(riskAssignments[0]) }}</span>
            </p>
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import AlertTriangle from "@lucide/vue/dist/esm/icons/triangle-alert.mjs";
import CircleOff from "@lucide/vue/dist/esm/icons/circle-off.mjs";
import FolderKanban from "@lucide/vue/dist/esm/icons/folder-kanban.mjs";
import Info from "@lucide/vue/dist/esm/icons/info.mjs";
import List from "@lucide/vue/dist/esm/icons/list.mjs";
import Network from "@lucide/vue/dist/esm/icons/network.mjs";
import Search from "@lucide/vue/dist/esm/icons/search.mjs";
import SearchX from "@lucide/vue/dist/esm/icons/search-x.mjs";

import chenAvatar from "../assets/avatars/chen-an.png";
import liAvatar from "../assets/avatars/li-min.png";
import wangAvatar from "../assets/avatars/wang-yue.png";
import zhaoAvatar from "../assets/avatars/zhao-ning.png";

const props = defineProps({
  language: { type: String, default: "zh" },
  members: { type: Array, default: () => [] },
  assignments: { type: Array, default: () => [] },
  memberLoad: { type: Array, default: () => [] },
});

const avatars = [chenAvatar, liAvatar, wangAvatar, zhaoAvatar];
const query = ref("");
const projectFilter = ref("");
const mode = ref("graph");
const selectedId = ref(null);
const selectedAssignment = ref(null);

const labels = {
  zh: {
    scope: "范围",
    allProjects: "全部项目",
    search: "搜索同事或任务",
    viewMode: "视图模式",
    demoNotice: "当前没有资源数据，正在展示示例沙盘；导入或新增安排后会自动切换为真实数据。",
    people: "同事",
    tasks: "任务",
    projects: "项目",
    hours: "小时",
    noRole: "未填写角色",
    noCurrentWork: "当前没有任务安排",
    period: "周期",
    ongoing: "持续",
    noResults: "没有匹配的关系",
    tryAnother: "请调整搜索词或项目范围。",
    lineWeight: "连线粗细（占用比例）",
    status: "状态说明",
    overloaded: "超负荷",
    atRisk: "风险",
    normal: "正常",
    capacityOverview: "容量概览",
    plannedHours: "本期计划工时",
    availableHours: "可用工时",
    relatedWork: "关联工作",
    riskNotes: "风险提示",
  },
  en: {
    scope: "Scope",
    allProjects: "All projects",
    search: "Search people or tasks",
    viewMode: "View mode",
    demoNotice: "No resource data yet. Showing a sample sandbox that will switch to live data after assignments are added.",
    people: "People",
    tasks: "Tasks",
    projects: "Projects",
    hours: "hours",
    noRole: "No role",
    noCurrentWork: "No current work",
    period: "Period",
    ongoing: "Ongoing",
    noResults: "No matching relationships",
    tryAnother: "Adjust the search or project scope.",
    lineWeight: "Line weight (allocation)",
    status: "Status",
    overloaded: "Overloaded",
    atRisk: "At risk",
    normal: "Normal",
    capacityOverview: "Capacity overview",
    plannedHours: "Planned hours",
    availableHours: "Available hours",
    relatedWork: "Related work",
    riskNotes: "Risk notes",
  },
};

const copy = computed(() => labels[props.language] || labels.zh);
const usingDemo = computed(() => !props.memberLoad.length && !props.assignments.length);

const demoAssignments = [
  { id: "d1", member_id: 1, project_name: "资源排期系统", task_name: "API 服务与资源模型", allocation_percent: 50, status: "blocked", start_date: "2026-08-01", end_date: "2026-08-28" },
  { id: "d2", member_id: 1, project_name: "数据同步服务", task_name: "同步服务技术预研", allocation_percent: 30, status: "active", start_date: "2026-08-05", end_date: "2026-08-20" },
  { id: "d3", member_id: 2, project_name: "客户门户改版", task_name: "Vue 工作台体验升级", allocation_percent: 80, status: "active", start_date: "2026-08-03", end_date: "2026-09-10" },
  { id: "d4", member_id: 2, project_name: "资源排期系统", task_name: "交互组件联调", allocation_percent: 30, status: "planned", start_date: "2026-08-11", end_date: "2026-08-26" },
  { id: "d5", member_id: 3, project_name: "客户门户改版", task_name: "回归测试计划", allocation_percent: 40, status: "blocked", start_date: "2026-08-05", end_date: "2026-08-20" },
  { id: "d6", member_id: 3, project_name: "数据同步服务", task_name: "接口验收", allocation_percent: 20, status: "active", start_date: "2026-08-10", end_date: "2026-08-31" },
  { id: "d7", member_id: 4, project_name: "资源排期系统", task_name: "需求梳理与交付节奏", allocation_percent: 25, status: "active", start_date: "2026-08-01", end_date: "2026-09-15" },
  { id: "d8", member_id: 4, project_name: "客户门户改版", task_name: "跨项目协调", allocation_percent: 20, status: "planned", start_date: "2026-08-11", end_date: "2026-08-25" },
];

const demoPeople = [
  { member_id: 1, name: "陈安", role: "后端工程师", team: "平台组", capacity_hours_week: 40, allocated_percent: 80, allocated_hours: 32, risk: "normal" },
  { member_id: 2, name: "李敏", role: "前端工程师", team: "体验组", capacity_hours_week: 40, allocated_percent: 110, allocated_hours: 44, risk: "overloaded" },
  { member_id: 3, name: "王越", role: "测试工程师", team: "质量组", capacity_hours_week: 40, allocated_percent: 60, allocated_hours: 24, risk: "blocked" },
  { member_id: 4, name: "赵宁", role: "项目经理", team: "交付组", capacity_hours_week: 40, allocated_percent: 45, allocated_hours: 18, risk: "normal" },
];

const people = computed(() => {
  const loads = usingDemo.value ? demoPeople : props.memberLoad;
  const work = usingDemo.value ? demoAssignments : props.assignments;
  return loads.map((load, index) => {
    const member = props.members.find((item) => item.id === load.member_id) || {};
    return {
      ...load,
      role: load.role || member.role || "",
      avatar: avatars[index % avatars.length],
      assignments: work.filter((item) => item.member_id === load.member_id),
    };
  });
});

const availableProjects = computed(() => {
  const names = people.value.flatMap((person) => person.assignments.map((item) => item.project_name));
  return [...new Set(names)].filter(Boolean).sort();
});

const filteredPeople = computed(() => {
  const needle = query.value.toLowerCase();
  return people.value
    .map((person) => ({
      ...person,
      assignments: person.assignments.filter((item) => {
        const matchesProject = !projectFilter.value || item.project_name === projectFilter.value;
        const text = `${person.name} ${person.role} ${item.project_name} ${item.task_name}`.toLowerCase();
        return matchesProject && (!needle || text.includes(needle));
      }),
    }))
    .filter((person) => {
      if (person.assignments.length) return true;
      if (projectFilter.value) return false;
      return !needle || `${person.name} ${person.role}`.toLowerCase().includes(needle);
    });
});

const visibleAssignmentCount = computed(() => filteredPeople.value.reduce((sum, person) => sum + person.assignments.length, 0));
const selectedPerson = computed(() => people.value.find((person) => person.member_id === selectedId.value) || filteredPeople.value[0] || null);
const riskAssignments = computed(() => selectedPerson.value?.assignments.filter((item) => item.status === "blocked" || item.allocation_percent >= 70) || []);

watch(people, (items) => {
  if (!items.some((item) => item.member_id === selectedId.value)) selectedId.value = items[0]?.member_id ?? null;
}, { immediate: true });

watch(selectedPerson, (person) => {
  selectedAssignment.value = person?.assignments[0] || null;
});

function selectAssignment(person, assignment) {
  selectedId.value = person.member_id;
  selectedAssignment.value = assignment;
}

function lineHeight(percent) {
  if (percent >= 60) return 6;
  if (percent >= 30) return 4;
  return 2;
}

function connectionClass(assignment) {
  if (assignment.status === "blocked") return "blocked";
  if (assignment.allocation_percent >= 70) return "risk";
  return "normal";
}

function statusLabel(status) {
  const values = props.language === "en"
    ? { planned: "Planned", active: "Active", blocked: "Blocked", done: "Done", paused: "Paused" }
    : { planned: "计划", active: "正常", blocked: "阻塞", done: "完成", paused: "暂停" };
  return values[status] || status;
}

function riskLabel(risk) {
  const values = props.language === "en"
    ? { overloaded: "Overloaded", blocked: "Blocked", tight: "Near capacity", underused: "Available", normal: "Normal" }
    : { overloaded: "超负荷", blocked: "有阻塞", tight: "接近满载", underused: "可继续安排", normal: "正常" };
  return values[risk] || values.normal;
}

function riskMessage(assignment) {
  if (props.language === "en") return assignment.status === "blocked" ? "Blocked work needs attention." : "High allocation may create delivery risk.";
  return assignment.status === "blocked" ? "任务已阻塞，需要尽快明确依赖与处理人。" : "占用比例较高，可能影响同一成员的其他交付。";
}
</script>

<style scoped>
.sandbox-view { display: grid; gap: 12px; }
.sandbox-toolbar { display: flex; align-items: end; justify-content: flex-end; gap: 10px; }
.sandbox-toolbar label { min-width: 170px; }
.sandbox-search { display: flex; align-items: center; gap: 8px; min-width: 250px; height: 40px; border: 1px solid var(--line); border-radius: 6px; background: #fff; padding: 0 10px; color: var(--muted); }
.sandbox-search input { min-height: 36px; border: 0; outline: 0; padding: 0; }
.view-switch { display: flex; height: 40px; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; background: #fff; }
.view-switch button { width: 46px; border: 0; border-right: 1px solid var(--line); background: #fff; color: var(--muted); }
.view-switch button:last-child { border-right: 0; }
.view-switch button.active { background: #dceafa; color: #234f84; }
.demo-notice { display: flex; align-items: center; gap: 8px; border: 1px solid #f0d6a8; border-radius: 7px; background: #fff8ed; color: #8a5b08; padding: 9px 12px; font-size: 13px; }
.sandbox-grid { display: grid; grid-template-columns: minmax(0, 1fr) 286px; gap: 14px; min-height: 690px; }
.relationship-stage, .detail-panel { border: 1px solid var(--line); border-radius: 8px; background: var(--surface); box-shadow: var(--shadow); }
.relationship-stage { display: flex; flex-direction: column; min-width: 0; padding: 16px; }
.stage-heading { display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: 270px; margin-bottom: 12px; color: var(--ink); font-size: 14px; }
.relationship-rows { display: grid; gap: 10px; }
.relationship-row { display: grid; grid-template-columns: 160px 250px minmax(230px, 1fr); align-items: center; min-height: 124px; }
.person-card { display: flex; align-items: center; gap: 10px; min-height: 108px; border: 1px solid var(--line); border-radius: 8px; background: #fff; color: var(--ink); padding: 12px; text-align: left; box-shadow: 0 8px 24px rgba(23, 32, 51, 0.06); }
.relationship-row.selected .person-card { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(15, 107, 127, 0.1); }
.person-card img { width: 48px; height: 48px; flex: 0 0 auto; border-radius: 50%; object-fit: cover; }
.person-copy { min-width: 0; }
.person-copy strong, .person-copy small, .person-copy b, .person-copy em { display: block; }
.person-copy strong { margin-bottom: 3px; }
.person-copy small, .person-copy em { color: var(--muted); font-size: 11px; font-style: normal; white-space: nowrap; }
.person-copy b { margin: 5px 0 1px; color: var(--primary); font-size: 20px; }
.person-copy b.overloaded, .person-copy b.blocked { color: var(--red); }
.person-copy b.tight { color: var(--yellow); }
.connection-stack, .task-stack { display: grid; align-content: center; gap: 8px; }
.connection-item { display: grid; grid-template-columns: minmax(0, 1fr) 45px; align-items: center; gap: 8px; }
.connection-item i { display: block; width: 100%; border-radius: 99px; background: #9aa6b7; }
.connection-item i.normal, .related-work i.normal { background: var(--primary); }
.connection-item i.risk, .related-work i.risk { background: #f06b09; }
.connection-item i.blocked, .related-work i.blocked { background: #e22b2b; }
.connection-item b { color: var(--muted); font-size: 12px; }
.connection-item i.risk + b, .connection-item i.blocked + b { color: #e85d08; }
.connection-empty { color: var(--muted); font-size: 12px; text-align: center; }
.task-card { display: grid; gap: 5px; min-height: 74px; border: 1px solid var(--line); border-radius: 8px; background: #fff; color: var(--ink); padding: 11px 12px; text-align: left; box-shadow: 0 5px 16px rgba(23, 32, 51, 0.05); }
.task-card:hover { border-color: var(--primary); }
.task-card.blocked { border-color: #efb2b2; }
.task-card strong { font-size: 14px; }
.task-card small { color: var(--muted); font-size: 11px; }
.project-line { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 11px; }
.project-line em { margin-left: auto; border-radius: 4px; background: #e5f4ee; color: var(--green); padding: 3px 6px; font-style: normal; font-weight: 700; }
.project-line em.blocked { background: #fdeaea; color: var(--red); }
.project-line em.planned { background: #fff1e5; color: #d85f09; }
.task-empty { display: flex; align-items: center; justify-content: center; gap: 7px; min-height: 72px; border: 1px dashed var(--line); border-radius: 8px; color: var(--muted); font-size: 12px; }
.sandbox-empty { display: grid; place-items: center; align-content: center; gap: 8px; min-height: 440px; color: var(--muted); }
.sandbox-empty strong { color: var(--ink); }
.sandbox-legend { display: flex; justify-content: space-between; gap: 20px; margin-top: auto; border-top: 1px solid var(--line); padding-top: 13px; font-size: 11px; color: var(--muted); }
.sandbox-legend > div { display: flex; align-items: center; gap: 13px; }
.sandbox-legend strong { color: var(--ink); }
.sandbox-legend span { display: inline-flex; align-items: center; gap: 5px; }
.weight { display: inline-block; width: 28px; border-radius: 99px; background: #8d98aa; }
.weight.thick { height: 6px; } .weight.medium { height: 4px; } .weight.thin { height: 2px; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: #9aa6b7; }
.dot.overload { background: #e22b2b; } .dot.risk { background: #f06b09; } .dot.normal { background: var(--primary); }
.detail-panel { align-self: start; overflow: hidden; }
.detail-head { display: flex; align-items: center; gap: 12px; padding: 18px; border-bottom: 1px solid var(--line); }
.detail-head img { width: 52px; height: 52px; border-radius: 50%; object-fit: cover; }
.detail-head strong, .detail-head span { display: block; }
.detail-head span { margin: 3px 0 7px; color: var(--muted); font-size: 12px; }
.detail-head em { color: var(--green); font-size: 12px; font-style: normal; font-weight: 700; }
.detail-head em.overloaded, .detail-head em.blocked { color: var(--red); }
.capacity-overview, .related-work, .risk-note { padding: 16px 18px; border-bottom: 1px solid var(--line); }
.detail-panel h3 { margin: 0 0 13px; font-size: 14px; }
.capacity-overview { display: grid; grid-template-columns: 94px 1fr; column-gap: 12px; }
.capacity-overview h3 { grid-column: 1 / -1; }
.capacity-chart { position: relative; width: 92px; height: 92px; }
.capacity-chart svg { width: 92px; height: 92px; transform: rotate(-90deg); }
.capacity-chart circle { fill: none; stroke-width: 10; }
.ring-track { stroke: #e7edf5; }
.ring-value { stroke: var(--primary); stroke-linecap: round; }
.ring-value.overloaded, .ring-value.blocked { stroke: var(--red); }
.capacity-chart > strong { position: absolute; inset: 0; display: grid; place-items: center; font-size: 21px; }
.capacity-chart small { font-size: 12px; }
.capacity-numbers { display: grid; align-content: center; gap: 2px; }
.capacity-numbers strong { margin-top: 5px; font-size: 13px; }
.capacity-numbers span { color: var(--muted); font-size: 11px; }
.related-work { display: grid; gap: 7px; }
.related-work h3 { margin-bottom: 5px; }
.related-work button { position: relative; display: grid; gap: 3px; border: 0; border-left: 2px solid transparent; background: transparent; color: var(--ink); padding: 7px 8px 7px 10px; text-align: left; }
.related-work button:hover, .related-work button.active { border-left-color: var(--primary); background: var(--surface-soft); }
.related-work button span { display: flex; align-items: center; gap: 5px; color: var(--muted); font-size: 10px; }
.related-work button i { width: 7px; height: 7px; border-radius: 50%; }
.related-work button strong { padding-right: 42px; font-size: 12px; }
.related-work button b { position: absolute; right: 8px; bottom: 8px; color: var(--primary); font-size: 12px; }
.risk-note { border-bottom: 0; }
.risk-note > div { display: flex; gap: 8px; border: 1px solid #f0d6a8; border-radius: 7px; background: #fff8ed; color: #dc620a; padding: 10px; }
.risk-note p { margin: 0; }
.risk-note strong, .risk-note span { display: block; }
.risk-note strong { margin-bottom: 4px; font-size: 12px; }
.risk-note span { color: #805317; font-size: 11px; line-height: 1.5; }
.list-mode .relationship-row { grid-template-columns: 160px 0 minmax(230px, 1fr); gap: 14px; }
.list-mode .connection-stack { overflow: hidden; }
@media (max-width: 1280px) {
  .sandbox-grid { grid-template-columns: 1fr; }
  .detail-panel { display: grid; grid-template-columns: repeat(3, 1fr); }
  .detail-head { border-right: 1px solid var(--line); }
  .capacity-overview, .related-work { border-right: 1px solid var(--line); border-bottom: 0; }
  .risk-note { border-bottom: 0; }
}
@media (max-width: 900px) {
  .sandbox-toolbar { align-items: stretch; flex-direction: column; }
  .sandbox-toolbar label, .sandbox-search { min-width: 0; }
  .stage-heading { display: none; }
  .relationship-row { grid-template-columns: 140px 90px minmax(220px, 1fr); }
  .detail-panel { grid-template-columns: 1fr; }
  .detail-head, .capacity-overview, .related-work { border-right: 0; border-bottom: 1px solid var(--line); }
  .sandbox-legend { align-items: flex-start; flex-direction: column; }
  .sandbox-legend > div { flex-wrap: wrap; }
}
</style>
