<template>
  <section class="resource-lab">
    <div class="lab-toolbar">
      <div class="lab-mode"><span class="live-dot" />{{ demo ? c.demo : c.live }}<span class="lab-beta">LAB</span></div>
      <div class="lab-filters">
        <select v-model="projectFilter" :aria-label="c.project"><option value="">{{ c.all }}</option><option v-for="p in graph.islands" :key="p.id" :value="String(p.id)">{{ p.name }}</option></select>
        <label class="lab-search"><Search :size="16" /><input v-model="query" :placeholder="c.search" :aria-label="c.search" type="search" /></label>
        <button class="lab-button" :class="{ pressed: riskOnly }" :aria-pressed="riskOnly" @click="riskOnly = !riskOnly"><TriangleAlert :size="16" />{{ c.risks }}</button>
        <button class="lab-button" :title="c.reset" @click="reset"><RotateCcw :size="16" />{{ c.reset }}</button>
      </div>
    </div>

    <div v-if="demo" class="lab-notice"><Info :size="15" />{{ c.demoNotice }}<button v-if="hasRealData" @click="demo = false">{{ c.backToLive }}</button></div>
    <div v-else-if="outsideAll" class="lab-notice"><CalendarDays :size="15" /><span>{{ c.outsideNotice }}</span><button v-if="latestDate" @click="emit('change-date', latestDate)">{{ c.goTo }} {{ latestDate }}</button></div>

    <div class="lab-workspace">
      <div class="lab-main">
        <div class="lab-metrics">
          <div><FolderKanban :size="18" /><span>{{ c.projects }}<strong>{{ islands.length }}<small>{{ c.projectUnit }}</small></strong></span></div>
          <div><Users :size="18" /><span>{{ c.people }}<strong>{{ visiblePeople.length }}<small>{{ c.personUnit }}</small></strong></span></div>
          <div><Gauge :size="18" /><span>{{ c.average }}<strong>{{ averageLoad }}<small>%</small></strong></span></div>
          <div><Network :size="18" /><span>{{ c.shared }}<strong>{{ sharedCount }}<small>{{ c.personUnit }}</small></strong></span></div>
          <div class="metric-risk"><TriangleAlert :size="18" /><span>{{ c.risks }}<strong>{{ riskCount }}<small>{{ c.personUnit }}</small></strong></span></div>
        </div>
        <div class="lab-viewbar">
          <div class="lab-segment"><button :class="{ selected: !listView }" :aria-pressed="!listView" @click="listView = false"><Box :size="15" />{{ c.islands }}</button><button :class="{ selected: listView }" :aria-pressed="listView" @click="listView = true"><List :size="15" />{{ c.list }}</button></div>
          <div class="lab-view-options"><label><input v-model="showLinks" type="checkbox" />{{ c.connections }}</label><label>{{ c.density }}<select v-model.number="spacing" :aria-label="c.density"><option :value=".9">{{ c.compact }}</option><option :value="1.15">{{ c.comfort }}</option><option :value="1.4">{{ c.spacious }}</option></select></label></div>
        </div>
        <div class="lab-stage">
          <ResourceIslandScene v-if="!listView" ref="sceneRef" :islands="islands" :selected-project="selectedProjectId" :selected-member="selectedMemberId" :english="english" :spacing="spacing" :show-links="showLinks" :avatar-for="avatarFor" @select-project="selectProject" @select-member="selectMember" @unavailable="listView = true" />
          <div v-else class="lab-project-list">
            <p v-if="!islands.length" class="lab-empty">{{ c.noResults }}</p>
            <button v-for="p in islands" :key="p.id" :class="{ selected: p.id === selectedProjectId }" @click="selectProject(p.id)"><span class="project-list-icon"><FolderKanban :size="22" /></span><span><strong>{{ p.name }}</strong><small>{{ p.people.length }} {{ c.personUnit }} · {{ p.work.length }} {{ c.workUnit }}</small></span><b>{{ Math.round(p.average) }}%</b><ChevronRight :size="17" /></button>
          </div>
        </div>
        <div class="lab-legend"><span><Network :size="14" />{{ c.linkLegend }}</span><span class="legend-risk"><TriangleAlert :size="14" />{{ c.riskLegend }}</span><span>{{ c.labelHint }}</span></div>
      </div>

      <aside class="lab-inspector" :aria-label="c.inspector">
        <template v-if="selectedProject">
          <div class="inspector-project"><span>{{ c.selectedProject }}</span><button @click="selectedMemberId = null; selectedTaskId = null"><FolderKanban :size="17" /><strong>{{ selectedProject.name }}</strong><ChevronDown :size="15" /></button></div>
          <template v-if="selectedPerson">
            <div class="person-heading"><img v-if="avatarFor(selectedPerson)" :src="avatarFor(selectedPerson)" alt="" /><span v-else class="person-initial">{{ initials(selectedPerson.name) }}</span><div><h2>{{ selectedPerson.name }}</h2><p>{{ selectedPerson.role || c.noRole }}</p><span class="lab-badge" :class="selectedPerson.risk">{{ riskLabel(selectedPerson.risk) }}</span></div></div>
            <div class="person-load"><strong :class="{ danger: selectedPerson.allocated >= 110 }">{{ Math.round(selectedPerson.allocated) }}<small>%</small></strong><span>{{ c.currentLoad }}<br />{{ round(selectedPerson.hours) }} / {{ selectedPerson.capacity_hours_week || 0 }} {{ c.hours }}</span></div>
            <div class="load-track"><span :style="{ width: Math.min(100, selectedPerson.allocated) + '%' }" :class="{ danger: selectedPerson.allocated >= 110 }" /></div>
            <div class="inspector-section"><div class="inspector-section-title"><h3>{{ c.workDetails }}</h3><span>{{ selectedPerson.work.length }}</span></div><p class="detail-context">{{ c.allPersonWork }} · {{ currentDate }}</p>
              <button v-for="a in selectedPerson.work" :key="a.id" class="work-row" :class="{ selected: selectedTaskId === a.id, inactive: !isCurrent(a) }" @click="selectTask(a)">
                <span class="work-title"><strong>{{ a.task_name }}</strong><span class="lab-badge" :class="a.status">{{ statusLabel(a.status) }}</span></span>
                <span class="work-project">{{ projectName(a.project_id) }}</span>
                <span class="work-allocation"><span>{{ c.allocation }}</span><b>{{ a.allocation_percent }}%</b></span>
                <span class="work-period">{{ a.start_date || '—' }} — {{ a.end_date || c.ongoing }}</span>
                <span v-if="!isCurrent(a)" class="work-outside"><CalendarDays :size="12" />{{ c.outside }}</span>
                <span v-if="a.status === 'blocked' && isCurrent(a)" class="work-outside"><TriangleAlert :size="12" />{{ c.blockedHint }}</span>
              </button>
              <p v-if="!selectedPerson.work.length" class="detail-context">{{ c.noWork }}</p>
            </div>
          </template>
          <template v-else>
            <div class="project-overview"><span>{{ c.projectAverage }}</span><strong>{{ Math.round(selectedProject.average) }}<small>%</small></strong><p>{{ selectedProject.work.length }} {{ c.workUnit }} · {{ selectedProject.people.length }} {{ c.personUnit }}</p></div>
            <div v-if="selectedProject.blocked.length" class="project-risk"><TriangleAlert :size="16" />{{ selectedProject.blocked.length }} {{ c.blockedWork }}</div>
          </template>
          <div class="inspector-section member-roster"><div class="inspector-section-title"><h3>{{ c.projectPeople }}</h3><span>{{ selectedProject.people.length }}</span></div><p class="detail-context">{{ c.sorted }}</p><button v-for="p in selectedProject.people" :key="p.id" :class="{ selected: p.id === selectedMemberId }" @click="selectMember(selectedProject.id, p.id)"><img v-if="avatarFor(p)" :src="avatarFor(p)" alt="" /><span v-else class="roster-initial">{{ initials(p.name) }}</span><span><strong>{{ p.name }}</strong><small>{{ p.role || c.noRole }}</small></span><b :class="{ danger: p.allocated >= 110 }">{{ Math.round(p.allocated) }}%</b></button><p v-if="!selectedProject.people.length" class="detail-context">{{ c.noPeople }}</p></div>
        </template>
        <div v-else class="lab-empty"><FolderKanban :size="28" /><p>{{ c.noResults }}</p><button class="lab-button" @click="reset">{{ c.reset }}</button></div>
      </aside>
    </div>
    <footer class="lab-footer"><span>{{ c.baseline }} {{ currentDate }} · {{ c.loadDefinition }}</span><button @click="demo = !demo; reset()" :disabled="!hasRealData && demo"><FlaskConical :size="14" />{{ demo ? c.backToLive : c.tryDemo }}</button></footer>
    <details class="unassigned" v-if="unassigned.length"><summary>{{ c.unassigned }} · {{ unassigned.length }}</summary><div><span v-for="p in unassigned" :key="p.id">{{ p.name }} · {{ p.role || c.noRole }}</span></div></details>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import ResourceIslandScene from './ResourceIslandScene.vue';
