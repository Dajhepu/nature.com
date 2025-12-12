import React, { useState, useEffect } from 'react';
import './CampaignModal.css';

const CampaignModal = ({ businessId, leadIds, onClose, onCampaignStart }) => {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [campaignName, setCampaignName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTemplates = async () => {
      if (!businessId) return;
      try {
        const response = await fetch(`/api/business/${businessId}/templates`);
        if (!response.ok) throw new Error('Failed to fetch templates');
        const data = await response.json();
        setTemplates(data);
      } catch (err) {
        setError(err.message);
      }
    };
    fetchTemplates();
  }, [businessId]);

  const handleStartCampaign = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/campaigns/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_id: businessId,
          template_id: selectedTemplate,
          lead_ids: leadIds,
          name: campaignName,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start campaign');
      }
      const data = await response.json();
      alert(data.message); // Show success message from the backend
      onCampaignStart();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <h2>Start a New Campaign</h2>
        <p>You are about to send a message to {leadIds.length} lead(s).</p>

        <div className="form-group">
          <label htmlFor="campaignName">Campaign Name</label>
          <input
            type="text"
            id="campaignName"
            value={campaignName}
            onChange={(e) => setCampaignName(e.target.value)}
            placeholder="e.g., 'Q1 Promo'"
          />
        </div>

        <div className="form-group">
          <label htmlFor="templateSelect">Select Message Template</label>
          <select
            id="templateSelect"
            value={selectedTemplate}
            onChange={(e) => setSelectedTemplate(e.target.value)}
          >
            <option value="">Shablonni tanlang...</option>
            {templates.map(template => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="error-message">{error}</p>}

        <div className="modal-actions">
          <button onClick={onClose} disabled={isLoading}>Cancel</button>
          <button onClick={handleStartCampaign} disabled={isLoading || !selectedTemplate || !campaignName}>
            {isLoading ? 'Starting...' : 'Start Campaign'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CampaignModal;
