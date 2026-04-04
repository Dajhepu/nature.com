import React, { useState } from 'react';
import CampaignModal from './CampaignModal';

const LeadsList = ({ leads, businessId, setLeads }) => {
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleStatusChange = async (leadId, newStatus) => {
    try {
      const response = await fetch(`/api/leads/${leadId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (response.ok) {
        const updatedLead = await response.json();
        setLeads(leads.map(lead => (lead.id === updatedLead.id ? updatedLead : lead)));
      } else {
        console.error('Failed to update lead status');
      }
    } catch (error) {
      console.error('Error updating lead status:', error);
    }
  };

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
        <h2>Yig'ilgan Kontaktlar ({leads.length})</h2>
        {selectedLeads.length > 0 && (
          <button onClick={() => setIsModalOpen(true)}>
            {selectedLeads.length} ta kontaktga xabar yuborish
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
            <strong>{lead.full_name}</strong> (Reyting: {lead.activity_score})
            <p>@{lead.username || 'Mavjud Emas'} - Manba: {lead.source}</p>
            <select
              value={lead.status || 'New'}
              onChange={(e) => handleStatusChange(lead.id, e.target.value)}
              style={{ marginLeft: 'auto' }}
            >
              <option value="New">New</option>
              <option value="Contacted">Contacted</option>
              <option value="Interested">Interested</option>
              <option value="Converted">Converted</option>
              <option value="Not Interested">Not Interested</option>
            </select>
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
