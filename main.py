from typer import Typer
from rich import print
from rich.markdown import Markdown
from supersecret.keys import API_USERNAME, API_PASSWORD
import requests
from datetime import datetime, timedelta
import os

# Init
app = Typer()

# Config
ROOT_DOMAIN = "example.com"
WEB_URL = f"https://{ROOT_DOMAIN}/"
API_URL = f"https://{ROOT_DOMAIN}/api/external/"
LOCAL_NOTES_PATH = "/enter/local/path/here"
SPACE_CHAR = "_"
SERVER_TIME_OFFSET = 8

# Functions
def generate_filename(title: str, id: int):
    return title.replace(" ", SPACE_CHAR) + "_ID:" + str(id) + ".md"

def get_id_from_filename(filename: str):
    return int(filename.split("_ID:")[1].split(".")[0])

def get_title_from_filename(filename: str):
    return filename.split("_ID:")[0].replace(SPACE_CHAR, " ")

def get_content_from_note_file(filename: str):
    with open(LOCAL_NOTES_PATH + filename, "r") as f:
        return f.read()

def dateify_str(date_str: str):
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')

def dateify_server_str(date_str: str):
    return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S GMT') + timedelta(hours=SERVER_TIME_OFFSET)

def stringify_date(date: datetime):
    return date.strftime('%Y-%m-%d %H:%M:%S.%f')

def get_note_from_list(notes_list: list, note_id: int):
    for note in notes_list:
        if note["id"] == note_id:
            return note
    return None


# Commands
@app.command()
def new_note(title: str, category: str = ""):
    print("Making new note...")
    title = title.replace(SPACE_CHAR, " ")
    r = requests.post(API_URL + "add-note", json={"username": API_USERNAME, "password": API_PASSWORD, "title": title, "content": "", "category": category})
    res = r.json()
    if res.get("success", False) == True:
        print("Note created successfully.")
    else:
        print("Error creating note: " + res.get("reason", "Unknown"))

@app.command()
def list_notes(limit: int = 10, show_content: bool = False):
    print("Listing notes...")
    r = requests.post(API_URL + "get-notes", json={"username": API_USERNAME, "password": API_PASSWORD})
    print(Markdown("# Notes"))
    for note in r.json():
        if show_content:
            if note['category'] != "" and note['category'] != None:
                print(Markdown("## " + note["title"] + " (" + str(note["id"]) + ") - `" + note["category"] + "`"))
            print(Markdown("## " + note["title"] + " (" + str(note["id"]) + ")"))
            print(Markdown(note["content"]))
            print(Markdown("---"))
        else:
            if note['category'] != "" and note['category'] != None:
                print(Markdown("## " + note["title"] + " (" + str(note["id"]) + ") - `" + note["category"] + "`"))
            else:
                print(Markdown("## " + note["title"] + " (" + str(note["id"]) + ")"))
            print(Markdown("---"))

@app.command()
def get_note(note_id: int):
    print(f"Getting note {note_id}...")
    r = requests.post(API_URL + "get-note", json={"username": API_USERNAME, "password": API_PASSWORD, "note-id": note_id})
    res = r.json()
    if res.get("success", False) == True:
        note = res["note"]
        print(Markdown("# " + note["title"]))
        print(Markdown(note["content"]))
    else:
        print("Error getting note: " + res.get("reason", "Unknown"))

