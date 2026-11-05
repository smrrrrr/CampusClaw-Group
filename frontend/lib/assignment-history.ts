export interface AssignmentProgress {
  submission_id: number | null;
  homework_status?: string;
  due_at: string | null;
}

export function canSubmitAssignment(hw: AssignmentProgress, now = Date.now()): boolean {
  return hw.homework_status !== "closed" && (!hw.due_at || new Date(hw.due_at).getTime() >= now);
}

export function isAssignmentHistory(hw: AssignmentProgress, now = Date.now()): boolean {
  return hw.submission_id !== null || !canSubmitAssignment(hw, now);
}
