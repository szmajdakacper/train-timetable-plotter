import React from "react";

const COLOR_PALETTE = [
  "#e6194b", "#4363d8", "#3cb44b", "#f58231", "#911eb4",
  "#ffe119", "#42d4f4", "#f032e6", "#fabed4", "#469990",
  "#dcbeff", "#9a6324", "#800000", "#aaffc3", "#808000",
  "#000075", "#a9a9a9", "#000000",
];

interface Props {
  activeColor: string | null;
  onSelectColor: (color: string) => void;
  onDone: () => void;
  onClearAll: () => void;
}

export default function ColorToolbar({
  activeColor,
  onSelectColor,
  onDone,
  onClearAll,
}: Props) {
  return (
    <div className="color-toolbar">
      <div className="color-buttons">
        {COLOR_PALETTE.map((hex) => (
          <button
            key={hex}
            className={`color-swatch ${activeColor === hex ? "pulsing" : ""}`}
            style={{ backgroundColor: hex, borderColor: hex }}
            title={hex}
            onClick={() => onSelectColor(hex)}
          />
        ))}
        {activeColor !== null && (
          <button className="btn-primary" onClick={onDone}>
            Gotowe
          </button>
        )}
        <button onClick={onClearAll}>Wyczyść kolory</button>
      </div>
    </div>
  );
}