@app.command()
def sync_notes():
    notes_in_server = requests.post(API_URL + "get-notes", json={"username": API_USERNAME, "password": API_PASSWORD, "limit": 10_000}).json()
    print("Syncing notes...")
    if not os.path.exists(LOCAL_NOTES_PATH):
        os.mkdir(LOCAL_NOTES_PATH)
    local_file_exists = os.path.exists(LOCAL_NOTES_PATH + ".flasky-status")
    if not local_file_exists:
        print("No local status file found. Looks like this is the first time you're syncing notes.")
        print("Retrieving all notes from the server...")
        print("Got " + str(len(notes_in_server)) + " notes from the server.")
        print("Making local status file...")
        with open(LOCAL_NOTES_PATH + ".flasky-status", "w") as f:
            f.write("last_synced: " + stringify_date(datetime.now()) + "\n")
            f.write("last_synced_note_count: " + str(len(notes_in_server)) + "\n")
        print("Making local status file.")
        print("Saving notes locally...")
        for note in notes_in_server:
            with open(LOCAL_NOTES_PATH + generate_filename(title=str(note["title"]),id=str(note["id"])), "w") as f:
                f.write(note["content"])
        print(f"Saved {len(notes_in_server)} notes locally.")
    else:
        print("Local status file found. Looks like you've synced notes before.")
        print("Comparing local status file with server notes...")
        with open(LOCAL_NOTES_PATH + ".flasky-status", "r") as f:
            for line in f.readlines():
                if line.startswith("last_synced:"):
                    last_synced = dateify_str(line.strip().strip("\n").split(": ")[1])
                elif line.startswith("last_synced_note_count:"):
                    last_synced_note_count = int(line.strip().strip("\n").split(": ")[1])
        
        local_notes = []
        for note in os.listdir(LOCAL_NOTES_PATH):
            if note.endswith(".md"):
                note_id = get_id_from_filename(note)
                note_title = get_title_from_filename(note)
                note_last_edited = datetime.fromtimestamp(os.path.getmtime(LOCAL_NOTES_PATH + note))
                note_content = get_content_from_note_file(note)
                local_notes.append({"id": note_id, "title": note_title, "content": note_content, "last_edited": note_last_edited})
        print(f"Found {len(local_notes)} local notes.")
        print("Comparing local notes with server notes...")

        notes_to_upload = []
        for note in local_notes:
            note_in_server = get_note_from_list(notes_in_server, note["id"])
            if note_in_server == None:
                notes_to_upload.append(note)
            else:
                print(note["last_edited"])
                print(dateify_server_str(note_in_server["date_last_changed"]))
                if note["last_edited"] > dateify_server_str(note_in_server["date_last_changed"]) and last_synced > dateify_server_str(note_in_server["date_last_changed"]):
                    notes_to_upload.append(note)
        print(f"Found {len(notes_to_upload)} notes to upload.")

        notes_to_download = []
        for note in notes_in_server:
            note_in_local = get_note_from_list(local_notes, note["id"])
            if note_in_local == None:
                notes_to_download.append(note)
            else:
                if dateify_server_str(note["date_last_changed"]) > note_in_local["last_edited"] and dateify_server_str(note["date_last_changed"]) > last_synced:
                    notes_to_download.append(note)
        print(f"Found {len(notes_to_download)} notes to download.")

        print("Uploading notes...")
        for note in notes_to_upload:
            print(f"Uploading note {note['title']}...")
            with open(LOCAL_NOTES_PATH + generate_filename(title=str(note["title"]), id=str(note["id"])), "r") as f:
                note_content = f.read()
            r = requests.post(API_URL + "edit-note", json={"username": API_USERNAME, "password": API_PASSWORD, "note-id": int(note["id"]), "title": note["title"], "content": note_content})
            res = r.json()
            if res.get("success", False) == True:
                print("Note uploaded successfully.")
            else:
                print("Error uploading note: " + res.get("reason", "Unknown"))
        
        print("Downloading notes...")
        for note in notes_to_download:
            print(f"Downloading note {note['title']}...")
            r = requests.post(API_URL + "get-note", json={"username": API_USERNAME, "password": API_PASSWORD, "note-id": int(note["id"])})
            res = r.json()
            if res.get("success", False) == True:
                new_note_filename = LOCAL_NOTES_PATH + generate_filename(title=note["title"], id=note["id"])
                with open(new_note_filename, "w") as f:
                    f.write(note.get("content", ""))
                    os.utime(new_note_filename, (dateify_server_str(note["date_last_changed"]).timestamp(), dateify_server_str(note["date_last_changed"]).timestamp()))
                print("Note downloaded successfully.")
            else:
                print(f"Error downloading note {note['title']}: {res.get('reason', 'Unknown')}")
        
        print("Updating local status file...")
        with open(LOCAL_NOTES_PATH + ".flasky-status", "w") as f:
            f.write("last_synced: " + stringify_date(datetime.now()) + "\n")
            f.write("last_synced_note_count: " + str(len(notes_in_server)) + "\n")

if __name__ == "__main__":
    app()
