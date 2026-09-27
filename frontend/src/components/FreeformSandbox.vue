<template>
  <div class="fs-app" @wheel.prevent="onWheel" @keydown.esc="hidePersonSummary">
    <div ref="canvas" class="fs-canvas" @pointerdown.capture="hidePersonSummary" @pointerdown="canvasDown" @dblclick="canvasDoubleClick">
      <div class="fs-world" :style="worldStyle">
        <svg class="fs-wires" width="6000" height="6000" aria-label="人员关系">
          <defs><marker id="fs-arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0 L9 4.5 L0 9" fill="#65758f" /></marker></defs>
          <g v-for="edge in visibleEdges" :key="edge.id" class="fs-edge" :class="{ chosen: selectedIds.includes(edge.id) }" @pointerdown.stop="selectOnly(edge.id)">
            <path :d="edgePath(edge)" class="fs-edge-hit" />
            <path :d="edgePath(edge)" class="fs-edge-line" :stroke-dasharray="edge.dashed ? '7 5' : ''" :marker-end="edge.direction === 'forward' ? 'url(#fs-arrow)' : null" />
            <text v-if="edge.label" :x="edgeMid(edge).x" :y="edgeMid(edge).y - 9" text-anchor="middle">{{ edge.label }}</text>
          </g>
        </svg>
        <div v-for="frame in frames" :key="frame.id" class="fs-frame" :class="{ chosen: selectedIds.includes(frame.id), collapsed: frame.collapsed }" :style="boxStyle(frame)" @pointerdown.stop="itemDown($event, frame)">
          <div class="fs-frame-head"><span>{{ frame.title }}</span><small>{{ frameCount(frame) }} 人</small><button type="button" @pointerdown.stop @click.stop="mutate(() => frame.collapsed = !frame.collapsed)">{{ frame.collapsed ? '展开' : '收起' }}</button><button type="button" class="fs-frame-delete" title="删除分组框" aria-label="删除分组框" @pointerdown.stop @click.stop="deleteFrame(frame)">×</button></div>
          <span class="fs-frame-resize" @pointerdown.stop="resizeDown($event, frame)"></span>
        </div>
        <div v-if="drawingFrame" class="fs-frame fs-frame-preview" :style="boxStyle(drawingFrame)"></div>
        <template v-for="node in visibleNodes" :key="node.id">
          <div v-if="node.type === 'person'" class="fs-person" :class="{ chosen: selectedIds.includes(node.id), figure: isFigure(node), expanded: !isFigure(node), virtual: node.virtual, locked: node.locked }" :style="boxStyle(node)" :data-node-id="node.id" tabindex="0" role="group" :aria-label="personName(node)" :aria-describedby="hoveredPerson?.id === node.id ? 'fs-person-summary' : undefined" @pointerenter="showPersonSummary($event, node)" @pointerleave="scheduleHidePersonSummary" @focus="showPersonSummary($event, node)" @blur="scheduleHidePersonSummary" @keydown.enter.stop.prevent="selectOnly(node.id)" @pointerdown.stop="itemDown($event, node)" @dblclick.stop="selectOnly(node.id); inspectorOpen = true">
            <template v-if="isFigure(node)">
              <span class="fs-figure-model" :class="{ busy: !node.virtual && personLoad(node) >= 100 }" aria-hidden="true"><PersonStanding :size="48" :stroke-width="2.6" /><i v-if="node.virtual" class="fs-figure-virtual">虚</i></span>
              <strong class="fs-figure-name">{{ personName(node) }}</strong>
            </template>
            <template v-else>
            <div class="fs-person-top"><div class="fs-avatar">{{ personName(node).slice(0, 1) }}</div><div class="fs-person-name"><strong>{{ personName(node) }}</strong><span>{{ personRole(node) || '未填写角色' }}</span><small v-if="node.display !== 'avatar'">{{ personTeam(node) || '未分组' }}</small></div><b v-if="node.virtual" class="fs-virtual-badge">虚拟</b></div>
            <div v-if="node.display !== 'avatar'" class="fs-load"><i :style="{ width: `${Math.min(personLoad(node), 100)}%`, background: personLoad(node) >= 100 ? '#ec8a52' : '#3485ed' }"></i><span>占用 {{ personLoad(node) }}%</span></div>
            <p v-if="node.display === 'detail'" class="fs-detail-line">{{ personProjects(node) || '暂无当前项目' }}</p>
            </template>
            <button v-if="selectedIds.includes(node.id) && !node.locked" type="button" class="fs-handle" title="拖到另一位人员连线" @pointerdown.stop="edgeDown($event, node)"></button>
          </div>
          <div v-else-if="node.type === 'note' || node.type === 'text'" class="fs-note" :class="[node.type, { chosen: selectedIds.includes(node.id) }]" :style="boxStyle(node)" @pointerdown.stop="itemDown($event, node)" @dblclick.stop="selectOnly(node.id); inspectorOpen = true">{{ node.text || (node.type === 'note' ? '双击填写便签' : '双击填写文字') }}</div>
        </template>
        <svg v-if="edgeDraft" class="fs-draft" width="6000" height="6000"><path :d="draftPath" /></svg>
      </div>
      <div v-if="!document.nodes.length && ready" class="fs-empty"><div class="fs-empty-icon">＋</div><h1>开始你的自由沙盘</h1><p>添加人员，拖动卡片，再从连接点拖出关系。</p><button type="button" @click.stop="pickerOpen = true">添加人员</button></div>
    </div>

    <div v-if="hoveredPerson" id="fs-person-summary" ref="summaryElement" class="fs-person-summary" role="tooltip" :style="summaryPosition" @pointerenter="keepPersonSummary" @pointerleave="scheduleHidePersonSummary" @pointerdown.stop @wheel.stop>
      <div class="fs-summary-title"><strong>{{ personName(hoveredPerson) }}</strong><span v-if="hoveredPerson.virtual">虚拟人员</span></div>
      <p class="fs-summary-meta">{{ personRole(hoveredPerson) || '未填写角色' }} · {{ personTeam(hoveredPerson) || '未分组' }}</p>
      <template v-if="!hoveredPerson.virtual">
        <div class="fs-summary-load"><span>当前占用</span><strong :class="{ busy: personLoad(hoveredPerson) >= 100 }">{{ personLoad(hoveredPerson) }}%</strong></div>
        <div class="fs-summary-meter"><i :class="{ busy: personLoad(hoveredPerson) >= 100 }" :style="{ width: `${Math.min(personLoad(hoveredPerson), 100)}%` }"></i></div>
        <p class="fs-summary-projects"><span>当前项目</span>{{ personProjects(hoveredPerson) || '暂无当前项目' }}</p>
      </template>
      <p v-else class="fs-summary-meta">用于规划，未计入正式人员占用。</p>
      <small>拖动调整位置 · 双击查看详情</small>
    </div>

    <header class="fs-header"><a href="/" title="返回主系统">‹</a><strong>自由沙盘</strong><span class="fs-divider"></span><input v-if="renaming" ref="renameInput" v-model="newTitle" class="fs-rename" aria-label="沙盘名称" maxlength="100" @keyup.enter="finishRename" @keyup.esc="renaming = false" @blur="finishRename" /><select v-else :value="activeId" aria-label="切换沙盘" @change="openSandbox($event.target.value)"><option v-for="item in sandboxes" :key="item.id" :value="item.id">{{ item.title }}</option></select><button type="button" title="重命名沙盘" @click="startRename">✎</button><button type="button" title="更新人员资料" @click="refreshPeople">↻</button><span class="fs-status" :class="saveState">● {{ saveLabel }}</span><button type="button" title="新建沙盘" @click="createSandbox()">＋</button></header>
    <nav class="fs-tools" aria-label="画布工具"><button v-for="item in tools" :key="item.id" type="button" :title="item.label" :class="{ active: tool === item.id }" @click="chooseTool(item.id)"><component :is="item.icon" :size="19" /></button><hr /><button type="button" title="撤销" :disabled="!history.length" @click="undo"><Undo2 :size="19" /></button><button type="button" title="重做" :disabled="!future.length" @click="redo"><Redo2 :size="19" /></button></nav>
    <div v-if="selectedIds.length" class="fs-selection-bar"><span>已选 {{ selectedIds.length }} 项</span><button type="button" @click="duplicateSelected">复制</button><button type="button" @click="deleteSelected">删除</button><button type="button" @click="inspectorOpen = !inspectorOpen">属性</button></div>
    <aside v-if="inspectorOpen && selected" class="fs-inspector"><div class="fs-inspector-head"><h2>{{ selected.type === 'person' ? '人员属性' : selected.type === 'frame' ? '分组属性' : selected.type === 'edge' ? '连线属性' : '内容属性' }}</h2><button type="button" @click="inspectorOpen = false">×</button></div>
      <template v-if="selected.type === 'person'"><div class="fs-inspector-person"><span class="fs-avatar">{{ personName(selected).slice(0,1) }}</span><div><strong>{{ personName(selected) }}</strong><small>{{ personRole(selected) }}</small></div></div><template v-if="selected.virtual"><label>姓名<input :value="selected.name" @change="setField(selected, 'name', $event.target.value)" /></label><label>角色<input :value="selected.role" @change="setField(selected, 'role', $event.target.value)" /></label><label>团队<input :value="selected.team" @change="setField(selected, 'team', $event.target.value)" /></label></template><template v-else><p class="fs-property">所属团队 <strong>{{ personTeam(selected) || '未分组' }}</strong></p><p class="fs-property">当前占用 <strong>{{ personLoad(selected) }}%</strong></p><p class="fs-property">基准日期 <strong>{{ today }}</strong></p><p class="fs-property">当前项目 <strong>{{ personProjects(selected) || '暂无' }}</strong></p></template><label>展示形态<select :value="isFigure(selected) ? 'figure' : 'detail'" @change="setField(selected, 'display', $event.target.value)"><option value="figure">小人</option><option value="detail">详情卡片</option></select></label><label>沙盘备注<textarea :value="selected.note || ''" @change="setField(selected, 'note', $event.target.value)"></textarea></label></template>
      <template v-else-if="selected.type === 'frame'"><label>分组名称<input :value="selected.title" @change="setField(selected, 'title', $event.target.value)" /></label><label>颜色<input type="color" :value="selected.color || '#dcecff'" @change="setField(selected, 'color', $event.target.value)" /></label><p class="fs-property">包含 {{ frameCount(selected) }} 人</p></template>
      <template v-else-if="selected.type === 'edge'"><label>关系标签<input :value="selected.label || ''" @change="setField(selected, 'label', $event.target.value)" placeholder="协作、支持、交接…" /></label><label>方向<select :value="selected.direction || 'none'" @change="setField(selected, 'direction', $event.target.value)"><option value="none">无方向</option><option value="forward">起点 → 终点</option></select></label><label class="fs-check"><input type="checkbox" :checked="selected.dashed" @change="setField(selected, 'dashed', $event.target.checked)" /> 虚线</label></template>
      <template v-else><label>内容<textarea :value="selected.text || ''" @change="setField(selected, 'text', $event.target.value)"></textarea></label></template>
      <label v-if="selected.type !== 'edge'" class="fs-check"><input type="checkbox" :checked="selected.locked" @change="setField(selected, 'locked', $event.target.checked)" /> 锁定位置</label><p class="fs-inspector-hint">画布修改不会影响正式安排。</p>
    </aside>
    <div class="fs-bottom-left"><button type="button" @click="showLibrary = !showLibrary">{{ showLibrary ? '隐藏' : '管理' }}沙盘</button><span>空格拖动画布 · 双击添加 · Shift 多选</span></div>
    <div class="fs-zoom"><button type="button" @click="changeZoom(-0.1)">−</button><span>{{ Math.round(document.viewport.zoom * 100) }}%</span><button type="button" @click="changeZoom(0.1)">＋</button><button type="button" title="适应全部" @click="fitAll">⛶</button></div>
    <div v-if="showLibrary" class="fs-library"><h3>沙盘列表</h3><button v-for="item in sandboxes" :key="item.id" type="button" @click="openSandbox(item.id); showLibrary = false">{{ item.title }}</button><hr /><button type="button" @click="createSandbox()">＋ 新建沙盘</button><button type="button" @click="copySandbox">复制当前沙盘</button><button type="button" class="fs-danger" @click="removeSandbox">删除当前沙盘</button></div>
    <div v-if="pickerOpen" class="fs-modal-backdrop" @pointerdown.self="pickerOpen = false"><div class="fs-picker"><div class="fs-picker-head"><h2>添加到画布</h2><button type="button" @click="pickerOpen = false">×</button></div><input v-model="personQuery" autofocus placeholder="搜索姓名、角色或团队" /><div class="fs-picker-list"><button v-for="person in filteredPeople" :key="person.id" type="button" @click="addPerson(person)"><span class="fs-avatar">{{ person.name.slice(0,1) }}</span><span><strong>{{ person.name }}</strong><small>{{ person.role || '未填写角色' }} · {{ person.team || '未分组' }}</small></span><b>添加 ＋</b></button><p v-if="!filteredPeople.length">没有匹配的同事</p></div><button type="button" class="fs-add-virtual" @click="addVirtual">＋ 添加虚拟人员</button></div></div>
    <div v-if="notice" class="fs-toast" role="status">{{ notice }}<button type="button" @click="notice = ''">×</button></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import MousePointer2 from '@lucide/vue/dist/esm/icons/mouse-pointer-2.mjs';
