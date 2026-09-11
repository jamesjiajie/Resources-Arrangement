<template>
  <section class="command-sandbox">
    <header class="command-topbar">
      <div><h1>资源指挥沙盘</h1><p>按编组观察团队力量与任务部署。</p></div>
      <div class="top-actions">
        <label class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索项目、同事、任务" /></label>
        <button type="button" :class="{ active: risksOnly }" @click="risksOnly = !risksOnly"><Filter :size="17" /> 风险筛选<span v-if="riskCount" class="signal"></span></button>
        <input v-model="localDate" type="date" @change="$emit('update-date', localDate)" />
        <button class="refresh" type="button" @click="$emit('refresh')"><RefreshCw :size="17" /> 刷新</button>
      </div>
    </header>

    <div class="section-title-row">
      <h2 class="section-heading">编组部署图 <small>{{ graphProjects.length }} 个项目</small></h2>
      <div class="layout-toolbar">
        <span v-if="layoutDirty" class="dirty-state">有未保存更改</span>
        <button type="button" :disabled="!layoutHistory.length" @click="undoLayout"><Undo2 :size="15" /> 撤销</button>
        <button type="button" @click="restoreLayout"><RotateCcw :size="15" /> 恢复默认</button>
        <button class="save-layout" type="button" :disabled="!layoutDirty" @click="saveLayout"><Save :size="15" /> 保存布局</button>
      </div>
    </div>
    <div class="control-strip">
      <div class="metrics">
        <span><small>团队总容量</small><b>{{ totalCapacity }}</b><em>小时/周</em></span>
        <span><small>团队总负荷</small><b>{{ totalHours }}</b><em>小时/周</em></span>
        <span><small>团队平均占用</small><b>{{ averageLoad }}%</b></span>
        <span><small>超负荷人数</small><b class="danger">{{ overloadedCount }}</b><em>人</em></span>
        <span><small>阻塞任务</small><b class="warning">{{ riskCount }}</b><em>项</em></span>
        <span><small>即将到期</small><b class="teal">{{ dueSoonCount }}</b><em>项</em></span>
      </div>
      <label class="select-control"><small>地图密度</small><select v-model="density"><option value="medium">中等</option><option value="high">较高</option></select></label>
      <button class="view-control" type="button" @click="perspective = !perspective"><Box :size="18" /><span><small>视图</small><b>{{ perspective ? '斜视' : '顶视' }}</b></span></button>
      <button class="plain-control" type="button" :class="{ active: focused }" @click="focused = !focused"><Focus :size="18" /> 聚焦</button>
      <button class="plain-control" type="button" @click="reset"><RotateCcw :size="18" /> 重置</button>
    </div>

    <div v-if="board.usingHistoricalSnapshot" class="snapshot-note"><Info :size="15" /> 基准日期暂无进行中安排，图中展示你的最近真实快照：{{ board.snapshotDate }}</div>
    <div class="workspace">
      <main ref="boardEl" class="deployment-board" :class="{ perspective, 'high-density': density === 'high', 'is-arranging': draggingZoneId || draggingProjectId }" :style="{ '--terrain': `url(${terrain})` }">
        <svg class="routes" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path v-for="route in zoneRoutes" :key="route.id" :d="routePath(route)" :class="route.kind" />
        </svg>
        <section
          v-for="zone in projectZones"
          :key="zone.id"
          class="deployment-zone"
          :class="[zone.id, { 'drop-target': dragoverZoneId === zone.id, 'is-dragging': draggingZoneId === zone.id }]"
          :style="zoneStyle(zone)"
        >
          <header>
            <button class="zone-drag-handle" type="button" :aria-label="`拖动${zone.label}`" @pointerdown="startZoneDrag($event, zone)"><GripVertical :size="16" /></button>
            <form v-if="editingZoneId === zone.id" class="zone-name-editor" @submit.prevent="confirmZoneName(zone.id)">
              <input ref="zoneNameInput" v-model.trim="editingZoneName" maxlength="18" aria-label="分区名称" @keydown.esc="cancelZoneName" />
              <button type="submit" aria-label="确认名称"><Check :size="14" /></button>
              <button type="button" aria-label="取消修改" @click="cancelZoneName"><X :size="14" /></button>
            </form>
            <template v-else>
              <h3>{{ zone.label }}</h3>
              <button class="zone-edit-button" type="button" :aria-label="`修改${zone.label}名称`" @click="editZoneName(zone)"><Pencil :size="13" /></button>
            </template>
            <small>{{ zone.projects.length }} 个项目</small>
          </header>
          <div class="zone-projects">
            <article
              v-for="project in zone.projects"
              :key="project.id"
              class="project-card"
              :class="[projectTone(project), { selected: selectedProjectId === project.id, dragging: draggingProjectId === project.id }]"
            >
              <button class="project-drag-handle" type="button" :aria-label="`拖动${project.name}`" @pointerdown.stop.prevent="startProjectDrag($event, project)"><GripVertical :size="13" /></button>
              <button class="project-card-content" type="button" :aria-label="project.name" @click="selectProject(project.id)">
                <span class="project-title"><Flag :size="14" /> {{ project.name }}</span><b>{{ projectLoad(project) }}%</b><small>{{ projectHours(project) }} 小时</small><i></i>
              </button>
            </article>
          </div>
          <div v-if="draggingProjectId && dragoverZoneId === zone.id" class="drop-message">移入此分区</div>
        </section>
        <div v-if="draggingProjectId" class="project-drag-ghost" :style="pointStyle(projectDragPoint)"><Flag :size="13" /> {{ draggingProjectName }}</div>
        <div class="operations-center"><strong>人员作战中心</strong><small>{{ board.snapshotDate || localDate }}</small></div>
        <button v-for="person in graphPeople" :key="person.id" class="person-node" :class="[{ selected: selectedPerson?.id === person.id }, person.risk]" :style="pointStyle(person.position)" type="button" @click="selectPerson(person.id)">
          <CartoonAvatar :index="avatarIndex(person)" :label="person.name" /><strong>{{ person.name }}</strong><b>{{ person.allocated }}%</b><small>{{ personHours(person) }} / {{ capacityFor(person) }} 小时</small>
        </button>
        <button v-for="task in taskNodes" :key="task.id" class="task-node" :class="task.status" :style="pointStyle(task.position)" type="button" @click="selectTask(task)">
          <b>{{ task.allocation_percent }}%</b><small>{{ short(task.task_name, 9) }}</small>
        </button>
        <div class="map-key"><span><Flag :size="14" /> 项目目标</span><span><UserRound :size="14" /> 团队成员</span><span><Circle :size="14" /> 任务分配</span><span class="line primary"></span>主要分配<span class="line secondary"></span>次要分配<AlertTriangle :size="14" /> 阻塞</div>
        <div v-if="layoutToast" class="layout-toast">{{ layoutToast }} <button v-if="layoutHistory.length" type="button" @click="undoLayout">撤销</button></div>
      </main>

      <aside class="inspector" v-if="selectedPerson">
        <header><h2>{{ selectedPerson.name }}</h2><button type="button" aria-label="关闭详情" @click="selectedPersonId = ''"><X :size="19" /></button></header>
        <div class="person-overview">
          <CartoonAvatar :index="avatarIndex(selectedPerson)" :label="selectedPerson.name" /><p>{{ selectedPerson.role }}<br /><span>{{ memberTeam(selectedPerson) }}</span></p>
          <strong :class="selectedPerson.risk">{{ selectedPerson.allocated }}%<small>{{ personHours(selectedPerson) }} / {{ capacityFor(selectedPerson) }} 小时</small></strong>
          <div class="load-ring" :style="{ '--load': Math.min(selectedPerson.allocated, 100) * 3.6 + 'deg' }"><span></span></div>
        </div>
        <div class="tabs"><button class="active" type="button">任务分配 ({{ selectedPerson.assignments.length }})</button><button type="button">资料</button></div>
        <div class="assignment-table">
          <div class="table-head"><span>任务 / 项目</span><span>状态</span><span>分配</span><span>期间</span></div>
          <button v-for="task in selectedPerson.assignments" :key="task.id" type="button" :class="{ selected: selectedTask?.id === task.id }" @click="selectTask(task)">
            <span><b>{{ task.task_name }}</b><small>{{ task.project_name }}</small></span><em>{{ statusText(task.status) }}</em><strong>{{ task.allocation_percent }}%</strong><small>{{ shortPeriod(task) }}</small>
          </button>
        </div>
        <section class="profile-section"><h3>能力与标签</h3><div><span>{{ selectedPerson.role || '未填写角色' }}</span><span>{{ memberTeam(selectedPerson) }}</span><span>项目协作</span></div></section>
        <section class="profile-section"><h3>备注</h3><p>{{ selectedTask?.notes || '暂无备注。' }}</p></section>
        <footer>数据快照：{{ board.snapshotDate || localDate }}</footer>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import AlertTriangle from "@lucide/vue/dist/esm/icons/triangle-alert.mjs";
