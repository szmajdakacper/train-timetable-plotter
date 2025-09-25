# Train Timetable Plotter

Interactive visualization tool for train timetables that allows you to:
- Upload Excel timetables
- View interactive train path plots
- Analyze station arrival/departure times
- Highlight specific trains for detailed analysis

## Features

- 📈 Interaktywny wykres tras (ECharts, komponent Streamlit)
- 🧾 Edytowalna tabela (AG Grid jako custom component)
- 🖱️ Edycja godziny z tabeli i z wykresu (dblclick + modal)
- 🔄 Propagacja zmian czasu w dół trasy
- 🧭 Zoom/pan na osi czasu i km, osobne suwaki zakresu X i Y
- 🕒 Poprawna obsługa czasów po północy (np. 00:05 (+1))
- ⬇️ Eksport do XLSX w układzie:
  - E3 = "numer pociągu", D11 = "km", E11 = "ze stacji"
  - kol. D od wiersza 12: km (liczby, format 0.000); kol. E: stacje
  - wiersz 3 od kol. F: numery pociągów; czasy HH:MM we właściwych komórkach
  - wiersz po ostatniej stacji: E = "do stacji"

## Installation

1. Clone this repository:
```bash
git clone [repository-url]
cd train-timetable-plotter
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Unix/MacOS:
source venv/bin/activate
```

3. Install backend dependencies:
```bash
pip install -r requirements.txt
```

4. Build frontend components (one time after clone or when changed):
```bash
# Grid component
cd train_grid_component/frontend
npm install
npm run build

# Plot component
cd ../../train_plot_component/frontend
npm install
npm run build

# Back to project root
cd ../../..
```

## Usage

1. Run the Streamlit application:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the URL shown in the terminal (usually `http://localhost:8501`)

3. Upload an Excel file containing train timetables:
   - File should contain stations in rows
   - Train numbers should be in the header row
   - Each sheet can represent a different line or direction

4. Interact with the app:
   - Dblclick w tabeli lub na punkcie wykresu otwiera modal edycji czasu
   - Checkbox w modalu pozwala propagować zmianę na dalszą część trasy
   - Suwakiem ustaw wysokość wykresu (600–4000 px)
   - Suwaki zoomu X/Y regulują zakres; linie poza zakresem są utrzymywane (filterMode="none")

## Input File Format

The Excel file should be structured as follows:
- Polish headers are expected:
  - "Numer pociągu" (header row with train numbers)
  - "ze stacji" and "do stacji" (mark the start and end of station list)
  - "km" (kilometre column)
- The first sheet serves as the reference list of stations and km; other sheets can have their own maps; wykres używa mapy stacji bieżącego arkusza, eksport do XLSX korzysta z map arkuszy docelowych
- Time values: HH:MM, HH:MM:SS, HH.MM (minutes), or Excel fraction of day (e.g., 0.25)
- Multiple sheets allowed for different lines/directions

## Contributing
## Debugging / Notes

- Czasy mogą być wpisywane jako HH:MM, HH:MM:SS, HH.MM, lub ułamki doby; parser obsługuje także sufiks "(+N)" (np. 00:05 (+1)).
- Eksport do XLSX wiąże czasy po kluczu (stacja, numer pociągu); dopasowanie stacji toleruje drobne różnice (normalizacja).
- Jeśli po zmianach w frontendzie komponentów coś nie działa, zbuduj je ponownie (`npm run build`).

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.