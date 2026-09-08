<template>
  <div class="island-scene" :class="{ 'scene-unavailable': unavailable }">
    <div ref="surface" class="scene-surface" :aria-label="english ? 'Interactive resource islands' : '可交互资源岛'" />
    <div v-if="unavailable" class="scene-message" role="status">{{ english ? '3D is unavailable in this browser. Use the project list to explore all resources.' : '当前浏览器无法显示 3D，请使用项目清单查看全部资源。' }}</div>
    <div v-if="!islands.length" class="scene-message">{{ english ? 'No matching projects' : '没有匹配的项目' }}</div>
    <div class="scene-hint"><MousePointer2 :size="15" /><span>{{ english ? 'Drag to orbit · Scroll to zoom · Right-drag to pan' : '拖拽旋转 · 滚轮缩放 · 右键平移' }}</span></div>
    <div class="scene-bottom">
      <div class="scene-map" :aria-label="english ? 'Project navigator' : '项目导航缩略图'">
        <span>{{ english ? 'NAVIGATOR' : '项目导航' }}</span>
        <div class="map-points">
          <button v-for="p in positions" :key="p.id" :title="islands.find(i => i.id === p.id)?.name" :aria-label="islands.find(i => i.id === p.id)?.name" :class="{ selected: p.id === selectedProject }" :style="mapStyle(p)" @click="emit('select-project', p.id); focus(p.id)" />
        </div>
      </div>
      <div class="scene-tools" v-if="!unavailable">
        <button :title="english ? 'Zoom out' : '缩小'" :aria-label="english ? 'Zoom out' : '缩小'" @click="zoom(.8)"><Minus :size="17" /></button>
        <button :title="english ? 'Zoom in' : '放大'" :aria-label="english ? 'Zoom in' : '放大'" @click="zoom(1.25)"><Plus :size="17" /></button>
        <span class="tool-divider" />
        <button :class="{ active: !topView }" :aria-pressed="!topView" @click="setView(false)"><Box :size="16" />{{ english ? '3D' : '3D 视图' }}</button>
        <button :class="{ active: topView }" :aria-pressed="topView" @click="setView(true)"><PanelsTopLeft :size="16" />{{ english ? 'Top' : '俯视' }}</button>
        <button :title="english ? 'Focus selected project' : '聚焦当前项目'" :aria-label="english ? 'Focus selected project' : '聚焦当前项目'" :disabled="selectedProject == null" @click="focus(selectedProject)"><Focus :size="17" /></button>
        <button :class="{ active: touring }" :aria-pressed="touring" @click="toggleTour"><Orbit :size="17" />{{ english ? 'Orbit' : '环游' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DObject, CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';
import Box from '@lucide/vue/dist/esm/icons/box.mjs';
import Focus from '@lucide/vue/dist/esm/icons/focus.mjs';
import Minus from '@lucide/vue/dist/esm/icons/minus.mjs';
import Plus from '@lucide/vue/dist/esm/icons/plus.mjs';
import Orbit from '@lucide/vue/dist/esm/icons/orbit.mjs';
import PanelsTopLeft from '@lucide/vue/dist/esm/icons/panels-top-left.mjs';
import MousePointer2 from '@lucide/vue/dist/esm/icons/mouse-pointer-2.mjs';
import { islandLayout, sharedProjectLinks } from '../lib/resourceSandbox.js';

const props = defineProps({ islands: { type: Array, default: () => [] }, selectedProject: [String, Number], selectedMember: [String, Number], english: Boolean, spacing: { type: Number, default: 1 }, showLinks: { type: Boolean, default: true }, avatarFor: Function });
const emit = defineEmits(['select-project', 'select-member', 'unavailable']);
const surface = ref(null), unavailable = ref(false), topView = ref(false), touring = ref(false);
const positions = computed(() => islandLayout(props.islands, props.spacing));
let scene, camera, renderer, labels, controls, content, observer, frame, dirty = true, disposed = false;
let pickTargets = [], labelObjects = [], size = { width: 1, height: 1 }, pointerStart;
const raycaster = new THREE.Raycaster();
const point = new THREE.Vector2();
const palette = ['#4397a5', '#8b8dc6', '#81a785', '#d5aa71', '#719bc0'];
const danger = p => ['blocked', 'overloaded'].includes(p.risk);

function mapStyle(p) {
  const extent = Math.max(12, ...positions.value.map(i => Math.max(Math.abs(i.x), Math.abs(i.z)) + 6));
  return { left: `${50 + p.x / extent * 43}%`, top: `${50 + p.z / extent * 40}%` };
}
function material(color, extra = {}) { return new THREE.MeshStandardMaterial({ color, roughness: .93, ...extra }); }
function mesh(geometry, mat, group, x, y, z) {
  const m = new THREE.Mesh(geometry, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; group.add(m); return m;
}
function disposeContent() {
  if (!content) return;
  content.traverse(o => {
    o.element?.remove(); o.geometry?.dispose();
    if (o.material) for (const m of Array.isArray(o.material) ? o.material : [o.material]) m.dispose();
  });
  scene.remove(content); pickTargets = []; labelObjects = [];
}
function addLabel(group, text, className, position, onClick, avatar, subtitle) {
  const el = document.createElement('button'); el.type = 'button'; el.className = `island-label ${className}`;
  if (avatar) { const img = document.createElement('img'); img.src = avatar; img.alt = ''; el.append(img); }
  const name = document.createElement('span'); name.textContent = text; el.append(name);
  if (subtitle) { const sub = document.createElement('b'); sub.textContent = subtitle; el.append(sub); }
  el.title = `${text}${subtitle ? ` · ${subtitle}` : ''}`;
  el.addEventListener('pointerdown', e => e.stopPropagation());
  el.addEventListener('click', e => { e.stopPropagation(); onClick(); });
  const label = new CSS2DObject(el); label.position.copy(position); group.add(label); labelObjects.push(label);
  return label;
}
function rebuild() {
  if (!renderer || unavailable.value) return;
  disposeContent(); content = new THREE.Group(); scene.add(content);
  const layout = new Map(positions.value.map(p => [p.id, p]));
  props.islands.forEach((island, index) => {
    const p = layout.get(island.id), selected = island.id === props.selectedProject;
    const group = new THREE.Group(); group.position.set(p.x, 0, p.z); content.add(group);
    const shape = new THREE.Shape();
    const contour = [];
    for (let j = 0; j < 14; j++) {
      const a = j / 14 * Math.PI * 2, r = p.radius * (1 + .075 * Math.sin(j * 2.7 + index));
      contour.push(new THREE.Vector2(Math.cos(a) * r, Math.sin(a) * r * .84));
    }
    shape.moveTo(contour[0].x, contour[0].y);
    for (let j = 1; j <= contour.length; j++) {
      const a = contour[j % contour.length], b = contour[(j + 1) % contour.length];
      shape.quadraticCurveTo(a.x, a.y, (a.x + b.x) / 2, (a.y + b.y) / 2);
    }
    shape.closePath();
    const geometry = new THREE.ExtrudeGeometry(shape, { depth: .3, bevelEnabled: true, bevelSegments: 3, steps: 1, bevelSize: .14, bevelThickness: .12, curveSegments: 8 });
    geometry.rotateX(-Math.PI / 2);
    const base = mesh(geometry, material(selected ? '#80c4cc' : '#cdd7d8'), group, 0, .28, 0);
    const land = mesh(geometry.clone(), material(selected ? '#f2f5ed' : '#f1f2ed'), group, 0, .5, 0); land.scale.set(.96, .75, .96);
    base.userData = land.userData = { projectId: island.id }; pickTargets.push(base, land);

    // Real scene geometry: soft sculpted islands and small trees, lit from above.
    for (let j = 0; j < 3; j++) {
      const a = (j / 3 * Math.PI * 2) + .5, x = Math.cos(a) * p.radius * .78, z = Math.sin(a) * p.radius * .65;
      mesh(new THREE.CylinderGeometry(.04, .07, .42, 5), material('#a79c87'), group, x, 1, z);
      mesh(new THREE.IcosahedronGeometry(.3, 1), material('#a9b8a0'), group, x, 1.35, z).scale.y = 1.4;
    }
    const visiblePeople = selected || props.islands.length <= 6 ? island.people : [];
    const cols = Math.ceil(Math.sqrt(visiblePeople.length || 1));
    const rows = Math.ceil(visiblePeople.length / cols);
    visiblePeople.forEach((person, j) => {
      const x = ((j % cols) - (cols - 1) / 2) * Math.min(2.8, p.radius * 1.4 / cols);
      const z = (Math.floor(j / cols) - (rows - 1) / 2) * Math.min(2.7, p.radius * 1.25 / rows);
      const chosen = person.id === props.selectedMember;
      const color = danger(person) ? '#d7654e' : person.risk === 'tight' ? '#c79952' : palette[index % palette.length];
      const pedestal = mesh(new THREE.CylinderGeometry(.32, .42, .16, 24), material(chosen ? '#206f80' : '#d7e1df'), group, x, .95, z);
      const token = mesh(new THREE.CapsuleGeometry(.13, .28, 3, 8), material(color), group, x, 1.22, z);
      pedestal.userData = token.userData = { projectId: island.id, memberId: person.id }; pickTargets.push(pedestal, token);
      const label = addLabel(group, person.name, `person-label ${danger(person) ? 'is-risk' : ''} ${chosen ? 'is-selected' : ''}`, new THREE.Vector3(x, 1.95, z), () => emit('select-member', island.id, person.id), props.avatarFor?.(person), `${Math.round(person.allocated)}%`);
      label.userData.priority = chosen ? 3 : selected ? 2 : 0;
    });
    const title = addLabel(group, island.name, `project-label ${selected ? 'is-selected' : ''}`, new THREE.Vector3(0, 2.7, -p.radius * 1.1), () => emit('select-project', island.id), null, `${island.people.length} ${props.english ? 'people' : '人'}`);
    title.userData.priority = 4;
  });
  if (props.showLinks) for (const link of sharedProjectLinks(props.islands)) {
    const a = layout.get(link.from), b = layout.get(link.to);
    const selected = link.people.some(p => p.id === props.selectedMember);
    const start = new THREE.Vector3(a.x, .56, a.z), end = new THREE.Vector3(b.x, .56, b.z);
    const mid = start.clone().lerp(end, .5); mid.y = 1.8;
    const path = new THREE.QuadraticBezierCurve3(start, mid, end);
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(path.getPoints(40)), new THREE.LineBasicMaterial({ color: link.risk ? '#cf9770' : selected ? '#167f92' : '#8bbdc5', transparent: true, opacity: props.selectedMember != null && !selected ? .2 : .85 }));
    content.add(line);
  }
  dirty = true;
}
function fit() {
  if (!camera) return;
  touring.value = false; controls.autoRotate = false;
  const extent = Math.max(8, ...positions.value.map(p => Math.max(Math.abs(p.x), Math.abs(p.z)) + p.radius + 3));
  controls.target.set(0, 0, 0); camera.position.set(0, extent * 1.45, extent * 1.75);
  camera.zoom = Math.min(1, size.width / size.height); camera.updateProjectionMatrix(); topView.value = false; controls.enableRotate = true; controls.update(); dirty = true;
}
function setView(top) {
  if (!camera) return;
  topView.value = top; touring.value = false; controls.autoRotate = false;
  const distance = camera.position.distanceTo(controls.target);
  camera.position.copy(controls.target).add(new THREE.Vector3(top ? 0 : distance * .3, top ? distance : distance * .65, top ? .01 : distance * .72));
  controls.enableRotate = !top; controls.update(); dirty = true;
}
function focus(id) {
  const p = positions.value.find(p => p.id === id); if (!p || !camera) return;
  const delta = new THREE.Vector3(p.x, 0, p.z).sub(controls.target);
  controls.target.add(delta); camera.position.add(delta);
  const direction = camera.position.clone().sub(controls.target).normalize();
  camera.position.copy(controls.target).addScaledVector(direction, 19 / Math.min(1, size.width / size.height));
  camera.zoom = 1; camera.updateProjectionMatrix(); controls.update(); dirty = true;
}
function zoom(factor) { if (!camera) return; const offset = camera.position.clone().sub(controls.target).multiplyScalar(1 / factor); offset.clampLength(8, 180); camera.position.copy(controls.target).add(offset); controls.update(); dirty = true; }
function toggleTour() { if (!controls) return; if (topView.value) setView(false); touring.value = !touring.value; controls.autoRotate = touring.value; dirty = true; }
function onPointerDown(e) { pointerStart = { x: e.clientX, y: e.clientY, button: e.button }; touring.value = false; if (controls) controls.autoRotate = false; }
function onPointerUp(e) {
  if (!pointerStart || pointerStart.button !== 0 || Math.hypot(e.clientX - pointerStart.x, e.clientY - pointerStart.y) > 5) return;
  const rect = renderer.domElement.getBoundingClientRect(); point.set((e.clientX - rect.left) / rect.width * 2 - 1, -(e.clientY - rect.top) / rect.height * 2 + 1);
  raycaster.setFromCamera(point, camera); const hit = raycaster.intersectObjects(pickTargets)[0];
  if (hit) { const { projectId, memberId } = hit.object.userData; if (memberId != null) emit('select-member', projectId, memberId); else emit('select-project', projectId); }
  pointerStart = null;
}
function lostContext(e) { e.preventDefault(); unavailable.value = true; emit('unavailable'); }
function renderLabels() {
  labels.render(scene, camera);
  // Semantic zoom: avoid overlapping names; all people remain in the inspector.
  const placed = [], projected = new THREE.Vector3();
  for (const label of [...labelObjects].sort((a, b) => b.userData.priority - a.userData.priority)) {
    label.getWorldPosition(projected).project(camera);
    const x = (projected.x + 1) * size.width / 2, y = (1 - projected.y) * size.height / 2;
    const w = label.element.offsetWidth || 90, h = label.element.offsetHeight || 40;
    const rect = { x: x - w / 2, y: y - h / 2, w, h };
    const overlaps = () => placed.some(r => rect.x < r.x + r.w + 5 && rect.x + rect.w + 5 > r.x && rect.y < r.y + r.h + 4 && rect.y + rect.h + 4 > r.y);
    // Keep the selected person's label visible above nearby project titles.
    let offset = 0;
    if (label.userData.priority === 3) while (overlaps() && offset < 100) { rect.y -= 10; offset += 10; }
    if (offset) label.element.style.transform += ` translateY(-${offset}px)`;
    const show = projected.z >= -1 && projected.z <= 1 && !overlaps();
    label.element.style.visibility = show ? 'visible' : 'hidden'; if (show) placed.push(rect);
  }
}
onMounted(() => {
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
    surface.value.append(renderer.domElement); renderer.domElement.tabIndex = 0;
    renderer.domElement.setAttribute('aria-label', props.english ? '3D canvas: drag to rotate, scroll to zoom, arrow keys to pan' : '3D 画布：拖动旋转，滚轮缩放，方向键平移');
    scene = new THREE.Scene(); camera = new THREE.PerspectiveCamera(38, 1, .1, 500);
    scene.add(new THREE.HemisphereLight('#ffffff', '#b6c4c0', 2.8));
    const sun = new THREE.DirectionalLight('#fffaf1', 3); sun.position.set(-12, 25, 15); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -40, right: 40, top: 40, bottom: -40, far: 100 }); sun.shadow.bias = -.001; scene.add(sun);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshBasicMaterial({ color: '#f4f7f9', toneMapped: false })); floor.rotation.x = -Math.PI / 2; scene.add(floor);
    const shadow = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.ShadowMaterial({ opacity: .12 })); shadow.rotation.x = -Math.PI / 2; shadow.position.y = .01; shadow.receiveShadow = true; scene.add(shadow);
    const grid = new THREE.GridHelper(120, 60, '#e0e7ec', '#e7edf1'); grid.position.y = .03; scene.add(grid);
    labels = new CSS2DRenderer(); labels.domElement.className = 'scene-labels'; surface.value.append(labels.domElement);
    controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true; controls.dampingFactor = .09; controls.minDistance = 8; controls.maxDistance = 180; controls.maxPolarAngle = Math.PI / 2.2; controls.screenSpacePanning = false; controls.autoRotateSpeed = .45;
    controls.listenToKeyEvents(renderer.domElement); controls.addEventListener('change', () => { dirty = true; });
    renderer.domElement.addEventListener('pointerdown', onPointerDown); renderer.domElement.addEventListener('pointerup', onPointerUp); renderer.domElement.addEventListener('webglcontextlost', lostContext);
    observer = new ResizeObserver(() => { size = { width: surface.value.clientWidth || 1, height: surface.value.clientHeight || 1 }; renderer.setSize(size.width, size.height); labels.setSize(size.width, size.height); camera.aspect = size.width / size.height; camera.updateProjectionMatrix(); dirty = true; }); observer.observe(surface.value);
    size = { width: surface.value.clientWidth || 1, height: surface.value.clientHeight || 1 }; rebuild(); fit();
    let previous = performance.now();
    function tick(now) {
      if (disposed) return; frame = requestAnimationFrame(tick);
      const elapsed = Math.min((now - previous) / 1000, .1); previous = now;
      if (document.hidden || unavailable.value) return;
      controls.update(elapsed);
      if (dirty || touring.value) { renderer.render(scene, camera); renderLabels(); dirty = false; }
    }
    frame = requestAnimationFrame(tick);
  } catch (error) { unavailable.value = true; emit('unavailable'); console.warn('Resource island renderer unavailable:', error.message); }
});
watch(() => [props.islands, props.selectedProject, props.selectedMember, props.spacing, props.showLinks, props.english], rebuild);
watch(() => props.islands.map(p => p.id).join('|'), () => { rebuild(); fit(); });
onBeforeUnmount(() => {
  disposed = true; cancelAnimationFrame(frame); observer?.disconnect(); controls?.dispose(); disposeContent();
  scene?.traverse(o => { o.geometry?.dispose(); o.material?.dispose?.(); });
  renderer?.domElement.removeEventListener('pointerdown', onPointerDown); renderer?.domElement.removeEventListener('pointerup', onPointerUp); renderer?.domElement.removeEventListener('webglcontextlost', lostContext);
  renderer?.dispose(); renderer?.forceContextLoss(); labels?.domElement.remove(); renderer?.domElement.remove();
});
defineExpose({ reset: fit, focus });
</script>