import Box from "@lucide/vue/dist/esm/icons/box.mjs";
import Circle from "@lucide/vue/dist/esm/icons/circle.mjs";
import Filter from "@lucide/vue/dist/esm/icons/funnel.mjs";
import Flag from "@lucide/vue/dist/esm/icons/flag.mjs";
import Focus from "@lucide/vue/dist/esm/icons/focus.mjs";
import Info from "@lucide/vue/dist/esm/icons/info.mjs";
import Check from "@lucide/vue/dist/esm/icons/check.mjs";
import GripVertical from "@lucide/vue/dist/esm/icons/grip-vertical.mjs";
import Pencil from "@lucide/vue/dist/esm/icons/pencil.mjs";
import RefreshCw from "@lucide/vue/dist/esm/icons/refresh-cw.mjs";
import RotateCcw from "@lucide/vue/dist/esm/icons/rotate-ccw.mjs";
import Search from "@lucide/vue/dist/esm/icons/search.mjs";
import Save from "@lucide/vue/dist/esm/icons/save.mjs";
import Undo2 from "@lucide/vue/dist/esm/icons/undo-2.mjs";
import UserRound from "@lucide/vue/dist/esm/icons/user-round.mjs";
import X from "@lucide/vue/dist/esm/icons/x.mjs";
import CartoonAvatar from "./CartoonAvatar.vue";
import terrain from "../assets/command-sandbox/terrain-board.png";
import { buildCommandBoard } from "../lib/commandSandbox.js";

