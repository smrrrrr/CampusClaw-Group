/** 将初批受理结果写成可在当前作业卡片核对的回执。 */
export interface GradeReceipt {
  task_ids: number[];
  created_count: number;
  existing_count: number;
  skipped_count: number;
}

export function formatGradeReceipt(receipt: GradeReceipt): string {
  const ids = receipt.task_ids.map(id => `#${id}`).join("、");
  let text: string;
  if (receipt.task_ids.length === 0) {
    text = "没有待初批的提交。";
  } else if (receipt.created_count === 0) {
    text = `没有新建任务。已复用任务 ${ids}（已有 ${receipt.existing_count} 个）。`;
  } else if (receipt.existing_count === 0) {
    text = `已新建 ${receipt.created_count} 个后台任务：${ids}。`;
  } else {
    text = `已新建 ${receipt.created_count} 个、复用 ${receipt.existing_count} 个后台任务；任务编号：${ids}。`;
  }
  if (receipt.skipped_count > 0) text += `已跳过 ${receipt.skipped_count} 份无需初批的提交。`;
  return text + "可稍后查看进度，AI 建议仍需教师确认。";
}

export function syncSubmissionCount<T extends { id: number; submitted_count: number }>(rows: T[], homeworkId: number, count: number): T[] {
  return rows.map(row => row.id === homeworkId ? { ...row, submitted_count: count } : row);
}

export function formatGradingAttempts(task: { execution_count: number; max_attempts: number }): string {
  return `批改尝试 ${task.execution_count} 次（本轮上限 ${task.max_attempts} 次）`;
}
