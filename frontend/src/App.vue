<template>
  <div class="app-shell">
    <aside class="side-panel">
      <div class="brand">
        <div class="brand-mark">RA</div>
        <div>
          <strong>资源安排</strong>
          <span>团队容量工作台</span>
        </div>
      </div>

      <nav class="nav-list" aria-label="主导航">
        <button
          v-for="item in navigation"
          :key="item.id"
          type="button"
          :class="{ active: view === item.id }"
          @click="view = item.id"
        >
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="side-summary">
        <span>团队平均占用</span>
        <strong>{{ stats.average_load || 0 }}%</strong>
        <div class="mini-bar">
          <i :style="{ width: bounded(stats.average_load || 0) + '%' }"></i>
        </div>
        <small>{{ stats.allocated_hours || 0 }} / {{ stats.total_capacity_hours || 0 }} 小时</small>
      </div>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div>
          <h1>{{ viewTitle }}</h1>
          <p>集中管理同事、项目、任务占用、优先级和状态变化。</p>
        </div>
        <div class="top-actions">
          <label>
            <span>基准日期</span>
            <input v-model="currentDate" type="date" @change="loadData" />
          </label>
          <button class="icon-button primary" type="button" title="刷新" @click="loadData">
            <RefreshCw :size="18" />
            <span>刷新</span>
          </button>
        </div>
      </header>

      <section v-if="error" class="alert">
        <AlertTriangle :size="18" />
        <span>{{ error }}</span>
      </section>

      <section v-if="view === 'dashboard'" class="dashboard-view">
        <div class="metric-grid">
          <article v-for="metric in metrics" :key="metric.label" class="metric">
            <component :is="metric.icon" :size="20" />
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </article>
        </div>

        <section class="section-block">
          <div class="section-title">
            <div>
              <h2>人员负载</h2>
              <p>按当前基准日期计算正在占用的任务安排。</p>
            </div>
            <span>{{ sortedLoads.length }} 人</span>
          </div>
          <div class="load-grid">
            <article v-for="load in sortedLoads" :key="load.member_id" class="load-card" :class="load.risk">
              <div class="load-top">
                <div>
                  <strong>{{ load.name }}</strong>
                  <span>{{ load.role || '未填写角色' }} · {{ load.team || '未分组' }}</span>
                </div>
                <b>{{ Math.round(load.allocated_percent) }}%</b>
              </div>
              <div class="capacity-bar">
                <i :style="{ width: bounded(load.allocated_percent) + '%' }"></i>
              </div>
              <div class="load-meta">
                <span>{{ load.allocated_hours }} / {{ load.capacity_hours_week }} 小时</span>
                <span>{{ riskLabel(load.risk) }}</span>
              </div>
              <p>{{ load.project_names.length ? load.project_names.join('、') : '暂无当前项目' }}</p>
            </article>
          </div>
        </section>

        <div class="dashboard-split">
          <section class="section-block">
            <div class="section-title">
              <div>
                <h2>项目占用</h2>
                <p>查看每个项目当前牵涉的人数和总占用。</p>
              </div>
            </div>
            <div class="project-load-list">
              <article v-for="project in projectLoad" :key="project.project_id">
                <div>
                  <strong>{{ project.name }}</strong>
                  <span>{{ project.code || '无编码' }} · {{ priorityLabel(project.priority) }}</span>
                </div>
                <div class="project-meter">
                  <i :style="{ width: bounded(project.allocated_percent) + '%' }"></i>
                </div>
                <b>{{ project.people_count }} 人 · {{ Math.round(project.allocated_percent) }}%</b>
              </article>
            </div>
          </section>

          <section class="section-block">
            <div class="section-title">
              <div>
                <h2>近期变化</h2>
                <p>保留新增、调整和删除记录。</p>
              </div>
            </div>
            <div class="activity-list">
              <article v-for="item in activity" :key="item.id">
                <span>{{ formatDateTime(item.created_at) }}</span>
                <strong>{{ item.summary }}</strong>
              </article>
            </div>
          </section>
        </div>
      </section>

      <section v-if="view === 'assignments'" class="work-view">
        <form class="form-panel" @submit.prevent="saveAssignment">
          <div class="section-title compact">
            <div>
              <h2>{{ editingAssignmentId ? '编辑安排' : '新增安排' }}</h2>
              <p>记录一位同事在一个项目上的具体任务和占用。</p>
            </div>
          </div>

          <div class="form-grid">
            <label>
              <span>同事</span>
              <select v-model="assignmentForm.member_id" required>
                <option value="">选择同事</option>
                <option v-for="member in members" :key="member.id" :value="member.id">{{ member.name }}</option>
              </select>
            </label>
            <label>
              <span>项目</span>
              <select v-model="assignmentForm.project_id" required>
                <option value="">选择项目</option>
                <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.name }}</option>
              </select>
            </label>
            <label class="span-2">
              <span>任务/职责</span>
              <input v-model.trim="assignmentForm.task_name" required placeholder="例如：支付模块接口联调" />
            </label>
            <label>
              <span>占用比例</span>
              <input v-model.number="assignmentForm.allocation_percent" type="number" min="0" max="200" required />
            </label>
            <label>
              <span>优先级</span>
              <select v-model="assignmentForm.priority">
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </select>
            </label>
            <label>
              <span>状态</span>
              <select v-model="assignmentForm.status">
                <option value="planned">计划中</option>
                <option value="active">进行中</option>
                <option value="blocked">阻塞</option>
                <option value="done">完成</option>
                <option value="paused">暂停</option>
              </select>
            </label>
            <label>
              <span>开始日期</span>
              <input v-model="assignmentForm.start_date" type="date" required />
            </label>
            <label>
              <span>结束日期</span>
              <input v-model="assignmentForm.end_date" type="date" />
            </label>
            <label class="span-2">
              <span>备注</span>
              <textarea v-model.trim="assignmentForm.notes" rows="3"></textarea>
            </label>
          </div>

          <div class="form-actions">
            <button class="icon-button primary" type="submit">
              <Save :size="18" />
              <span>{{ editingAssignmentId ? '保存修改' : '新增安排' }}</span>
            </button>
            <button class="icon-button" type="button" @click="resetAssignmentForm">
              <RotateCcw :size="18" />
              <span>清空</span>
            </button>
          </div>
        </form>

        <section class="table-panel">
          <div class="section-title compact">
            <div>
              <h2>安排列表</h2>
              <p>搜索同事、项目或任务，快速定位安排。</p>
            </div>
            <div class="filters">
              <div class="search-box">
                <Search :size="17" />
                <input v-model.trim="search" placeholder="搜索同事、项目、任务" />
              </div>
              <select v-model="statusFilter">
                <option value="">全部状态</option>
                <option value="planned">计划中</option>
                <option value="active">进行中</option>
                <option value="blocked">阻塞</option>
                <option value="done">完成</option>
                <option value="paused">暂停</option>
              </select>
            </div>
          </div>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>同事</th>
                  <th>项目</th>
                  <th>任务</th>
                  <th>占用</th>
                  <th>状态</th>
                  <th>周期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in filteredAssignments" :key="item.id">
                  <td>
                    <strong>{{ item.member_name }}</strong>
                    <span>{{ item.member_role }}</span>
                  </td>
                  <td>{{ item.project_name }}</td>
                  <td>{{ item.task_name }}</td>
                  <td>{{ item.allocation_percent }}%</td>
                  <td><span class="status-pill" :class="item.status">{{ statusLabel(item.status) }}</span></td>
                  <td>{{ item.start_date }} - {{ item.end_date || '持续' }}</td>
                  <td>
                    <div class="row-actions">
                      <button class="square-button" type="button" title="编辑" @click="editAssignment(item)">
                        <Pencil :size="17" />
                      </button>
                      <button class="square-button danger" type="button" title="删除" @click="removeItem('assignments', item.id)">
                        <Trash2 :size="17" />
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </section>

      <section v-if="view === 'members'" class="work-view">
        <form class="form-panel" @submit.prevent="createMember">
          <div class="section-title compact">
            <div>
              <h2>新增同事</h2>
              <p>容量以每周小时为基准，安排占用按百分比折算。</p>
            </div>
          </div>
          <div class="form-grid">
            <label>
              <span>姓名</span>
              <input v-model.trim="memberForm.name" required />
            </label>
            <label>
              <span>角色</span>
              <input v-model.trim="memberForm.role" />
            </label>
            <label>
              <span>小组</span>
              <input v-model.trim="memberForm.team" />
            </label>
            <label>
              <span>周容量小时</span>
              <input v-model.number="memberForm.capacity_hours_week" type="number" min="1" />
            </label>
            <label>
              <span>状态</span>
              <select v-model="memberForm.status">
                <option value="available">可安排</option>
                <option value="busy">忙碌</option>
                <option value="away">暂离</option>
              </select>
            </label>
            <label class="span-2">
              <span>备注</span>
              <textarea v-model.trim="memberForm.notes" rows="3"></textarea>
            </label>
          </div>
          <div class="form-actions">
            <button class="icon-button primary" type="submit">
              <UserPlus :size="18" />
              <span>新增同事</span>
            </button>
          </div>
        </form>

        <div class="entity-grid">
          <article v-for="member in members" :key="member.id" class="entity-card">
            <div class="entity-head">
              <div>
                <strong>{{ member.name }}</strong>
                <span>{{ member.role || '未填写角色' }}</span>
              </div>
              <Users :size="20" />
            </div>
            <p>{{ member.team || '未分组' }} · {{ member.capacity_hours_week }} 小时/周 · {{ memberStatusLabel(member.status) }}</p>
            <small>{{ member.notes || '暂无备注' }}</small>
          </article>
        </div>
      </section>

      <section v-if="view === 'projects'" class="work-view">
        <form class="form-panel" @submit.prevent="createProject">
          <div class="section-title compact">
            <div>
              <h2>新增项目</h2>
              <p>用状态和优先级帮助安排排序与资源判断。</p>
            </div>
          </div>
          <div class="form-grid">
            <label>
              <span>项目名</span>
              <input v-model.trim="projectForm.name" required />
            </label>
            <label>
              <span>编码</span>
              <input v-model.trim="projectForm.code" />
            </label>
            <label>
              <span>负责人</span>
              <input v-model.trim="projectForm.owner" />
            </label>
            <label>
              <span>优先级</span>
              <select v-model="projectForm.priority">
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </select>
            </label>
            <label>
              <span>状态</span>
              <select v-model="projectForm.status">
                <option value="planning">规划中</option>
                <option value="active">进行中</option>
                <option value="paused">暂停</option>
                <option value="done">完成</option>
              </select>
            </label>
            <label>
              <span>开始日期</span>
              <input v-model="projectForm.start_date" type="date" />
            </label>
            <label>
              <span>结束日期</span>
              <input v-model="projectForm.end_date" type="date" />
            </label>
            <label class="span-2">
              <span>备注</span>
              <textarea v-model.trim="projectForm.notes" rows="3"></textarea>
            </label>
          </div>
          <div class="form-actions">
            <button class="icon-button primary" type="submit">
              <FolderPlus :size="18" />
              <span>新增项目</span>
            </button>
          </div>
        </form>

        <div class="entity-grid">
          <article v-for="project in projects" :key="project.id" class="entity-card">
            <div class="entity-head">
              <div>
                <strong>{{ project.name }}</strong>
                <span>{{ project.code || '无编码' }}</span>
              </div>
              <BriefcaseBusiness :size="20" />
            </div>
            <p>{{ project.owner || '未指定负责人' }} · {{ projectStatusLabel(project.status) }} · {{ priorityLabel(project.priority) }}</p>
            <small>{{ project.start_date || '未定' }} - {{ project.end_date || '持续' }}</small>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import AlertTriangle from "@lucide/vue/dist/esm/icons/triangle-alert.mjs";
