import React, { useState } from "react";

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
  const [showHelp, setShowHelp] = useState(false);

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
        <button onClick={() => setShowHelp(true)}>Instrukcja</button>
      </div>

      {showHelp && (
        <div className="dialog-overlay" onClick={() => setShowHelp(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Zmień kolor — instrukcja</h3>
            <div className="color-help-body">
              <p><strong>Jak zmienić kolor pociągu?</strong></p>
              <ol>
                <li>Kliknij przycisk z wybranym kolorem.</li>
                <li>
                  Kliknij dowolną komórkę pociągu w <strong>tabeli</strong> lub
                  punkt na <strong>wykresie</strong> — linia na wykresie i tło
                  kolumny w tabeli zmienią kolor.
                </li>
              </ol>
              <p><strong>Dodatkowe opcje:</strong></p>
              <ul>
                <li>
                  <strong>Czarny</strong> — resetuje kolor pociągu do
                  domyślnego (czarnego).
                </li>
                <li>
                  <strong>Gotowe</strong> — kończy kolorowanie; kliknięcia znów
                  otwierają okno edycji czasu.
                </li>
                <li>
                  <strong>Wyczyść kolory</strong> — usuwa wszystkie przypisane
                  kolory.
                </li>
              </ul>
              <p>
                <strong>Uwaga:</strong> Gdy narzędzie koloru jest aktywne,
                edycja czasu jest zablokowana. Aby wrócić do edycji, kliknij
                „Gotowe".
              </p>
            </div>
            <div className="dialog-buttons" style={{ marginTop: 16 }}>
              <button
                className="btn-primary"
                onClick={() => setShowHelp(false)}
              >
                Zamknij
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
