import React, { useCallback, useRef, useState } from "react";

interface Props {
  onUpload: (file: File) => void;
  loading: boolean;
}

export default function FileUpload({ onUpload, loading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(
    (file: File) => {
      const name = file.name.toLowerCase();
      if (name.endsWith(".xlsx") || name.endsWith(".json")) {
        onUpload(file);
      }
    },
    [onUpload],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <div
      className={`file-upload ${dragOver ? "drag-over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.json"
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
          e.target.value = "";
        }}
      />
      {loading ? (
        <p>Wczytywanie...</p>
      ) : (
        <>
          <p>Przeciągnij plik Excel (.xlsx) lub projekt (.json) tutaj</p>
          <p className="file-upload-hint">lub kliknij, aby wybrać plik</p>
        </>
      )}
    </div>
  );
}
