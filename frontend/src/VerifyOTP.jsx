import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from './api';

export default function VerifyOTP() {
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  
  const location = useLocation();
  const navigate = useNavigate();

  // Grab the phone number and flow type passed from the previous screen
  const phoneNumber = location.state?.phone_number;
  const flow = location.state?.flow; // 'login' or 'register'

  // If someone tries to access this page directly via URL, kick them back to login
  if (!phoneNumber || !flow) {
    navigate('/login');
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Determine the correct endpoint based on where they came from
    const endpoint = flow === 'register' 
      ? '/auth/register/verify' 
      : '/auth/login/verify';
    
    try {
      const response = await api.post(endpoint, {
        phone_number: phoneNumber,
        otp: otp
      });

      // Scenario A: Backend returns tokens immediately (Registration or standard Login)
      if (response.data.access) {
        localStorage.setItem('access', response.data.access);
        localStorage.setItem('refresh', response.data.refresh);
        navigate('/'); // Send them to the main chat!
      } 
      // Scenario B: Backend confirms OTP but withholds tokens (2FA required)
      else if (response.data.message === "OTP verified.") {
        navigate('/2fa', { state: { phone_number: phoneNumber } });
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Invalid OTP.');
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '400px', margin: 'auto' }}>
      <h2>Verify OTP</h2>
      <p>Code sent to: {phoneNumber}</p>
      
      {error && <p style={{ color: 'red' }}>{error}</p>}
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <input 
          type="text" 
          placeholder="123456" 
          value={otp} 
          onChange={(e) => setOtp(e.target.value)} 
          maxLength="6"
          required 
          style={{ padding: '8px' }}
        />
        <button type="submit" style={{ padding: '8px' }}>Verify Code</button>
      </form>
    </div>
  );
}