import { buildResourceGraph, demoResources, isCurrentAssignment } from '../lib/resourceSandbox.js';
import Search from '@lucide/vue/dist/esm/icons/search.mjs';
import TriangleAlert from '@lucide/vue/dist/esm/icons/triangle-alert.mjs';
import RotateCcw from '@lucide/vue/dist/esm/icons/rotate-ccw.mjs';
import Info from '@lucide/vue/dist/esm/icons/info.mjs';
import CalendarDays from '@lucide/vue/dist/esm/icons/calendar-days.mjs';
import FolderKanban from '@lucide/vue/dist/esm/icons/folder-kanban.mjs';
import Users from '@lucide/vue/dist/esm/icons/users.mjs';
import Gauge from '@lucide/vue/dist/esm/icons/gauge.mjs';
import Network from '@lucide/vue/dist/esm/icons/network.mjs';
import Box from '@lucide/vue/dist/esm/icons/box.mjs';
import List from '@lucide/vue/dist/esm/icons/list.mjs';
import ChevronRight from '@lucide/vue/dist/esm/icons/chevron-right.mjs';
import ChevronDown from '@lucide/vue/dist/esm/icons/chevron-down.mjs';
import FlaskConical from '@lucide/vue/dist/esm/icons/flask-conical.mjs';
import chen from '../assets/avatars/chen-an.png';
import li from '../assets/avatars/li-min.png';
import wang from '../assets/avatars/wang-yue.png';
import zhao from '../assets/avatars/zhao-ning.png';

