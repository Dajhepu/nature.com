import React, { useState, useEffect } from 'react';

const Dashboard = ({ campaignId }) => {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch(
          `/api/campaigns/${campaignId}/metrics`
        );
        const data = await response.json();
        if (response.ok) {
          setMetrics(data);
        } else {
          console.error('Error fetching metrics:', data.error);
        }
      } catch (error) {
        console.error('Error fetching metrics:', error);
      }
    };

    if (campaignId) {
      fetchMetrics();
    }
  }, [campaignId]);

  if (!metrics) {
    return <div>Dashboard yuklanmoqda...</div>;
  }

  return (
    <div>
      <h2>{metrics.campaign_name}: Boshqaruv paneli</h2>
      <p>Jami Kontaktlar: {metrics.total_leads}</p>
      <p>Konversiya Darajasi: {metrics.conversion_rate * 100}%</p>
      <p>ROI (Kiritilgan sarmoya rentabelligi): {metrics.roi * 100}%</p>
      <p>Kafolat Jarayoni: {metrics.guarantee_progress.toFixed(2)}%</p>
    </div>
  );
};

export default Dashboard;