import BarChart3 from "@lucide/vue/dist/esm/icons/chart-bar.mjs";
import BriefcaseBusiness from "@lucide/vue/dist/esm/icons/briefcase-business.mjs";
import CalendarRange from "@lucide/vue/dist/esm/icons/calendar-range.mjs";
import FolderKanban from "@lucide/vue/dist/esm/icons/folder-kanban.mjs";
import FolderPlus from "@lucide/vue/dist/esm/icons/folder-plus.mjs";
import Gauge from "@lucide/vue/dist/esm/icons/gauge.mjs";
import Pencil from "@lucide/vue/dist/esm/icons/pencil.mjs";
import RefreshCw from "@lucide/vue/dist/esm/icons/refresh-cw.mjs";
import RotateCcw from "@lucide/vue/dist/esm/icons/rotate-ccw.mjs";
import Save from "@lucide/vue/dist/esm/icons/save.mjs";
import Search from "@lucide/vue/dist/esm/icons/search.mjs";
import Trash2 from "@lucide/vue/dist/esm/icons/trash-2.mjs";
import UserPlus from "@lucide/vue/dist/esm/icons/user-plus.mjs";
import Users from "@lucide/vue/dist/esm/icons/users.mjs";

const today = new Date().toISOString().slice(0, 10);
const view = ref("dashboard");
const currentDate = ref(today);
const error = ref("");
const search = ref("");
const statusFilter = ref("");
const editingAssignmentId = ref(null);

