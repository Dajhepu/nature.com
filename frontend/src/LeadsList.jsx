import React from 'react';

const LeadsList = ({ leads }) => {
  return (
    <div>
      <h2>Generated Leads</h2>
      <ul>
        {leads.map((lead) => (
          <li key={lead.id}>
            <strong>{lead.full_name}</strong> (Score: {lead.activity_score})
            <p>@{lead.username || 'N/A'} - Source: {lead.source}</p>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default LeadsList;
