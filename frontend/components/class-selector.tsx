"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

/**
 * 班级选择器：从 teaching_classes（store）读取任教班级列表。
 * 后端二次校验 class_id IN teaching_classes，篡改请求会被 403 拒绝。
 */
export function ClassSelector({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (classId: number) => void;
}) {
  const teachingClasses = useAuthStore((s) => s.teachingClasses);
  const [classes, setClasses] = useState<{ id: number; name: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setClasses([]);
    // 优先用 store 中的 teachingClasses 快速渲染；后端列表作为名称补充
    if (teachingClasses && teachingClasses.length > 0) {
      api
        .listClasses()
        .then((rows) => {
          if (!cancelled) setClasses(rows.filter((row) => teachingClasses.includes(row.id)));
        })
        .catch(() => {
          // 后端请求失败时用 store 中的 ID 做兜底
          if (!cancelled) setClasses(teachingClasses.map((id) => ({ id, name: `班级 ${id}` })));
        })
        .finally(() => { if (!cancelled) setLoading(false); });
    } else {
      setLoading(false);
    }
    return () => { cancelled = true; };
  }, [teachingClasses]);

  if (loading) return <span className="hint">加载班级…</span>;
  if (classes.length === 0)
    return <span className="hint">未分配任教班级</span>;

  return (
    <select
      aria-label="选择任教班级"
      className="input"
      style={{ width: "auto", padding: "8px 12px" }}
      value={value ?? ""}
      onChange={(e) => onChange(Number(e.target.value))}
    >
      {classes.map((c) => (
        <option key={c.id} value={c.id}>
          {c.name}
        </option>
      ))}
    </select>
  );
}
