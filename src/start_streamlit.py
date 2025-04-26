import os
import subprocess
import sys

# Der Name der Datei mit dem Streamlit-Visualisierungsskript
STREAMLIT_SCRIPT = 'visualisierung.py'


def start_streamlit():
    # Bestimme den Pfad zum Streamlit-Skript
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, STREAMLIT_SCRIPT)

    # Starte Streamlit mittels subprocess
    try:
        subprocess.run(['streamlit', 'run', script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ein Fehler ist beim Starten von Streamlit aufgetreten: {e}")
        sys.exit(1)


if __name__ == '__main__':
    start_streamlit()