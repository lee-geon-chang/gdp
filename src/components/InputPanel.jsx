// TODO: implement

import { useState } from 'react';
import useBopStore from '../store/bopStore';
import { api } from '../services/api';

function InputPanel() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { setBopData } = useBopStore();

  const handleGenerate = async () => {
    if (!input.trim()) {
      setError('입력 내용을 입력해주세요');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const bopData = await api.generateBOP(input);
      setBopData(bopData);
      setInput('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>BOP 생성</h2>
      <textarea
        style={styles.textarea}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="예: 전기 자전거 생산 라인 생성"
        disabled={loading}
      />
      {error && <div style={styles.error}>{error}</div>}
      <button
        style={styles.button}
        onClick={handleGenerate}
        disabled={loading}
      >
        {loading ? '생성 중...' : 'BOP 생성'}
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
    margin: '0 0 15px 0',
    fontSize: '18px',
    fontWeight: 'bold',
  },
  textarea: {
    width: '100%',
    minHeight: '80px',
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
    backgroundColor: '#4a90e2',
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

export default InputPanel;
