import { useState, useRef, useEffect } from 'react';
import useBopStore from '../store/bopStore';
import { api } from '../services/api';
import useTranslation from '../i18n/useTranslation';

function UnifiedChatPanel() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { messages, setBopData, addMessage, exportBopData, selectedModel, setSelectedModel, supportedModels, setSupportedModels, selectedLanguage, setSelectedLanguage } = useBopStore();
  const messagesEndRef = useRef(null);
  const { t } = useTranslation();

  // Load supported models on component mount
  useEffect(() => {
    const loadModels = async () => {
      try {
        console.log('[DEBUG] Fetching /api/models...');
        const response = await fetch('/api/models');
        console.log('[DEBUG] Response status:', response.status);
        if (response.ok) {
          const models = await response.json();
          console.log('[DEBUG] Models loaded:', models);
          setSupportedModels(models);
        } else {
          console.error('[DEBUG] Response not OK:', response.status);
        }
      } catch (err) {
        console.error('Failed to load models:', err);
      }
    };
    loadModels();
  }, [setSupportedModels]);

  // 메시지 추가 시 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) {
      setError(t('chat.emptyError'));
      return;
    }

    const userMessage = input.trim();
    setLoading(true);
    setError('');
    setInput('');

    // 사용자 메시지를 히스토리에 추가
    addMessage('user', userMessage);

    try {
      // collapsed BOP 데이터와 최신 대화 히스토리 획득
      const collapsedBop = exportBopData();
      const currentMessages = useBopStore.getState().messages;

      // BOP가 비어있으면 null로 전송 (프로세스가 없는 경우)
      const bopToSend = collapsedBop && collapsedBop.processes && collapsedBop.processes.length > 0
        ? collapsedBop
        : null;

      // 통합 채팅 API 호출 (선택된 모델 및 언어 사용)
      const response = await api.unifiedChat(userMessage, bopToSend, currentMessages, selectedModel, selectedLanguage);

      console.log('[DEBUG] API Response:', response);
      console.log('[DEBUG] BOP Data exists:', !!response.bop_data);

      // 어시스턴트 메시지를 히스토리에 추가
      addMessage('assistant', response.message);

      // BOP 데이터가 업데이트된 경우
      if (response.bop_data) {
        console.log('[DEBUG] Setting BOP Data:', response.bop_data);
        setBopData(response.bop_data);
        console.log('[DEBUG] BOP Data set successfully');
      } else {
        console.warn('[WARN] No BOP data in response');
      }
    } catch (err) {
      console.error('[ERROR] API call failed:', err);
      const errorMessage = err.message || String(err);
      setError(errorMessage);
      // 에러 메시지도 히스토리에 추가
      addMessage('assistant', `${t('chat.error')}: ${errorMessage}`);
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
      <div style={styles.titleBar}>
        <h2 style={styles.title}>{t('chat.title')}</h2>
        <div style={styles.titleControls}>
          {Object.keys(supportedModels).length > 0 && (
            <select
              style={styles.modelSelect}
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={loading}
            >
              {Object.entries(supportedModels).map(([modelId, modelInfo]) => (
                <option key={modelId} value={modelId}>
                  {modelInfo.display}
                </option>
              ))}
            </select>
          )}
          <div style={styles.langToggle}>
            <button
              style={{
                ...styles.langButton,
                ...(selectedLanguage === 'ko' ? styles.langButtonActive : {}),
              }}
              onClick={() => setSelectedLanguage('ko')}
              disabled={loading}
            >
              KR
            </button>
            <button
              style={{
                ...styles.langButton,
                ...(selectedLanguage === 'en' ? styles.langButtonActive : {}),
              }}
              onClick={() => setSelectedLanguage('en')}
              disabled={loading}
            >
              EN
            </button>
          </div>
        </div>
      </div>

      {/* 대화 히스토리 */}
      <div style={styles.messagesContainer}>
        {messages.length === 0 && (
          <div style={styles.placeholder}>
            <p style={styles.placeholderTitle}>
              {t('chat.placeholder')}
            </p>
            <p style={styles.placeholderText}>
              {t('chat.examples')}
            </p>
            <ul style={styles.exampleList}>
              <li>{t('chat.ex1')}</li>
              <li>{t('chat.ex2')}</li>
              <li>{t('chat.ex3')}</li>
              <li>{t('chat.ex4')}</li>
            </ul>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            style={{
              ...styles.message,
              ...(msg.role === 'user' ? styles.userMessage : styles.assistantMessage),
            }}
          >
            <div style={styles.messageRole}>
              {msg.role === 'user' ? '👤 You' : '🤖 AI'}
            </div>
            <div style={styles.messageContent}>{msg.content}</div>
          </div>
        ))}

        {loading && (
          <div style={{ ...styles.message, ...styles.assistantMessage }}>
            <div style={styles.messageRole}>🤖 AI</div>
            <div style={styles.messageContent}>{t('chat.thinking')}</div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 입력창 */}
      <div style={styles.inputContainer}>
        {error && <div style={styles.error}>{error}</div>}
        <div style={styles.inputWrapper}>
          <textarea
            style={styles.textarea}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={t('chat.inputPlaceholder')}
            disabled={loading}
            rows={2}
          />
          <button
            style={styles.sendButton}
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >
            {t('chat.send')}
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: '#fff',
  },
  titleBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '15px 20px',
    borderBottom: '1px solid #e0e0e0',
    backgroundColor: '#f8f9fa',
  },
  title: {
    margin: '0',
    fontSize: '18px',
    fontWeight: 'bold',
  },
  titleControls: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  },
  modelSelect: {
    padding: '5px 10px',
    borderRadius: '4px',
    border: '1px solid #ccc',
    fontSize: '13px',
    backgroundColor: '#fff',
    cursor: 'pointer',
  },
  langToggle: {
    display: 'flex',
    borderRadius: '4px',
    overflow: 'hidden',
    border: '1px solid #ccc',
  },
  langButton: {
    padding: '4px 10px',
    fontSize: '12px',
    fontWeight: 'bold',
    border: 'none',
    backgroundColor: '#fff',
    color: '#666',
    cursor: 'pointer',
    transition: 'background-color 0.2s, color 0.2s',
  },
  langButtonActive: {
    backgroundColor: '#4a90e2',
    color: '#fff',
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
  },
  placeholder: {
    textAlign: 'center',
    color: '#666',
    padding: '40px 20px',
  },
  placeholderTitle: {
    fontSize: '16px',
    fontWeight: 'bold',
    marginBottom: '20px',
  },
  placeholderText: {
    fontSize: '14px',
    marginBottom: '10px',
  },
  exampleList: {
    listStyle: 'none',
    padding: 0,
    fontSize: '13px',
    color: '#888',
  },
  message: {
    padding: '12px 15px',
    borderRadius: '8px',
    maxWidth: '80%',
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#e3f2fd',
    marginLeft: 'auto',
  },
  assistantMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#f5f5f5',
    marginRight: 'auto',
  },
  messageRole: {
    fontSize: '12px',
    fontWeight: 'bold',
    marginBottom: '5px',
    color: '#666',
  },
  messageContent: {
    fontSize: '14px',
    lineHeight: '1.5',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  inputContainer: {
    borderTop: '1px solid #e0e0e0',
    padding: '15px 20px',
    backgroundColor: '#f8f9fa',
  },
  inputWrapper: {
    display: 'flex',
    gap: '10px',
    alignItems: 'flex-end',
  },
  textarea: {
    flex: 1,
    padding: '10px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    resize: 'none',
    fontFamily: 'inherit',
  },
  sendButton: {
    padding: '10px 20px',
    backgroundColor: '#4a90e2',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
    fontWeight: 'bold',
    whiteSpace: 'nowrap',
  },
  error: {
    color: '#ff6b6b',
    fontSize: '13px',
    marginBottom: '10px',
  },
};

export default UnifiedChatPanel;
