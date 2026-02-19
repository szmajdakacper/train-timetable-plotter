import React from "react";
import { downloadUrl } from "../api";

export default function ExportBar() {
  return (
    <div className="export-bar">
      <a href={downloadUrl("xlsx")} className="btn-download">
        Pobierz rozkład do xlsx
      </a>
      <a href={downloadUrl("project")} className="btn-download">
        Zapisz projekt
      </a>
      <a href={downloadUrl("circuits")} className="btn-download">
        Pobierz obiegi pojazdów
      </a>
    </div>
  );
}