const props = defineProps({ language: { type: String, default: 'zh' }, currentDate: String, members: { type: Array, default: () => [] }, projects: { type: Array, default: () => [] }, assignments: { type: Array, default: () => [] }, memberLoad: { type: Array, default: () => [] } });
const emit = defineEmits(['change-date']);
const english = computed(() => props.language === 'en');
const copy = {
  zh: { live:'实时数据', demo:'示例数据', project:'项目范围', all:'全部项目', search:'搜索项目、同事或任务', risks:'风险人员', reset:'重置', demoNotice:'正在体验示例资源岛；示例不会写入或修改实际安排。', backToLive:'返回真实数据', outsideNotice:'当前日期没有生效的安排。仍可查看历史关系，当前负荷为 0%。', goTo:'查看最近安排', projects:'项目', projectUnit:'个', people:'团队成员', personUnit:'人', average:'成员平均占用', shared:'跨项目成员', islands:'空间资源岛', list:'项目清单', connections:'协作连线', density:'间距', compact:'紧凑', comfort:'适中', spacious:'宽松', workUnit:'条安排', noResults:'没有匹配的项目，请调整搜索或筛选。', linkLegend:'连线 = 共享成员', riskLegend:'橙色 = 共享成员有风险', labelHint:'放大或聚焦查看成员', inspector:'资源详情', selectedProject:'当前项目', noRole:'未填写角色', currentLoad:'当前总占用', hours:'小时 / 周', workDetails:'工作明细', allPersonWork:'该成员的全部项目安排', allocation:'分配比例', ongoing:'持续', outside:'不在当前基准日期内', blockedHint:'任务阻塞，请关注依赖与处理人。', noWork:'暂无工作安排', projectAverage:'参与成员当前平均占用', blockedWork:'条任务已阻塞', projectPeople:'项目成员', sorted:'按当前总占用排序 · 点击查看全部工作', noPeople:'该项目还没有安排成员', baseline:'基准日期', loadDefinition:'成员占用包含其全部项目', tryDemo:'体验示例', unassigned:'尚无项目安排的同事' },
  en: { live:'Live data', demo:'Sample data', project:'Project scope', all:'All projects', search:'Search projects, people or work', risks:'At risk', reset:'Reset', demoNotice:'Exploring sample islands. No changes are made to your real assignments.', backToLive:'Back to live data', outsideNotice:'No assignments apply on this date. Historical relationships remain visible; current load is 0%.', goTo:'Latest work', projects:'Projects', projectUnit:'', people:'People', personUnit:'', average:'Mean member load', shared:'Cross-project', islands:'Resource islands', list:'Project list', connections:'Connections', density:'Spacing', compact:'Compact', comfort:'Comfort', spacious:'Spacious', workUnit:'assignments', noResults:'No projects match. Adjust your search or filters.', linkLegend:'Connection = shared people', riskLegend:'Orange = shared people at risk', labelHint:'Zoom or focus to see people', inspector:'Resource details', selectedProject:'SELECTED PROJECT', noRole:'No role specified', currentLoad:'Current total load', hours:'hours / week', workDetails:'Work details', allPersonWork:'All projects for this person', allocation:'Allocation', ongoing:'Ongoing', outside:'Outside the current baseline date', blockedHint:'Blocked work: review dependencies and ownership.', noWork:'No assignments', projectAverage:'Current mean load of participants', blockedWork:'blocked assignments', projectPeople:'Project members', sorted:'By current total load · select to inspect all work', noPeople:'No people assigned yet', baseline:'Baseline', loadDefinition:'Member load includes all their projects', tryDemo:'Try sample', unassigned:'People without project assignments' }
};
const c = computed(() => copy[english.value ? 'en' : 'zh']);
const hasRealData = computed(() => !!(props.members.length || props.projects.length || props.assignments.length));
const demo = ref(!hasRealData.value), query = ref(''), projectFilter = ref(''), riskOnly = ref(false), listView = ref(false), spacing = ref(1.15), showLinks = ref(true);
const selectedProjectId = ref(null), selectedMemberId = ref(null), selectedTaskId = ref(null), sceneRef = ref(null);
const source = computed(() => demo.value ? demoResources(props.currentDate) : props);
const graph = computed(() => buildResourceGraph({ ...source.value, date: props.currentDate }));
const islands = computed(() => {
  const needle = query.value.trim().toLowerCase();
  return graph.value.islands.filter(p => (!projectFilter.value || String(p.id) === projectFilter.value) && (!riskOnly.value || p.risky) && (!needle || `${p.name} ${p.people.map(p => `${p.name} ${p.role}`).join(' ')} ${p.work.map(a => a.task_name).join(' ')}`.toLowerCase().includes(needle)));
});
const selectedProject = computed(() => islands.value.find(p => p.id === selectedProjectId.value));
const selectedPerson = computed(() => graph.value.people.find(p => p.id === selectedMemberId.value));
const visiblePeople = computed(() => [...new Map(islands.value.flatMap(p => p.people).map(p => [p.id, p])).values()]);
const averageLoad = computed(() => visiblePeople.value.length ? Math.round(visiblePeople.value.reduce((s, p) => s + p.allocated, 0) / visiblePeople.value.length) : 0);
const sharedCount = computed(() => visiblePeople.value.filter(p => islands.value.filter(i => i.people.some(person => person.id === p.id)).length > 1).length);
const riskCount = computed(() => visiblePeople.value.filter(p => ['blocked', 'overloaded', 'tight'].includes(p.risk)).length);
const outsideAll = computed(() => source.value.assignments.length > 0 && !source.value.assignments.some(isCurrent));
const latestDate = computed(() => source.value.assignments.flatMap(a => [a.end_date || a.start_date]).filter(Boolean).sort().at(-1));
const unassigned = computed(() => graph.value.people.filter(p => !p.work.length));
const round = n => Math.round(n * 10) / 10;
const isCurrent = a => isCurrentAssignment(a, props.currentDate);
const avatarFor = p => demo.value ? [chen, li, wang, zhao][p.id - 1] : null;
const initials = name => name.includes(',') ? name.split(',')[0].slice(0, 2).toUpperCase() : name.slice(0, 2);
const projectName = id => graph.value.islands.find(p => p.id === id)?.name || '—';
function riskLabel(risk) { return (english.value ? { normal:'Normal', overloaded:'Overloaded', tight:'Tight', blocked:'Blocked', underused:'Available' } : { normal:'正常', overloaded:'超负荷', tight:'紧张', blocked:'阻塞', underused:'有余量' })[risk] || risk; }
function statusLabel(status) { return (english.value ? { active:'Active', planned:'Planned', blocked:'Blocked', paused:'Paused', done:'Done', archived:'Archived' } : { active:'进行中', planned:'计划', blocked:'阻塞', paused:'暂停', done:'完成', archived:'归档' })[status] || status; }
function selectProject(id) { selectedProjectId.value = id; selectedMemberId.value = null; selectedTaskId.value = null; }
function selectMember(projectId, memberId) { selectedProjectId.value = projectId; selectedMemberId.value = memberId; selectedTaskId.value = null; }
async function selectTask(a) { projectFilter.value = ''; query.value = ''; riskOnly.value = false; selectedProjectId.value = a.project_id; selectedTaskId.value = a.id; await nextTick(); sceneRef.value?.focus(a.project_id); }
function reset() { query.value = ''; projectFilter.value = ''; riskOnly.value = false; spacing.value = 1.15; showLinks.value = true; selectedMemberId.value = null; selectedTaskId.value = null; selectedProjectId.value = graph.value.islands[0]?.id ?? null; sceneRef.value?.reset(); }
watch(hasRealData, (has, before) => { if (has && !before) demo.value = false; });
watch(demo, reset);
watch(islands, ps => {
  if (!ps.some(p => p.id === selectedProjectId.value)) { selectedProjectId.value = ps[0]?.id ?? null; selectedMemberId.value = null; selectedTaskId.value = null; }
  if (selectedMemberId.value != null && !ps.find(p => p.id === selectedProjectId.value)?.people.some(p => p.id === selectedMemberId.value)) selectedMemberId.value = null;
}, { immediate: true });
</script>

