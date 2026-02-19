import React from "react";

const COLOR_PALETTE = [
  { name: "Czerwony", hex: "#e6194b" },
  { name: "Niebieski", hex: "#4363d8" },
  { name: "Zielony", hex: "#3cb44b" },
  { name: "Pomarańczowy", hex: "#f58231" },
  { name: "Fioletowy", hex: "#911eb4" },
  { name: "Żółty", hex: "#ffe119" },
  { name: "Czarny", hex: "#000000" },
] as const;

const LIGHT_COLORS = new Set(["#ffe119"]);

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
      <span className="color-toolbar-label">Zmień kolor</span>
      <div className="color-buttons">
        {COLOR_PALETTE.map(({ name, hex }) => (
          <button
            key={hex}
            className={`color-btn ${activeColor === hex ? "pulsing" : ""}`}
            style={{
              backgroundColor: hex,
              color: LIGHT_COLORS.has(hex) ? "#1a1a1a" : "#fff",
              borderColor: hex,
            }}
            onClick={() => onSelectColor(hex)}
          >
            {name}
          </button>
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
