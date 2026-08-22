import { useState, useEffect } from 'react';
import api from './api';
import UserSidebar from './UserSidebar';

export default function Chat() {
  const [currentUser, setCurrentUser] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  
  // New state for the search bar
  const [searchUsername, setSearchUsername] = useState('');

  // 1. Fetch initial data on component mount
  const fetchConversations = async () => {
    try {
      const convRes = await api.get('/conversations');
      setConversations(convRes.data);
    } catch (err) {
      console.error("Failed to load conversations", err);
    }
  };

  useEffect(() => {
    const initializeChat = async () => {
      try {
        const userRes = await api.get('/users/me/about/');
        setCurrentUser(userRes.data);
        await fetchConversations();
      } catch (err) {
        console.error("Failed to load initial data", err);
      }
    };
    initializeChat();
  }, []);

  // 2. Fetch messages whenever a new conversation is clicked
  useEffect(() => {
    if (!activeChat) return;

    const fetchMessages = async () => {
      try {
        const msgRes = await api.get(`/conversations/${activeChat.id}/messages`);
        setMessages(msgRes.data);
      } catch (err) {
        console.error("Failed to load messages", err);
      }
    };
    
    fetchMessages();
  }, [activeChat]);

  // 3. Send a new message
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || !activeChat) return;

    const formData = new FormData();
    formData.append("text", inputText);

    try {
      const res = await api.post(`/conversations/${activeChat.id}/messages`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setMessages((prev) => [...prev, res.data]);
      setInputText('');
    } catch (err) {
      alert("Validation Error: " + JSON.stringify(err.response?.data));
    }
  };

  // 4. Create a Private Chat from the Search Bar
  const handleCreatePrivateChat = async (e) => {
    e.preventDefault();
    if (!searchUsername.trim()) return;

    try {
      await api.post('/conversations/create-private', {
        username: searchUsername.trim()
      });
      
      // Clear the search bar and refresh the chat list
      setSearchUsername('');
      await fetchConversations();
    } catch (err) {
      // The backend returns a 400 with "User does not exist." if the username is wrong
      alert(err.response?.data?.non_field_errors?.[0] || JSON.stringify(err.response?.data) || "Failed to create chat.");
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'sans-serif' }}>
      
      
      {/* Sidebar: Conversation List */}
      <div style={{ width: '300px', borderRight: '1px solid #ccc', display: 'flex', flexDirection: 'column', backgroundColor: '#fff' }}>
        
        {/* Top Header: Hamburger & Search Bar */}
        <div style={{ padding: '10px', backgroundColor: '#008069', display: 'flex', alignItems: 'center', gap: '10px' }}>
          


          {/* 1. Hamburger Menu & Modals */}
          <UserSidebar 
            currentUser={currentUser} 
            setCurrentUser={setCurrentUser} 
            onChatCreated={fetchConversations} 
          />
          
          <form onSubmit={handleCreatePrivateChat} style={{ display: 'flex', flex: 1, gap: '5px' }}>
            <input 
              type="text" 
              placeholder="Search username..." 
              value={searchUsername}
              onChange={(e) => setSearchUsername(e.target.value)}
              style={{ 
                flex: 1, padding: '8px 12px', borderRadius: '20px', border: 'none', outline: 'none', fontSize: '0.9rem' 
              }}
            />
            <button type="submit" style={{ 
              backgroundColor: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '1.2rem' 
            }} title="Start Chat">
              ➕
            </button>
          </form>
          
        </div>
        
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {conversations.length === 0 ? (
            <p style={{ padding: '20px', color: '#666', textAlign: 'center' }}>No chats yet.</p>
          ) : (
            conversations.map((conv) => (
              <div 
                key={conv.id} 
                onClick={() => setActiveChat(conv)}
                style={{ 
                  padding: '15px', 
                  cursor: 'pointer', 
                  borderBottom: '1px solid #f0f0f0',
                  backgroundColor: activeChat?.id === conv.id ? '#ebebeb' : 'transparent',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px'
                }}
              >
                {/* Optional: Show PFP of the chat if you want it in the list */}
                <div style={{ width: '45px', height: '45px', borderRadius: '50%', backgroundColor: '#ccc', overflow: 'hidden', flexShrink: 0 }}>
                   <img 
                      src={conv.profile_picture ? (conv.profile_picture.startsWith('http') ? conv.profile_picture : `http://127.0.0.1:8000${conv.profile_picture}`) : `https://ui-avatars.com/api/?background=random&color=fff&name=${encodeURIComponent(conv.title)}`} 
                      alt="" 
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                   />
                </div>
                <strong style={{ fontSize: '1.05rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {conv.title}
                </strong>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Area: Chat History & Input */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: '#e5ddd5' }}>
        
        {/* Chat Header */}
        <div style={{ padding: '15px 20px', backgroundColor: '#f0f2f5', borderBottom: '1px solid #ccc', display: 'flex', alignItems: 'center', gap: '15px', height: '65px' }}>
          {activeChat && (
            <>
              <div style={{ width: '40px', height: '40px', borderRadius: '50%', backgroundColor: '#ccc', overflow: 'hidden' }}>
                 <img 
                    src={activeChat.profile_picture ? (activeChat.profile_picture.startsWith('http') ? activeChat.profile_picture : `http://127.0.0.1:8000${activeChat.profile_picture}`) : `https://ui-avatars.com/api/?background=random&color=fff&name=${encodeURIComponent(activeChat.title)}`} 
                    alt="" 
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                 />
              </div>
              <strong style={{ fontSize: '1.1rem' }}>{activeChat.title}</strong>
            </>
          )}
        </div>

        {/* Message List */}
        <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {!activeChat ? (
            <div style={{ margin: 'auto', padding: '10px 20px', backgroundColor: 'rgba(255,255,255,0.8)', borderRadius: '20px', color: '#667781', fontWeight: '500' }}>Select a conversation to start chatting.</div>
          ) : messages.length === 0 ? (
            <div style={{ margin: 'auto', padding: '10px 20px', backgroundColor: 'rgba(255,255,255,0.8)', borderRadius: '20px', color: '#667781', fontWeight: '500' }}>No messages yet.</div>
          ) : (
            messages.map((msg, idx) => {
              const isMe = msg.sender === currentUser?.id;
              const timeString = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

              return (
                <div key={msg.id || idx} style={{ 
                  alignSelf: isMe ? 'flex-end' : 'flex-start',
                  backgroundColor: isMe ? '#d9fdd3' : '#ffffff',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  maxWidth: '65%',
                  boxShadow: '0 1px 1px rgba(0,0,0,0.1)',
                  display: 'flex',
                  flexDirection: 'column',
                  borderTopRightRadius: isMe ? '0' : '8px',
                  borderTopLeftRadius: isMe ? '8px' : '0'
                }}>
                  <span style={{ fontSize: '0.95rem', wordWrap: 'break-word', lineHeight: '1.4' }}>
                    {msg.text}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: '#667781', alignSelf: 'flex-end', marginTop: '4px' }}>
                    {timeString}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Input Area */}
        {activeChat && (
          <form onSubmit={handleSendMessage} style={{ padding: '15px 20px', backgroundColor: '#f0f2f5', display: 'flex', gap: '12px', alignItems: 'center' }}>
            <input 
              type="text" 
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type a message..."
              style={{ flex: 1, padding: '12px 15px', borderRadius: '8px', border: 'none', outline: 'none', fontSize: '1rem', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}
            />
            <button type="submit" style={{ padding: '12px 20px', backgroundColor: '#008069', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
              Send
            </button>
          </form>
        )}
      </div>
    </div>
  );
}