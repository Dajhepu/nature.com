import React, { useState } from 'react';
import LeadsList from './LeadsList';
import Campaigns from './Campaigns';
import Dashboard from './Dashboard';
import Login from './Login';
import Register from './Register';

function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [showRegister, setShowRegister] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    business_type: '',
    location: '',
    status: '',
    user_id: null,
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

  const handleRegisterBusiness = async (e) => {
    e.preventDefault();
    if (!currentUser) {
      alert("Please log in to register a business.");
      return;
    }

    const businessData = { ...formData, user_id: currentUser.id };

    try {
      const response = await fetch('/api/business', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(businessData),
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

  if (!loggedIn) {
    return (
      <div>
        {showRegister ? (
          <Register />
        ) : (
          <Login setLoggedIn={setLoggedIn} setCurrentUser={setCurrentUser} />
        )}
        <button onClick={() => setShowRegister(!showRegister)}>
          {showRegister ? 'Go to Login' : 'Go to Register'}
        </button>
      </div>
    );
  }

  return (
    <div className="App">
      <h1>Register Your Business</h1>
      <form onSubmit={handleRegisterBusiness}>
        <input type="text" name="name" value={formData.name} onChange={handleChange} placeholder="Business Name" />
        <input type="text" name="business_type" value={formData.business_type} onChange={handleChange} placeholder="Business Type" />
        <input type="text" name="location" value={formData.location} onChange={handleChange} placeholder="Location" />
        <input type="text" name="status" value={formData.status} onChange={handleChange} placeholder="Status" />
        <button type="submit">Register Business</button>
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
