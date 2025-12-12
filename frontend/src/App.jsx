import React, { useState, useEffect } from 'react';
import LeadsList from './LeadsList';
import Campaigns from './Campaigns';
import Dashboard from './Dashboard';
import './App.css'; // Import the CSS file

function App({ user, businessId, onInvalidBusiness }) {
  // --- Core State ---
  const [leads, setLeads] = useState([]);
  const [campaignId, setCampaignId] = useState(null);

  // --- UI State for Telegram Scraper ---
  const [groupLink, setGroupLink] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- Fetch Leads on Initial Load and After Changes ---
  const fetchLeads = async () => {
    if (!businessId) return;
    try {
      const response = await fetch(`/api/business/${businessId}/leads`);
      const data = await response.json();
      if (response.ok) {
        setLeads(data);
      } else {
        console.error('Error fetching leads:', data.error);
        if (data.error && data.error.includes('not found')) {
          onInvalidBusiness();
        }
      }
    } catch (err) {
      console.error('An error occurred while fetching leads:', err);
    }
  };

  useEffect(() => {
    if (businessId) {
      fetchLeads();
    }
  }, [businessId]);

  // --- Event Handlers ---
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
        fetchLeads(); // Refresh leads list
      } else {
        alert(`Error: ${generateData.error}`);
        if (generateData.error && generateData.error.includes('not found')) {
          onInvalidBusiness();
        }
      }
    } catch (error) {
      console.error('Error generating leads:', error);
      alert('An error occurred while generating leads.');
    }
  };

  const handleGroupLinkChange = (e) => {
    setGroupLink(e.target.value);
  };

  const handleScrapeTelegramGroup = async () => {
    if (!groupLink) {
      alert('Please enter a Telegram group link.');
      return;
    }
    if (!businessId) {
        alert('Please register or select a business first.');
        return;
    }
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/telegram/scrape_group', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_link: groupLink, business_id: businessId }),
      });

      const data = await response.json();

      if (response.ok) {
        alert(data.message || `Scraping complete. Found and saved ${data.saved_leads} new leads.`);
        fetchLeads();
      } else {
        const errorMessage = data.error || `Server error: ${response.status}`;
        setError(errorMessage);
        alert(`Error: ${errorMessage}`);
        if (errorMessage.includes('not found')) {
          onInvalidBusiness();
        }
      }
    } catch (err) {
      const errorMessage = 'An unexpected network error occurred.';
      setError(errorMessage);
      alert(`Error: ${errorMessage}`);
      console.error('Error scraping Telegram group:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Lead Generation Dashboard</h1>
      </header>

      <div>
        <div className="container">
          <h2>Lead Generation Tools</h2>
          <p>Enter a public Telegram group link to scrape its active members and add them as leads.</p>
          <div className="input-group">
            <input
              type="text"
              name="groupLink"
              value={groupLink}
              onChange={handleGroupLinkChange}
              placeholder="e.g., @groupname or https://t.me/groupname"
            />
            <button onClick={handleScrapeTelegramGroup} disabled={isLoading}>
              {isLoading ? 'Scraping...' : 'Scrape Telegram Leads'}
            </button>
            <button onClick={handleGenerateLeads}>
              Generate Leads (Mock)
            </button>
          </div>
          {error && <p style={{ color: 'red', marginTop: '10px' }}>Error: {error}</p>}
        </div>

        <LeadsList leads={leads} />
        <Campaigns businessId={businessId} setCampaignId={setCampaignId} />

        {campaignId && <Dashboard campaignId={campaignId} />}
      </div>
    </div>
  );
}

export default App;
