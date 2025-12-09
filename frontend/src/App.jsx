import React, { useState } from 'react';
import LeadsList from './LeadsList';
import Campaigns from './Campaigns';
import Dashboard from './Dashboard';

function App() {
  const [formData, setFormData] = useState({
    name: '',
    business_type: '',
    location: '',
    status: '',
    user_id: 1, // TODO: Replace with authenticated user ID
  });
  const [leads, setLeads] = useState([]);
  const [businessId, setBusinessId] = useState(null);
  const [campaignId, setCampaignId] = useState(null);
  const [soha, setSoha] = useState('');

  // Expose setBusinessId for Playwright verification
  if (process.env.NODE_ENV === 'development') {
    window.setBusinessId = setBusinessId;
  }

  const handleSohaChange = (e) => {
    setSoha(e.target.value);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/business', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();
      if (response.ok) {
        alert('Business registered successfully!');
        // TODO: Replace with the actual business ID from the API response
        setBusinessId(1);
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error registering business:', error);
      alert('An error occurred during registration.');
    }
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
        alert(`Error: ${data.error}`);
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
      <h1>Register Your Business</h1>
      <form onSubmit={handleRegister}>
        {/* Form inputs... */}
        <button type="submit">Register</button>
      </form>

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
