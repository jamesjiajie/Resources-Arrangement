<template>
  <div class="app-shell">
    <aside class="side-panel">
      <div class="brand">
        <div class="brand-mark">RA</div>
        <div>
          <strong>{{ t.appName }}</strong>
          <span>{{ t.appTagline }}</span>
        </div>
      </div>

      <nav class="nav-list" :aria-label="t.mainNav">
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
        <span>{{ t.teamAverageLoad }}</span>
        <strong>{{ stats.average_load || 0 }}%</strong>
        <div class="mini-bar">
          <i :style="{ width: bounded(stats.average_load || 0) + '%' }"></i>
        </div>
        <small>{{ stats.allocated_hours || 0 }} / {{ stats.total_capacity_hours || 0 }} {{ t.hours }}</small>
      </div>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div>
          <h1>{{ viewTitle }}</h1>
          <p>{{ viewDescription }}</p>
        </div>
        <div class="top-actions">
          <button class="language-toggle" type="button" :title="t.switchLanguage" @click="toggleLanguage">
            <Languages :size="17" />
            <span>{{ language === "zh" ? "EN" : "中" }}</span>
          </button>
          <label>
            <span>{{ t.baseDate }}</span>
            <input v-model="currentDate" type="date" @change="loadData" />
          </label>
          <button class="icon-button primary" type="button" :title="t.refresh" @click="loadData">
            <RefreshCw :size="18" />
            <span>{{ t.refresh }}</span>
          </button>
        </div>
      </header>

      <section v-if="error" class="alert">
        <AlertTriangle :size="18" />
        <span>{{ error }}</span>
      </section>

      <ResourceSandbox
        v-if="view === 'sandbox'"
        :language="language"
        :current-date="currentDate"
        :members="members"
        :assignments="assignments"
        :member-load="memberLoad"
      />

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
              <h2>{{ t.peopleLoadTitle }}</h2>
              <p>{{ t.peopleLoadDescription }}</p>
            </div>
            <span>{{ sortedLoads.length }} {{ t.peopleUnit }}</span>
          </div>
          <div class="load-grid">
            <article v-for="load in sortedLoads" :key="load.member_id" class="load-card" :class="load.risk">
              <div class="load-top">
                <div>
                  <strong>{{ load.name }}</strong>
                  <span>{{ load.role || t.noRole }} · {{ load.team || t.noTeam }}</span>
                </div>
                <b>{{ Math.round(load.allocated_percent) }}%</b>
              </div>
              <div class="capacity-bar">
                <i :style="{ width: bounded(load.allocated_percent) + '%' }"></i>
              </div>
              <div class="load-meta">
                <span>{{ load.allocated_hours }} / {{ load.capacity_hours_week }} {{ t.hours }}</span>
                <span>{{ riskLabel(load.risk) }}</span>
              </div>
              <p>{{ load.project_names.length ? load.project_names.join(language === "zh" ? "、" : ", ") : t.noCurrentProjects }}</p>
            </article>
          </div>
        </section>

        <div class="dashboard-split">
          <section class="section-block">
            <div class="section-title">
              <div>
                <h2>{{ t.projectLoadTitle }}</h2>
                <p>{{ t.projectLoadDescription }}</p>
              </div>
            </div>
            <div class="project-load-list">
              <article v-for="project in projectLoad" :key="project.project_id">
                <div>
                  <strong>{{ project.name }}</strong>
                  <span>{{ project.code || t.noCode }} · {{ priorityLabel(project.priority) }}</span>
                </div>
                <div class="project-meter">
                  <i :style="{ width: bounded(project.allocated_percent) + '%' }"></i>
                </div>
                <b>{{ project.people_count }} {{ t.peopleUnit }} · {{ Math.round(project.allocated_percent) }}%</b>
              </article>
            </div>
          </section>

          <section class="section-block">
            <div class="section-title">
              <div>
                <h2>{{ t.recentActivityTitle }}</h2>
                <p>{{ t.activityDescription }}</p>
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
              <h2>{{ editingAssignmentId ? t.editAssignment : t.newAssignment }}</h2>
              <p>{{ t.assignmentFormDescription }}</p>
            </div>
          </div>

          <div class="form-grid">
            <label>
              <span>{{ t.member }}</span>
              <select v-model="assignmentForm.member_id" required>
                <option value="">{{ t.selectMember }}</option>
                <option v-for="member in members" :key="member.id" :value="member.id">{{ member.name }}</option>
              </select>
            </label>
            <label>
              <span>{{ t.project }}</span>
              <select v-model="assignmentForm.project_id" required>
                <option value="">{{ t.selectProject }}</option>
                <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.name }}</option>
              </select>
            </label>
            <label class="span-2">
              <span>{{ t.projectPmItem }}</span>
              <input v-model.trim="assignmentForm.project_pm_item" :placeholder="t.projectPmItemPlaceholder" />
            </label>
            <label class="span-2">
              <span>{{ t.taskName }}</span>
              <input v-model.trim="assignmentForm.task_name" required :placeholder="t.taskPlaceholder" />
            </label>
            <label>
              <span>{{ t.allocationPercent }}</span>
              <input v-model.number="assignmentForm.allocation_percent" type="number" min="0" max="200" required />
            </label>
            <label>
              <span>{{ t.priority }}</span>
              <select v-model="assignmentForm.priority">
                <option value="high">{{ t.high }}</option>
                <option value="medium">{{ t.medium }}</option>
                <option value="low">{{ t.low }}</option>
              </select>
            </label>
            <label>
              <span>{{ t.status }}</span>
              <select v-model="assignmentForm.status">
                <option value="planned">{{ t.planned }}</option>
                <option value="active">{{ t.active }}</option>
                <option value="blocked">{{ t.blocked }}</option>
                <option value="done">{{ t.done }}</option>
                <option value="paused">{{ t.paused }}</option>
              </select>
            </label>
            <label>
              <span>{{ t.startDate }}</span>
              <input v-model="assignmentForm.start_date" type="date" required />
            </label>
            <label>
              <span>{{ t.endDate }}</span>
              <input v-model="assignmentForm.end_date" type="date" />
            </label>
            <label class="span-2">
              <span>{{ t.notes }}</span>
              <textarea v-model.trim="assignmentForm.notes" rows="3"></textarea>
            </label>
          </div>

          <div class="form-actions">
            <button class="icon-button primary" type="submit">
              <Save :size="18" />
              <span>{{ editingAssignmentId ? t.saveChanges : t.newAssignment }}</span>
            </button>
            <button class="icon-button" type="button" @click="resetAssignmentForm">
              <RotateCcw :size="18" />
              <span>{{ t.clear }}</span>
            </button>
          </div>
        </form>

        <section class="table-panel">
          <div class="section-title compact">
            <div>
              <h2>{{ t.assignmentList }}</h2>
              <p>{{ t.assignmentListDescription }}</p>
            </div>
            <div class="filters">
              <div class="search-box">
                <Search :size="17" />
                <input v-model.trim="search" :placeholder="t.searchPlaceholder" />
              </div>
              <select v-model="statusFilter">
                <option value="">{{ t.allStatuses }}</option>
                <option value="planned">{{ t.planned }}</option>
                <option value="active">{{ t.active }}</option>
                <option value="blocked">{{ t.blocked }}</option>
                <option value="done">{{ t.done }}</option>
                <option value="paused">{{ t.paused }}</option>
              </select>
            </div>
          </div>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{{ t.member }}</th>
                  <th>{{ t.project }}</th>
                  <th>{{ t.projectPmItem }}</th>
                  <th>{{ t.task }}</th>
                  <th>{{ t.allocation }}</th>
                  <th>{{ t.status }}</th>
                  <th>{{ t.period }}</th>
                  <th>{{ t.actions }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in filteredAssignments" :key="item.id">
                  <td>
                    <strong>{{ item.member_name }}</strong>
                    <span>{{ item.member_role }}</span>
                  </td>
                  <td>{{ item.project_name }}</td>
                  <td>{{ item.project_pm_item || t.notSet }}</td>
                  <td>{{ item.task_name }}</td>
                  <td>{{ item.allocation_percent }}%</td>
                  <td><span class="status-pill" :class="item.status">{{ statusLabel(item.status) }}</span></td>
                  <td>{{ item.start_date }} - {{ item.end_date || t.ongoing }}</td>
                  <td>
                    <div class="row-actions">
                      <button class="square-button" type="button" :title="t.edit" @click="editAssignment(item)">
                        <Pencil :size="17" />
                      </button>
                      <button class="square-button danger" type="button" :title="t.delete" @click="removeItem('assignments', item.id)">
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
              <h2>{{ t.newMember }}</h2>
              <p>{{ t.memberFormDescription }}</p>
            </div>
          </div>
          <div class="form-grid">
            <label>
              <span>{{ t.name }}</span>
              <input v-model.trim="memberForm.name" required />
            </label>
            <label>
              <span>{{ t.role }}</span>
              <input v-model.trim="memberForm.role" />
            </label>
            <label>
              <span>{{ t.team }}</span>
              <input v-model.trim="memberForm.team" />
            </label>
            <label>
              <span>{{ t.weeklyCapacityHours }}</span>
              <input v-model.number="memberForm.capacity_hours_week" type="number" min="1" />
            </label>
            <label>
              <span>{{ t.status }}</span>
              <select v-model="memberForm.status">
                <option value="available">{{ t.available }}</option>
                <option value="busy">{{ t.busy }}</option>
                <option value="away">{{ t.away }}</option>
              </select>
            </label>
            <label class="span-2">
              <span>{{ t.notes }}</span>
              <textarea v-model.trim="memberForm.notes" rows="3"></textarea>
            </label>
          </div>
          <div class="form-actions">
            <button class="icon-button primary" type="submit">
              <UserPlus :size="18" />
              <span>{{ t.newMember }}</span>
            </button>
          </div>
        </form>

        <div class="entity-grid">
          <article v-for="member in members" :key="member.id" class="entity-card">
            <div class="entity-head">
              <div>
                <strong>{{ member.name }}</strong>
                <span>{{ member.role || t.noRole }}</span>
              </div>
              <Users :size="20" />
            </div>
            <p>{{ member.team || t.noTeam }} · {{ member.capacity_hours_week }} {{ t.hoursPerWeek }} · {{ memberStatusLabel(member.status) }}</p>
            <small>{{ member.notes || t.noNotes }}</small>
          </article>
        </div>
      </section>

      <section v-if="view === 'projects'" class="work-view">
        <form class="form-panel" @submit.prevent="createProject">
          <div class="section-title compact">
            <div>
              <h2>{{ t.newProject }}</h2>
              <p>{{ t.projectFormDescription }}</p>
            </div>
          </div>
          <div class="form-grid">
            <label>
              <span>{{ t.projectName }}</span>
              <input v-model.trim="projectForm.name" required />
            </label>
            <label>
              <span>{{ t.code }}</span>
              <input v-model.trim="projectForm.code" />
            </label>
            <label>
              <span>{{ t.owner }}</span>
              <input v-model.trim="projectForm.owner" />
            </label>
            <label>
              <span>{{ t.priority }}</span>
              <select v-model="projectForm.priority">
                <option value="high">{{ t.high }}</option>
                <option value="medium">{{ t.medium }}</option>
                <option value="low">{{ t.low }}</option>
              </select>
            </label>
            <label>
              <span>{{ t.status }}</span>
              <select v-model="projectForm.status">
                <option value="planning">{{ t.planning }}</option>
                <option value="active">{{ t.active }}</option>
                <option value="paused">{{ t.paused }}</option>
                <option value="done">{{ t.done }}</option>
              </select>
            </label>
            <label>
              <span>{{ t.startDate }}</span>
              <input v-model="projectForm.start_date" type="date" />
            </label>
            <label>
              <span>{{ t.endDate }}</span>
              <input v-model="projectForm.end_date" type="date" />
            </label>
            <label class="span-2">
              <span>{{ t.notes }}</span>
              <textarea v-model.trim="projectForm.notes" rows="3"></textarea>
            </label>
          </div>
          <div class="form-actions">
            <button class="icon-button primary" type="submit">
              <FolderPlus :size="18" />
              <span>{{ t.newProject }}</span>
            </button>
          </div>
        </form>

        <div class="entity-grid">
          <article v-for="project in projects" :key="project.id" class="entity-card">
            <div class="entity-head">
              <div>
                <strong>{{ project.name }}</strong>
                <span>{{ project.code || t.noCode }}</span>
              </div>
              <BriefcaseBusiness :size="20" />
            </div>
            <p>{{ project.owner || t.noOwner }} · {{ projectStatusLabel(project.status) }} · {{ priorityLabel(project.priority) }}</p>
            <small>{{ project.start_date || t.notSet }} - {{ project.end_date || t.ongoing }}</small>
          </article>
        </div>
      </section>

      <section v-if="view === 'tasks'" class="work-view">
        <div class="metric-grid task-metrics">
          <article v-for="metric in taskMetrics" :key="metric.label" class="metric">
            <component :is="metric.icon" :size="20" />
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </article>
        </div>

        <form class="form-panel" @submit.prevent="saveLongTermTask">
          <div class="section-title compact">
            <div>
              <h2>{{ editingTaskId ? t.editLongTermTask : t.newLongTermTask }}</h2>
              <p>{{ t.longTermTaskFormDescription }}</p>
            </div>
          </div>
          <div class="form-grid">
            <label class="span-2">
              <span>{{ t.taskTitle }}</span>
              <input v-model.trim="taskForm.title" required :placeholder="t.taskTitlePlaceholder" />
            </label>
            <label>
              <span>{{ t.owner }}</span>
              <input v-model.trim="taskForm.owner" :placeholder="t.ownerPlaceholder" />
            </label>
            <label>
              <span>{{ t.category }}</span>
              <input v-model.trim="taskForm.category" :placeholder="t.categoryPlaceholder" />
            </label>
            <label>
              <span>{{ t.status }}</span>
              <select v-model="taskForm.status">
                <option value="planned">{{ t.planned }}</option>
                <option value="active">{{ t.active }}</option>
                <option value="blocked">{{ t.blocked }}</option>
                <option value="done">{{ t.done }}</option>
                <option value="archived">{{ t.archived }}</option>
              </select>
            </label>
            <label>
              <span>{{ t.priority }}</span>
              <select v-model="taskForm.priority">
                <option value="high">{{ t.high }}</option>
                <option value="medium">{{ t.medium }}</option>
                <option value="low">{{ t.low }}</option>
              </select>
            </label>
            <label>
              <span>{{ t.progress }}</span>
              <input v-model.number="taskForm.progress" type="number" min="0" max="100" />
            </label>
            <label>
              <span>{{ t.startDate }}</span>
              <input v-model="taskForm.start_date" type="date" />
            </label>
            <label>
              <span>{{ t.targetDate }}</span>
              <input v-model="taskForm.target_date" type="date" />
            </label>
            <label class="span-2">
              <span>{{ t.notes }}</span>
              <textarea v-model.trim="taskForm.notes" rows="3"></textarea>
            </label>
          </div>
          <div class="form-actions">
            <button class="icon-button primary" type="submit">
              <Save :size="18" />
              <span>{{ editingTaskId ? t.saveChanges : t.newLongTermTask }}</span>
            </button>
            <button class="icon-button" type="button" @click="resetTaskForm">
              <RotateCcw :size="18" />
              <span>{{ t.clear }}</span>
            </button>
          </div>
        </form>

        <section class="table-panel">
          <div class="section-title compact">
            <div>
              <h2>{{ t.longTermTaskList }}</h2>
              <p>{{ t.longTermTaskListDescription }}</p>
            </div>
            <div class="filters">
              <div class="search-box">
                <Search :size="17" />
                <input v-model.trim="taskSearch" :placeholder="t.taskSearchPlaceholder" />
              </div>
              <select v-model="taskStatusFilter">
                <option value="">{{ t.allStatuses }}</option>
                <option value="planned">{{ t.planned }}</option>
                <option value="active">{{ t.active }}</option>
                <option value="blocked">{{ t.blocked }}</option>
                <option value="done">{{ t.done }}</option>
                <option value="archived">{{ t.archived }}</option>
              </select>
            </div>
          </div>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{{ t.task }}</th>
                  <th>{{ t.owner }}</th>
                  <th>{{ t.status }}</th>
                  <th>{{ t.priority }}</th>
                  <th>{{ t.progress }}</th>
                  <th>{{ t.period }}</th>
                  <th>{{ t.actions }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in filteredLongTermTasks" :key="item.id">
                  <td>
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.category || t.noCategory }}</span>
                  </td>
                  <td>{{ item.owner || t.noOwner }}</td>
                  <td><span class="status-pill" :class="item.status">{{ statusLabel(item.status) }}</span></td>
                  <td>{{ priorityLabel(item.priority) }}</td>
                  <td>
                    <div class="progress-cell">
                      <div class="capacity-bar">
                        <i :style="{ width: bounded(item.progress) + '%' }"></i>
                      </div>
                      <b>{{ item.progress }}%</b>
                    </div>
                  </td>
                  <td>{{ item.start_date || t.notSet }} - {{ item.target_date || t.ongoing }}</td>
                  <td>
                    <div class="row-actions">
                      <button class="square-button" type="button" :title="t.edit" @click="editLongTermTask(item)">
                        <Pencil :size="17" />
                      </button>
                      <button class="square-button" type="button" :title="t.markDone" @click="completeLongTermTask(item)">
                        <Check :size="17" />
                      </button>
                      <button class="square-button danger" type="button" :title="t.delete" @click="removeLongTermTask(item.id)">
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

      <section v-if="view === 'imports'" class="work-view">
        <section class="form-panel">
          <div class="section-title compact">
            <div>
              <h2>{{ t.excelImportTitle }}</h2>
              <p>{{ t.excelImportDescription }}</p>
            </div>
          </div>

          <div class="import-layout">
            <label class="file-picker">
              <span>{{ t.excelFile }}</span>
              <input type="file" accept=".xlsx" @change="handleImportFile" />
            </label>
            <label>
              <span>{{ t.importMode }}</span>
              <select v-model="importMode">
                <option value="append">{{ t.importAppend }}</option>
                <option value="replace_month">{{ t.importReplaceMonth }}</option>
                <option value="update_catalog">{{ t.importUpdateCatalog }}</option>
              </select>
            </label>
          </div>

          <div class="form-actions">
            <button class="icon-button primary" type="button" :disabled="!importFile || importing" @click="previewImport">
              <FileUp :size="18" />
              <span>{{ importing ? t.importWorking : t.previewImport }}</span>
            </button>
            <button class="icon-button" type="button" :disabled="!importPreview || importing" @click="applyImport">
              <Save :size="18" />
              <span>{{ t.applyImport }}</span>
            </button>
          </div>
        </section>

        <section v-if="importPreview" class="section-block">
          <div class="section-title">
            <div>
              <h2>{{ t.importPreview }}</h2>
              <p>{{ importPreview.filename }} · {{ importPreview.sheet_name }} · {{ importPreview.resource_month }}</p>
            </div>
          </div>
          <div class="metric-grid import-metrics">
            <article class="metric">
              <Users :size="20" />
              <span>{{ t.members }}</span>
              <strong>{{ importPreview.stats.member_count }}</strong>
            </article>
            <article class="metric">
              <FolderKanban :size="20" />
              <span>{{ t.projects }}</span>
              <strong>{{ importPreview.stats.project_count }}</strong>
            </article>
            <article class="metric">
              <CalendarRange :size="20" />
              <span>{{ t.assignments }}</span>
              <strong>{{ importPreview.stats.assignment_count }}</strong>
            </article>
            <article class="metric">
              <AlertTriangle :size="20" />
              <span>{{ t.importIssues }}</span>
              <strong>{{ importPreview.stats.issue_count }}</strong>
            </article>
          </div>

          <div v-if="importPreview.issues.length" class="issue-list">
            <article v-for="issue in importPreview.issues" :key="`${issue.row}-${issue.message}`">
              <strong>{{ issue.row ? `Row ${issue.row}` : issue.level }}</strong>
              <span>{{ issue.message }}</span>
            </article>
          </div>

          <div class="table-wrap">
            <table class="preview-table">
              <thead>
                <tr>
                  <th>{{ t.sourceRow }}</th>
                  <th>{{ t.member }}</th>
                  <th>{{ t.project }}</th>
                  <th>{{ t.projectPmItem }}</th>
                  <th>{{ t.task }}</th>
                  <th>{{ t.stage }}</th>
                  <th>{{ t.allocation }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in previewAssignments" :key="item.source_key">
                  <td>{{ item.row }}</td>
                  <td>{{ item.member_name }}</td>
                  <td>{{ item.project_name }}</td>
                  <td>{{ item.project_pm_item || t.notSet }}</td>
                  <td>{{ item.task_name }}</td>
                  <td>{{ item.stage }}</td>
                  <td>{{ item.allocation_percent }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-if="importResult" class="section-block">
          <div class="section-title compact">
            <div>
              <h2>{{ t.importComplete }}</h2>
              <p>
                {{ t.importCreatedAssignments }} {{ importResult.created_assignments }} ·
                {{ t.importCreatedMembers }} {{ importResult.created_members }} ·
                {{ t.importCreatedProjects }} {{ importResult.created_projects }}
              </p>
            </div>
          </div>
        </section>
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
import Check from "@lucide/vue/dist/esm/icons/check.mjs";
import FileUp from "@lucide/vue/dist/esm/icons/file-up.mjs";
import FolderKanban from "@lucide/vue/dist/esm/icons/folder-kanban.mjs";
import FolderPlus from "@lucide/vue/dist/esm/icons/folder-plus.mjs";
import Gauge from "@lucide/vue/dist/esm/icons/gauge.mjs";
import Languages from "@lucide/vue/dist/esm/icons/languages.mjs";
import ListChecks from "@lucide/vue/dist/esm/icons/list-checks.mjs";
import Network from "@lucide/vue/dist/esm/icons/network.mjs";
import Pencil from "@lucide/vue/dist/esm/icons/pencil.mjs";
import RefreshCw from "@lucide/vue/dist/esm/icons/refresh-cw.mjs";
import RotateCcw from "@lucide/vue/dist/esm/icons/rotate-ccw.mjs";
import Save from "@lucide/vue/dist/esm/icons/save.mjs";
import Search from "@lucide/vue/dist/esm/icons/search.mjs";
import Trash2 from "@lucide/vue/dist/esm/icons/trash-2.mjs";
import UserPlus from "@lucide/vue/dist/esm/icons/user-plus.mjs";
import Users from "@lucide/vue/dist/esm/icons/users.mjs";
import ResourceSandbox from "./components/ResourceSandbox.vue";

const today = new Date().toISOString().slice(0, 10);
const savedLanguage = window.localStorage.getItem("language");
const language = ref(savedLanguage === "en" ? "en" : "zh");
const view = ref("dashboard");
const currentDate = ref(today);
const error = ref("");
const search = ref("");
const statusFilter = ref("");
const taskSearch = ref("");
const taskStatusFilter = ref("");
const editingAssignmentId = ref(null);
const editingTaskId = ref(null);
const importFile = ref(null);
const importPreview = ref(null);
const importMode = ref("replace_month");
const importResult = ref(null);
const importing = ref(false);

const stats = ref({});
const members = ref([]);
const projects = ref([]);
const assignments = ref([]);
const longTermTasks = ref([]);
const memberLoad = ref([]);
const projectLoad = ref([]);
const activity = ref([]);

const translations = {
  zh: {
    appName: "资源安排",
    appTagline: "团队容量工作台",
    mainNav: "主导航",
    teamAverageLoad: "团队平均占用",
    hours: "小时",
    hoursPerWeek: "小时/周",
    topbarDescription: "集中管理同事、项目、任务占用、优先级和状态变化。",
    switchLanguage: "切换语言",
    baseDate: "基准日期",
    refresh: "刷新",
    dashboard: "总览",
    assignments: "安排",
    members: "同事",
    projects: "项目",
    tasks: "任务管理",
    sandbox: "资源沙盘",
    imports: "导入",
    dashboardTitle: "资源总览",
    assignmentsTitle: "任务安排",
    membersTitle: "团队同事",
    projectsTitle: "项目组合",
    tasksTitle: "长期任务管理",
    sandboxTitle: "关系脉络图",
    sandboxDescription: "一眼看清谁在做什么、谁超负荷、哪里被阻塞。",
    memberMetric: "同事",
    activeProjectsMetric: "进行中项目",
    activeAssignmentsMetric: "进行中安排",
    blockedMetric: "延期/阻塞",
    averageLoadMetric: "平均负载",
    peopleLoadTitle: "人员负载",
    peopleLoadDescription: "按当前基准日期计算正在占用的任务安排。",
    peopleUnit: "人",
    noRole: "未填写角色",
    noTeam: "未分组",
    noCurrentProjects: "暂无当前项目",
    projectLoadTitle: "项目占用",
    projectLoadDescription: "查看每个项目当前牵涉的人数和总占用。",
    noCode: "无编码",
    recentActivityTitle: "近期变化",
    activityDescription: "保留新增、调整和删除记录。",
    editAssignment: "编辑安排",
    newAssignment: "新增安排",
    assignmentFormDescription: "记录一位同事在一个项目上的具体任务和占用。",
    member: "同事",
    project: "项目",
    selectMember: "选择同事",
    selectProject: "选择项目",
    taskName: "任务/职责",
    taskPlaceholder: "例如：支付模块接口联调",
    projectPmItem: "项目 PM",
    projectPmItemPlaceholder: "例如：张三",
    allocationPercent: "占用比例",
    priority: "优先级",
    high: "高",
    medium: "中",
    low: "低",
    status: "状态",
    planned: "计划中",
    active: "进行中",
    blocked: "阻塞",
    done: "完成",
    paused: "暂停",
    archived: "已归档",
    startDate: "开始日期",
    endDate: "结束日期",
    targetDate: "目标日期",
    progress: "进度",
    notes: "备注",
    saveChanges: "保存修改",
    clear: "清空",
    assignmentList: "安排列表",
    assignmentListDescription: "搜索同事、项目、项目 PM 或任务，快速定位安排。",
    searchPlaceholder: "搜索同事、项目、项目 PM、任务",
    allStatuses: "全部状态",
    task: "任务",
    allocation: "占用",
    period: "周期",
    actions: "操作",
    ongoing: "持续",
    edit: "编辑",
    delete: "删除",
    newMember: "新增同事",
    memberFormDescription: "容量以每周小时为基准，安排占用按百分比折算。",
    name: "姓名",
    role: "角色",
    team: "小组",
    weeklyCapacityHours: "周容量小时",
    available: "可安排",
    busy: "忙碌",
    away: "暂离",
    noNotes: "暂无备注",
    newProject: "新增项目",
    projectFormDescription: "用状态和优先级帮助安排排序与资源判断。",
    projectName: "项目名",
    code: "编码",
    owner: "负责人",
    planning: "规划中",
    noOwner: "未指定负责人",
    ownerPlaceholder: "例如：赵宁",
    notSet: "未定",
    category: "分类",
    categoryPlaceholder: "例如：技术债 / 流程改进",
    noCategory: "未分类",
    taskTitle: "任务标题",
    taskTitlePlaceholder: "例如：建立季度资源预测机制",
    editLongTermTask: "编辑长期任务",
    newLongTermTask: "新增长期任务",
    longTermTaskFormDescription: "跟踪跨周或跨月推进的事项，不计入短期资源占用。",
    longTermTaskList: "长期任务列表",
    longTermTaskListDescription: "按状态、负责人、分类和标题查找长期事项。",
    taskSearchPlaceholder: "搜索任务、负责人、分类",
    markDone: "标记完成",
    longTermActiveMetric: "进行中任务",
    longTermBlockedMetric: "阻塞任务",
    longTermDueMetric: "7 天内到期",
    longTermDoneMetric: "已完成",
    requestFailed: "请求失败",
    deleteConfirm: "确认删除这条记录？关联数据可能会一起删除。",
    excelImportTitle: "Excel 导入",
    excelImportDescription: "上传资源安排表，先预览人员、项目和安排，再确认写入 portal。",
    excelFile: "Excel 文件",
    importMode: "导入模式",
    importAppend: "追加导入",
    importReplaceMonth: "替换同月份导入记录",
    importUpdateCatalog: "更新人员/项目并替换安排",
    previewImport: "解析预览",
    applyImport: "确认导入",
    importWorking: "处理中",
    importPreview: "导入预览",
    importIssues: "提示",
    sourceRow: "来源行",
    stage: "阶段",
    importComplete: "导入完成",
    importCreatedAssignments: "新增安排",
    importCreatedMembers: "新增同事",
    importCreatedProjects: "新增项目",
    risks: {
      blocked: "有阻塞",
      overloaded: "超负载",
      tight: "接近满载",
      underused: "可继续安排",
      normal: "正常",
    },
    statuses: {
      planned: "计划中",
      active: "进行中",
      blocked: "阻塞",
      done: "完成",
      paused: "暂停",
      archived: "已归档",
    },
    memberStatuses: {
      available: "可安排",
      busy: "忙碌",
      away: "暂离",
    },
    projectStatuses: {
      planning: "规划中",
      active: "进行中",
      paused: "暂停",
      done: "完成",
    },
    priorities: {
      high: "高优先级",
      medium: "中优先级",
      low: "低优先级",
    },
  },
  en: {
    appName: "Resource Planner",
    appTagline: "Team capacity workspace",
    mainNav: "Main navigation",
    teamAverageLoad: "Average team load",
    hours: "hours",
    hoursPerWeek: "hours/week",
    topbarDescription: "Manage teammates, projects, task allocation, priority, and status changes in one place.",
    switchLanguage: "Switch language",
    baseDate: "Base date",
    refresh: "Refresh",
    dashboard: "Overview",
    assignments: "Assignments",
    members: "Members",
    projects: "Projects",
    tasks: "Tasks",
    sandbox: "Resource Sandbox",
    imports: "Import",
    dashboardTitle: "Resource Overview",
    assignmentsTitle: "Task Assignments",
    membersTitle: "Team Members",
    projectsTitle: "Project Portfolio",
    tasksTitle: "Long-Term Task Management",
    sandboxTitle: "Relationship Map",
    sandboxDescription: "See ownership, workload, and blocked work at a glance.",
    memberMetric: "Members",
    activeProjectsMetric: "Active Projects",
    activeAssignmentsMetric: "Active Assignments",
    blockedMetric: "Overdue / Blocked",
    averageLoadMetric: "Average Load",
    peopleLoadTitle: "People Load",
    peopleLoadDescription: "Calculated from active assignments on the selected base date.",
    peopleUnit: "people",
    noRole: "No role",
    noTeam: "No team",
    noCurrentProjects: "No current projects",
    projectLoadTitle: "Project Load",
    projectLoadDescription: "See current headcount and total allocation for each project.",
    noCode: "No code",
    recentActivityTitle: "Recent Activity",
    activityDescription: "Keeps records of additions, changes, and deletions.",
    editAssignment: "Edit Assignment",
    newAssignment: "New Assignment",
    assignmentFormDescription: "Record one teammate's task and allocation on a project.",
    member: "Member",
    project: "Project",
    selectMember: "Select member",
    selectProject: "Select project",
    taskName: "Task / Responsibility",
    taskPlaceholder: "Example: Payment API integration",
    projectPmItem: "Project PM",
    projectPmItemPlaceholder: "Example: Jordan Lee",
    allocationPercent: "Allocation percent",
    priority: "Priority",
    high: "High",
    medium: "Medium",
    low: "Low",
    status: "Status",
    planned: "Planned",
    active: "Active",
    blocked: "Blocked",
    done: "Done",
    paused: "Paused",
    archived: "Archived",
    startDate: "Start date",
    endDate: "End date",
    targetDate: "Target date",
    progress: "Progress",
    notes: "Notes",
    saveChanges: "Save Changes",
    clear: "Clear",
    assignmentList: "Assignment List",
    assignmentListDescription: "Search members, projects, project PMs, or tasks to find assignments quickly.",
    searchPlaceholder: "Search member, project, project PM, task",
    allStatuses: "All statuses",
    task: "Task",
    allocation: "Allocation",
    period: "Period",
    actions: "Actions",
    ongoing: "Ongoing",
    edit: "Edit",
    delete: "Delete",
    newMember: "New Member",
    memberFormDescription: "Capacity is weekly hours, and assignment load is calculated by percentage.",
    name: "Name",
    role: "Role",
    team: "Team",
    weeklyCapacityHours: "Weekly capacity hours",
    available: "Available",
    busy: "Busy",
    away: "Away",
    noNotes: "No notes",
    newProject: "New Project",
    projectFormDescription: "Use status and priority to support sorting and resource decisions.",
    projectName: "Project name",
    code: "Code",
    owner: "Owner",
    planning: "Planning",
    noOwner: "No owner",
    ownerPlaceholder: "Example: Ning Zhao",
    notSet: "Not set",
    category: "Category",
    categoryPlaceholder: "Example: Tech debt / Process",
    noCategory: "No category",
    taskTitle: "Task title",
    taskTitlePlaceholder: "Example: Build quarterly capacity forecast",
    editLongTermTask: "Edit Long-Term Task",
    newLongTermTask: "New Long-Term Task",
    longTermTaskFormDescription: "Track work that runs across weeks or months without adding short-term allocation.",
    longTermTaskList: "Long-Term Task List",
    longTermTaskListDescription: "Find long-running work by status, owner, category, or title.",
    taskSearchPlaceholder: "Search task, owner, category",
    markDone: "Mark Done",
    longTermActiveMetric: "Active Tasks",
    longTermBlockedMetric: "Blocked Tasks",
    longTermDueMetric: "Due in 7 Days",
    longTermDoneMetric: "Done",
    requestFailed: "Request failed",
    deleteConfirm: "Delete this record? Related data may also be removed.",
    excelImportTitle: "Excel Import",
    excelImportDescription: "Upload the resource workbook, preview people, projects, and assignments, then apply it to the portal.",
    excelFile: "Excel file",
    importMode: "Import mode",
    importAppend: "Append import",
    importReplaceMonth: "Replace same-month imports",
    importUpdateCatalog: "Update catalog and replace assignments",
    previewImport: "Preview Import",
    applyImport: "Apply Import",
    importWorking: "Working",
    importPreview: "Import Preview",
    importIssues: "Issues",
    sourceRow: "Source row",
    stage: "Stage",
    importComplete: "Import Complete",
    importCreatedAssignments: "Created assignments",
    importCreatedMembers: "Created members",
    importCreatedProjects: "Created projects",
    risks: {
      blocked: "Blocked",
      overloaded: "Overloaded",
      tight: "Near capacity",
      underused: "Available",
      normal: "Normal",
    },
    statuses: {
      planned: "Planned",
      active: "Active",
      blocked: "Blocked",
      done: "Done",
      paused: "Paused",
      archived: "Archived",
    },
    memberStatuses: {
      available: "Available",
      busy: "Busy",
      away: "Away",
    },
    projectStatuses: {
      planning: "Planning",
      active: "Active",
      paused: "Paused",
      done: "Done",
    },
    priorities: {
      high: "High priority",
      medium: "Medium priority",
      low: "Low priority",
    },
  },
};

const t = computed(() => translations[language.value]);

const navigation = computed(() => [
  { id: "dashboard", label: t.value.dashboard, icon: Gauge },
  { id: "assignments", label: t.value.assignments, icon: CalendarRange },
  { id: "members", label: t.value.members, icon: Users },
  { id: "projects", label: t.value.projects, icon: FolderKanban },
  { id: "tasks", label: t.value.tasks, icon: ListChecks },
  { id: "sandbox", label: t.value.sandbox, icon: Network },
  { id: "imports", label: t.value.imports, icon: FileUp },
]);

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
const taskForm = reactive(defaultTaskForm());

const viewTitle = computed(() => {
  return {
    dashboard: t.value.dashboardTitle,
    assignments: t.value.assignmentsTitle,
    members: t.value.membersTitle,
    projects: t.value.projectsTitle,
    tasks: t.value.tasksTitle,
    sandbox: t.value.sandboxTitle,
    imports: t.value.excelImportTitle,
  }[view.value];
});

const viewDescription = computed(() => {
  return view.value === "sandbox" ? t.value.sandboxDescription : t.value.topbarDescription;
});

const metrics = computed(() => [
  { label: t.value.memberMetric, value: stats.value.member_count || 0, icon: Users },
  { label: t.value.activeProjectsMetric, value: stats.value.active_project_count || 0, icon: BriefcaseBusiness },
  { label: t.value.activeAssignmentsMetric, value: stats.value.active_assignment_count || 0, icon: CalendarRange },
  {
    label: t.value.blockedMetric,
    value: (stats.value.overdue_assignment_count || 0) + (stats.value.blocked_assignment_count || 0),
    icon: AlertTriangle,
  },
  { label: t.value.averageLoadMetric, value: `${stats.value.average_load || 0}%`, icon: BarChart3 },
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
    const text = `${item.member_name} ${item.project_name} ${item.project_pm_item || ""} ${item.task_name}`.toLowerCase();
    return (!needle || text.includes(needle)) && (!statusFilter.value || item.status === statusFilter.value);
  });
});

