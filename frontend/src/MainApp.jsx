import React, { useState, useEffect } from 'react';
import App from './App';
import Login from './Login';
import RegisterBusiness from './RegisterBusiness';

const MainApp = () => {
  const [user, setUser] = useState(null);
  const [businessId, setBusinessId] = useState(null);

  useEffect(() => {
    // Check for user and business info in local storage to persist session
    const storedUser = localStorage.getItem('user');
    const storedBusinessId = localStorage.getItem('businessId');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
      if (storedBusinessId) {
        setBusinessId(storedBusinessId);
      }
    }
  }, []);

  const handleLoginSuccess = (data) => {
    setUser(data.user);
    localStorage.setItem('user', JSON.stringify(data.user));
    if (data.business) {
      setBusinessId(data.business.id);
      localStorage.setItem('businessId', data.business.id);
    }
  };

  const handleBusinessRegistered = (newBusinessId) => {
    setBusinessId(newBusinessId);
    localStorage.setItem('businessId', newBusinessId);
  };

  const handleLogout = () => {
    setUser(null);
    setBusinessId(null);
    localStorage.removeItem('user');
    localStorage.removeItem('businessId');
  };

  if (!user) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  if (!businessId) {
    return <RegisterBusiness user={user} onBusinessRegistered={handleBusinessRegistered} />;
  }

  return <App user={user} businessId={businessId} onLogout={handleLogout} />;
};

export default MainApp;