const props = defineProps({ members: { type: Array, default: () => [] }, assignments: { type: Array, default: () => [] }, memberLoad: { type: Array, default: () => [] }, currentDate: { type: String, default: "" } });
defineEmits(["update-date", "refresh"]);
const femaleNames = new Set(["crystal", "zinnia", "linda", "anny", "zoey", "eliina", "winnie", "cindy"]);
const avatarPools = { female: [0, 2, 5, 6], male: [1, 3, 4, 7] };
const mediumPersonPositions = [[39,35],[61,35],[39,63],[61,63]];
const highPersonPositions = [[34,35],[50,35],[66,35],[34,63],[50,63],[66,63]];
const taskPositions = [[28,51],[72,51]];
const zoneDefinitions = [
  { id: 'core', label: '核心基础设施区', names: ['som', 'commercial fixed', 'rbs'], anchor: [36, 22], axis: 'vertical', frame: [2, 2, 46, 22] },
  { id: 'platform', label: '平台与智能应用区', names: ['nexus', 'ai hub', 'lts-migration'], anchor: [64, 22], axis: 'vertical', frame: [52, 2, 46, 22] },
  { id: 'support', label: '业务支撑与替换区', names: ['3gs-boss', 'quadiem replacement'], anchor: [24, 50], axis: 'horizontal', frame: [2, 32, 22, 36] },
  { id: 'overseas', label: '海外与财务区', names: ['aaoe', 'inv'], anchor: [76, 50], axis: 'horizontal', frame: [76, 32, 22, 36] },
  { id: 'operations', label: '运营与媒体区', names: ['med', 'mvno', 'now-tv'], anchor: [50, 77], axis: 'vertical', frame: [17, 74, 66, 18] },
];
const layoutStorageKey = 'resource-command-sandbox-layout-v1';
function defaultLayout() { return { labels: Object.fromEntries(zoneDefinitions.map((zone) => [zone.id, zone.label])), positions: Object.fromEntries(zoneDefinitions.map((zone) => [zone.id, zone.frame.slice(0, 2)])), projectZones: {} }; }
function loadLayout() { try { const saved = JSON.parse(window.localStorage.getItem(layoutStorageKey) || 'null'); const fallback = defaultLayout(); return saved && typeof saved === 'object' ? { labels: { ...fallback.labels, ...saved.labels }, positions: { ...fallback.positions, ...saved.positions }, projectZones: saved.projectZones || {} } : fallback; } catch { return defaultLayout(); } }
const query = ref(""); const projectFilter = ref(""); const selectedPersonId = ref(""); const selectedProjectId = ref(""); const selectedTaskId = ref(""); const perspective = ref(true); const focused = ref(false); const risksOnly = ref(false); const density = ref("high"); const localDate = ref(props.currentDate);
const layout = ref(loadLayout()); const savedLayout = ref(JSON.stringify(layout.value)); const layoutHistory = ref([]); const editingZoneId = ref(''); const editingZoneName = ref(''); const zoneNameInput = ref(null); const boardEl = ref(null); const draggingZoneId = ref(''); const draggingProjectId = ref(''); const draggingProjectName = ref(''); const projectDragPoint = ref([0, 0]); const dragoverZoneId = ref(''); const layoutToast = ref('');
let dragStart = null; let toastTimer = 0;
const board = computed(() => buildCommandBoard(props));
const layoutDirty = computed(() => JSON.stringify(layout.value) !== savedLayout.value);
const filteredPeople = computed(() => board.value.people.filter((person) => { const text = `${person.name} ${person.role} ${person.assignments.map((task) => `${task.project_name} ${task.task_name}`).join(' ')}`.toLowerCase(); return (!query.value || text.includes(query.value.toLowerCase())) && (!projectFilter.value || person.assignments.some((task) => String(task.project_id || task.project_name) === projectFilter.value)) && (!risksOnly.value || ['blocked','overloaded','tight'].includes(person.risk)); }));
const selectedPerson = computed(() => board.value.people.find((person) => person.id === selectedPersonId.value) || filteredPeople.value[0] || board.value.people[0]);
const selectedTask = computed(() => selectedPerson.value?.assignments.find((task) => task.id === selectedTaskId.value));
const graphPeople = computed(() => { const limit = focused.value ? 1 : density.value === 'high' ? 6 : 4; const list = focused.value ? [selectedPerson.value] : filteredPeople.value; const positions = density.value === 'high' ? highPersonPositions : mediumPersonPositions; return list.filter(Boolean).slice(0, limit).map((person, index) => ({ ...person, position: positions[index] || [50, 52] })); });
const graphProjects = computed(() => { const ids = new Set(graphPeople.value.flatMap((person) => person.assignments.map((task) => String(task.project_id || task.project_name)))); let list = board.value.projects.filter((project) => (!projectFilter.value || project.id === projectFilter.value) && (ids.has(project.id) || !focused.value)); if (selectedProjectId.value) list.sort((a) => a.id === selectedProjectId.value ? -1 : 0); return list; });
const projectZones = computed(() => zoneDefinitions.map((zone) => ({ ...zone, label: layout.value.labels[zone.id] || zone.label, projects: graphProjects.value.filter((project) => zoneForProject(project) === zone.id) })));
const taskNodes = computed(() => graphPeople.value.slice(0, 2).flatMap((person, index) => person.assignments.slice(0, 1).map((task) => ({ ...task, personId: person.id, position: taskPositions[index] }))));
const zoneRoutes = computed(() => { const result = []; for (const person of graphPeople.value) { const grouped = new Map(); for (const task of person.assignments) { const project = graphProjects.value.find((item) => item.id === String(task.project_id || task.project_name)); if (!project) continue; const zone = zoneDefinitions.find((item) => item.id === zoneForProject(project)); const prior = grouped.get(zone.id) || { zone, tasks: [] }; prior.tasks.push(task); grouped.set(zone.id, prior); } for (const { zone, tasks } of grouped.values()) { const [left, top] = layout.value.positions[zone.id] || zone.frame; const dx = left - zone.frame[0]; const dy = top - zone.frame[1]; result.push({ id: `${zone.id}-${person.id}`, x1: zone.anchor[0] + dx, y1: zone.anchor[1] + dy, x2: person.position[0], y2: person.position[1], axis: zone.axis, kind: tasks.some((task) => task.status === 'blocked') ? 'blocked' : tasks.some((task) => Number(task.allocation_percent) >= 50) ? 'primary' : 'secondary' }); } } return result; });
const riskCount = computed(() => board.value.assignments.filter((task) => task.status === 'blocked').length);
const overloadedCount = computed(() => board.value.people.filter((person) => person.allocated > 100).length);
const averageLoad = computed(() => board.value.people.length ? Math.round(board.value.people.reduce((sum, person) => sum + person.allocated, 0) / board.value.people.length) : 0);
const totalCapacity = computed(() => props.members.reduce((sum, member) => sum + Number(member.capacity_hours_week || 40), 0));
const totalHours = computed(() => board.value.people.reduce((sum, person) => sum + personHours(person), 0));
const dueSoonCount = computed(() => board.value.assignments.filter((task) => task.end_date && task.end_date >= localDate.value && (new Date(task.end_date) - new Date(localDate.value)) / 86400000 <= 7).length);
watch(() => props.currentDate, (value) => { localDate.value = value; });
watch(filteredPeople, (people) => { if (!people.some((person) => person.id === selectedPersonId.value)) selectedPersonId.value = people[0]?.id || ''; }, { immediate: true });
function selectPerson(id) { selectedPersonId.value = id; selectedTaskId.value = ''; }
function selectProject(id) { projectFilter.value = projectFilter.value === id ? '' : id; selectedProjectId.value = id; }
function selectTask(task) { selectedPersonId.value = String(task.member_id); selectedTaskId.value = task.id; }
function reset() { query.value = ''; projectFilter.value = ''; selectedProjectId.value = ''; selectedTaskId.value = ''; perspective.value = true; focused.value = false; risksOnly.value = false; density.value = 'high'; }
function snapshotLayout() { layoutHistory.value.push(JSON.stringify(layout.value)); if (layoutHistory.value.length > 20) layoutHistory.value.shift(); }
function zoneStyle(zone) { const [left, top] = layout.value.positions[zone.id] || zone.frame; return { left: `${left}%`, top: `${top}%`, width: `${zone.frame[2]}%`, height: `${zone.frame[3]}%` }; }
function editZoneName(zone) { editingZoneId.value = zone.id; editingZoneName.value = zone.label; nextTick(() => zoneNameInput.value?.focus()); }
function cancelZoneName() { editingZoneId.value = ''; editingZoneName.value = ''; }
function confirmZoneName(zoneId) { const value = editingZoneName.value.trim(); if (!value || value === layout.value.labels[zoneId]) return cancelZoneName(); snapshotLayout(); layout.value.labels[zoneId] = value; cancelZoneName(); showLayoutToast('分区名称已更新'); }
function startZoneDrag(event, zone) { if (event.button !== 0 || !boardEl.value) return; event.preventDefault(); const rect = boardEl.value.getBoundingClientRect(); const [left, top] = layout.value.positions[zone.id] || zone.frame; snapshotLayout(); draggingZoneId.value = zone.id; dragStart = { x: event.clientX, y: event.clientY, left, top, width: zone.frame[2], height: zone.frame[3], rect }; window.addEventListener('pointermove', moveZone); window.addEventListener('pointerup', endZoneDrag, { once: true }); }
function moveZone(event) { if (!dragStart || !draggingZoneId.value) return; const x = dragStart.left + (event.clientX - dragStart.x) / dragStart.rect.width * 100; const y = dragStart.top + (event.clientY - dragStart.y) / dragStart.rect.height * 100; layout.value.positions[draggingZoneId.value] = [Math.round(Math.max(0, Math.min(100 - dragStart.width, x))), Math.round(Math.max(0, Math.min(100 - dragStart.height, y)))]; }
function endZoneDrag() { window.removeEventListener('pointermove', moveZone); if (dragStart && draggingZoneId.value) { const prior = JSON.parse(layoutHistory.value.at(-1) || '{}'); if (JSON.stringify(prior.positions?.[draggingZoneId.value]) === JSON.stringify(layout.value.positions[draggingZoneId.value])) layoutHistory.value.pop(); else showLayoutToast('分区位置已调整'); } draggingZoneId.value = ''; dragStart = null; }
function startProjectDrag(event, project) { if (event.button !== 0 || !boardEl.value) return; draggingProjectId.value = project.id; draggingProjectName.value = project.name; moveProject(event); window.addEventListener('pointermove', moveProject); window.addEventListener('pointerup', endProjectDrag, { once: true }); }
function moveProject(event) { if (!draggingProjectId.value || !boardEl.value) return; const rect = boardEl.value.getBoundingClientRect(); const point = [(event.clientX - rect.left) / rect.width * 100, (event.clientY - rect.top) / rect.height * 100]; projectDragPoint.value = point; dragoverZoneId.value = projectZones.value.find((zone) => { const [left, top] = layout.value.positions[zone.id] || zone.frame; return point[0] >= left && point[0] <= left + zone.frame[2] && point[1] >= top && point[1] <= top + zone.frame[3]; })?.id || ''; }
function endProjectDrag() { window.removeEventListener('pointermove', moveProject); const target = dragoverZoneId.value; if (target) dropProject(target); else clearProjectDrag(); }
function clearProjectDrag() { draggingProjectId.value = ''; draggingProjectName.value = ''; dragoverZoneId.value = ''; }
function dropProject(zoneId) { const projectId = draggingProjectId.value; const project = graphProjects.value.find((item) => item.id === projectId); if (!projectId || zoneForProject(project || {}) === zoneId) return clearProjectDrag(); snapshotLayout(); layout.value.projectZones[projectId] = zoneId; showLayoutToast(`已将 ${project?.name || '项目'} 移至 ${layout.value.labels[zoneId]}`); clearProjectDrag(); }
function undoLayout() { const prior = layoutHistory.value.pop(); if (!prior) return; layout.value = JSON.parse(prior); showLayoutToast('已撤销上一步'); }
function restoreLayout() { snapshotLayout(); layout.value = defaultLayout(); showLayoutToast('已恢复默认布局'); }
function saveLayout() { window.localStorage.setItem(layoutStorageKey, JSON.stringify(layout.value)); savedLayout.value = JSON.stringify(layout.value); layoutHistory.value = []; showLayoutToast('已保存布局'); }
function showLayoutToast(message) { layoutToast.value = message; window.clearTimeout(toastTimer); toastTimer = window.setTimeout(() => { layoutToast.value = ''; }, 3200); }
function memberRecord(person) { return props.members.find((member) => String(member.id) === person.id) || {}; }
function avatarGender(person) { const member = memberRecord(person); const supplied = String(member.gender || member.sex || '').toLowerCase(); if (['female', 'f', '女'].includes(supplied)) return 'female'; if (['male', 'm', '男'].includes(supplied)) return 'male'; const firstName = String(person.name || '').split(',')[1]?.trim().split(/\s+/)[0].toLowerCase(); return femaleNames.has(firstName) ? 'female' : 'male'; }
function avatarIndex(person) { const pool = avatarPools[avatarGender(person)]; const hash = [...String(person.id)].reduce((sum, char) => sum + char.charCodeAt(0), 0); return pool[hash % pool.length]; }
function capacityFor(person) { return Number(props.members.find((member) => String(member.id) === person.id)?.capacity_hours_week || 40); }
function personHours(person) { return Math.round(capacityFor(person) * person.allocated / 100); }
function memberTeam(person) { return props.members.find((member) => String(member.id) === person.id)?.team || '未分组'; }
function projectLoad(project) { return project.people ? Math.round(project.assignments.reduce((sum, task) => sum + Number(task.allocation_percent || 0), 0) / project.people) : 0; }
function projectHours(project) { return Math.round(project.assignments.reduce((sum, task) => sum + Number(task.allocation_percent || 0) * 0.4, 0)); }
function projectTone(project) { return project.risk ? 'risk' : projectLoad(project) >= 80 ? 'busy' : 'normal'; }
function zoneForProject(project) { return layout.value.projectZones[project.id] || zoneDefinitions.find((zone) => zone.names.includes(String(project.name || '').toLowerCase()))?.id || 'operations'; }
function routePath(route) { if (route.axis === 'horizontal') { const mid = (route.x1 + route.x2) / 2; return `M ${route.x1} ${route.y1} H ${mid} V ${route.y2} H ${route.x2}`; } const mid = (route.y1 + route.y2) / 2; return `M ${route.x1} ${route.y1} V ${mid} H ${route.x2} V ${route.y2}`; }
function pointStyle([left, top]) { return { left: `${left}%`, top: `${top}%` }; }
function statusText(status) { return ({ active: '进行中', planned: '计划中', blocked: '阻塞', done: '完成' })[status] || status; }
function short(value, length) { const text = String(value || '未命名'); return text.length > length ? `${text.slice(0, length)}…` : text; }
function shortPeriod(task) { return `${task.start_date || '未定'} ~ ${task.end_date || '持续'}`; }
onBeforeUnmount(() => { window.removeEventListener('pointermove', moveZone); window.removeEventListener('pointermove', moveProject); window.clearTimeout(toastTimer); });
</script>