const stats = ref({});
const members = ref([]);
const projects = ref([]);
const assignments = ref([]);
const memberLoad = ref([]);
const projectLoad = ref([]);
const activity = ref([]);

const navigation = [
  { id: "dashboard", label: "总览", icon: Gauge },
  { id: "assignments", label: "安排", icon: CalendarRange },
  { id: "members", label: "同事", icon: Users },
  { id: "projects", label: "项目", icon: FolderKanban },
];

const memberForm = reactive({
  name: "",
  role: "",
  team: "",
  capacity_hours_week: 40,
  status: "available",
  notes: "",
});

const projectForm = reactive({
  name: "",
  code: "",
  owner: "",
  status: "active",
  priority: "medium",
  start_date: "",
  end_date: "",
  notes: "",
});

const assignmentForm = reactive(defaultAssignmentForm());

const viewTitle = computed(() => {
  return {
    dashboard: "资源总览",
    assignments: "任务安排",
    members: "团队同事",
    projects: "项目组合",
  }[view.value];
});

const metrics = computed(() => [
  { label: "同事", value: stats.value.member_count || 0, icon: Users },
  { label: "进行中项目", value: stats.value.active_project_count || 0, icon: BriefcaseBusiness },
  { label: "进行中安排", value: stats.value.active_assignment_count || 0, icon: CalendarRange },
  {
    label: "延期/阻塞",
    value: (stats.value.overdue_assignment_count || 0) + (stats.value.blocked_assignment_count || 0),
    icon: AlertTriangle,
  },
  { label: "平均负载", value: `${stats.value.average_load || 0}%`, icon: BarChart3 },
]);

