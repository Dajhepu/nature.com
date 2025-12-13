
// frontend/src/Analytics.jsx
import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const Analytics = ({ businessId }) => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await fetch(`/api/business/${businessId}/analytics`);
        if (response.ok) {
          const data = await response.json();
          setAnalytics(data);
        } else {
          setError('Failed to fetch analytics data');
        }
      } catch (err) {
        setError('An error occurred while fetching analytics data');
      } finally {
        setLoading(false);
      }
    };

    if (businessId) {
      fetchAnalytics();
    }
  }, [businessId]);

  if (loading) {
    return <div className="container"><p>Loading analytics...</p></div>;
  }

  if (error) {
    return <div className="container"><p>{error}</p></div>;
  }

  if (!analytics) {
    return <div className="container"><p>No analytics data available.</p></div>;
  }

  const statusData = Object.entries(analytics.lead_status_distribution).map(([name, value]) => ({ name, value }));
  const sourceData = Object.entries(analytics.leads_by_source).map(([name, value]) => ({ name, value }));
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF'];

  return (
    <div className="container">
      <h2>Analytics Dashboard</h2>
      <div className="analytics-summary">
        <div className="summary-card">
          <h3>Total Leads</h3>
          <p>{analytics.total_leads}</p>
        </div>
        <div className="summary-card">
          <h3>Total Messages Sent</h3>
          <p>{analytics.total_messages_sent}</p>
        </div>
      </div>
      <div className="analytics-charts">
        <div className="chart-container">
          <h3>Lead Status Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} fill="#8884d8" label>
                {statusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="chart-container">
          <h3>Leads by Source</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={sourceData}>
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
