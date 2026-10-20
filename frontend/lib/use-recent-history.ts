"use client";

import { useEffect, useState } from "react";
import { createRecentHistory } from "./recent-history";

const history = createRecentHistory(() => window.localStorage);

export function useRecentHistory(key: string | null) {
  const [snapshot, setSnapshot] = useState<{ key: string | null; entries: string[] }>({ key: null, entries: [] });
  useEffect(() => {
    const refresh = () => setSnapshot({ key, entries: history.read(key) });
    refresh();
    const onStorage = (event: StorageEvent) => {
      if (event.key === key || event.key === null) refresh();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [key]);

  return {
    // Do not flash another account/subject's entries while its effect is pending.
    entries: snapshot.key === key ? snapshot.entries : [],
    add: (value: string) => setSnapshot({ key, entries: history.add(key, value) }),
    clear: () => setSnapshot({ key, entries: history.clear(key) }),
  };
}