const sortedLoads = computed(() => {
  const order = { blocked: 0, overloaded: 1, tight: 2, underused: 3, normal: 4 };
  return [...memberLoad.value].sort((a, b) => {
    return (order[a.risk] ?? 9) - (order[b.risk] ?? 9) || b.allocated_percent - a.allocated_percent;
  });
});

const filteredAssignments = computed(() => {
  const needle = search.value.toLowerCase();
  return assignments.value.filter((item) => {
    const text = `${item.member_name} ${item.project_name} ${item.task_name}`.toLowerCase();
    return (!needle || text.includes(needle)) && (!statusFilter.value || item.status === statusFilter.value);
  });
});

function defaultAssignmentForm() {
  return {
    member_id: "",
    project_id: "",
    task_name: "",
    allocation_percent: 50,
    start_date: currentDate?.value || today,
    end_date: "",
    status: "active",
    priority: "medium",
    notes: "",
  };
}

async function request(path, options = {}) {
  error.value = "";
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.error || "请求失败");
  }
  return body;
}

async function loadData() {
  try {
    const data = await request(`/api/overview?date=${currentDate.value}`);
    stats.value = data.stats;
    members.value = data.members;
    projects.value = data.projects;
    assignments.value = data.assignments;
    memberLoad.value = data.member_load;
    projectLoad.value = data.project_load;
    activity.value = data.activity;
  } catch (err) {
    error.value = err.message;
  }
}

