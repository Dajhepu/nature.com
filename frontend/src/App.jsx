import React, { useState } from 'react';
import LeadsList from './LeadsList';
import Campaigns from './Campaigns';
import Dashboard from './Dashboard';

function App() {
  const [leads, setLeads] = useState([]);
  const [businessId, setBusinessId] = useState(1);
  const [campaignId, setCampaignId] = useState(null);
  const [soha, setSoha] = useState('');

  const handleSohaChange = (e) => {
    setSoha(e.target.value);
  };

  const handleGenerateLeads = async () => {
    if (!businessId) {
      alert('Please register a business first.');
      return;
    }
    try {
      const generateResponse = await fetch(
        `/api/business/${businessId}/generate_leads`,
        { method: 'POST' }
      );
      const generateData = await generateResponse.json();
      if (generateResponse.ok) {
        alert(generateData.message);

        const leadsResponse = await fetch(`/api/business/${businessId}/leads`);
        const leadsData = await leadsResponse.json();
        if (leadsResponse.ok) {
          setLeads(leadsData);
        } else {
          alert(`Error fetching leads: ${leadsData.error}`);
        }
      } else {
        alert(`Error: ${generateData.error}`);
      }
    } catch (error) {
      console.error('Error generating leads:', error);
      alert('An error occurred while generating leads.');
    }
  };

  const handleScrapeInstagram = async () => {
    if (!businessId) {
      alert('Please register a business first.');
      return;
    }
    if (!soha) {
      alert('Please enter a soha.');
      return;
    }
    try {
      const response = await fetch('/api/scrape_instagram', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ soha, business_id: businessId }),
      });

      const data = await response.json();
      if (response.ok) {
        alert(data.message);
        // Refresh leads
        const leadsResponse = await fetch(`/api/business/${businessId}/leads`);
        const leadsData = await leadsResponse.json();
        if (leadsResponse.ok) {
          setLeads(leadsData);
        }
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error scraping Instagram:', error);
      alert('An error occurred while scraping Instagram.');
    }
  };

  return (
    <div className="App">
      {businessId && (
        <div>
          <input
            type="text"
            name="soha"
            value={soha}
            onChange={handleSohaChange}
            placeholder="Enter Soha (e.g., restoran)"
          />
          <button onClick={handleScrapeInstagram}>Scrape Instagram</button>
          <button onClick={handleGenerateLeads}>Generate Leads</button>
          <LeadsList leads={leads} />
          <Campaigns businessId={businessId} setCampaignId={setCampaignId} />
        </div>
      )}

      {campaignId && <Dashboard campaignId={campaignId} />}
    </div>
  );
}

export default App;
