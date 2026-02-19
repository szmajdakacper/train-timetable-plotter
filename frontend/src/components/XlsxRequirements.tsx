import React, { useState } from "react";

export default function XlsxRequirements() {
  const [open, setOpen] = useState(false);

  return (
    <details
      className="xlsx-requirements"
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
    >
      <summary>Wymagania do pliku xlsx</summary>
      <div className="xlsx-requirements-body">
        <p>
          <strong>Plik musi być w formacie <code>.xlsx</code></strong> (Excel
          2007+).
        </p>

        <h4>Wymagane nagłówki</h4>
        <p>
          W każdym arkuszu muszą znajdować się następujące komórki-nagłówki
          (wielkość liter i polskie znaki nie mają znaczenia):
        </p>
        <table className="req-table">
          <thead>
            <tr>
              <th>Nagłówek</th>
              <th>Dopuszczalne warianty</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Numer pociągu</td>
              <td>
                <code>Numer pociągu</code>, <code>Nr pociągu</code>,{" "}
                <code>Pociąg</code>, <code>Train number</code>
              </td>
            </tr>
            <tr>
              <td>Kilometraż</td>
              <td>
                <code>km</code>, <code>Kilometraż</code>,{" "}
                <code>Kilometr</code>
              </td>
            </tr>
            <tr>
              <td>Początek listy stacji</td>
              <td>
                <code>Ze stacji</code>, <code>Od stacji</code>,{" "}
                <code>Start stacji</code>
              </td>
            </tr>
            <tr>
              <td>Koniec listy stacji</td>
              <td>
                <code>Do stacji</code>, <code>Na stację</code>,{" "}
                <code>Cel stacji</code>, <code>Koniec stacji</code>
              </td>
            </tr>
          </tbody>
        </table>

        <h4>Struktura arkusza</h4>
        <ul>
          <li>
            <strong>Stacje</strong> — wymienione w kolumnie poniżej nagłówka
            „Ze stacji", każda z wartością <code>km</code> w sąsiedniej
            kolumnie.
          </li>
          <li>
            <strong>Numery pociągów</strong> — w wierszu oznaczonym nagłówkiem
            „Numer pociągu". Numer musi zawierać co najmniej jedną cyfrę.
          </li>
          <li>
            <strong>Czasy</strong> — w komórkach na przecięciu wiersza stacji i
            kolumny pociągu.
          </li>
        </ul>

        <h4>Formaty czasu</h4>
        <p>Akceptowane formaty w komórkach z czasem:</p>
        <ul>
          <li>
            <code>HH:MM</code> lub <code>HH:MM:SS</code> (np.{" "}
            <code>14:30</code>)
          </li>
          <li>
            <code>HH.MM</code> (np. <code>14.30</code> — dwie cyfry po kropce =
            minuty)
          </li>
          <li>
            Ułamek doby Excela (np. <code>0.604</code> = 14:30)
          </li>
          <li>
            Obiekt <code>datetime</code> / <code>time</code> z Excela
          </li>
          <li>
            Sufiks dnia <code>(+1)</code>, <code>(+2)</code> itp. dla przejazdów
            po północy
          </li>
        </ul>

        <h4>Wiele arkuszy</h4>
        <p>
          Lista stacji i km w każdym arkuszu powinna być taka sama jak w
          pierwszym arkuszu (jest weryfikowana). Każdy arkusz może zawierać inne
          pociągi.
        </p>

        <h4>Scalone komórki</h4>
        <p>
          Scalone komórki są obsługiwane — wartość z lewej górnej komórki
          zostanie skopiowana do wszystkich komórek zakresu.
        </p>

        <h4>Ukryte kolumny</h4>
        <p>
          Kolumny oznaczone w Excelu jako ukryte zostaną automatycznie pominięte.
        </p>

        <a
          className="btn-download"
          href="/api/example"
          download="d1_test.xlsx"
        >
          Pobierz przykładowy plik
        </a>
      </div>
    </details>
  );
}
