import React from 'react';

const LeadsList = ({ leads }) => {
  return (
    <div>
      <h2>Generated Leads</h2>
      <ul>
        {leads.map((lead) => (
          <li key={lead.id}>
            <strong>{lead.customer_name}</strong> ({lead.sentiment})
            <p>{lead.review_text}</p>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default LeadsList;
