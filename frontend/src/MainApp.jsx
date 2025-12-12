import React from 'react';
import App from './App';

const MainApp = () => {
  // Hardcoded user and businessId for simplicity
  const user = { id: 1, username: 'default_user' };
  const businessId = 1;

  const handleInvalidBusiness = () => {
    console.log("Business validation has been removed.");
  };

  return <App user={user} businessId={businessId} onInvalidBusiness={handleInvalidBusiness} />;
};

export default MainApp;