async function createMember() {
  try {
    await request("/api/members", { method: "POST", body: JSON.stringify(memberForm) });
    Object.assign(memberForm, { name: "", role: "", team: "", capacity_hours_week: 40, status: "available", notes: "" });
    await loadData();
  } catch (err) {
    error.value = err.message;
  }
}

async function createProject() {
  try {
    await request("/api/projects", { method: "POST", body: JSON.stringify(projectForm) });
    Object.assign(projectForm, {
      name: "",
      code: "",
      owner: "",
      status: "active",
      priority: "medium",
      start_date: "",
      end_date: "",
      notes: "",
    });
    await loadData();
  } catch (err) {
    error.value = err.message;
  }
}

async function saveAssignment() {
  try {
    const path = editingAssignmentId.value ? `/api/assignments/${editingAssignmentId.value}` : "/api/assignments";
    await request(path, {
      method: editingAssignmentId.value ? "PUT" : "POST",
      body: JSON.stringify(assignmentForm),
    });
    resetAssignmentForm();
    await loadData();
  } catch (err) {
    error.value = err.message;
  }
}

function editAssignment(item) {
  editingAssignmentId.value = item.id;
  Object.assign(assignmentForm, {
    member_id: item.member_id,
    project_id: item.project_id,
    task_name: item.task_name,
    allocation_percent: item.allocation_percent,
    start_date: item.start_date,
    end_date: item.end_date || "",
    status: item.status,
    priority: item.priority,
    notes: item.notes || "",
  });
  view.value = "assignments";
}

function resetAssignmentForm() {
  editingAssignmentId.value = null;
  Object.assign(assignmentForm, defaultAssignmentForm());
}

async function removeItem(type, id) {
  if (!window.confirm("确认删除这条记录？关联数据可能会一起删除。")) {
    return;
  }
  try {
    await request(`/api/${type}/${id}`, { method: "DELETE" });
    await loadData();
  } catch (err) {
    error.value = err.message;
  }
}

function bounded(value) {
  return Math.max(0, Math.min(Number(value) || 0, 100));
}

function formatDateTime(value) {
  return value ? value.replace("T", " ").slice(0, 16) : "";
}

function riskLabel(value) {
  return {
    blocked: "有阻塞",
    overloaded: "超负载",
    tight: "接近满载",
    underused: "可继续安排",
    normal: "正常",
  }[value] || value;
}

function statusLabel(value) {
  return {
    planned: "计划中",
    active: "进行中",
    blocked: "阻塞",
    done: "完成",
    paused: "暂停",
  }[value] || value;
}

function memberStatusLabel(value) {
  return {
    available: "可安排",
    busy: "忙碌",
    away: "暂离",
  }[value] || value;
}

function projectStatusLabel(value) {
  return {
    planning: "规划中",
    active: "进行中",
    paused: "暂停",
    done: "完成",
  }[value] || value;
}

function priorityLabel(value) {
  return {
    high: "高优先级",
    medium: "中优先级",
    low: "低优先级",
  }[value] || value;
}

onMounted(loadData);
</script>
