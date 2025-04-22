import React, { useState } from 'react';
import "../styles/KnowledgeCenter.css";
import KnowledgeGroup from "../components/KnowledgeGroup";

interface GroupedKnowledge {
    partition_id: string;
    query: string;
    updated_at: string;
    chunks: Chunk[];
}

interface Chunk {
    chunk_index: number;
    content: string;
}

interface UploadStatus {
    isUploading: boolean;
    success?: string;
    error?: string;
}

const KnowledgeCenter: React.FC = () => {
    const [knowledgeList, setKnowledgeList] = useState<GroupedKnowledge[]>([]);
    const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
        isUploading: false
    });

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        if (!file.name.endsWith('.txt')) {
            setUploadStatus({
                isUploading: false,
                error: 'Endast .txt filer stöds'
            });
            return;
        }

        setUploadStatus({ isUploading: true });

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:5000/api/upload-document', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Ett fel uppstod vid uppladdning');
            }

            setUploadStatus({
                isUploading: false,
                success: `${file.name} har laddats upp och bearbetats framgångsrikt`
            });

            // Uppdatera listan med dokument
            fetchKnowledge();

        } catch (error: any) {
            setUploadStatus({
                isUploading: false,
                error: `Fel vid uppladdning: ${error.message}`
            });
        }
    };

    const fetchKnowledge = async () => {
        try {
            const response = await fetch('http://localhost:5000/api/knowledge');
            const data = await response.json();
            setKnowledgeList(data);
        } catch (error) {
            console.error('Fel vid hämtning av kunskap:', error);
        }
    };

    const handleDelete = async (query: string, partition_id: string) => {
        try {
            const response = await fetch(`http://localhost:5000/api/knowledge/${encodeURIComponent(query)}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Kunde inte ta bort dokumentet');
            }

            setKnowledgeList(prev => prev.filter(g => g.partition_id !== partition_id));
        } catch (error) {
            console.error('Fel vid borttagning:', error);
        }
    };

    const handleDeleteAll = async () => {
        if (!window.confirm('Är du säker på att du vill ta bort all data? Detta går inte att ångra.')) {
            return;
        }

        try {
            const response = await fetch('http://localhost:5000/api/knowledge', {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Kunde inte ta bort all data');
            }

            setKnowledgeList([]);
            setUploadStatus({
                isUploading: false,
                success: 'All data har tagits bort'
            });
        } catch (error) {
            console.error('Fel vid borttagning av all data:', error);
            setUploadStatus({
                isUploading: false,
                error: 'Kunde inte ta bort all data'
            });
        }
    };

    const handleUpdate = async (query: string, newContent: string) => {
        try {
            const response = await fetch(`http://localhost:5000/api/knowledge/${encodeURIComponent(query)}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content: newContent })
            });

            if (!response.ok) {
                throw new Error('Kunde inte uppdatera dokumentet');
            }

            // Uppdatera listan för att visa de senaste ändringarna
            fetchKnowledge();
        } catch (error) {
            console.error('Fel vid uppdatering:', error);
        }
    };

    React.useEffect(() => {
        fetchKnowledge();
    }, []);

    return (
        <div className="knowledge-container">
            <h2>Knowledge Center</h2>
            
            {/* Enkel filuppladdning */}
            <div className="upload-section">
                <input
                    type="file"
                    accept=".txt"
                    onChange={handleFileUpload}
                    style={{ marginBottom: '1rem' }}
                />
                
                {/* Status och felmeddelanden */}
                {uploadStatus.isUploading && (
                    <div className="status-message">
                        Laddar upp och bearbetar fil...
                    </div>
                )}
                {uploadStatus.success && (
                    <div className="success-message">
                        {uploadStatus.success}
                        <button onClick={() => setUploadStatus({ isUploading: false })}>×</button>
                    </div>
                )}
                {uploadStatus.error && (
                    <div className="error-message">
                        {uploadStatus.error}
                        <button onClick={() => setUploadStatus({ isUploading: false })}>×</button>
                    </div>
                )}
            </div>

            {/* Rensa all data knapp */}
            <div className="clear-all-section">
                <button 
                    className="clear-all-button"
                    onClick={handleDeleteAll}
                >
                    Rensa all data
                </button>
            </div>

            {/* Lista över uppladdade dokument */}
            <h3>Uppladdade dokument</h3>
            <div className="knowledge-list">
                {knowledgeList.map((group) => (
                    <KnowledgeGroup
                        key={group.partition_id}
                        group={group}
                        onDelete={handleDelete}
                        onUpdate={handleUpdate}
                    />
                ))}
            </div>
        </div>
    );
};

export default KnowledgeCenter;
