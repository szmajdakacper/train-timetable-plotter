FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python backend + shared modules
COPY backend/ ./backend/
COPY utils.py table_editor.py excel_loader.py ./
COPY example_table/ ./example_table/

# Copy pre-built frontend (committed in repo)
COPY frontend/dist ./frontend/dist

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
