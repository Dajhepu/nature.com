import React, { useState, useEffect } from 'react';

function MessageTemplates({ businessId }) {
  const [prompt, setPrompt] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingTemplate, setEditingTemplate] = useState(null);

  const fetchTemplates = async () => {
    if (!businessId) return;
    try {
      const response = await fetch(`/api/business/${businessId}/templates`);
      if (!response.ok) throw new Error('Shablonlarni yuklab bolmadi');
      const data = await response.json();
      setTemplates(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (templateId) => {
    if (window.confirm("Haqiqatdan ham bu shablonni o'chirmoqchimisiz?")) {
      try {
        const response = await fetch(`/api/templates/${templateId}`, {
          method: 'DELETE',
        });
        if (!response.ok) throw new Error("Shablonni o'chirishda xatolik");
        fetchTemplates(); // Refresh the list
      } catch (err) {
        setError(err.message);
      }
    }
  };

  const handleEdit = (template) => {
    setEditingTemplate(template);
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!editingTemplate) return;

    try {
      const response = await fetch(`/api/templates/${editingTemplate.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: editingTemplate.name,
          content: editingTemplate.content,
        }),
      });

      if (!response.ok) throw new Error("Shablonni yangilashda xatolik");

      setEditingTemplate(null);
      fetchTemplates(); // Refresh the list
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, [businessId]);

  const handleGenerateSuggestions = async () => {
    if (!prompt) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/ai/generate_template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });
      if (!response.ok) throw new Error('Takliflarni olib bolmadi');
      const data = await response.json();
      setSuggestions(data.suggestions);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveTemplate = async (content) => {
    const name = prompt.substring(0, 20) || 'Yangi AI Shablon';
    try {
      const response = await fetch(`/api/business/${businessId}/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, content }),
      });
      if (!response.ok) throw new Error('Shablonni saqlashda xatolik');
      fetchTemplates(); // Refresh the list
      setSuggestions([]); // Clear suggestions
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div>
      {/* AI Template Generation */}
      <div className="container">
        <h2>AI Yordamida Shablon Yaratish</h2>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Mahsulotingiz yoki xizmatingiz haqida qisqacha yozing..."
          rows="3"
        />
        <button onClick={handleGenerateSuggestions} disabled={isLoading}>
          {isLoading ? 'Yaratilmoqda...' : 'Takliflar Yaratish'}
        </button>
        {error && <p className="error-message">{error}</p>}
        <div className="suggestions-list">
          {suggestions.map((s, index) => (
            <div key={index} className="suggestion-item">
              <p>{s}</p>
              <button onClick={() => handleSaveTemplate(s)}>Shablon sifatida saqlash</button>
            </div>
          ))}
        </div>
      </div>

      {/* Saved Templates */}
      <div className="container">
        <h2>Saqlangan Shablonlar</h2>
        <ul className="templates-list">
          {templates.map(t => (
            <li key={t.id} className="template-item">
              <div>
                <strong>{t.name}</strong>
                <p>{t.content}</p>
              </div>
              <div className="template-actions">
                <button onClick={() => handleEdit(t)}>Tahrirlash</button>
                <button onClick={() => handleDelete(t.id)}>O'chirish</button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {editingTemplate && (
        <div className="modal-backdrop">
          <div className="modal">
            <h2>Shablonni Tahrirlash</h2>
            <form onSubmit={handleUpdate}>
              <input
                type="text"
                value={editingTemplate.name}
                onChange={(e) => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
              />
              <textarea
                value={editingTemplate.content}
                onChange={(e) => setEditingTemplate({ ...editingTemplate, content: e.target.value })}
                rows="5"
              />
              <div className="modal-actions">
                <button type="submit">Saqlash</button>
                <button type="button" onClick={() => setEditingTemplate(null)}>Bekor qilish</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default MessageTemplates;