<style scoped>
.island-scene{position:relative;min-width:0;height:100%;min-height:560px;overflow:hidden;border-radius:10px;background:#f4f7f9}
.scene-surface{position:absolute;inset:0;touch-action:none}.scene-surface :deep(canvas){display:block;outline-offset:-3px;cursor:grab}.scene-surface :deep(canvas:active){cursor:grabbing}
.scene-surface :deep(.scene-labels){position:absolute;inset:0;pointer-events:none;overflow:hidden}
.scene-surface :deep(.island-label){pointer-events:auto;border:1px solid #e0e6e8;border-radius:8px;background:#fffffff2;color:#243746;box-shadow:0 3px 8px #263d4810;font:inherit;font-size:12px;display:flex;align-items:center;gap:5px;padding:5px 8px;max-width:200px;white-space:nowrap}
.scene-surface :deep(.island-label span){overflow:hidden;text-overflow:ellipsis;max-width:130px}
.scene-surface :deep(.island-label img){width:29px;height:29px;border-radius:50%;object-fit:cover}
.scene-surface :deep(.person-label){flex-direction:column;gap:2px;padding:5px 6px;max-width:86px;min-width:48px;font-size:11px;border-radius:7px}
.scene-surface :deep(.person-label span){max-width:74px}
.scene-surface :deep(.island-label b){font-size:11px;color:#397d8a}.scene-surface :deep(.island-label.is-risk b){color:#bd4f37}
.scene-surface :deep(.project-label){font-weight:650;font-size:13px;background:#edf5f6f2;border-color:#d1e4e6;max-width:240px}
.scene-surface :deep(.project-label span){max-width:180px}.scene-surface :deep(.is-selected){border-color:#257e91;box-shadow:0 0 0 2px #4da4b329}
.scene-hint{position:absolute;top:18px;left:18px;display:flex;align-items:center;gap:7px;color:#71838c;font-size:12px;pointer-events:none}
.scene-bottom{position:absolute;bottom:18px;left:18px;right:18px;display:flex;align-items:flex-end;justify-content:space-between;gap:12px;pointer-events:none}
.scene-map{width:130px;min-width:100px;background:#ffffffde;border:1px solid #dce5e9;border-radius:8px;padding:9px;pointer-events:auto}.scene-map>span{font-size:9px;color:#7b8d96;letter-spacing:1px}.map-points{height:68px;position:relative}.map-points button{position:absolute;width:13px;height:11px;border:1px solid #abc4c9;background:#d5e3e5;border-radius:4px;transform:translate(-50%,-50%);padding:0}.map-points button.selected{background:#388a9b;border-color:#16687c;box-shadow:0 0 0 3px #3b93a025}
.scene-tools{display:flex;align-items:center;background:#ffffffed;border:1px solid #dde6eb;border-radius:8px;padding:4px;box-shadow:0 4px 12px #263d4808;pointer-events:auto;flex-wrap:wrap}
.scene-tools button{display:flex;align-items:center;justify-content:center;gap:6px;padding:9px;border:0;border-radius:5px;background:transparent;color:#6c7e89;font-size:12px;min-height:36px}.scene-tools button:hover{background:#edf4f5}.scene-tools button.active{background:#256e80;color:white}.tool-divider{height:20px;border-left:1px solid #dce4e8;margin:0 3px}
.scene-message{position:absolute;left:20%;right:20%;top:42%;text-align:center;color:#6d7c87;line-height:1.8}.scene-unavailable{background:#edf3f5}
@media(max-width:700px){.scene-hint{font-size:10px;left:10px}.scene-bottom{left:10px;right:10px;bottom:10px}.scene-map{display:none}.scene-tools{margin-left:auto}.island-scene{min-height:450px}}
</style>