const filteredLongTermTasks = computed(() => {
  const needle = taskSearch.value.toLowerCase();
  return longTermTasks.value.filter((item) => {
    const text = `${item.title} ${item.owner} ${item.category} ${item.notes}`.toLowerCase();
    return (!needle || text.includes(needle)) && (!taskStatusFilter.value || item.status === taskStatusFilter.value);
  });
});

const taskMetrics = computed(() => {
  const activeTasks = longTermTasks.value.filter((item) => item.status === "active");
  const blockedTasks = longTermTasks.value.filter((item) => item.status === "blocked");
  const doneTasks = longTermTasks.value.filter((item) => item.status === "done");
  const dueSoonTasks = longTermTasks.value.filter((item) => {
    if (!item.target_date || ["done", "archived"].includes(item.status)) {
      return false;
    }
    const days = daysUntil(item.target_date);
    return days >= 0 && days <= 7;
  });
  return [
    { label: t.value.longTermActiveMetric, value: activeTasks.length, icon: ListChecks },
    { label: t.value.longTermBlockedMetric, value: blockedTasks.length, icon: AlertTriangle },
    { label: t.value.longTermDueMetric, value: dueSoonTasks.length, icon: CalendarRange },
    { label: t.value.longTermDoneMetric, value: doneTasks.length, icon: Check },
  ];
});

