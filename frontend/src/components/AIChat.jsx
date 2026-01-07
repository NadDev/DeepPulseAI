import { useState, useRef, useEffect } from 'react';
import { Send, AlertCircle } from 'lucide-react';
import { aiAPI } from '../services/aiAPI';
import './AIChat.css';

function AIChat() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
      text: 'Hello! I\'m your AI Trading Agent. Ask me anything about crypto markets, trading strategies, or current market conditions. How can I help you today?',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      text: input,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setError(null);

    // Get AI response
    try {
      setLoading(true);
      const response = await aiAPI.chat(input);

      const aiMessage = {
        id: messages.length + 2,
        type: 'ai',
        text: response.response || response.message || 'I couldn\'t process that. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (err) {
      setError(err.message || 'Failed to get AI response');
      const errorMessage = {
        id: messages.length + 2,
        type: 'error',
        text: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-chat">
      <div className="chat-container">
        <div className="messages-container">
          {messages.map(msg => (
            <div key={msg.id} className={`message message-${msg.type}`}>
              <div className="message-content">
                <p className="message-text">{msg.text}</p>
                <span className="message-time">
                  {msg.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
            </div>
          ))}
          {loading && (
            <div className="message message-loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="chat-error">
            <AlertCircle size={16} />
            <p>{error}</p>
          </div>
        )}

        <form className="chat-form" onSubmit={handleSendMessage}>
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask me about markets, strategies, or trading analysis..."
            disabled={loading}
            className="chat-input"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="chat-send-btn"
            title="Send message"
          >
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
}

export default AIChat;
