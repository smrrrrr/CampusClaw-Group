"use client";

export function RecentHistory({ label, entries, onSelect, onClear, disabled = false, fillOnly = false }: {
  label: string;
  entries: string[];
  onSelect: (value: string) => void;
  onClear: () => void;
  disabled?: boolean;
  fillOnly?: boolean;
}) {
  return <section className="recent-history" aria-label={label}>
    <div className="recent-history-heading"><strong>{label}</strong>
      {entries.length > 0 && <button type="button" onClick={onClear} aria-label={`清空${label}`}>清空</button>}
    </div>
    {entries.length > 0 ? <div className="recent-history-items">
      {entries.map((entry) => <button type="button" key={entry} title={entry} disabled={disabled}
        onClick={() => onSelect(entry)}>{entry}</button>)}
    </div> : <p className="hint">{fillOnly ? "发送问题后，会在这里保留最近的提问。" : "搜索后，会在这里保留最近的关键词。"}</p>}
    <p className="hint recent-history-note">仅保存在当前浏览器，最多 10 条。{fillOnly ? "点击回填，确认后发送。清空不会删除历史会话。" : "点击关键词可再次搜索。"}</p>
  </section>;
}
