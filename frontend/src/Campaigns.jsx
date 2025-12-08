import React, { useState } from 'react';

const Campaigns = ({ businessId, setCampaignId }) => {
  const [campaignName, setCampaignName] = useState('');

  const handleCreateCampaign = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/campaigns', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: campaignName,
          business_id: businessId,
        }),
      });

      const data = await response.json();
      if (response.ok) {
        alert(data.message);
        // TODO: Replace with the actual campaign ID from the API response
        setCampaignId(1);
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error creating campaign:', error);
      alert('An error occurred while creating the campaign.');
    }
  };

  return (
    <div>
      <h2>Create a New Campaign</h2>
      <form onSubmit={handleCreateCampaign}>
        <input
          type="text"
          value={campaignName}
          onChange={(e) => setCampaignName(e.target.value)}
          placeholder="Campaign Name"
          required
        />
        <button type="submit">Create and Start Campaign</button>
      </form>
    </div>
  );
};

export default Campaigns;
