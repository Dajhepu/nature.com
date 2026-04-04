import React, { useState, useEffect } from 'react';
import LeadsList from './LeadsList';
import Dashboard from './Dashboard';
import MessageTemplates from './MessageTemplates';
import TrendAnalysis from './TrendAnalysis'; // Import the new component
import Analytics from './Analytics'; // Import the new component
import SmartMoney from './SmartMoney';
import './App.css'; // Import the CSS file

function App({ user, businessId, onInvalidBusiness }) {
  // --- Core State ---
  const [leads, setLeads] = useState([]);
  const [currentView, setCurrentView] = useState('leads'); // 'leads', 'templates', 'trends', 'analytics', or 'smart-money'

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
  const handleGroupLinkChange = (e) => {
    setGroupLink(e.target.value);
  };

  const handleScrapeTelegramGroup = async () => {
    if (!groupLink) {
      alert('Iltimos, Telegram guruhi havolasini kiriting.');
      return;
    }
    if (!businessId) {
        alert('Iltimos, avval ro\'yxatdan o\'ting yoki biznesni tanlang.');
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
        alert(data.message || `Skanerlash yakunlandi. ${data.saved_leads} ta yangi lead topildi va saqlandi.`);
        fetchLeads();
      } else {
        const errorMessage = data.error || `Server xatosi: ${response.status}`;
        setError(errorMessage);
        alert(`Xato: ${errorMessage}`);
        if (errorMessage.includes('not found')) {
          onInvalidBusiness();
        }
      }
    } catch (err) {
      const errorMessage = 'Kutilmagan tarmoq xatosi yuz berdi.';
      setError(errorMessage);
      alert(`Xato: ${errorMessage}`);
      console.error('Error scraping Telegram group:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Lead Yaratish Paneli</h1>
        <nav>
          <button onClick={() => setCurrentView('leads')} className={currentView === 'leads' ? 'active' : ''}>
            Kontaktlar
          </button>
          <button onClick={() => setCurrentView('templates')} className={currentView === 'templates' ? 'active' : ''}>
            Xabar Shablonlari
          </button>
          <button onClick={() => setCurrentView('trends')} className={currentView === 'trends' ? 'active' : ''}>
            Trendlar Tahlili
          </button>
          <button onClick={() => setCurrentView('analytics')} className={currentView === 'analytics' ? 'active' : ''}>
            Analitika
          </button>
          <button onClick={() => setCurrentView('smart-money')} className={currentView === 'smart-money' ? 'active' : ''}>
            Aqlli Hamyonlar
          </button>
        </nav>
      </header>

      <div>
        {currentView === 'leads' && (
          <>
            <div className="container">
              <h2>Lead Yaratish Asboblari</h2>
              <p>Faol a'zolarni skanerlash va ularni lead sifatida qo'shish uchun ommaviy Telegram guruhi havolasini kiriting.</p>
              <div className="input-group">
                <input
                  type="text"
                  name="groupLink"
                  value={groupLink}
                  onChange={handleGroupLinkChange}
                  placeholder="masalan, @groupname yoki https://t.me/groupname"
                />
                <button onClick={handleScrapeTelegramGroup} disabled={isLoading}>
                  {isLoading ? 'Skanerlanmoqda...' : 'Telegram Leadlarni Skanerlash'}
                </button>
              </div>
              {error && <p style={{ color: 'red', marginTop: '10px' }}>Xato: {error}</p>}
            </div>
            <LeadsList leads={leads} businessId={businessId} setLeads={setLeads} />
          </>
        )}
        {currentView === 'templates' && <MessageTemplates businessId={businessId} />}
        {currentView === 'trends' && <TrendAnalysis businessId={businessId} />}
        {currentView === 'analytics' && <Analytics businessId={businessId} />}
        {currentView === 'smart-money' && <SmartMoney businessId={businessId} onClose={() => setCurrentView('leads')} />}
      </div>
    </div>
  );
}

export default App;
