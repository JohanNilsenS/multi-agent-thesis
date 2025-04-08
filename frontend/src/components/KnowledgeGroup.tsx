import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Edit2, Trash2, Save, X } from 'react-feather';

interface Chunk {
    chunk_index: number;
    content: string;
}

interface GroupedKnowledge {
    partition_id: string;
    query: string;
    updated_at: string;
    chunks: Chunk[];
    source?: string;
}

interface Props {
    group: GroupedKnowledge;
    onDelete: (query: string, partition_id: string) => void;
    onUpdate: (query: string, newContent: string) => void;
}

const KnowledgeGroup: React.FC<Props> = ({ group, onDelete, onUpdate }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [editingChunkIndex, setEditingChunkIndex] = useState<number | null>(null);
    const [editedContent, setEditedContent] = useState('');

    const handleEditChunk = (chunk: Chunk) => {
        setEditingChunkIndex(chunk.chunk_index);
        setEditedContent(chunk.content);
    };

    const handleSaveChunk = () => {
        if (editingChunkIndex === null) return;

        const updatedChunks = [...group.chunks].sort((a, b) => a.chunk_index - b.chunk_index);
        const chunkIndex = updatedChunks.findIndex(c => c.chunk_index === editingChunkIndex);
        if (chunkIndex === -1) return;

        updatedChunks[chunkIndex] = { ...updatedChunks[chunkIndex], content: editedContent };
        const fullContent = updatedChunks.map(chunk => chunk.content).join('\n');
        
        onUpdate(group.query, fullContent);
        setEditingChunkIndex(null);
        setEditedContent('');
    };

    const handleCancelEdit = () => {
        setEditingChunkIndex(null);
        setEditedContent('');
    };

    const sortedChunks = [...group.chunks].sort((a, b) => a.chunk_index - b.chunk_index);

    return (
        <div className="knowledge-group-item">
            <div 
                className={`knowledge-header ${isExpanded ? 'expanded' : ''}`}
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="knowledge-info">
                    <h4>{group.query}</h4>
                    <div className="knowledge-meta">
                        <span className="update-time">
                            Uppdaterad: {new Date(group.updated_at).toLocaleString()}
                        </span>
                        <span className="chunk-count">
                            Antal chunks: {group.chunks.length}
                        </span>
                        {group.source && (
                            <span className="source-info">
                                Källa: {group.source}
                            </span>
                        )}
                    </div>
                </div>
                <div className="knowledge-actions">
                    <button 
                        className="delete-button"
                        onClick={(e) => {
                            e.stopPropagation();
                            onDelete(group.query, group.partition_id);
                        }}
                    >
                        <Trash2 size={16} />
                        <span>Ta bort</span>
                    </button>
                    <div className="expand-icon">
                        {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </div>
                </div>
            </div>

            {isExpanded && (
                <div className="knowledge-content">
                    {sortedChunks.map((chunk) => (
                        <div key={chunk.chunk_index} className="chunk">
                            <div className="chunk-header">
                                <span>Chunk {chunk.chunk_index + 1}</span>
                                {editingChunkIndex === chunk.chunk_index ? (
                                    <div className="chunk-actions">
                                        <button className="save-button" onClick={handleSaveChunk}>
                                            <Save size={16} />
                                            <span>Spara</span>
                                        </button>
                                        <button className="cancel-button" onClick={handleCancelEdit}>
                                            <X size={16} />
                                            <span>Avbryt</span>
                                        </button>
                                    </div>
                                ) : (
                                    <button 
                                        className="edit-button"
                                        onClick={() => handleEditChunk(chunk)}
                                    >
                                        <Edit2 size={16} />
                                        <span>Redigera</span>
                                    </button>
                                )}
                            </div>
                            {editingChunkIndex === chunk.chunk_index ? (
                                <textarea
                                    value={editedContent}
                                    onChange={(e) => setEditedContent(e.target.value)}
                                    className="chunk-textarea"
                                    rows={5}
                                />
                            ) : (
                                <div className="chunk-content">{chunk.content}</div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default KnowledgeGroup;