import Hand from '@lucide/vue/dist/esm/icons/hand.mjs';
import UserRoundPlus from '@lucide/vue/dist/esm/icons/user-round-plus.mjs';
import Waypoints from '@lucide/vue/dist/esm/icons/waypoints.mjs';
import Square from '@lucide/vue/dist/esm/icons/square.mjs';
import Type from '@lucide/vue/dist/esm/icons/type.mjs';
import StickyNote from '@lucide/vue/dist/esm/icons/sticky-note.mjs';
import Undo2 from '@lucide/vue/dist/esm/icons/undo-2.mjs';
import Redo2 from '@lucide/vue/dist/esm/icons/redo-2.mjs';
import PersonStanding from '@lucide/vue/dist/esm/icons/person-standing.mjs';

const today = new Date().toISOString().slice(0, 10);
const blank = (title = '未命名沙盘') => ({ title, nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 }, revision: 0 });
const tools = [{ id: 'select', icon: MousePointer2, label: '选择' }, { id: 'pan', icon: Hand, label: '平移' }, { id: 'person', icon: UserRoundPlus, label: '添加人员' }, { id: 'edge', icon: Waypoints, label: '连线' }, { id: 'frame', icon: Square, label: '分组框' }, { id: 'text', icon: Type, label: '文字' }, { id: 'note', icon: StickyNote, label: '便签' }];
const canvas = ref(null), document = ref(blank()), activeId = ref(''), sandboxes = ref([]), people = ref([]), loads = ref([]), renameInput = ref(null), renaming = ref(false), newTitle = ref('');
const selectedIds = ref([]), inspectorOpen = ref(false), pickerOpen = ref(false), showLibrary = ref(false), personQuery = ref('');
const tool = ref('select'), ready = ref(false), notice = ref(''), saveState = ref('saved'), history = ref([]), future = ref([]);
const drawingFrame = ref(null), edgeDraft = ref(null);
const hoveredPersonId = ref(null), summaryElement = ref(null), summaryPosition = ref({ visibility: 'hidden' });
let summaryShowTimer, summaryHideTimer;
let gesture = null, saveTimer = null, saving = false, dirty = false, hydrated = false, spaceHeld = false, clipboard = null;
const id = () => crypto.randomUUID();
const copy = value => JSON.parse(JSON.stringify(value));
const worldStyle = computed(() => ({ transform: `translate(${document.value.viewport.x}px, ${document.value.viewport.y}px) scale(${document.value.viewport.zoom})` }));
const frames = computed(() => document.value.nodes.filter(n => n.type === 'frame'));
const visibleNodes = computed(() => document.value.nodes.filter(n => n.type !== 'frame' && !frames.value.some(f => f.id === n.groupId && f.collapsed)));
const hoveredPerson = computed(() => visibleNodes.value.find(n => n.id === hoveredPersonId.value && n.type === 'person'));
const visibleEdges = computed(() => document.value.edges.filter(e => visibleNodes.value.some(n => n.id === e.from) && visibleNodes.value.some(n => n.id === e.to)));
const selected = computed(() => [...document.value.nodes, ...document.value.edges].find(n => n.id === selectedIds.value[0]));
const filteredPeople = computed(() => people.value.filter(p => `${p.name} ${p.role} ${p.team}`.toLowerCase().includes(personQuery.value.toLowerCase())).slice(0, 60));
const saveLabel = computed(() => ({ saved: '已保存', saving: '保存中', failed: '仅保存在本机', conflict: '其他窗口已修改' }[saveState.value]));
const personRecord = n => people.value.find(p => String(p.id) === String(n.memberId));
const loadRecord = n => loads.value.find(p => String(p.member_id) === String(n.memberId));
const personName = n => n.virtual ? n.name : personRecord(n)?.name || n.snapshot?.name || '来源已不存在';
const personRole = n => n.virtual ? n.role : personRecord(n)?.role || n.snapshot?.role || '';
const personTeam = n => n.virtual ? n.team : personRecord(n)?.team || n.snapshot?.team || '';
const personLoad = n => n.virtual ? 0 : Math.round(Number(loadRecord(n)?.allocated_percent || 0));
const personProjects = n => loadRecord(n)?.project_names?.join('、') || '';
const frameCount = f => document.value.nodes.filter(n => n.type === 'person' && n.groupId === f.id).length;
// Legacy card/avatar values also render as figures, without rewriting saved layouts.
const isFigure = n => n.display !== 'detail';
const size = n => n.type === 'frame' ? [n.w, n.h] : n.type === 'person' ? isFigure(n) ? [100, 88] : [230, 150] : n.type === 'note' ? [200, 120] : [220, 60];
const boxStyle = n => ({ left: `${n.x}px`, top: `${n.y}px`, width: `${size(n)[0]}px`, height: `${size(n)[1]}px`, ...(n.type === 'frame' ? { '--frame-color': n.color || '#dcecff' } : {}) });
const center = n => ({ x: n.x + size(n)[0] / 2, y: n.y + size(n)[1] / 2 });
function edgePoints(e) { const a = document.value.nodes.find(n => n.id === e.from), b = document.value.nodes.find(n => n.id === e.to); if (!a || !b) return null; const ac = center(a), bc = center(b), vertical = Math.abs(bc.y - ac.y) > Math.abs(bc.x - ac.x); if (vertical) return { vertical, a: { x: ac.x, y: ac.y + (bc.y >= ac.y ? size(a)[1] / 2 : -size(a)[1] / 2) }, b: { x: bc.x, y: bc.y + (bc.y >= ac.y ? -size(b)[1] / 2 : size(b)[1] / 2) } }; return { vertical, a: { x: ac.x + (bc.x >= ac.x ? size(a)[0] / 2 : -size(a)[0] / 2), y: ac.y }, b: { x: bc.x + (bc.x >= ac.x ? -size(b)[0] / 2 : size(b)[0] / 2), y: bc.y } }; }
function edgePath(e) { const p = edgePoints(e); if (!p) return ''; if (p.vertical) { const bend = (p.b.y - p.a.y) / 2; return `M${p.a.x} ${p.a.y} C${p.a.x} ${p.a.y + bend},${p.b.x} ${p.b.y - bend},${p.b.x} ${p.b.y}`; } const bend = (p.b.x - p.a.x) / 2; return `M${p.a.x} ${p.a.y} C${p.a.x + bend} ${p.a.y},${p.b.x - bend} ${p.b.y},${p.b.x} ${p.b.y}`; }
function edgeMid(e) { const p = edgePoints(e); return p ? { x: (p.a.x + p.b.x) / 2, y: (p.a.y + p.b.y) / 2 } : { x: 0, y: 0 }; }
const draftPath = computed(() => edgeDraft.value ? `M${edgeDraft.value.x1} ${edgeDraft.value.y1} L${edgeDraft.value.x2} ${edgeDraft.value.y2}` : '');
function hidePersonSummary() {
  clearTimeout(summaryShowTimer);
  clearTimeout(summaryHideTimer);
  hoveredPersonId.value = null;
}
function keepPersonSummary() { clearTimeout(summaryHideTimer); }
function scheduleHidePersonSummary() {
  clearTimeout(summaryShowTimer);
  clearTimeout(summaryHideTimer);
  summaryHideTimer = setTimeout(hidePersonSummary, 140);
}
function showPersonSummary(event, node) {
  if (gesture || event.buttons || event.pointerType === 'touch') return;
  hidePersonSummary();
  const anchor = event.currentTarget.getBoundingClientRect();
  summaryShowTimer = setTimeout(async () => {
    hoveredPersonId.value = node.id;
    summaryPosition.value = { visibility: 'hidden' };
    await nextTick();
    if (!summaryElement.value || hoveredPersonId.value !== node.id) return;
    const { width, height } = summaryElement.value.getBoundingClientRect();
    const left = anchor.right + width + 24 <= window.innerWidth ? anchor.right + 12 : anchor.left - width - 12;
    summaryPosition.value = {
      left: `${Math.max(12, Math.min(left, window.innerWidth - width - 12))}px`,
      top: `${Math.max(12, Math.min(anchor.top, window.innerHeight - height - 12))}px`,
      visibility: 'visible',
    };
  }, event.type === 'focus' ? 0 : 180);
}
function canvasPoint(event) { const rect = canvas.value.getBoundingClientRect(), v = document.value.viewport; return { x: (event.clientX - rect.left - v.x) / v.zoom, y: (event.clientY - rect.top - v.y) / v.zoom }; }
function snapshot() { history.value.push(JSON.stringify({ nodes: document.value.nodes, edges: document.value.edges })); if (history.value.length > 100) history.value.shift(); future.value = []; }
function mutate(fn) { snapshot(); fn(); }
function setField(target, field, value) { if (target[field] !== value) mutate(() => target[field] = value); }
function undo() { if (!history.value.length) return; future.value.push(JSON.stringify({ nodes: document.value.nodes, edges: document.value.edges })); const prior = JSON.parse(history.value.pop()); document.value.nodes = prior.nodes; document.value.edges = prior.edges; }
function redo() { if (!future.value.length) return; history.value.push(JSON.stringify({ nodes: document.value.nodes, edges: document.value.edges })); const next = JSON.parse(future.value.pop()); document.value.nodes = next.nodes; document.value.edges = next.edges; }
function selectOnly(itemId) { selectedIds.value = [itemId]; inspectorOpen.value = true; }
function chooseTool(value) { tool.value = value; if (value === 'person') { pickerOpen.value = true; tool.value = 'select'; } }
function itemDown(event, item) { if (event.button !== 0) return; if (tool.value === 'edge' && item.type === 'person') { edgeDown(event, item); return; } if (item.locked) { selectOnly(item.id); return; } if (event.shiftKey) selectedIds.value = selectedIds.value.includes(item.id) ? selectedIds.value.filter(x => x !== item.id) : [...selectedIds.value, item.id]; else if (!selectedIds.value.includes(item.id)) selectedIds.value = [item.id]; inspectorOpen.value = true; if (!selectedIds.value.includes(item.id)) return; snapshot(); const moving = new Set(selectedIds.value); if (item.type === 'frame') document.value.nodes.filter(n => n.groupId === item.id).forEach(n => moving.add(n.id)); gesture = { kind: 'move', startX: event.clientX, startY: event.clientY, origin: document.value.nodes.filter(n => moving.has(n.id)).map(n => ({ id: n.id, x: n.x, y: n.y })), moved: false }; }
function edgeDown(event, item) { event.preventDefault(); const p = center(item); edgeDraft.value = { from: item.id, x1: p.x + size(item)[0] / 2, y1: p.y, x2: p.x, y2: p.y }; gesture = { kind: 'edge' }; }
function resizeDown(event, frame) { if (frame.locked) return; event.preventDefault(); snapshot(); gesture = { kind: 'resize', id: frame.id, x: event.clientX, y: event.clientY, w: frame.w, h: frame.h }; selectOnly(frame.id); }
function canvasDown(event) { if (event.button !== 0 && event.button !== 1) return; if (spaceHeld || tool.value === 'pan' || event.button === 1) { gesture = { kind: 'pan', x: event.clientX, y: event.clientY, vx: document.value.viewport.x, vy: document.value.viewport.y }; return; } if (tool.value === 'frame') { const p = canvasPoint(event); drawingFrame.value = { x: p.x, y: p.y, w: 0, h: 0 }; gesture = { kind: 'frame', start: p }; return; } if (tool.value === 'note' || tool.value === 'text') { const p = canvasPoint(event); addNode({ id: id(), type: tool.value, x: p.x, y: p.y, text: tool.value === 'note' ? '新便签' : '新文字' }); tool.value = 'select'; return; } selectedIds.value = []; inspectorOpen.value = false; }
function canvasDoubleClick(event) { if (event.target !== canvas.value && !event.target.classList.contains('fs-world')) return; pickerOpen.value = true; }
function onMove(event) { if (!gesture) return; const zoom = document.value.viewport.zoom; if (gesture.kind === 'pan') { document.value.viewport.x = gesture.vx + event.clientX - gesture.x; document.value.viewport.y = gesture.vy + event.clientY - gesture.y; } else if (gesture.kind === 'move') { const dx = (event.clientX - gesture.startX) / zoom, dy = (event.clientY - gesture.startY) / zoom; gesture.moved = Math.abs(dx) + Math.abs(dy) > 2; for (const origin of gesture.origin) { const node = document.value.nodes.find(n => n.id === origin.id); if (node) { node.x = origin.x + dx; node.y = origin.y + dy; } } } else if (gesture.kind === 'resize') { const node = document.value.nodes.find(n => n.id === gesture.id); if (node) { node.w = Math.max(220, gesture.w + (event.clientX - gesture.x) / zoom); node.h = Math.max(160, gesture.h + (event.clientY - gesture.y) / zoom); } } else if (gesture.kind === 'frame') { const p = canvasPoint(event); drawingFrame.value = { x: Math.min(p.x, gesture.start.x), y: Math.min(p.y, gesture.start.y), w: Math.abs(p.x - gesture.start.x), h: Math.abs(p.y - gesture.start.y) }; } else if (gesture.kind === 'edge') { const p = canvasPoint(event); edgeDraft.value.x2 = p.x; edgeDraft.value.y2 = p.y; } }
function onUp(event) { if (!gesture) return; if (gesture.kind === 'edge') { const target = globalThis.document.elementFromPoint(event.clientX, event.clientY)?.closest('[data-node-id]'); const to = target?.dataset.nodeId; if (to && to !== edgeDraft.value.from) { mutate(() => document.value.edges.push({ id: id(), type: 'edge', from: edgeDraft.value.from, to, label: '', direction: 'none' })); selectOnly(document.value.edges.at(-1).id); } edgeDraft.value = null; tool.value = 'select'; } else if (gesture.kind === 'frame' && drawingFrame.value?.w > 90 && drawingFrame.value?.h > 70) { const frame = { id: id(), type: 'frame', ...drawingFrame.value, title: '新分组', color: '#dcecff' }; mutate(() => { document.value.nodes.push(frame); document.value.nodes.filter(n => n.id !== frame.id && n.type === 'person').forEach(n => { const c = center(n); if (c.x >= frame.x && c.x <= frame.x + frame.w && c.y >= frame.y && c.y <= frame.y + frame.h) n.groupId = frame.id; }); }); selectOnly(frame.id); tool.value = 'select'; drawingFrame.value = null; } else if (gesture.kind === 'move') { if (!gesture.moved) { history.value.pop(); } else { for (const origin of gesture.origin) { const node = document.value.nodes.find(n => n.id === origin.id); if (!node || node.type === 'frame') continue; const c = center(node); const frame = [...frames.value].reverse().find(f => f.id !== node.id && c.x >= f.x && c.x <= f.x + f.w && c.y >= f.y && c.y <= f.y + f.h); node.groupId = frame?.id || null; } } } gesture = null; drawingFrame.value = null; }
function addNode(node) { mutate(() => document.value.nodes.push(node)); selectOnly(node.id); }
function nextPersonPoint() { const rect = canvas.value.getBoundingClientRect(), count = document.value.nodes.filter(n => n.type === 'person').length, columns = Math.max(1, Math.floor((rect.width - (inspectorOpen.value ? 420 : 160)) / 132)); return canvasPoint({ clientX: rect.left + 120 + count % columns * 132, clientY: rect.top + 165 + Math.floor(count / columns) * 116 }); }
function addPerson(person) { const p = nextPersonPoint(); addNode({ id: id(), type: 'person', x: p.x, y: p.y, memberId: person.id, snapshot: { name: person.name, role: person.role, team: person.team }, display: 'figure' }); pickerOpen.value = false; personQuery.value = ''; }
function addVirtual() { const p = nextPersonPoint(); addNode({ id: id(), type: 'person', x: p.x, y: p.y, virtual: true, name: '待确定人员', role: '待定岗位', team: '', display: 'figure' }); pickerOpen.value = false; }
function deleteSelected() { if (!selectedIds.value.length) return; const removing = new Set(selectedIds.value); mutate(() => { document.value.nodes.filter(n => n.type === 'frame' && removing.has(n.id)).forEach(f => document.value.nodes.filter(n => n.groupId === f.id).forEach(n => n.groupId = null)); document.value.nodes = document.value.nodes.filter(n => !removing.has(n.id)); document.value.edges = document.value.edges.filter(e => !removing.has(e.id) && !removing.has(e.from) && !removing.has(e.to)); }); selectedIds.value = []; inspectorOpen.value = false; }
function deleteFrame(frame) { selectedIds.value = [frame.id]; deleteSelected(); }
function copySelected() { const nodeIds = new Set(selectedIds.value); document.value.nodes.filter(n => nodeIds.has(n.groupId)).forEach(n => nodeIds.add(n.id)); clipboard = copy([...document.value.nodes.filter(n => nodeIds.has(n.id)), ...document.value.edges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to))]); }
function pasteSelected() { if (!clipboard?.length) return; const nodes = clipboard.filter(n => n.type !== 'edge'), ids = new Map(nodes.map(n => [n.id, id()])); mutate(() => { nodes.forEach(n => document.value.nodes.push({ ...copy(n), id: ids.get(n.id), x: n.x + 28, y: n.y + 28, ...(n.virtual ? { name: `${n.name} 副本` } : {}), groupId: ids.get(n.groupId) || n.groupId })); clipboard.filter(e => e.type === 'edge' && ids.has(e.from) && ids.has(e.to)).forEach(e => document.value.edges.push({ ...e, id: id(), from: ids.get(e.from), to: ids.get(e.to) })); }); selectedIds.value = [...ids.values()]; }
function duplicateSelected() { copySelected(); pasteSelected(); }
function changeZoom(delta, clientX, clientY) { const rect = canvas.value.getBoundingClientRect(), px = (clientX ?? rect.left + rect.width / 2) - rect.left, py = (clientY ?? rect.top + rect.height / 2) - rect.top, v = document.value.viewport, old = v.zoom; v.zoom = Math.min(2, Math.max(.2, +(old + delta).toFixed(2))); v.x = px - (px - v.x) * v.zoom / old; v.y = py - (py - v.y) * v.zoom / old; }
function onWheel(event) { if (event.ctrlKey || event.metaKey) changeZoom(event.deltaY > 0 ? -.05 : .05, event.clientX, event.clientY); else { document.value.viewport.x -= event.deltaX; document.value.viewport.y -= event.deltaY; } }
function fitAll() { const nodes = document.value.nodes; if (!nodes.length) { document.value.viewport = { x: 0, y: 0, zoom: 1 }; return; } const minX = Math.min(...nodes.map(n => n.x)), minY = Math.min(...nodes.map(n => n.y)), maxX = Math.max(...nodes.map(n => n.x + size(n)[0])), maxY = Math.max(...nodes.map(n => n.y + size(n)[1])); const rect = canvas.value.getBoundingClientRect(), zoom = Math.min(1.5, Math.max(.2, Math.min((rect.width - 240) / (maxX - minX + 80), (rect.height - 180) / (maxY - minY + 80)))); document.value.viewport = { x: (rect.width - (maxX - minX) * zoom) / 2 - minX * zoom, y: (rect.height - (maxY - minY) * zoom) / 2 - minY * zoom, zoom }; }
function keyDown(event) { if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return; if (event.code === 'Space') { spaceHeld = true; event.preventDefault(); } if (event.key === 'Escape') { gesture = null; edgeDraft.value = null; drawingFrame.value = null; pickerOpen.value = false; tool.value = 'select'; } if (event.key === 'Delete' || event.key === 'Backspace') deleteSelected(); if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); event.shiftKey ? redo() : undo(); } if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'c') { event.preventDefault(); copySelected(); } if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'v') { event.preventDefault(); pasteSelected(); } }
function keyUp(event) { if (event.code === 'Space') spaceHeld = false; }
async function api(path, options) {
  const response = await fetch(`/api/freeform-sandboxes${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!response.ok) {
    const { detail } = await response.json().catch(() => ({}));
    const message = typeof detail === 'string' ? detail : (Array.isArray(detail) ? detail : [detail])
      .map(item => typeof item === 'string' ? item : typeof item?.msg === 'string' ? [item.loc?.join('.'), item.msg].filter(Boolean).join('：') : '')
      .filter(Boolean).join('；');
    const error = new Error(message || `请求失败（HTTP ${response.status}）`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}
async function refreshList() { sandboxes.value = (await api('')).sandboxes; }
async function refreshPeople() { try { const response = await fetch(`/api/overview?date=${today}`); if (!response.ok) throw new Error('读取失败'); const data = await response.json(); people.value = data.members || []; loads.value = data.member_load || []; notice.value = '人员资料已更新'; } catch (error) { notice.value = `更新人员资料失败：${error.message}`; } }
async function createSandbox(seed) { try { const fresh = seed || blank(); const result = await api('', { method: 'POST', body: JSON.stringify(fresh) }); await refreshList(); await openSandbox(result.id); showLibrary.value = false; } catch (error) { notice.value = `新建失败：${error.message}`; } }
async function openSandbox(sandboxId) { if (!sandboxId) return; try { hydrated = false; clearTimeout(saveTimer); const data = await api(`/${sandboxId}`); const draft = localStorage.getItem(`freeform-draft:${sandboxId}`); const recovered = draft ? JSON.parse(draft) : null; document.value = recovered ? { ...data, ...recovered, revision: data.revision } : data; activeId.value = sandboxId; history.value = []; future.value = []; selectedIds.value = []; inspectorOpen.value = false; window.history.replaceState(null, '', `/free-sandbox/${sandboxId}`); await nextTick(); hydrated = true; ready.value = true; dirty = Boolean(recovered); if (recovered?.revision && recovered.revision !== data.revision) { saveState.value = 'conflict'; notice.value = '本机草稿和服务端版本不同，请复制当前沙盘保存为新方案'; } else if (recovered) scheduleSave(); else saveState.value = 'saved'; } catch (error) { notice.value = `加载失败：${error.message}`; } }
async function startRename() { newTitle.value = document.value.title; renaming.value = true; await nextTick(); renameInput.value?.focus(); renameInput.value?.select(); }
function finishRename() { if (!renaming.value) return; const title = newTitle.value.trim(); renaming.value = false; if (title && title !== document.value.title) setField(document.value, 'title', title); }
async function copySandbox() { await createSandbox({ ...copy(document.value), title: `${document.value.title} 副本`, revision: 0 }); }
async function removeSandbox() { if (!confirm(`删除「${document.value.title}」？`)) return; try { await api(`/${activeId.value}`, { method: 'DELETE' }); localStorage.removeItem(`freeform-draft:${activeId.value}`); await refreshList(); if (sandboxes.value.length) await openSandbox(sandboxes.value[0].id); else await createSandbox(); showLibrary.value = false; } catch (error) { notice.value = `删除失败：${error.message}`; } }
function scheduleSave() { if (!hydrated || !activeId.value) return; dirty = true; try { localStorage.setItem(`freeform-draft:${activeId.value}`, JSON.stringify({ title: document.value.title, nodes: document.value.nodes, edges: document.value.edges, viewport: document.value.viewport, revision: document.value.revision })); } catch { notice.value = '本机草稿存储已满，请及时保存'; } if (saveState.value !== 'conflict') saveState.value = 'saving'; clearTimeout(saveTimer); saveTimer = setTimeout(save, 850); }
async function save() { if (saving || !dirty || !activeId.value || saveState.value === 'conflict') return; saving = true; dirty = false; const sandboxId = activeId.value; const payload = copy(document.value); try { const result = await api(`/${sandboxId}`, { method: 'PUT', body: JSON.stringify(payload) }); if (sandboxId === activeId.value) { document.value.revision = result.revision; if (!dirty) { localStorage.removeItem(`freeform-draft:${sandboxId}`); saveState.value = 'saved'; await refreshList(); } } } catch (error) { dirty = true; saveState.value = error.status === 409 ? 'conflict' : 'failed'; notice.value = error.status === 409 ? '其他窗口已修改；请复制当前沙盘保存为新方案' : `保存失败，已保留本机草稿：${error.message}`; } finally { saving = false; if (dirty && saveState.value === 'saving') setTimeout(save, 0); } }
watch(() => JSON.stringify({ title: document.value.title, nodes: document.value.nodes, edges: document.value.edges, viewport: document.value.viewport }), scheduleSave);
watch(() => [document.value.viewport.x, document.value.viewport.y, document.value.viewport.zoom, activeId.value, pickerOpen.value], hidePersonSummary);
onBeforeUnmount(hidePersonSummary);
watch(() => document.value.title, value => { const entry = sandboxes.value.find(s => s.id === activeId.value); if (entry) entry.title = value; });
onMounted(async () => { window.addEventListener('pointermove', onMove); window.addEventListener('pointerup', onUp); window.addEventListener('keydown', keyDown); window.addEventListener('keyup', keyUp); try { await refreshPeople(); notice.value = ''; await refreshList(); const routeId = location.pathname.split('/')[2]; if (routeId) await openSandbox(routeId); else if (sandboxes.value.length) await openSandbox(sandboxes.value[0].id); else await createSandbox(); } catch (error) { notice.value = `初始化失败：${error.message}`; } });
onBeforeUnmount(() => { clearTimeout(saveTimer); window.removeEventListener('pointermove', onMove); window.removeEventListener('pointerup', onUp); window.removeEventListener('keydown', keyDown); window.removeEventListener('keyup', keyUp); });
</script>

<style src="./freeform-sandbox.css"></style>