const previewAssignments = computed(() => {
  return importPreview.value ? importPreview.value.assignments.slice(0, 20) : [];
});

function defaultAssignmentForm() {
  return {
    member_id: "",
    project_id: "",
    project_pm_item: "",
    task_name: "",
    allocation_percent: 50,
    start_date: currentDate?.value || today,
    end_date: "",
    status: "active",
    priority: "medium",
    notes: "",
  };
}

function defaultTaskForm() {
  return {
    title: "",
    owner: "",
    category: "",
    status: "active",
    priority: "medium",
    progress: 0,
    start_date: today,
    target_date: "",
    notes: "",
  };
}

function toggleLanguage() {
  language.value = language.value === "zh" ? "en" : "zh";
  window.localStorage.setItem("language", language.value);
}

async function request(path, options = {}) {
  error.value = "";
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.error || t.value.requestFailed);
  }
  return body;
}

async function uploadExcel(path) {
  if (!importFile.value) {
    throw new Error(t.value.excelFile);
  }
  error.value = "";
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "X-Filename": encodeURIComponent(importFile.value.name),
    },
    body: await importFile.value.arrayBuffer(),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.error || t.value.requestFailed);
  }
  return body;
}

async function loadData() {
  try {
    const data = await request(`/api/overview?date=${currentDate.value}`);
    const taskData = await request("/api/tasks");
    stats.value = data.stats;
    members.value = data.members;
    projects.value = data.projects;
    assignments.value = data.assignments;
    longTermTasks.value = taskData.tasks;
    memberLoad.value = data.member_load;
    projectLoad.value = data.project_load;
    activity.value = data.activity;
  } catch (err) {
    error.value = err.message;
  }
}

