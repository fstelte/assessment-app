# run.py
# Dit is het startpunt van de applicatie.
import os
from pathlib import Path

from app import create_app, db
# Pas dit aan met je daadwerkelijke modelnamen
from app.models import User, ContextScope
from dotenv import load_dotenv

# Laad eerst de root .env zodat alle applicaties dezelfde configuratie delen
ROOT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ROOT_ENV_PATH.exists():
    load_dotenv(ROOT_ENV_PATH, override=False)

# Sta lokale overrides toe voor legacy bia_app specifieke instellingen
LOCAL_ENV_PATH = Path(__file__).resolve().parent / ".env"
if LOCAL_ENV_PATH.exists():
    load_dotenv(LOCAL_ENV_PATH, override=False)
    
# --- DE WIJZIGING IS HIER ---
# Lees de configuratienaam uit de environment variabelen.
# Als FLASK_CONFIG niet is ingesteld, wordt 'default' gebruikt.
config_name = os.getenv('FLASK_CONFIG') #or 'default'

# Maak de Flask app instance aan met de gekozen configuratie.
print(f"INFO: Applicatie wordt gestart met configuratie: '{config_name}'")
app = create_app(config_name)
# --- EINDE WIJZIGING ---

@app.shell_context_processor
def make_shell_context():
    """
    Maakt een shell context aan die automatisch de database instance en modellen importeert
    wanneer 'flask shell' wordt uitgevoerd.
    """
    # Zorg dat de naam hier overeenkomt met je model (ContextScope vs BusinessProcess)
    return {'db': db, 'User': User, 'ContextScope': ContextScope} 

if __name__ == '__main__':
    app.run(debug=True, host= '0.0.0.0' , port='5001')