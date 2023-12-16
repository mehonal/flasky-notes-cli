# About

Flasky Notes CLI is an extension for Flasky Notes that allows performing various actions on a Flasky Notes instance via its external API.


# Missing Features, Limitations & Issues

## `sync-notes`
- Current implementation lacks changing note last edited locally to match the server's when the notes are synced for the first time.
- There is no handling of deleted notes.

## `get-note`
- Current implementation only supports getting notes using ID.

# Planned Features

## `search-notes`
- Command to search all notes and list their IDs, titles, category and content based on the parameters provided.
