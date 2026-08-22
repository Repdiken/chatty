import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from './api';

export default function Login() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      // Hit the login OTP endpoint
      const response = await api.post('/auth/login/request-otp', { 
        phone_number: phoneNumber 
      });
      
      // Mimic SMS delivery by alerting the OTP returned from the dev server
      alert(response.data.message);
      
      // Send the user to the OTP page, passing the phone number and flow type in the state
      navigate('/verify-otp', { 
        state: { phone_number: phoneNumber, flow: 'login' } 
      });
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to request OTP.');
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '400px', margin: 'auto' }}>
      <h2>Login to Chatty</h2>
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
        <button type="submit" style={{ padding: '8px' }}>Request Login OTP</button>
      </form>
      
      <p style={{ marginTop: '15px' }}>
        Don't have an account? <Link to="/register">Register here</Link>
      </p>
    </div>
  );
}