<style scoped>
.resource-lab{--lab-teal:#287b8b;--lab-muted:#7a8899;font-size:14px}.lab-toolbar,.lab-filters,.lab-mode,.lab-viewbar,.lab-view-options,.lab-legend,.lab-footer{display:flex;align-items:center;gap:12px}.lab-toolbar{justify-content:space-between;margin-bottom:18px}.lab-mode{font-size:12px;color:#5d7182;white-space:nowrap}.live-dot{width:6px;height:6px;border-radius:50%;background:#388b79}.lab-beta{font-size:9px;letter-spacing:1.5px;border:1px solid #d9e2e8;border-radius:4px;padding:3px 5px;color:#7e8c99}.lab-filters{justify-content:flex-end;flex:1}.lab-filters>select{max-width:190px}.lab-search{position:relative;min-width:180px;width:min(300px,30vw);margin:0}.lab-search>svg{position:absolute;left:11px;top:12px;color:#81909e}.lab-search input{padding-left:35px;font-size:13px}.lab-filters>select{font-size:13px}.lab-button{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:40px;background:#fff;border:1px solid #dce4ec;color:#5b6c7c;border-radius:6px;padding:8px 12px;white-space:nowrap;font-size:12px}.lab-button:hover,.lab-button.pressed{background:#eaf3f5;color:#236e7f;border-color:#a4ccd3}.lab-notice{display:flex;align-items:center;gap:8px;margin-bottom:14px;padding:10px 13px;color:#876d3c;background:#fff9ed;border:1px solid #eee1c8;border-radius:6px;font-size:12px;line-height:1.5}.lab-notice>svg{flex-shrink:0}.lab-notice button{margin-left:auto;white-space:nowrap;border:0;background:transparent;color:#256d7c;text-decoration:underline;font-size:12px}.lab-workspace{display:grid;grid-template-columns:minmax(0,1fr) 294px;gap:20px;align-items:start}.lab-main{min-width:0}.lab-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));background:white;border:1px solid #e0e7ee;border-radius:8px;padding:19px 8px;min-height:88px}.lab-metrics>div{display:flex;align-items:center;gap:9px;border-right:1px solid #edf0f4;padding:0 12px;min-width:0}.lab-metrics>div:last-child{border:0}.lab-metrics svg{color:#548ba1;flex-shrink:0}.lab-metrics>div>span{display:block;font-size:10px;color:#728192;white-space:nowrap}.lab-metrics strong{display:block;color:#233044;font-size:23px;font-weight:650;margin-top:4px;line-height:1.1}.lab-metrics strong small{font-size:11px;font-weight:400;margin-left:4px;color:#8995a0}.lab-metrics .metric-risk svg{color:#c68a55}.lab-viewbar{justify-content:space-between;margin:16px 0 0;min-height:40px;gap:8px}.lab-segment{display:flex;gap:3px}.lab-segment button{display:flex;align-items:center;gap:6px;border:0;background:transparent;color:#7a8998;padding:8px 9px;font-size:12px;border-radius:5px;white-space:nowrap}.lab-segment button.selected{background:#e6f0f2;color:#236d80;font-weight:600}.lab-view-options{gap:13px}.lab-view-options label{display:flex;align-items:center;gap:5px;font-size:11px;color:#7c8a98;white-space:nowrap}.lab-view-options input{width:13px;min-height:13px;accent-color:#287b8b}.lab-view-options select{width:66px;min-height:28px;padding:3px;font-size:11px;background:transparent;border-color:#dde5eb}.lab-stage{height:clamp(560px,calc(100vh - 450px),720px);margin-top:4px}.lab-project-list{height:100%;overflow:auto;padding:10px 0}.lab-project-list>button{display:flex;align-items:center;text-align:left;gap:13px;width:100%;padding:20px 17px;background:white;border:1px solid #e5eaef;border-radius:8px;margin-bottom:9px;color:#344756}.lab-project-list>button.selected{border-color:#5d9fae;background:#f0f7f8}.project-list-icon{padding:10px;background:#e8f1f3;border-radius:7px;color:#4e8896}.lab-project-list>button>span:nth-child(2){flex:1;min-width:0}.lab-project-list strong,.lab-project-list small{display:block}.lab-project-list small{margin-top:7px;color:#7a8b99;font-size:12px}.lab-project-list b{color:#3b7f8d}.lab-legend{justify-content:flex-start;font-size:10px;color:#81909d;gap:15px;padding:14px 0}.lab-legend span{display:flex;align-items:center;gap:5px}.lab-legend svg{color:#60a4b1}.lab-legend .legend-risk svg{color:#d39b76}.lab-legend>span:last-child{margin-left:auto}
.lab-inspector{background:white;border:1px solid #dfe6ed;border-radius:9px;max-height:calc(100vh - 180px);min-height:650px;overflow:auto;scrollbar-width:thin}.inspector-project{padding:19px 20px 16px;border-bottom:1px solid #eef1f5}.inspector-project>span{font-size:10px;color:#8c98a6;letter-spacing:.7px}.inspector-project>button{display:flex;gap:8px;align-items:center;border:0;background:transparent;padding:8px 0 0;color:#326778;text-align:left;width:100%}.inspector-project strong{flex:1;font-size:13px;overflow-wrap:anywhere}.person-heading{padding:24px 20px 8px;display:flex;align-items:center;gap:13px}.person-heading img,.person-initial{height:50px;width:50px;border-radius:50%;object-fit:cover;flex-shrink:0}.person-initial{display:grid;place-items:center;background:#e6f0f2;color:#32778a;font-size:17px;font-weight:650}.person-heading h2{font-size:17px;line-height:1.35;margin:0;overflow-wrap:anywhere}.person-heading p{font-size:11px;color:#83909e;margin:6px 0 8px}.lab-badge{display:inline-block;background:#eaf4ef;color:#408a70;font-size:10px;border-radius:3px;padding:3px 5px;white-space:nowrap;line-height:1.3}.lab-badge.blocked,.lab-badge.overloaded{color:#ba563f;background:#fff0ea}.lab-badge.tight{color:#ad8443;background:#fbf4e6}.lab-badge.planned{color:#5b7fa3;background:#edf3f9}.lab-badge.paused,.lab-badge.done,.lab-badge.archived{color:#87919d;background:#f0f2f5}.person-load{display:flex;gap:15px;align-items:center;padding:10px 20px}.person-load>strong{font-size:36px;color:#2c7c8d;letter-spacing:-1px;font-weight:600}.person-load small{font-size:19px;margin-left:2px}.person-load>span{font-size:10px;color:#8b97a5;line-height:1.8}.danger{color:#c05d44!important}.load-track{margin:0 20px 21px;height:5px;background:#eef2f5;border-radius:6px;overflow:hidden}.load-track>span{display:block;height:100%;background:#6ca8ae;border-radius:inherit}.load-track>span.danger{background:#d67b62}.inspector-section{padding:18px 20px;border-top:1px solid #eef1f5}.inspector-section-title{display:flex;justify-content:space-between;align-items:center;gap:10px}.inspector-section-title h3{margin:0;font-size:13px;font-weight:650}.inspector-section-title>span{font-size:11px;color:#8e9aa6}.detail-context{font-size:10px;color:#8c98a4;line-height:1.6;margin:7px 0 8px}.work-row{display:block;width:100%;border:0;border-bottom:1px solid #edf0f4;border-left:2px solid transparent;background:transparent;text-align:left;padding:14px 0 14px 10px;color:#324454}.work-row.selected{border-left-color:#39889b;background:#f3f8f9}.work-row:hover{background:#f7fafb}.work-title{display:flex;align-items:flex-start;gap:8px;justify-content:space-between}.work-title>strong{font-size:12px;line-height:1.7;overflow-wrap:anywhere}.work-project{font-size:10px;color:#8b99a4;margin-top:7px;display:block}.work-allocation{display:flex;gap:12px;align-items:center;margin-top:12px;font-size:11px;color:#84919f}.work-allocation b{color:#4d7484}.work-period{font-size:10px;color:#82909e;display:block;margin-top:8px;line-height:1.6}.work-outside{display:flex;gap:4px;align-items:center;color:#b08751;font-size:10px;margin-top:7px;line-height:1.5}.work-row.inactive .work-title>strong{color:#6c7b88}.project-overview{padding:25px 20px}.project-overview>span{font-size:11px;color:#83909e}.project-overview>strong{display:block;font-size:38px;color:#2a788b;margin-top:12px;font-weight:600}.project-overview small{font-size:19px}.project-overview p{font-size:11px;color:#83909e}.project-risk{margin:0 20px 18px;display:flex;align-items:center;gap:7px;font-size:12px;color:#bb7653}.member-roster>button{width:100%;display:flex;align-items:center;gap:9px;border:0;background:transparent;border-radius:5px;padding:11px 0;color:#3a4a5a;text-align:left}.member-roster>button:hover,.member-roster>button.selected{background:#f0f6f7}.member-roster img,.roster-initial{width:30px;height:30px;border-radius:50%;object-fit:cover;flex-shrink:0}.roster-initial{display:grid;place-items:center;background:#edf3f5;color:#698392;font-size:10px}.member-roster>button>span:nth-child(2){flex:1;min-width:0}.member-roster strong{display:block;font-size:11px;overflow-wrap:anywhere}.member-roster small{display:block;font-size:10px;color:#8a97a3;margin-top:4px}.member-roster b{font-size:12px;color:#498592}.lab-empty{padding:40px 20px;color:#84929e;text-align:center;line-height:1.8;font-size:13px}.lab-footer{justify-content:space-between;border-top:1px solid #e4eaf0;padding:13px 0 3px;color:#8b98a5;font-size:10px}.lab-footer>button{display:flex;align-items:center;gap:5px;background:transparent;border:0;color:#6c8492;font-size:11px;padding:5px}.unassigned{color:#7a8d9a;font-size:11px;margin-top:10px}.unassigned>div{display:flex;flex-wrap:wrap;gap:15px;padding:15px 0}.resource-lab button:focus-visible{outline:3px solid #4c9bad88;outline-offset:2px}
@media(min-width:1550px){.lab-workspace{grid-template-columns:minmax(0,1fr) 320px}.lab-inspector{min-height:700px}.lab-metrics>div>span{font-size:12px}}
@media(max-width:1150px){.lab-toolbar{align-items:flex-start;flex-direction:column;gap:10px}.lab-filters{width:100%;flex-wrap:wrap;justify-content:flex-start}.lab-search{flex:1;width:auto}.lab-workspace{grid-template-columns:minmax(0,1fr) 260px;gap:12px}.lab-metrics>div{padding:0 6px;gap:5px}.lab-metrics svg{display:none}.lab-metrics strong{font-size:20px}.lab-view-options{gap:5px}.lab-view-options label{font-size:10px}.lab-legend{flex-wrap:wrap;gap:8px}.lab-legend>span:last-child{margin-left:0}}
@media(max-width:900px){.lab-workspace{grid-template-columns:1fr}.lab-inspector{max-height:none;min-height:0}.lab-stage{height:560px}.lab-metrics svg{display:block}.lab-filters>select{max-width:160px}.lab-footer{flex-wrap:wrap}.lab-notice{flex-wrap:wrap}.lab-notice button{margin-left:0}.member-roster{max-height:350px;overflow:auto}}
@media(max-width:520px){.lab-viewbar{align-items:flex-start;flex-direction:column}.lab-view-options{align-self:flex-end}.lab-stage{height:450px}.lab-metrics{padding:13px 3px}.lab-metrics>div{padding:0 4px}.lab-metrics svg{display:none}.lab-metrics>div>span{font-size:9px}.lab-metrics strong{font-size:19px}.lab-filters{gap:6px}.lab-filters>select{max-width:130px}.lab-search{min-width:150px}.lab-mode{font-size:11px}.lab-notice{font-size:11px}}
</style>
