import { useState, useEffect } from 'react';
import mermaid from 'mermaid';
import './DiagramEditor.css';

function DiagramEditor() {
  const [diagrams, setDiagrams] = useState([]);
  const [currentDiagram, setCurrentDiagram] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [diagramContent, setDiagramContent] = useState('graph TD\n  A --> B');
  const [renderedSvg, setRenderedSvg] = useState('');

  // Load diagrams on mount
  useEffect(() => {
    fetchDiagrams();
  }, []);

  // Configure mermaid once
  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, theme: 'default' });
  }, []);

  // Render preview when content changes
  useEffect(() => {
    const render = async () => {
      try {
        const { svg } = await mermaid.render('preview', diagramContent);
        setRenderedSvg(svg);
      } catch (err) {
        console.error('Mermaid render error:', err);
        setRenderedSvg('<pre style="color:red">Render error</pre>');
      }
    };
    render();
  }, [diagramContent]);

  const fetchDiagrams = async () => {
    try {
      const response = await fetch('http://api.test/api/diagrams');
      const data = await response.json();
      setDiagrams(data || []);
    } catch (error) {
      console.error('Error fetching diagrams:', error);
    }
  };

  const getCodeFromEditor = () => diagramContent;

  const saveDiagram = async () => {
    if (!title.trim()) {
      alert('Please enter a title');
      return;
    }

    // Use the textarea content as the source of truth
    const content = getCodeFromEditor();
    
    if (!content.trim()) {
      alert('Please enter diagram content');
      return;
    }

    try {
      const isUpdate = currentDiagram !== null;
      const url = isUpdate 
        ? `http://api.test/api/diagrams/${currentDiagram.id}`
        : 'http://api.test/api/diagrams';
      
      const response = await fetch(url, {
        method: isUpdate ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          content: content.trim(),
          created_by: 'current_user',
          tags: ['mermaid']
        })
      });

      if (response.ok) {
        const saved = await response.json();
        alert(isUpdate ? `Diagram updated: ${saved.title}` : `Diagram saved: ${saved.title}`);
        setTitle('');
        setDescription('');
        setDiagramContent('graph TD\n  A --> B');
        setCurrentDiagram(null);
        updateIframeWithContent('graph TD\n  A --> B');
        fetchDiagrams();
      } else {
        const error = await response.json();
        alert(`Error saving diagram: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error saving diagram:', error);
      alert('Error saving diagram: ' + error.message);
    }
  };

  const loadDiagram = async (diagram) => {
    console.log('Loading diagram:', diagram);
    try {
      const url = `http://api.test/api/diagrams/${diagram.id}/content`;
      console.log('Fetching from:', url);
      const response = await fetch(url);
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Received data:', data);
      
      setCurrentDiagram(diagram);
      setTitle(diagram.title);
      setDescription(diagram.description || '');
      setDiagramContent(data.content);
      
      console.log('Diagram loaded successfully!');
    } catch (error) {
      console.error('Error loading diagram:', error);
      alert('Error loading diagram: ' + error.message);
    }
  };

  const deleteDiagram = async (diagramId) => {
    if (!confirm('Are you sure you want to delete this diagram?')) {
      return;
    }

    try {
      const response = await fetch(`http://api.test/api/diagrams/${diagramId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        alert('Diagram deleted successfully');
        fetchDiagrams();
        if (currentDiagram && currentDiagram.id === diagramId) {
          setCurrentDiagram(null);
          setTitle('');
          setDescription('');
          setDiagramContent('graph TD\n  A --> B');
        }
      }
    } catch (error) {
      console.error('Error deleting diagram:', error);
      alert('Error deleting diagram');
    }
  };

  return (
    <div className="diagram-editor">
      <div className="sidebar">
        <h2>Saved Diagrams</h2>
        <div className="diagram-list">
          {diagrams.map((diagram) => (
            <div 
              key={diagram.id} 
              className={`diagram-item ${currentDiagram?.id === diagram.id ? 'active' : ''}`}
            >
              <div onClick={() => loadDiagram(diagram)}>
                <h3>{diagram.title}</h3>
                <p>{diagram.description}</p>
                <small>{new Date(diagram.created_at).toLocaleDateString()}</small>
              </div>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  deleteDiagram(diagram.id);
                }}
                className="delete-btn"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="main-content">
        <div className="toolbar">
          <input
            type="text"
            placeholder="Diagram Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="title-input"
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="description-input"
          />
          <button onClick={saveDiagram} className="save-btn">
            {currentDiagram ? 'Update Diagram' : 'Save Diagram'}
          </button>
          {currentDiagram && (
            <button 
              onClick={() => {
                setCurrentDiagram(null);
                setTitle('');
                setDescription('');
                setDiagramContent('graph TD\n  A --> B');
              }}
              className="new-btn"
            >
              New Diagram
            </button>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px', height: '100%', overflow: 'hidden' }}>
          {/* Code editor sidebar */}
          <div style={{ flex: '0 0 320px', display: 'flex', flexDirection: 'column', borderRight: '1px solid #ddd', backgroundColor: '#f9f9f9' }}>
            <div style={{ padding: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #ddd' }}>
              <label style={{ fontSize: '0.9rem', fontWeight: '500', color: '#333', margin: 0 }}>
                Diagram Code
              </label>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(diagramContent);
                  alert('Code copied to clipboard!');
                }}
                style={{
                  fontSize: '0.75rem',
                  padding: '4px 8px',
                  background: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '3px',
                  cursor: 'pointer'
                }}
              >
                Copy
              </button>
            </div>
            <textarea
              value={diagramContent}
              onChange={(e) => setDiagramContent(e.target.value)}
              placeholder="Edit diagram code here..."
              style={{
                flex: 1,
                padding: '10px',
                border: 'none',
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                resize: 'none',
                overflow: 'auto',
                backgroundColor: 'white'
              }}
            />
          </div>

          {/* Mermaid inline preview */}
          <div className="preview-container">
            <div
              className="mermaid-preview"
              dangerouslySetInnerHTML={{ __html: renderedSvg }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default DiagramEditor;
