# API-dokumentation

## Översikt
Detta API tillhandahåller endpoints för att interagera med vårt multi-agent system. API:et är byggt med Flask och använder RESTful principer.

## Autentisering
För närvarande krävs ingen autentisering för att använda API:et, men alla känsliga operationer skyddas av miljövariabler.

## Base URL
```
http://localhost:5000/api
```

## Endpoints

### 1. Supervisor Agent

#### Skicka en uppgift till SupervisorAgent
```
POST /api/ask-supervisor
```

**Beskrivning**: Skickar en uppgift till SupervisorAgent som sedan delegerar den till lämplig agent.

**Request Body**:
```json
{
    "task": "git: explain app.py"
}
```

**Exempel på användning**:
```python
import requests

response = requests.post(
    "http://localhost:5000/api/ask-supervisor",
    json={"task": "git: explain app.py"}
)
print(response.json())
```

**Response**:
```json
{
    "source": "GitAgent",
    "content": "Förklaring av app.py..."
}
```

**Felkoder**:
- `400 Bad Request`: Om task inte finns i request body
- `500 Internal Server Error`: Om något går fel i agenten

### 2. Knowledge Center

#### Hämta all kunskap
```
GET /api/knowledge
```

**Beskrivning**: Hämtar all lagrad kunskap från databasen.

**Response**:
```json
[
    {
        "partition_id": "550e8400-e29b-41d4-a716-446655440000",
        "query": "vad är flask?",
        "chunks": [
            {
                "chunk_index": 0,
                "content": "Flask är ett Python webbramverk..."
            }
        ],
        "updated_at": "2024-03-20T12:00:00Z"
    }
]
```

#### Ta bort specifik kunskap
```
DELETE /api/knowledge/<query>
```

**Beskrivning**: Tar bort en specifik kunskapsentry baserat på sökfrågan.

**Exempel**:
```python
import requests

response = requests.delete(
    "http://localhost:5000/api/knowledge/vad%20är%20flask"
)
print(response.json())
```

**Response**:
```json
{
    "message": "Deleted 3 chunks."
}
```

#### Ladda upp dokument
```
POST /api/upload-document
```

**Beskrivning**: Laddar upp ett dokument till kunskapsbasen. Dokumentet processas och delas upp i chunks.

**Request**:
- Content-Type: multipart/form-data
- Body: Fil som ska laddas upp

**Exempel**:
```python
import requests

with open('dokument.txt', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        "http://localhost:5000/api/upload-document",
        files=files
    )
print(response.json())
```

**Response**:
```json
{
    "message": "Document processed successfully",
    "filename": "dokument.txt",
    "chunks_processed": 5,
    "partition_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Felhantering

Alla endpoints returnerar fel i följande format:

```json
{
    "error": "Felmeddelande",
    "status_code": 400
}
```

Vanliga felkoder:
- `400 Bad Request`: Ogiltig request
- `404 Not Found`: Resurs hittades inte
- `500 Internal Server Error`: Serverfel

## Rate Limiting

För närvarande finns ingen rate limiting implementerad, men det rekommenderas att inte skicka fler än 10 requests per sekund.

## Exempel på användning

### Python
```python
import requests

# Skicka en uppgift
response = requests.post(
    "http://localhost:5000/api/ask-supervisor",
    json={"task": "git: explain app.py"}
)
print(response.json())

# Hämta kunskap
response = requests.get("http://localhost:5000/api/knowledge")
print(response.json())
```

### JavaScript/TypeScript
```typescript
// Skicka en uppgift
const response = await fetch('http://localhost:5000/api/ask-supervisor', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        task: 'git: explain app.py'
    })
});
const data = await response.json();
console.log(data);

// Hämta kunskap
const knowledgeResponse = await fetch('http://localhost:5000/api/knowledge');
const knowledgeData = await knowledgeResponse.json();
console.log(knowledgeData);
```

## WebSocket

För realtidsuppdateringar används WebSocket på endpoint:
```
ws://localhost:5000/ws
```

**Exempel på användning**:
```javascript
const socket = new WebSocket('ws://localhost:5000/ws');

socket.onmessage = (event) => {
    console.log('Mottaget meddelande:', event.data);
};

socket.onopen = () => {
    socket.send(JSON.stringify({
        type: 'subscribe',
        channel: 'updates'
    }));
};
```

## Versionering

För närvarande finns ingen versionshantering av API:et. Alla ändringar dokumenteras i changelog. 