import React, { useState } from "react";

interface Props {
  station: string;
  km: number;
  trainNumber: string;
  sheet: string;
  defaultHour: number;
  defaultMinute: number;
  stopType: string | null;
  hasExistingTime: boolean;
  onSave: (hour: number, minute: number, propagate: boolean) => void;
  onClear: () => void;
  onCancel: () => void;
}

export default function EditDialog({
  station,
  km,
  trainNumber,
  sheet,
  defaultHour,
  defaultMinute,
  stopType,
  hasExistingTime,
  onSave,
  onClear,
  onCancel,
}: Props) {
  const [hour, setHour] = useState(defaultHour);
  const [minute, setMinute] = useState(defaultMinute);
  const [propagate, setPropagate] = useState(true);

  const stationLabel = stopType ? `${station} (${stopType})` : station;

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <h3>Edycja czasu</h3>
        <p className="dialog-info">
          Arkusz: {sheet} &bull; Stacja: {stationLabel} &bull; km: {km.toFixed(3)} &bull; Pociąg: {trainNumber}
        </p>

        <div className="dialog-time-input">
          <label>Godzina:</label>
          <input
            type="number"
            min={0}
            max={23}
            value={hour}
            onChange={(e) => setHour(Math.max(0, Math.min(23, parseInt(e.target.value) || 0)))}
          />
          <span>:</span>
          <input
            type="number"
            min={0}
            max={59}
            value={minute}
            onChange={(e) => setMinute(Math.max(0, Math.min(59, parseInt(e.target.value) || 0)))}
          />
        </div>

        <label className="dialog-checkbox">
          <input
            type="checkbox"
            checked={propagate}
            disabled={!hasExistingTime}
            onChange={(e) => setPropagate(e.target.checked)}
          />
          Uwzględnij zmianę na dalszej części trasy
        </label>

        <div className="dialog-buttons">
          <button className="btn-primary" onClick={() => onSave(hour, minute, propagate)}>
            Zapisz
          </button>
          <button className="btn-danger" onClick={onClear}>
            Usuń postój
          </button>
          <button onClick={onCancel}>Anuluj</button>
        </div>
      </div>
    </div>
  );
}
