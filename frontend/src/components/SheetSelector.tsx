import React from "react";

interface Props {
  sheets: string[];
  selected: string;
  onSelect: (sheet: string) => void;
}

export default function SheetSelector({ sheets, selected, onSelect }: Props) {
  if (sheets.length === 0) return null;

  return (
    <div className="sheet-selector">
      <span className="sheet-selector-label">Arkusz:</span>
      {sheets.map((s) => (
        <button
          key={s}
          className={`sheet-btn ${s === selected ? "active" : ""}`}
          onClick={() => onSelect(s)}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
