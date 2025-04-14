# Multi-Agent System

Ett system för att hantera och automatisera olika typer av uppgifter med hjälp av AI-agenter.

## Krav

För att köra projektet behöver du följande:

### Backend
- Python 3.8 eller senare
- Docker Desktop (för MongoDB)
- Följande miljövariabler i `.env`:
  ```
  LLM_API_KEY=din-api-nyckel
  LLM_ENDPOINT=din-llm-endpoint-url
  MONGO_URI=mongodb://användarnamn:lösenord@localhost:27017/
  ```

### Frontend
- Node.js 16 eller senare
- npm eller yarn

## Installation

1. Klona repot
2. Installera backend-beroenden:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Installera frontend-beroenden:
   ```bash
   cd frontend
   npm install
   ```

4. Starta MongoDB med Docker:
   ```bash
   docker run -d -p 27017:27017 --name mongodb mongo:latest
   ```

5. Starta backend:
   ```bash
   cd backend
   python app.py
   ```

6. Starta frontend:
   ```bash
   cd frontend
   npm start
   ```

## Konfiguration

För att använda Git-agenten behöver du även följande miljövariabler:
```
GITHUB_AGENT_TOKEN=din-github-token
GITHUB_REPO_NAME=ditt-repo-namn
GITHUB_REPO_OWNER=ditt-github-användarnamn
```