function handleImportFile(event) {
  importFile.value = event.target.files?.[0] || null;
  importPreview.value = null;
  importResult.value = null;
}

async function previewImport() {
  try {
    importing.value = true;
    importResult.value = null;
    importPreview.value = await uploadExcel("/api/imports/excel/preview");
  } catch (err) {
    error.value = err.message;
  } finally {
    importing.value = false;
  }
}

async function applyImport() {
  if (!importPreview.value) {
    return;
  }
  try {
    importing.value = true;
    const data = await uploadExcel(`/api/imports/excel/apply?mode=${importMode.value}`);
    importResult.value = data.result;
    await loadData();
  } catch (err) {
    error.value = err.message;
  } finally {
    importing.value = false;
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

async function saveLongTermTask() {
  try {
    const path = editingTaskId.value ? `/api/tasks/${editingTaskId.value}` : "/api/tasks";
    await request(path, {
      method: editingTaskId.value ? "PUT" : "POST",
      body: JSON.stringify(taskForm),
    });
    resetTaskForm();
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
    project_pm_item: item.project_pm_item || "",
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

function editLongTermTask(item) {
  editingTaskId.value = item.id;
  Object.assign(taskForm, {
    title: item.title,
    owner: item.owner || "",
    category: item.category || "",
    status: item.status,
    priority: item.priority,
    progress: item.progress,
    start_date: item.start_date || "",
    target_date: item.target_date || "",
    notes: item.notes || "",
  });
  view.value = "tasks";
}

function resetTaskForm() {
  editingTaskId.value = null;
  Object.assign(taskForm, defaultTaskForm());
}

async function completeLongTermTask(item) {
  try {
    await request(`/api/tasks/${item.id}`, {
      method: "PUT",
      body: JSON.stringify({ ...item, status: "done", progress: 100 }),
    });
    await loadData();
  } catch (err) {
    error.value = err.message;
  }
}

async function removeLongTermTask(id) {
  if (!window.confirm(t.value.deleteConfirm)) {
    return;
  }
  try {
    await request(`/api/tasks/${id}`, { method: "DELETE" });
    await loadData();
  } catch (err) {
    error.value = err.message;
  }
}

async function removeItem(type, id) {
  if (!window.confirm(t.value.deleteConfirm)) {
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

function daysUntil(value) {
  const target = new Date(`${value}T00:00:00`);
  const base = new Date(`${currentDate.value}T00:00:00`);
  return Math.ceil((target.getTime() - base.getTime()) / 86400000);
}

function riskLabel(value) {
  return t.value.risks[value] || value;
}

function statusLabel(value) {
  return t.value.statuses[value] || value;
}

function memberStatusLabel(value) {
  return t.value.memberStatuses[value] || value;
}

function projectStatusLabel(value) {
  return t.value.projectStatuses[value] || value;
}

function priorityLabel(value) {
  return t.value.priorities[value] || value;
}

onMounted(loadData);
</script>
