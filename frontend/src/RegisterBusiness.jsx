import React, { useState } from 'react';

const RegisterBusiness = ({ user, onBusinessRegistered }) => {
  const [formData, setFormData] = useState({
    name: '',
    business_type: '',
    location: '',
    status: '',
    user_id: user.id,
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleRegisterBusiness = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/business', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const data = await response.json();
      if (response.ok) {
        alert('Business registered successfully!');
        onBusinessRegistered(data.business_id);
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error registering business:', error);
      alert('An error occurred during registration.');
    }
  };

  return (
    <div className="container">
      <h2>Register Your Business</h2>
      <form onSubmit={handleRegisterBusiness} className="form-group">
        <input type="text" name="name" value={formData.name} onChange={handleChange} placeholder="Business Name" required />
        <input type="text" name="business_type" value={formData.business_type} onChange={handleChange} placeholder="Business Type" required />
        <input type="text" name="location" value={formData.location} onChange={handleChange} placeholder="Location" required />
        <input type="text" name="status" value={formData.status} onChange={handleChange} placeholder="Status" />
        <button type="submit">Register Business</button>
      </form>
    </div>
  );
};

export default RegisterBusiness;
