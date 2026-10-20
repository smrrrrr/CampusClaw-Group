export const RECENT_HISTORY_LIMIT = 10;
const MAX_ENTRY_LENGTH = 4000;

export function historyKey(studentId: number | null | undefined, classId: number | null | undefined,
  feature: "materials" | "assistant", subject: string): string | null {
  if (studentId == null || classId == null) return null;
  return `campusclaw:recent:v1:${studentId}:${classId}:${feature}:${encodeURIComponent(subject)}`;
}

function normalize(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.filter((entry): entry is string => typeof entry === "string")
    .map((entry) => entry.trim()).filter((entry) => entry.length > 0 && entry.length <= MAX_ENTRY_LENGTH))]
    .slice(0, RECENT_HISTORY_LIMIT);
}

// Storage can be blocked by browser settings. Keep this page usable in memory then.
export function createRecentHistory(getStorage: () => Pick<Storage, "getItem" | "setItem" | "removeItem">) {
  const memory = new Map<string, string[]>();
  const volatile = new Set<string>();
  const read = (key: string | null): string[] => {
    if (!key) return [];
    if (volatile.has(key)) return memory.get(key) ?? [];
    try {
      const raw = getStorage().getItem(key);
      let entries: string[] = [];
      try { entries = normalize(raw == null ? [] : JSON.parse(raw)); } catch { /* Ignore corrupt history. */ }
      memory.set(key, entries);
      return entries;
    } catch { return memory.get(key) ?? []; }
  };
  return {
    read,
    add(key: string | null, value: string): string[] {
      if (!key) return [];
      const term = value.trim();
      const existing = read(key);
      if (!term || term.length > MAX_ENTRY_LENGTH) return existing;
      const entries = normalize([term, ...existing]);
      memory.set(key, entries);
      try { getStorage().setItem(key, JSON.stringify(entries)); volatile.delete(key); }
      catch { volatile.add(key); }
      return entries;
    },
    clear(key: string | null): string[] {
      if (key) {
        memory.set(key, []);
        try { getStorage().removeItem(key); volatile.delete(key); }
        catch { volatile.add(key); }
      }
      return [];
    },
  };
}
