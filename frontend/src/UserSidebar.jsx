import { useState } from 'react';
import api from './api';

// Notice we added onChatCreated to the props!
export default function UserSidebar({ currentUser, setCurrentUser, onChatCreated }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeModal, setActiveModal] = useState(null); // 'profile', '2fa', or 'group'
  const [isHoveringPfp, setIsHoveringPfp] = useState(false);

  // --- Draft Profile State ---
  const [draftProfile, setDraftProfile] = useState({
    first_name: '', last_name: '', username: '', bio: '', pfpPreview: '', pfpFile: null,
  });

  // --- 2FA State ---
  const [passwords, setPasswords] = useState({ current: '', newPass: '', confirm: '' });
  const [twoFactorAction, setTwoFactorAction] = useState('menu');
  const [error, setError] = useState('');

  // --- Group Chat State ---
  const [groupTitle, setGroupTitle] = useState('');
  const [groupUsernames, setGroupUsernames] = useState('');

  // --- Helpers ---
  const getPfpUrl = (user) => {
    if (user?.profile_picture) {
      const url = user.profile_picture;
      return url.startsWith('http') ? url : `http://127.0.0.1:8000${url}`;
    }
    const name = user?.first_name || user?.username || 'User';
    return `https://ui-avatars.com/api/?background=ffffff&color=008069&name=${encodeURIComponent(name)}`;
  };

  const openProfileModal = () => {
    setDraftProfile({
      first_name: currentUser?.first_name || '',
      last_name: currentUser?.last_name || '',
      username: currentUser?.username || '',
      bio: currentUser?.bio || '',
      pfpPreview: getPfpUrl(currentUser),
      pfpFile: null,
    });
    setActiveModal('profile');
    setIsOpen(false);
  };

  // --- API Handlers ---
  const handlePfpSelection = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setDraftProfile((prev) => ({ ...prev, pfpFile: file, pfpPreview: URL.createObjectURL(file) }));
  };

  const handleMasterSave = async () => {
    try {
      if (draftProfile.username !== (currentUser?.username || '')) {
        await api.patch('/users/me/about/username-change', { username: draftProfile.username });
      }

      const formData = new FormData();
      let hasFormData = false;

      if (draftProfile.first_name !== (currentUser?.first_name || '')) { formData.append('first_name', draftProfile.first_name); hasFormData = true; }
      if (draftProfile.last_name !== (currentUser?.last_name || '')) { formData.append('last_name', draftProfile.last_name); hasFormData = true; }
      if (draftProfile.bio !== (currentUser?.bio || '')) { formData.append('bio', draftProfile.bio); hasFormData = true; }
      if (draftProfile.pfpFile) { formData.append('profile_picture', draftProfile.pfpFile); hasFormData = true; }

      if (hasFormData) {
        await api.patch('/users/me/about/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      }

      const res = await api.get('/users/me/about/');
      setCurrentUser(res.data);
      setActiveModal(null);
    } catch (err) {
      alert("Failed to save changes: " + JSON.stringify(err.response?.data || err.message));
    }
  };

  const handle2FASubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      let res;
      if (twoFactorAction === 'remove') {
        res = await api.put('/users/me/security/2fa/remove', { current_password: passwords.current });
      } else {
        const payload = currentUser.two_factor_enabled
          ? { current_password: passwords.current, new_password: passwords.newPass, new_password_2: passwords.confirm }
          : { password: passwords.newPass, password_2: passwords.confirm };
        res = await api.put('/users/me/security/2fa', payload);
      }

      if (res.data.access) {
        localStorage.setItem('access', res.data.access);
        localStorage.setItem('refresh', res.data.refresh);
      }
      
      setCurrentUser((prev) => ({ ...prev, two_factor_enabled: twoFactorAction !== 'remove' }));
      setTwoFactorAction('menu');
      setPasswords({ current: '', newPass: '', confirm: '' });
      alert(res.data.message);
    } catch (err) {
      setError(JSON.stringify(err.response?.data || "An error occurred."));
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    try {
      // Split comma-separated usernames and remove extra spaces
      const usernamesArray = groupUsernames.split(',').map(u => u.trim()).filter(u => u !== '');
      
      // I am assuming your endpoint for groups is /conversations/create-group based on our earlier setup
      await api.post('/conversations/create-group', {
        title: groupTitle,
        usernames: usernamesArray
      });

      // Refresh the chat list in the main window!
      if (onChatCreated) onChatCreated();
      
      setActiveModal(null);
      setGroupTitle('');
      setGroupUsernames('');
    } catch (err) {
      alert(JSON.stringify(err.response?.data) || "Failed to create group.");
    }
  };

  // --- UI Components ---
  const renderProfileModal = () => (
    // ... Exactly the same as before, left collapsed for brevity ...
    <div style={modalOverlayStyle} onClick={() => setActiveModal(null)}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ marginTop: 0, textAlign: 'center' }}>My Profile</h3>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
          <div 
            style={{ position: 'relative', width: '90px', height: '90px', borderRadius: '50%', overflow: 'hidden', cursor: 'pointer', border: '2px solid #008069' }}
            onMouseEnter={() => setIsHoveringPfp(true)}
            onMouseLeave={() => setIsHoveringPfp(false)}
            onClick={() => document.getElementById('pfp-upload-input').click()}
          >
            <img src={draftProfile.pfpPreview} alt="PFP" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            {isHoveringPfp && <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: '0.8rem', fontWeight: 'bold' }}>Upload</div>}
            <input type="file" id="pfp-upload-input" style={{ display: 'none' }} accept="image/*" onChange={handlePfpSelection} />
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          {['first_name', 'last_name', 'username', 'bio'].map((field) => (
            <div key={field} style={{ display: 'flex', flexDirection: 'column' }}>
              <label style={{ color: '#008069', fontSize: '0.85rem', textTransform: 'capitalize', marginBottom: '4px', fontWeight: 'bold' }}>{field.replace('_', ' ')}</label>
              <input type="text" value={draftProfile[field]} onChange={(e) => setDraftProfile({ ...draftProfile, [field]: e.target.value })} style={cleanInputStyle} />
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '25px' }}>
          <button onClick={() => setActiveModal(null)} style={btnLightStyle}>Cancel</button>
          <button onClick={handleMasterSave} style={btnStyle}>Save Changes</button>
        </div>
      </div>
    </div>
  );

  const render2FAModal = () => (
    // ... Exactly the same as before ...
    <div style={modalOverlayStyle} onClick={() => setActiveModal(null)}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ marginTop: 0 }}>Two-Step Verification</h3>
        {twoFactorAction === 'menu' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <p>Status: <strong>{currentUser?.two_factor_enabled ? 'Enabled' : 'Disabled'}</strong></p>
            {currentUser?.two_factor_enabled ? (
              <>
                <button onClick={() => setTwoFactorAction('change')} style={btnStyle}>Change Password</button>
                <button onClick={() => setTwoFactorAction('remove')} style={{...btnStyle, backgroundColor: '#d32f2f'}}>Remove 2FA</button>
              </>
            ) : <button onClick={() => setTwoFactorAction('enable')} style={btnStyle}>Enable 2FA</button>}
          </div>
        ) : (
          <form onSubmit={handle2FASubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {error && <div style={{ color: 'red', fontSize: '0.85rem' }}>{error}</div>}
            {(twoFactorAction === 'change' || twoFactorAction === 'remove') && <input type="password" placeholder="Current Password" required style={inputStyle} value={passwords.current} onChange={(e) => setPasswords({...passwords, current: e.target.value})} />}
            {(twoFactorAction === 'enable' || twoFactorAction === 'change') && (
              <><input type="password" placeholder="New Password" required style={inputStyle} value={passwords.newPass} onChange={(e) => setPasswords({...passwords, newPass: e.target.value})} /><input type="password" placeholder="Confirm New Password" required style={inputStyle} value={passwords.confirm} onChange={(e) => setPasswords({...passwords, confirm: e.target.value})} /></>
            )}
            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button type="submit" style={btnStyle}>Submit</button>
              <button type="button" onClick={() => {setTwoFactorAction('menu'); setError('');}} style={btnLightStyle}>Back</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );

  // New Group Chat Modal
  const renderGroupModal = () => (
    <div style={modalOverlayStyle} onClick={() => setActiveModal(null)}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ marginTop: 0, textAlign: 'center' }}>New Group</h3>
        
        <form onSubmit={handleCreateGroup} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={{ color: '#008069', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Group Title</label>
            <input 
              type="text" 
              value={groupTitle} 
              onChange={(e) => setGroupTitle(e.target.value)} 
              style={cleanInputStyle} 
              placeholder="e.g., Weekend Trip" 
              required 
            />
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={{ color: '#008069', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Members (Usernames)</label>
            <input 
              type="text" 
              value={groupUsernames} 
              onChange={(e) => setGroupUsernames(e.target.value)} 
              style={cleanInputStyle} 
              placeholder="e.g. john_doe, alice123" 
              required 
            />
            <span style={{ fontSize: '0.75rem', color: '#666', marginTop: '4px' }}>Separate usernames with commas.</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button type="button" onClick={() => setActiveModal(null)} style={btnLightStyle}>Cancel</button>
            <button type="submit" style={btnStyle}>Create Group</button>
          </div>
        </form>
      </div>
    </div>
  );

  return (
    <>
      <div style={{ padding: '15px 20px', cursor: 'pointer', display: 'flex', alignItems: 'center' }} onClick={() => setIsOpen(true)}>
        <div style={{ fontSize: '1.5rem', color: 'white' }}>☰</div>
      </div>

      <div style={{...overlayStyle, opacity: isOpen ? 1 : 0, pointerEvents: isOpen ? 'auto' : 'none'}} onClick={() => setIsOpen(false)}></div>

      <div style={{...drawerStyle, transform: isOpen ? 'translateX(0)' : 'translateX(-100%)'}}>
        
        <div style={{ padding: '20px', backgroundColor: '#008069', color: 'white', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '15px' }}>
          <div style={{ width: '50px', height: '50px', borderRadius: '50%', overflow: 'hidden', backgroundColor: 'white' }}>
            <img src={getPfpUrl(currentUser)} alt="PFP" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{currentUser?.first_name || 'User'}</h3>
            <p style={{ margin: 0, opacity: 0.8, fontSize: '0.85rem' }}>{currentUser?.phone_number}</p>
          </div>
        </div>
        
        <div style={menuItemStyle} onClick={openProfileModal}>👤 My Profile</div>
        {/* NEW BUTTON ADDED HERE */}
        <div style={menuItemStyle} onClick={() => { setActiveModal('group'); setIsOpen(false); }}>👥 New Group</div>
        <div style={menuItemStyle} onClick={() => { setActiveModal('2fa'); setIsOpen(false); }}>🔒 Two-Step Verification</div>
        <div style={menuItemStyle} onClick={() => { localStorage.clear(); window.location.href = '/login'; }}>🚪 Log Out</div>
      </div>

      {activeModal === 'profile' && renderProfileModal()}
      {activeModal === '2fa' && render2FAModal()}
      {activeModal === 'group' && renderGroupModal()}
    </>
  );
}

// --- Styles ---
const overlayStyle = { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.4)', transition: 'opacity 0.3s', zIndex: 40 };
const drawerStyle = { position: 'fixed', top: 0, left: 0, bottom: 0, width: '280px', backgroundColor: '#fff', boxShadow: '2px 0 5px rgba(0,0,0,0.2)', transition: 'transform 0.3s ease-out', zIndex: 50 };
const menuItemStyle = { padding: '15px 20px', cursor: 'pointer', transition: 'background-color 0.2s', borderBottom: '1px solid #f0f0f0', color: '#333' };
const modalOverlayStyle = { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60 };
const modalStyle = { backgroundColor: '#fff', padding: '25px', borderRadius: '10px', width: '350px', boxShadow: '0 4px 15px rgba(0,0,0,0.2)' };
const inputStyle = { flex: 1, padding: '8px', borderRadius: '5px', border: '1px solid #ccc', outline: 'none' };
const cleanInputStyle = { padding: '10px', borderRadius: '5px', border: '1px solid #e0e0e0', outline: 'none', backgroundColor: '#f9f9f9', transition: 'border 0.2s', width: '100%', boxSizing: 'border-box' };
const btnStyle = { padding: '10px 15px', backgroundColor: '#008069', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' };
const btnLightStyle = { padding: '10px 15px', backgroundColor: '#e0e0e0', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold', color: '#333' };