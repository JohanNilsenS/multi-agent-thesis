# Teknisk Dokumentation

## Systemarkitektur

### Backend
Backend-applikationen är byggd med Flask och består av följande huvudkomponenter:

1. **Agenter**
   - `GitAgent`: Hanterar Git-relaterade uppgifter
   - `ResearchAgent`: Hanterar forsknings- och sökuppgifter
   - `SupervisorAgent`: Koordinerar och delegerar uppgifter till andra agenter

2. **Databas**
   - MongoDB för lagring av data
   - FAISS för vektorsökning och semantisk matchning

3. **API**
   - RESTful API med Flask Blueprints
   - WebSocket för realtidskommunikation

### Frontend
Frontend-applikationen är byggd med React och TypeScript:

1. **Komponenter**
   - `ChatInterface`: Hanterar användarinteraktion och visning av meddelanden
   - `KnowledgeCenter`: Hanterar kunskapsbasen
   - `Header`: Navigeringsmeny

2. **State Management**
   - React Hooks för lokal state
   - Context API för global state

## Använda Bibliotek

### Backend
- **Flask**: Webbramverk för API
- **PyMongo**: MongoDB-driver för Python
- **FAISS**: Vektorsökning och semantisk matchning
- **Docker**: Containerisering av MongoDB
- **python-dotenv**: Hantering av miljövariabler
- **requests**: HTTP-requests för externa API:er

### Frontend
- **React**: UI-bibliotek
- **TypeScript**: Typning och bättre utvecklarupplevelse
- **React Router**: Navigering
- **Axios**: HTTP-requests
- **CSS Modules**: Styling

## API-dokumentation

### Endpoints

#### `/api/ask-supervisor`
- **Metod**: POST
- **Beskrivning**: Skicka en uppgift till SupervisorAgent
- **Request Body**:
  ```json
  {
    "task": "git: explain app.py"
  }
  ```
- **Response**:
  ```json
  {
    "source": "GitAgent",
    "content": "Förklaring av app.py..."
  }
  ```

#### `/api/knowledge`
- **Metod**: GET
- **Beskrivning**: Hämta all kunskap från databasen
- **Response**:
  ```json
  [
    {
      "partition_id": "uuid",
      "query": "sökfråga",
      "chunks": [
        {
          "chunk_index": 0,
          "content": "Innehåll..."
        }
      ],
      "updated_at": "timestamp"
    }
  ]
  ```

#### `/api/knowledge/<query>`
- **Metod**: DELETE
- **Beskrivning**: Ta bort en specifik kunskapsentry
- **Response**:
  ```json
  {
    "message": "Deleted X chunks."
  }
  ```

#### `/api/upload-document`
- **Metod**: POST
- **Beskrivning**: Ladda upp ett dokument till kunskapsbasen
- **Request**: FormData med fil
- **Response**:
  ```json
  {
    "message": "Document processed successfully",
    "filename": "filnamn.txt",
    "chunks_processed": 5,
    "partition_id": "uuid"
  }
  ```

## Datamodeller

### Research Entry
```python
{
    "query": str,           # Original sökfråga
    "chunk": str,           # Innehåll i chunken
    "chunk_index": int,     # Index för chunken
    "embedding": list,      # Vektorembedding
    "partition_id": str,    # UUID för att gruppera relaterade chunks
    "updated_at": datetime, # Senaste uppdateringstid
    "metadata": dict        # Ytterligare metadata
}
```

### Agent Response
```typescript
interface AgentResponse {
    source: string;     // Agentens namn
    content: string;    // Svaret från agenten
    isUser?: boolean;   // Om meddelandet är från användaren
}
```

## Säkerhet

1. **Miljövariabler**
   - API-nycklar och tokens lagras i `.env`
   - Känslig information hanteras säkert

2. **CORS**
   - Konfigurerad för att endast tillåta specifika domäner
   - Säker hantering av cross-origin requests

3. **Databas**
   - Autentisering krävs för MongoDB-anslutning
   - Säker hantering av användardata

## Prestanda

1. **Caching**
   - MongoDB-cache för sökresultat
   - FAISS-index för snabb vektorsökning

2. **Asynkron bearbetning**
   - Asynkrona agenter för parallell bearbetning
   - WebSocket för realtidsuppdateringar

3. **Optimering**
   - Chunking av stora dokument
   - Effektiv vektorsökning med FAISS 