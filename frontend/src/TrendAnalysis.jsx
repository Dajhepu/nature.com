// frontend/src/TrendAnalysis.jsx
import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts';
import { WordCloud } from '@isoterik/react-word-cloud';

const TrendAnalysis = ({ businessId }) => {

  const getSentimentEmoji = (sentiment) => {
    switch (sentiment) {
      case 'positive': return '😊';
      case 'negative': return '😠';
      default: return '😐';
    }
  };

  const trendItemStyle = {
    marginBottom: '1rem',
    paddingBottom: '0.5rem',
    borderBottom: '1px solid #444'
  };

  const [groups, setGroups] = useState([]);
  const [newGroupLink, setNewGroupLink] = useState('');
  const [trends, setTrends] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch monitored groups on component load
  useEffect(() => {
    fetchGroups();
    fetchTrends();
  }, [businessId]);

  const fetchGroups = async () => {
    try {
      const response = await fetch(`/api/business/${businessId}/monitored_groups`);
      if (response.ok) {
        const data = await response.json();
        setGroups(data);
      } else {
        console.error("Failed to fetch groups");
      }
    } catch (err) {
      console.error("Error fetching groups:", err);
    }
  };

  const fetchTrends = async () => {
    try {
      const response = await fetch(`/api/business/${businessId}/trends`);
      if (response.ok) {
        const data = await response.json();
        setTrends(data);
      } else {
        console.error("Failed to fetch trends");
      }
    } catch (err) {
      console.error("Error fetching trends:", err);
    }
  };

  const handleAddGroup = async () => {
    if (!newGroupLink) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/business/${businessId}/monitored_groups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_link: newGroupLink }),
      });
      const data = await response.json();
      if (response.ok) {
        setGroups([...groups, data.group]);
        setNewGroupLink('');
      } else {
        setError(data.error || "Failed to add group");
      }
    } catch (err) {
      setError("An unexpected error occurred.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleTriggerAnalysis = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/business/${businessId}/trigger_analysis`, {
        method: 'POST',
      });
      const data = await response.json();
      if (response.ok) {
        alert(data.message);
        fetchTrends(); // Refresh trends after analysis
      } else {
        setError(data.error || "Failed to trigger analysis");
      }
    } catch (err) {
      setError("An unexpected error occurred during analysis.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container">
      <h2>Trend Tahlili</h2>

      {/* Group Management */}
      <div className="input-group">
        <h3>Kuzatiladigan Guruhlar</h3>
        <ul>
          {groups.map(g => <li key={g.id}>{g.group_link}</li>)}
        </ul>
        <input
          type="text"
          value={newGroupLink}
          onChange={(e) => setNewGroupLink(e.target.value)}
          placeholder="Yangi guruh havolasi (masalan, @durov)"
        />
        <button onClick={handleAddGroup} disabled={isLoading}>
          {isLoading ? 'Qo\'shilmoqda...' : 'Guruh Qo\'shish'}
        </button>
      </div>

      {/* Analysis Trigger */}
      <div className="input-group" style={{ marginTop: '2rem' }}>
        <h3>Tahlil</h3>
        <p>Guruhlardagi so'nggi xabarlarni tahlil qilish uchun quyidagi tugmani bosing.</p>
        <button onClick={handleTriggerAnalysis} disabled={isLoading}>
          {isLoading ? 'Tahlil qilinmoqda...' : 'Tahlilni Boshlash'}
        </button>
      </div>

      {error && <p style={{ color: 'red' }}>Xatolik: {error}</p>}

      {/* Trend Results */}
      <div style={{ marginTop: '2rem', display: 'flex', gap: '2rem' }}>
        <div style={{ flex: 1 }}>
          <h3>Top 10 Trenddagi So'zlar</h3>
          {trends.length > 0 ? (
            <ul>
              {trends.map(t => (
                <li key={t.word} style={trendItemStyle}>
                  <div>
                    <strong>{t.word}</strong> {getSentimentEmoji(t.sentiment)}
                  </div>
                  <small>Trend Skori: {t.trend_score}</small>
                  <p style={{ margin: '0.5rem 0 0', fontStyle: 'italic' }}>"{t.summary}"</p>
                </li>
              ))}
            </ul>
          ) : (
            <p>Ma'lumotlar yo'q.</p>
          )}
        </div>
        <div style={{ flex: 2 }}>
          <h3>So'zlar Buluti</h3>
          {trends.length > 0 ? (
            <div style={{ height: '400px', width: '100%' }}>
              <WordCloud
                words={trends.map(t => ({ text: t.word, value: t.trend_score }))}
                width={400}
                height={400}
              />
            </div>
          ) : (
            <p>Hozircha trendlar mavjud emas. Tahlilni boshlang.</p>
          )}
        </div>
      </div>
      <div style={{ marginTop: '2rem' }}>
          <h3>Trend Grafik</h3>
          {trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="word" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="trend_score" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p>Grafik uchun ma'lumotlar yo'q.</p>
          )}
        </div>
    </div>
  );
};

export default TrendAnalysis;
