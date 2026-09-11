import assert from "node:assert/strict";
import test from "node:test";
import { buildCommandBoard, isCurrentAssignment } from "../frontend/src/lib/commandSandbox.js";

test("date scope excludes completed and future planned assignments", () => {
  assert.equal(isCurrentAssignment({ status: "done", start_date: "2026-08-01", end_date: "2026-08-10" }, "2026-08-08"), false);
  assert.equal(isCurrentAssignment({ status: "planned", start_date: "2026-08-10", end_date: "2026-08-20" }, "2026-08-08"), false);
  assert.equal(isCurrentAssignment({ status: "active", start_date: "2026-08-10", end_date: "2026-08-20" }, "2026-08-08"), true);
});

test("board groups people and projects, retaining a blocked signal", () => {
  const board = buildCommandBoard({ currentDate: "2026-08-08", assignments: [
    { id: 1, member_id: 9, member_name: "周可", project_id: 2, project_name: "门户", task_name: "联调", allocation_percent: 60, status: "blocked", start_date: "2026-08-01", end_date: "2026-08-20" },
  ] });
  assert.equal(board.usingHistoricalSnapshot, false);
  assert.equal(board.people[0].risk, "blocked");
  assert.equal(board.projects[0].name, "门户");
});

test("board falls back to the latest real snapshot instead of sample data", () => {
  const board = buildCommandBoard({ currentDate: "2026-09-08", assignments: [
    { id: 1, member_id: 1, member_name: "真实成员", project_id: 1, project_name: "真实项目", task_name: "真实任务", allocation_percent: 50, status: "active", start_date: "2026-08-01", end_date: "2026-08-31" },
  ] });
  assert.equal(board.usingHistoricalSnapshot, true);
  assert.equal(board.snapshotDate, "2026-08-31");
  assert.equal(board.people[0].name, "真实成员");
});
