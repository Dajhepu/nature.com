import React, { useState } from 'react';
import CampaignModal from './CampaignModal';

const LeadsList = ({ leads, businessId }) => {
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleSelectLead = (leadId) => {
    setSelectedLeads(prev =>
      prev.includes(leadId)
        ? prev.filter(id => id !== leadId)
        : [...prev, leadId]
    );
  };

  return (
    <div className="container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Generated Leads ({leads.length})</h2>
        {selectedLeads.length > 0 && (
          <button onClick={() => setIsModalOpen(true)}>
            Send Message to {selectedLeads.length} Lead(s)
          </button>
        )}
      </div>
      <ul className="leads-list">
        {leads.map((lead) => (
          <li key={lead.id} className="lead-item">
            <input
              type="checkbox"
              checked={selectedLeads.includes(lead.id)}
              onChange={() => handleSelectLead(lead.id)}
              style={{ marginRight: '1rem' }}
            />
            <strong>{lead.full_name}</strong> (Score: {lead.activity_score})
            <p>@{lead.username || 'N/A'} - Source: {lead.source}</p>
          </li>
        ))}
      </ul>
      {isModalOpen && (
        <CampaignModal
          businessId={businessId}
          leadIds={selectedLeads}
          onClose={() => setIsModalOpen(false)}
          onCampaignStart={() => {
            setIsModalOpen(false);
            setSelectedLeads([]);
            // Optionally, refresh campaigns or show a success message
          }}
        />
      )}
    </div>
  );
};

export default LeadsList;
