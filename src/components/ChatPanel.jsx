// TODO: implement

import { useState } from 'react';
import useBopStore from '../store/bopStore';
import { api } from '../services/api';

function ChatPanel() {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { bopData, setBopData } = useBopStore();

  const handleSend = async () => {
    if (!message.trim()) {
      setError('메시지를 입력해주세요');
      return;
    }

    if (!bopData || !bopData.steps || bopData.steps.length === 0) {
      setError('먼저 BOP를 생성해주세요');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const updatedBop = await api.chatBOP(message, bopData);
      setBopData(updatedBop);
      setMessage('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>BOP 수정</h2>
      <div style={styles.examples}>
        <small style={styles.exampleTitle}>예시:</small>
        <small style={styles.example}>• "3번 공정 삭제해줘"</small>
        <small style={styles.example}>• "검사 공정 추가해줘"</small>
        <small style={styles.example}>• "용접 시간을 60초로 변경해줘"</small>
      </div>
      <textarea
        style={styles.textarea}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="수정 요청을 입력하세요..."
        disabled={loading}
      />
      {error && <div style={styles.error}>{error}</div>}
      <button
        style={styles.button}
        onClick={handleSend}
        disabled={loading}
      >
        {loading ? '수정 중...' : '수정 요청'}
      </button>
    </div>
  );
}

const styles = {
  container: {
    padding: '20px',
    backgroundColor: '#f5f5f5',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  title: {
    margin: '0 0 10px 0',
    fontSize: '18px',
    fontWeight: 'bold',
  },
  examples: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    marginBottom: '15px',
    padding: '10px',
    backgroundColor: '#e8f4f8',
    borderRadius: '4px',
  },
  exampleTitle: {
    fontWeight: 'bold',
    color: '#555',
  },
  example: {
    color: '#666',
  },
  textarea: {
    width: '100%',
    minHeight: '60px',
    padding: '10px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    resize: 'vertical',
    marginBottom: '10px',
    boxSizing: 'border-box',
  },
  button: {
    width: '100%',
    padding: '10px',
    backgroundColor: '#50c878',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  error: {
    color: '#ff6b6b',
    fontSize: '14px',
    marginBottom: '10px',
  },
};

export default ChatPanel;
