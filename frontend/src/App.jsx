import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './Login';
import Register from './Register';
import VerifyOTP from './VerifyOTP';
import Chat from './Chat';

// --- Temporary Placeholder Components ---
const TwoFactorAuth = () => <div>2FA Page (Enter Password)</div>;

// --- Security Wrapper ---
// Checks if the user has a token. If not, redirects them to /login.
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('access');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

// --- Main Application Router ---
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify-otp" element={<VerifyOTP />} />
        <Route path="/2fa" element={<TwoFactorAuth />} />
        
        {/* Protected Routes */}
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          } 
        />
      </Routes>
    </BrowserRouter>
  );
}