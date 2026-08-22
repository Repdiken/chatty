import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from './api';

export default function Register() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      // Hit the registration OTP endpoint
      const response = await api.post('/auth/register/request-otp', { 
        phone_number: phoneNumber 
      });
      
      alert(response.data.message);
      
      // Send the user to the OTP page, noting this is a registration flow
      navigate('/verify-otp', { 
        state: { phone_number: phoneNumber, flow: 'register' } 
      });
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to request OTP.');
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '400px', margin: 'auto' }}>
      <h2>Register for Chatty</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <input 
          type="text" 
          placeholder="+905XXXXXXXXX" 
          value={phoneNumber} 
          onChange={(e) => setPhoneNumber(e.target.value)} 
          required 
          style={{ padding: '8px' }}
        />
        <button type="submit" style={{ padding: '8px' }}>Request Registration OTP</button>
      </form>
      
      <p style={{ marginTop: '15px' }}>
        Already have an account? <Link to="/login">Login here</Link>
      </p>
    </div>
  );
}