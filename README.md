# Continuum

Continuum is a modular project intelligence platform designed to explore scalable system architecture, modular backend services, and declarative UI composition.

At its core, Continuum treats a project as a root aggregate. All functionality—planning, documentation, analysis, and automation—is implemented as independently deployable modules that attach to projects via strict data contracts.

## Architecture

- Core service provides project identity, module discovery, and shared infrastructure
- Modules are autonomous services with their own schemas and APIs
- PostgreSQL enforces referential integrity across modules
- Frontend renders module-defined UI metadata using generic components
- No micro-frontends or runtime JavaScript injection

## Core Concepts
## Modules
## UI Composition Model
## Tech Stack
## Running Locally
## Design Tradeoffs

- Declarative UI metadata was chosen over micro-frontends to reduce runtime complexity
- Module schemas are initialized at startup to avoid Docker init race conditions
- UUIDs are used for all core identifiers to support distributed deployment

## Additional Notes

Development
```shell
docker compose --env-file .env up --build -d
```

To test the prod version go to [app.test](http://app.test)

To make this work you will need to add the following domains to your hosts file
```
app.test
api.test
traefik.test
```
to do that on Linux/macOS you will need to edit
```shell
sudo nano /etc/hosts
```
Add
```
127.0.0.1   app.test
127.0.0.1   api.test
127.0.0.1   traefik.test
```
and on Windows
```shell
notepad C:\Windows\System32\drivers\etc\hosts
```
and add
```
127.0.0.1   app.test
127.0.0.1   api.test
127.0.0.1   traefik.test
```

You need to do this as browsers need a host header
```
GET / HTTP/1.1
Host: app.test
```
and Traefik mathces headers with your router links
```
traefik.http.routers.frontend.rule=Host(`app.test`)
```
Without the hosts file entry:
- The request will not include the correct Host name.
- Traefik will not match the router.
- Traefik returns 404 page not found.


### Notes on Ollama

On macOS/Linux systems you may have to run 
```
chmod +x infra/ollama/pull-models.sh
```

to get the ollama service to run and pull the initial LLMs you have chosen.