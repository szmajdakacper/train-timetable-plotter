# Train Timetable Plotter

Interactive visualization tool for train timetables that allows you to:
- Upload Excel timetables
- View interactive train path plots
- Analyze station arrival/departure times
- Highlight specific trains for detailed analysis

## Features

- 📈 Interactive plot with train paths
- 📊 Detailed timetable view for each sheet
- 🔍 Train highlighting for easy analysis (klik nagłówka kolumny pociągu)
- 🪵 Debug mode toggle in sidebar
- 📱 Responsive design that works on all devices

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

3. Install required packages:
```bash
pip install -r requirements.txt
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

4. Interact with the visualization:
   - Click train numbers to highlight specific trains
   - Hover over points to see detailed timing information
   - View multiple sheets for different lines/directions

## Input File Format

The Excel file should be structured as follows:
- Polish headers are expected:
  - "Numer pociągu" (header row with train numbers)
  - "ze stacji" and "do stacji" (mark the start and end of station list)
  - "km" (kilometre column)
- The first sheet serves as the reference list of stations and km; other sheets must use the same stations
- Time values: HH:MM, HH:MM:SS, HH.MM (minutes), or Excel fraction of day (e.g., 0.25)
- Multiple sheets allowed for different lines/directions

## Contributing
## Debugging

Enable "Tryb debug" in the sidebar to print additional logs to the server console. This helps diagnose time parsing and column mapping issues.

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.