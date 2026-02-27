
import json
import os
import re

# Define file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = SCRIPT_DIR # Assuming script is at root as per user request context

missing_file = os.path.join(ROOT_DIR, "missing_used_keys.json")
en_file = os.path.join(ROOT_DIR, "scaffold/translations/en.json")
nl_file = os.path.join(ROOT_DIR, "scaffold/translations/nl.json")
en_new_file = os.path.join(ROOT_DIR, "scaffold/translations/en.json.new")
nl_new_file = os.path.join(ROOT_DIR, "scaffold/translations/nl.json.new")

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error decoding JSON {filepath}: {e}")
        return {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {filepath}")

def get_nested_value(data, key_path):
    keys = key_path.split('.')
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

def set_nested_value(data, key_path, value):
    keys = key_path.split('.')
    current = data
    for i, key in enumerate(keys[:-1]):
        if key not in current:
            current[key] = {}
        current = current[key]
        if not isinstance(current, dict):
            print(f"WARNING: Key collision at '{key}' in path '{key_path}'. Existing value type: {type(current)}")
            return False
    
    last_key = keys[-1]
    if last_key not in current:
        current[last_key] = value
        # print(f"Added: {key_path} -> {value}")
        return True
    return False

def generate_english_text(key_path):
    parts = key_path.split('.')
    last_part = parts[-1]
    
    text_source = last_part
    if last_part in ['label', 'heading', 'title'] and len(parts) > 1:
        text_source = parts[-2]
    
    text = text_source.replace('_', ' ')
    
    # Capitalize first letter (Sentence case)
    if not text: return ""
    text = text[0].upper() + text[1:]
    
    # Special handlings
    if text.lower() == "id": text = "ID"
    if text.lower() == "mfa": text = "MFA"
    
    return text

DUTCH_MAP = {
    "submit": "Verzenden",
    "save": "Opslaan",
    "cancel": "Annuleren",
    "close": "Sluiten",
    "delete": "Verwijderen",
    "edit": "Bewerken",
    "view": "Bekijken",
    "export": "Exporteren",
    "import": "Importeren",
    "title": "Titel",
    "email": "E-mail",
    "password": "Wachtwoord",
    "login": "Aanmelden",
    "register": "Registreren",
    "name": "Naam",
    "firstname": "Voornaam",
    "lastname": "Achternaam",
    "first_name": "Voornaam",
    "last_name": "Achternaam",
    "description": "Beschrijving",
    "actions": "Acties",
    "back": "Terug",
    "next": "Volgende",
    "yes": "Ja",
    "no": "Nee",
    "none": "Geen",
    "date": "Datum",
    "user": "Gebruiker",
    "users": "Gebruikers",
    "admin": "Beheerder",
    "overview": "Overzicht",
    "dashboard": "Dashboard",
    "profile": "Profiel",
    "home": "Start",
    "logout": "Afmelden",
    "settings": "Instellingen",
    "template": "Sjabloon",
    "language": "Taal",
    "role": "Rol",
    "roles": "Rollen",
    "assign": "Toewijzen",
    "remove": "Verwijderen",
    "disable": "Uitschakelen",
    "enable": "Inschakelen",
    "confirm": "Bevestigen",
    "required": "Verplicht",
    "error": "Fout",
    "errors": "Fouten",
    "warning": "Waarschuwing",
    "success": "Succes",
    "approve": "Goedkeuren",
    "comment": "Opmerking",
    "status": "Status",
    "unknown": "Onbekend",
    "search": "Zoeken",
    "filter": "Filteren", 
    "reset": "Resetten",
    "dark": "Donker",
    "light": "Licht",
    "theme": "Thema",
    "username": "Gebruikersnaam",
    "assessment": "Assessment",
    "assessments": "Assessments",
    "start": "Starten",
    "create": "Aanmaken",
    "new": "Nieuw",
    "download": "Downloaden",
    "upload": "Uploaden",
    "file": "Bestand",
    "help": "Hulp",
    "heading": "Kop",
    "label": "Label",
    "message": "Bericht",
    "risk": "Risico",
    "risks": "Risico's",
    "impact": "Impact",
    "probability": "Kans",
    "threat": "Dreiging",
    "vulnerability": "Kwetsbaarheid",
    "incident": "Incident",
    "response": "Respons",
    "auth": "Authenticatie",
    "log": "Log",
    "audit": "Audit",
    "trail": "Spoor",
    "license": "Licentie",
    "version": "Versie",
    "github": "GitHub",
    "changelog": "Wijzigingslog",
    "built": "Gebouwd",
    "by": "door",
    "navigation": "Navigatie",
    "brand": "Merk",
    "bia": "BIA",
    "assignee": "Toegewezene",
    "due": "Vervalt",
    "answer": "Antwoord",
    "placeholder": "Plaatsaanduiding",
    "review": "Beoordelen",
    "return": "Terugsturen",
    "remember": "Onthouden",
    "me": "mij",
    "device": "Apparaat",
    "instructions": "Instructies",
    "secret": "Geheim",
    "uri": "URI",
    "otp": "OTP",
    "length": "Lengte",
    "mismatch": "Komt niet overeen",
    "current": "Huidig",
    "cta": "CTA",
    "intro": "Intro",
    "authenticated": "Geauthenticeerd",
    "guest": "Gast",
    "pending_reviews": "Openstaande beoordelingen",
    "headers": "Headers",
    "submitted_at": "Ingediend op",
    "submitter": "Indiener",
    "templates_hint": "Sjablonen hint",
    "verify": "Verifieer",
    "enroll": "Inschrijven",
    "provisioning": "Provisioning",
    "regenerate": "Opnieuw genereren",
    "refresh": "Verversen",
    "back_to_users": "Terug naar gebruikers",
    "not_provisioned": "Niet geprovisioneerd",
    "confirm_delete": "Verwijderen bevestigen",
    "manage_mfa": "MFA beheren",
    "all_roles_assigned": "Alle rollen toegewezen",
    "no_roles_configured": "Geen rollen geconfigureerd",
    "select_role": "Selecteer rol",
    "link_bia_dashboard": "Link BIA Dashboard",
    "link_csa_dashboard": "Link CSA Dashboard",
    "flash": "Flash",
    "admin_must_remain": "Beheerder moet blijven",
    "cannot_delete_current_account": "Kan huidige account niet verwijderen",
    "final_admin_cannot_be_deactivated": "Laatste beheerder kan niet gedeactiveerd worden",
    "page_title": "Paginatitel",
    "page_heading": "Pagina kop",
    "register_link": "Registratie link",
    "register_prompt": "Registratie prompt",
    "login_link": "Inlog link",
    "login_prompt": "Inlog prompt",
    "archive_note": "Archief notitie",
    "open_assignments": "Open opdrachten",
    "action_open": "Actie open",
    "templates_hint_link": "Sjablonen hint link",
    "unknown_date": "Onbekende datum",
    "unknown_user": "Onbekende gebruiker",
    "admin_import_controls": "Beheer Import Controls",
    "admin_users": "Beheer Gebruikers",
    "admin_roles": "Beheer Rollen",
    "assessments_overview": "Assessments Overzicht",
    "assign_assessment": "Assessment Toewijzen",
    "start_assessment": "Start Assessment",
    "manage_dropdown": "Beheer Dropdown",
    "mfa_reset": "MFA Reset",
    "mfa_setup": "MFA Opzetten",
    "submit_for_review": "Indienen voor beoordeling",
    "return_to_assignee": "Terug naar toegewezene",
    "remember_device": "Apparaat onthouden",
    "confirm_required": "Bevestiging vereist",
    "password_length": "Wachtwoordlengte",
    "password_mismatch": "Wachtwoorden komen niet overeen",
    "password_required": "Wachtwoord vereist",
    "confirm_password": "Bevestig wachtwoord",
    "current_password": "Huidig wachtwoord",
    "new_password": "Nieuw wachtwoord",
    "cta_login": "CTA Login",
    "cta_start": "CTA Start",
    "lead_guest": "Lead Gast",
    "intro_authenticated": "Intro Geauthenticeerd",
    "data_file": "Data bestand",
    "file_allowed": "Bestand toegestaan",
    "file_required": "Bestand vereist",
    "role_missing": "Rol ontbreekt",
    "role_required": "Rol vereist",
}

def generate_dutch_text(key_path):
    parts = key_path.split('.')
    last_part = parts[-1]
    
    # Try exact match on last part first
    if last_part in DUTCH_MAP:
        return DUTCH_MAP[last_part]
        
    text_source = last_part
    if last_part in ['label', 'heading', 'title', 'placeholder'] and len(parts) > 1:
        text_source = parts[-2]
    
    # Try mapping again
    if text_source in DUTCH_MAP:
        return DUTCH_MAP[text_source]

    # Handle composed words like "confirm_password"
    words = text_source.split('_')
    translated_words = []
    
    for word in words:
        w_lower = word.lower()
        if w_lower in DUTCH_MAP:
             translated_words.append(DUTCH_MAP[w_lower])
        else:
             translated_words.append(word.capitalize())
             
    return ' '.join(translated_words)

def main():
    missing_data = load_json(missing_file)
    print(f"Loaded missing data keys: {list(missing_data.keys())}")
    if "missing_en" in missing_data:
        print(f"Found {len(missing_data['missing_en'])} missing EN keys")
    else:
        print("missing_en key NOT FOUND in missing_used_keys.json")

    en_data = load_json(en_file)
    nl_data = load_json(nl_file)
    en_new_data = load_json(en_new_file)
    
    added_en = 0
    added_nl = 0
    
    if "missing_en" in missing_data:
        for key in missing_data["missing_en"]:
            val = get_nested_value(en_new_data, key)
            if not val:
                val = generate_english_text(key)
            
            # DEBUG
            # print(f"Processing key: {key}, Val: {val}")

            if set_nested_value(en_data, key, val):
                added_en += 1
            else:
                 print(f"Failed to add key: {key}. Value already exists or collision.")

    if "missing_nl" in missing_data:
        for key in missing_data["missing_nl"]:
            val = generate_dutch_text(key)
            if set_nested_value(nl_data, key, val):
                added_nl += 1

    save_json(en_file, en_data)
    save_json(nl_file, nl_data)
    print(f"Update complete. Added {added_en} EN keys, {added_nl} NL keys.")

if __name__ == "__main__":
    main()