<style scoped>
.command-sandbox{color:#152238;min-width:0;padding-bottom:24px}.command-topbar{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:24px}.command-topbar h1{font-size:28px;margin:0 0 5px}.command-topbar p{margin:0;color:#66758a}.top-actions{display:flex;align-items:center;gap:10px}.top-actions button,.top-actions input,.search-box{height:42px;border:1px solid #d7dfe9;border-radius:8px;background:#fff;color:#29384d}.search-box{display:flex;align-items:center;gap:8px;padding:0 12px}.search-box input{width:210px;border:0;height:auto;outline:0}.top-actions>input{padding:0 12px}.top-actions button{display:flex;align-items:center;gap:7px;padding:0 14px;cursor:pointer}.top-actions .refresh{background:#23798a;color:#fff;border-color:#23798a}.top-actions button.active{background:#fff3ef;border-color:#e7a08d}.signal{width:7px;height:7px;border-radius:50%;background:#d93632;align-self:flex-start;margin:5px -7px 0 0}.section-heading{font-size:18px;border-left:3px solid #233b5b;padding-left:12px;margin:0 0 12px}.control-strip{display:grid;grid-template-columns:minmax(570px,1fr) 126px 148px 100px 100px;gap:12px;margin-bottom:14px}.metrics{display:grid;grid-template-columns:repeat(6,1fr);background:#fff;border:1px solid #d9e1ea;border-radius:8px}.metrics span{padding:12px 14px;border-right:1px solid #e6ebf1;white-space:nowrap}.metrics span:last-child{border:0}.metrics small,.select-control small,.view-control small{display:block;color:#66768b;font-size:11px}.metrics b{font-size:20px;margin-right:4px}.metrics em{font-style:normal;font-size:10px;color:#748196}.metrics .danger{color:#d93632}.metrics .warning{color:#dc7b28}.metrics .teal{color:#23818e}.select-control,.view-control,.plain-control{background:#fff;border:1px solid #d9e1ea;border-radius:8px;min-height:72px;padding:10px 14px}.select-control select{border:0;margin-top:8px;font-weight:700;color:#26364a;background:transparent}.view-control,.plain-control{display:flex;align-items:center;justify-content:center;gap:9px;cursor:pointer;color:#25364a}.view-control span{text-align:left}.view-control b{display:block;margin-top:6px}.plain-control.active{color:#187589;background:#edf8f9}.snapshot-note{display:flex;align-items:center;gap:6px;color:#86631b;background:#fff9e9;border:1px solid #f0dfb4;border-radius:7px;padding:8px 11px;margin-bottom:10px;font-size:12px}.workspace{display:grid;grid-template-columns:minmax(680px,1fr) 330px;gap:18px;align-items:stretch}.deployment-board{height:680px;position:relative;overflow:hidden;border:1px solid #bfc6c8;border-radius:24px;background:#f4f3ef var(--terrain) center/cover;box-shadow:0 14px 26px rgba(39,48,58,.16),inset 0 0 0 8px rgba(255,255,255,.42);transition:transform .25s;transform-origin:center top}.deployment-board.perspective{transform:perspective(1600px) rotateX(1.2deg)}.routes{position:absolute;inset:0;width:100%;height:100%;z-index:1}.routes line{stroke:#9ca9b9;stroke-width:.28;vector-effect:non-scaling-stroke}.routes .primary{stroke:#20aebe;stroke-width:.52}.routes .secondary{stroke:#63aaca;stroke-dasharray:1 1}.routes .blocked{stroke:#d16a4e;stroke-dasharray:.8 .7}.project-card,.person-node,.task-node{position:absolute;z-index:2;transform:translate(-50%,-50%);cursor:pointer}.project-card{width:178px;min-height:74px;text-align:left;background:rgba(255,255,255,.92);border:1px solid #cad8d2;border-radius:8px;padding:11px 14px;box-shadow:0 8px 15px rgba(40,55,68,.14)}.project-card .project-title{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:700}.project-card b{display:block;font-size:18px;color:#31806f;margin-top:6px}.project-card small{color:#69778a}.project-card i{display:block;height:4px;border-radius:3px;background:#65a996;margin-top:8px}.project-card.busy{border-color:#e8bf9b}.project-card.busy b{color:#db6e30}.project-card.busy i{background:#dd7740}.project-card.risk{border-color:#e0aaa1}.project-card.risk b{color:#c9473d}.project-card.risk i{background:#ce5149}.person-node{width:112px;min-height:132px;border:1px solid #cdd4dc;border-radius:46px 46px 24px 24px;background:rgba(255,255,255,.95);box-shadow:0 10px 20px rgba(47,61,76,.2);padding:12px 8px 10px;text-align:center}.person-node.selected{border:3px solid #20bcc7;box-shadow:0 0 0 8px rgba(43,199,205,.17),0 10px 20px rgba(47,61,76,.18)}.person-node img{width:54px;height:54px;border-radius:50%;object-fit:cover}.person-node strong,.person-node b,.person-node small{display:block}.person-node strong{font-size:12px;margin:4px 0}.person-node b{font-size:17px;color:#248078}.person-node.overloaded b,.person-node.blocked b{color:#d73e35}.person-node small{font-size:10px;color:#68778a}.task-node{width:62px;height:62px;border:1px solid #bfcbd4;border-radius:50%;background:#fff;box-shadow:0 5px 10px rgba(41,55,67,.14);padding:4px;text-align:center}.task-node b,.task-node small{display:block}.task-node b{font-size:13px;color:#278276}.task-node small{font-size:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.task-node.blocked{border-color:#e4a28e}.task-node.blocked b{color:#d34935}.map-key{position:absolute;z-index:4;left:14px;bottom:12px;display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.9);border-radius:7px;padding:8px 10px;font-size:10px;color:#5e6e81}.map-key span{display:flex;align-items:center;gap:4px}.map-key .line{width:22px;height:2px;background:#21aebe}.map-key .line.secondary{background:#8ba2b6;border-top:1px dashed #fff}.inspector{min-width:0;background:#fff;border:1px solid #d8e0e9;border-radius:9px;box-shadow:0 8px 25px rgba(35,51,69,.08);padding:18px;display:flex;flex-direction:column}.inspector>header{display:flex;justify-content:space-between;align-items:center}.inspector h2{margin:0;font-size:21px}.inspector header button{border:0;background:transparent;cursor:pointer;color:#5e6e80}.person-overview{display:grid;grid-template-columns:68px 1fr auto;gap:12px;align-items:center;margin:22px 0}.person-overview>img{width:68px;height:68px;border-radius:50%;object-fit:cover}.person-overview p{font-size:12px;color:#5f6f82;line-height:1.8}.person-overview p span{color:#7d8997}.person-overview>strong{font-size:27px;color:#248078}.person-overview>strong.overloaded,.person-overview>strong.blocked{color:#d53a32}.person-overview>strong small{font-size:11px;color:#637185;display:block}.load-ring{grid-column:3;width:58px;height:58px;border-radius:50%;background:conic-gradient(#258493 var(--load),#edf0f3 0);display:grid;place-items:center}.load-ring span{width:43px;height:43px;border-radius:50%;background:#fff}.tabs{display:flex;border-bottom:1px solid #dbe2e9}.tabs button{border:0;background:transparent;padding:10px 7px;color:#6b798b;cursor:pointer}.tabs button.active{color:#17273c;border-bottom:2px solid #1d3554;font-weight:700}.assignment-table{border:1px solid #e0e6ed;border-radius:7px;margin-top:14px;overflow:hidden}.table-head,.assignment-table>button{display:grid;grid-template-columns:1fr 48px 42px 72px;gap:5px;align-items:center}.table-head{background:#f4f6f8;color:#6d7988;font-size:10px;padding:8px}.assignment-table>button{width:100%;border:0;border-top:1px solid #e7ebef;background:#fff;text-align:left;padding:10px 8px;cursor:pointer}.assignment-table>button.selected{background:#edf8fa}.assignment-table button span b,.assignment-table button span small{display:block}.assignment-table button span b{font-size:11px}.assignment-table button span small,.assignment-table button>small{font-size:9px;color:#748196}.assignment-table button em{font-size:9px;color:#25806e;font-style:normal}.assignment-table button strong{font-size:11px}.profile-section{border-top:1px solid #e2e7ed;margin-top:18px;padding-top:14px}.profile-section h3{font-size:13px;margin:0 0 9px}.profile-section div{display:flex;gap:5px;flex-wrap:wrap}.profile-section div span{font-size:10px;background:#f0f2f5;border-radius:5px;padding:5px 7px}.profile-section p{font-size:11px;color:#69778a}.inspector footer{margin-top:auto;border-top:1px solid #e3e8ed;padding-top:14px;color:#7a8795;font-size:10px}@media(max-width:1250px){.control-strip{grid-template-columns:1fr 110px 110px}.metrics{grid-column:1/-1}.workspace{grid-template-columns:minmax(600px,1fr) 290px}.deployment-board{height:620px}}@media(max-width:900px){.command-topbar{display:block}.top-actions{margin-top:14px;flex-wrap:wrap}.control-strip{grid-template-columns:repeat(2,1fr)}.metrics{grid-template-columns:repeat(3,1fr)}.workspace{grid-template-columns:1fr}.inspector{min-height:460px}.deployment-board{min-width:680px}.workspace{overflow:auto}}
.top-actions button{white-space:nowrap}
.section-heading small{margin-left:8px;color:#758296;font-size:12px;font-weight:500}
.person-node .cartoon-avatar{width:54px;height:54px;margin:0 auto}
.person-overview>.cartoon-avatar{width:68px;height:68px}
.routes path{fill:none;stroke:#9ca9b9;stroke-width:.28;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}.routes path.primary{stroke:#20aebe;stroke-width:.52}.routes path.secondary{stroke:#78a5b6;stroke-dasharray:1 1}.routes path.blocked{stroke:#d16a4e;stroke-dasharray:.8 .7}
.deployment-zone{--zone-color:#2d8fc3;position:absolute;z-index:2;border:1px solid color-mix(in srgb,var(--zone-color) 44%,white);border-radius:14px;background:color-mix(in srgb,var(--zone-color) 8%,rgba(255,255,255,.82));padding:10px 12px}.deployment-zone>header{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}.deployment-zone h3{margin:0;color:color-mix(in srgb,var(--zone-color) 72%,#18304d);font-size:13px}.deployment-zone>header small{color:#758296;font-size:9px}.deployment-zone.core{left:2%;top:2%;width:46%;height:22%;--zone-color:#2699d1}.deployment-zone.platform{right:2%;top:2%;width:46%;height:22%;--zone-color:#2ca775}.deployment-zone.support{left:2%;top:32%;width:22%;height:36%;--zone-color:#7265d5}.deployment-zone.overseas{right:2%;top:32%;width:22%;height:36%;--zone-color:#269b7d}.deployment-zone.operations{left:17%;bottom:8%;width:66%;height:18%;--zone-color:#e07830}.zone-projects{display:grid;grid-template-columns:repeat(auto-fit,minmax(98px,1fr));gap:8px}.support .zone-projects,.overseas .zone-projects{grid-template-columns:1fr}.deployment-zone .project-card{position:relative;left:auto;top:auto;width:auto;min-height:0;transform:none;padding:8px 9px;border-color:color-mix(in srgb,var(--zone-color) 35%,#d8e0e8);border-radius:7px;box-shadow:0 4px 10px rgba(37,55,72,.09)}.deployment-zone .project-card.selected{outline:2px solid var(--zone-color);outline-offset:1px}.deployment-zone .project-card .project-title{font-size:10px;line-height:1.2}.deployment-zone .project-card b{font-size:15px;margin-top:4px}.deployment-zone .project-card small{font-size:9px}.deployment-zone .project-card i{height:3px;margin-top:5px}.operations-center{position:absolute;z-index:2;left:50%;top:50%;transform:translate(-50%,-50%);display:grid;place-items:center;width:130px;height:58px;border-radius:50%;background:rgba(255,255,255,.74);box-shadow:0 0 0 14px rgba(35,166,178,.06);text-align:center;color:#58758d}.operations-center strong,.operations-center small{display:block}.operations-center strong{font-size:13px}.operations-center small{font-size:10px;margin-top:3px}.deployment-board .person-node{z-index:3}.deployment-board .task-node{z-index:3}.deployment-board .map-key{left:14px;right:14px;bottom:7px;justify-content:center}.deployment-board.high-density .person-node{width:94px;min-height:112px;padding:8px 6px}.deployment-board.high-density .person-node .cartoon-avatar{width:44px;height:44px}.deployment-board.high-density .person-node strong{font-size:10px}.deployment-board.high-density .person-node b{font-size:15px}
.deployment-board .person-node{width:96px;min-height:112px;padding:8px 6px;border-radius:38px 38px 20px 20px}.deployment-board .person-node.selected{border-width:2px;box-shadow:0 0 0 6px rgba(43,199,205,.14),0 8px 16px rgba(47,61,76,.16)}.deployment-board .person-node .cartoon-avatar{width:44px;height:44px}.deployment-board .person-node strong{margin:3px 0;font-size:10px;line-height:1.15;letter-spacing:-.15px;white-space:nowrap}.deployment-board .person-node b{font-size:15px}.deployment-board .person-node small{font-size:9px}.deployment-board .task-node{width:54px;height:54px}.deployment-board .task-node b{font-size:12px}.deployment-board.high-density .person-node{width:82px;min-height:98px;padding:6px 4px;border-radius:32px 32px 17px 17px}.deployment-board.high-density .person-node .cartoon-avatar{width:36px;height:36px}.deployment-board.high-density .person-node strong{font-size:9px;letter-spacing:-.3px}.deployment-board.high-density .person-node b{font-size:13px}.deployment-board.high-density .person-node small{font-size:8px}.deployment-board.high-density .operations-center{width:108px;height:48px}.deployment-board.high-density .operations-center strong{font-size:11px}
.section-title-row{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:12px}.section-title-row .section-heading{margin:0}.layout-toolbar{display:flex;align-items:center;gap:7px}.layout-toolbar button{height:32px;display:flex;align-items:center;gap:5px;border:1px solid #d7e0e8;border-radius:7px;background:#fff;color:#40536a;padding:0 10px;cursor:pointer}.layout-toolbar button:disabled{opacity:.45;cursor:default}.layout-toolbar .save-layout{color:#fff;background:#23798a;border-color:#23798a}.dirty-state{font-size:11px;color:#b55b26;background:#fff2e8;border-radius:999px;padding:5px 9px}.deployment-board.is-arranging{background-color:#eef8f9}.deployment-zone{transition:left .16s ease,top .16s ease,box-shadow .16s ease}.deployment-zone.is-dragging{z-index:5;transition:none;box-shadow:0 15px 30px rgba(29,74,95,.2)}.deployment-zone.drop-target{z-index:4;border:2px dashed var(--zone-color);background:color-mix(in srgb,var(--zone-color) 15%,white);box-shadow:0 0 0 5px color-mix(in srgb,var(--zone-color) 10%,transparent)}.deployment-zone>header{justify-content:flex-start}.deployment-zone>header>small{margin-left:auto}.zone-drag-handle,.zone-edit-button,.zone-name-editor button{display:grid;place-items:center;width:24px;height:24px;padding:0;border:0;border-radius:5px;background:transparent;color:var(--zone-color);cursor:pointer}.zone-drag-handle{margin-left:-7px;cursor:grab;touch-action:none}.zone-drag-handle:active{cursor:grabbing}.zone-edit-button{opacity:.55}.deployment-zone:hover .zone-edit-button,.zone-edit-button:focus-visible{opacity:1;background:color-mix(in srgb,var(--zone-color) 10%,white)}.zone-name-editor{display:flex;align-items:center;gap:3px;min-width:0}.zone-name-editor input{width:150px;height:26px;border:1px solid var(--zone-color);border-radius:5px;background:#fff;padding:0 7px;color:#17324a;font-weight:700;outline:0}.zone-name-editor button{background:#fff}.project-drag-handle{width:18px;height:18px;display:grid;place-items:center;color:#8090a2;cursor:grab;flex:0 0 auto;touch-action:none}.deployment-zone .project-card.dragging{opacity:.38}.project-drag-ghost{position:absolute;z-index:9;transform:translate(-50%,-50%);display:flex;align-items:center;gap:6px;max-width:170px;border:1px solid #e6a273;border-radius:7px;background:#fff;color:#29384d;padding:8px 10px;box-shadow:0 12px 24px rgba(33,54,70,.22);font-size:10px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;pointer-events:none}.drop-message{position:absolute;inset:38px 10px 10px;display:grid;place-items:center;border:2px dashed var(--zone-color);border-radius:8px;background:rgba(255,255,255,.86);color:color-mix(in srgb,var(--zone-color) 75%,#18304d);font-weight:700;font-size:13px;pointer-events:none}.layout-toast{position:absolute;z-index:8;left:50%;bottom:48px;transform:translateX(-50%);display:flex;align-items:center;gap:12px;border-radius:8px;background:#183348;color:#fff;padding:9px 13px;box-shadow:0 8px 20px rgba(26,43,58,.24);font-size:11px}.layout-toast button{border:0;background:transparent;color:#72dbe1;font-weight:700;cursor:pointer;padding:0}.deployment-zone.core,.deployment-zone.platform,.deployment-zone.support,.deployment-zone.overseas,.deployment-zone.operations{right:auto;bottom:auto}
.deployment-zone .project-card{padding:0;overflow:hidden}.project-card-content{display:block;width:100%;border:0;background:transparent;color:inherit;text-align:left;padding:8px 9px 8px 27px;cursor:pointer}.project-drag-handle{position:absolute;z-index:2;left:5px;top:7px;width:18px;height:18px;display:grid;place-items:center;padding:0;border:0;border-radius:4px;background:transparent;color:#8090a2;cursor:grab;touch-action:none}.project-drag-handle:hover,.project-drag-handle:focus-visible{color:var(--zone-color);background:color-mix(in srgb,var(--zone-color) 10%,white)}
@media(max-width:900px){.section-title-row{align-items:flex-start;flex-direction:column}.layout-toolbar{flex-wrap:wrap}.dirty-state{order:4}.zone-name-editor input{width:120px}}
</style>
