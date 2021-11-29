# KevinMalone
A self reporting bot for the movement model

## Functionality

- `/report` - creates a private message to the user with a link the guild's airtable

## Development in VS Code

Requires the following VS Code extensions to be installed:

- Docker
- Remote – Containers

## Develop with Intellisense, Run, and Debug in Dev Container

### Open Dev Container

- click `Open a Remote Window` button in lower left corner
- click `Reopen in Container`
- click `From Dockerfile`

### Debug in Dev Container

- Open `Run and Debug`
- Select `Python:Bot` and click Run Button
- Stop when done testing bot

### Run Tests

- Open `Testing`
- Click the Run or Debug Button

### Close Dev Container

- In the lower left, select `Reopen Folder Locally`

### Source Control

- Open Folder w/o Dev Container and check in code


## Setup Docker and Dev Container

- Create a new folder
- add a `bot` folder with these files:
  - __init__.py
  - __main__.py
  - commands.py
- `Docker: Add Docker files to Workspace`
  - Application Platform: `Python: General`
  - App's Entry Point: `bot/__main__.py`
  - Include optional Docker Compose files: `no`
- `Remote-Containers: Open Folder in Container`
  - select parent folder and click Open
  - `From Dockerfile`
- Add extensions to Dev Container for development
  - `Python`
- Open Terminal and run the following in the Dev Container
  - `python bot/__main__.py`
- `ctrl`-`c` to stop bot

### Setup Debug in Dev Container

- `Run and Debug`
- `Add Configuration...`
- `Python`
- `Python File`
- Set `name` to `Python: Bot`
- Set `program` to `bot/`

## Credits

- <https://github.com/python-discord/bot>

## License

MIT © Govrn
