import { useState, useRef } from 'react';
import { api } from '../../services/api';
import useBopStore from '../../store/bopStore';
import useTranslation from '../../i18n/useTranslation';

function ToolUploadView({ onNavigate, onUploadComplete }) {
  const { addMessage } = useBopStore();
  const { t } = useTranslation();

  const [uploadedCode, setUploadedCode] = useState('');
  const [fileName, setFileName] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [useSchemaOverride, setUseSchemaOverride] = useState(false);
  const [schemaOverride, setSchemaOverride] = useState({ input: null, output: null });
  const [error, setError] = useState('');

  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.name.endsWith('.py')) {
      setError(t('tool.pyOnly'));
      return;
    }
    setError('');
    const reader = new FileReader();
    reader.onload = (ev) => {
      setUploadedCode(ev.target.result);
      setFileName(file.name);
      setAnalysisResult(null);
    };
    reader.readAsText(file);
  };

  const handleAnalyze = async () => {
    if (!uploadedCode) return;
    setAnalyzing(true);
    setError('');
    try {
      const inputOverride = useSchemaOverride && schemaOverride.input ? schemaOverride.input : null;
      const outputOverride = useSchemaOverride && schemaOverride.output ? schemaOverride.output : null;
      const result = await api.analyzeScript(uploadedCode, fileName, null, inputOverride, outputOverride);
      setAnalysisResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRegister = async () => {
    if (!analysisResult || !uploadedCode) return;
    setRegistering(true);
    setError('');

    try {
      const registerData = {
        tool_name: analysisResult.tool_name,
        description: analysisResult.description,
        execution_type: analysisResult.execution_type,
        file_name: fileName,
        source_code: uploadedCode,
        input_schema: analysisResult.input_schema,
        output_schema: analysisResult.output_schema,
        params_schema: analysisResult.params_schema || null,
      };

      await api.registerTool(registerData);
      addMessage('assistant', t('tool.registeredMsg', { name: analysisResult.tool_name }));

      // Reset
      setUploadedCode('');
      setFileName('');
      setAnalysisResult(null);
      onUploadComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div style={styles.content}>
      <div style={styles.header}>
        <button style={styles.backBtn} onClick={() => onNavigate('main')}>← {t('tool.backToList')}</button>
        <h3 style={styles.title}>{t('tool.uploadTitle')}</h3>
      </div>

      {/* Step 1: File Upload */}
      <div style={styles.section}>
        <label style={styles.label}>{t('tool.step1FileLabel')}</label>
        <input
          ref={fileInputRef}
          type="file"
          accept=".py"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <button style={styles.secondaryBtn} onClick={() => fileInputRef.current?.click()}>
          {fileName || t('tool.fileSelect')}
        </button>
      </div>

      {/* Step 2: Code Preview */}
      {uploadedCode && (
        <div style={styles.section}>
          <label style={styles.label}>{t('tool.step2Preview')}</label>
          <pre style={{ ...styles.codePreview, maxHeight: '300px', overflow: 'auto' }}>
            {uploadedCode}
          </pre>
        </div>
      )}

      {/* Step 2.5: Schema Override */}
      {uploadedCode && !analysisResult && (
        <div style={styles.section}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={useSchemaOverride}
              onChange={e => setUseSchemaOverride(e.target.checked)}
            />
            {t('tool.schemaOverride')}
          </label>
          {useSchemaOverride && (
            <div style={{ ...styles.resultCard, marginTop: 8 }}>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, color: '#555', display: 'block', marginBottom: 4 }}>{t('tool.inputSchemaJson')}</label>
                <textarea
                  style={{ ...styles.textarea, fontFamily: 'monospace', fontSize: 11, minHeight: 120 }}
                  placeholder='{"type": "json", "description": "BOP 데이터"}'
                  value={schemaOverride.input ? JSON.stringify(schemaOverride.input, null, 2) : ''}
                  onChange={e => {
                    try {
                      const parsed = e.target.value.trim() ? JSON.parse(e.target.value) : null;
                      setSchemaOverride(prev => ({ ...prev, input: parsed }));
                      setError('');
                    } catch (err) {
                      setError(t('tool.inputSchemaJsonError'));
                    }
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: 12, color: '#555', display: 'block', marginBottom: 4 }}>{t('tool.outputSchemaJson')}</label>
                <textarea
                  style={{ ...styles.textarea, fontFamily: 'monospace', fontSize: 11, minHeight: 120 }}
                  placeholder='{"type": "json", "description": "수정된 BOP 데이터"}'
                  value={schemaOverride.output ? JSON.stringify(schemaOverride.output, null, 2) : ''}
                  onChange={e => {
                    try {
                      const parsed = e.target.value.trim() ? JSON.parse(e.target.value) : null;
                      setSchemaOverride(prev => ({ ...prev, output: parsed }));
                      setError('');
                    } catch (err) {
                      setError(t('tool.outputSchemaJsonError'));
                    }
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Step 3: Analyze Button */}
      {uploadedCode && !analysisResult && (
        <div style={styles.section}>
          <label style={styles.label}>{t('tool.step3Analyze', { mode: useSchemaOverride ? t('tool.schemaMode') : t('tool.analyzeMode') })}</label>
          <button
            style={styles.primaryBtn}
            onClick={handleAnalyze}
            disabled={analyzing || (useSchemaOverride && (!schemaOverride.input || !schemaOverride.output))}
          >
            {analyzing ? (useSchemaOverride ? t('tool.preparingRegister') : t('tool.analyzing')) : (useSchemaOverride ? t('tool.schemaMode') : t('tool.analyze'))}
          </button>
        </div>
      )}

      {/* Step 4: Analysis Result */}
      {analysisResult && (
        <div style={styles.section}>
          <label style={styles.label}>{t('tool.step4Result')}</label>
          <div style={styles.resultCard}>
            <div style={styles.resultRow}>
              <span style={styles.resultLabel}>{t('tool.toolName')}</span>
              <input
                style={styles.input}
                value={analysisResult.tool_name}
                onChange={e => setAnalysisResult({ ...analysisResult, tool_name: e.target.value })}
              />
            </div>
            <div style={styles.resultRow}>
              <span style={styles.resultLabel}>{t('tool.description')}</span>
              <input
                style={styles.input}
                value={analysisResult.description}
                onChange={e => setAnalysisResult({ ...analysisResult, description: e.target.value })}
              />
            </div>
            <div style={styles.resultRow}>
              <span style={styles.resultLabel}>{t('tool.input')}</span>
              <span style={styles.resultValue}>
                {analysisResult.input_schema?.type} - {analysisResult.input_schema?.description}
              </span>
            </div>
            <div style={styles.resultRow}>
              <span style={styles.resultLabel}>{t('tool.output')}</span>
              <span style={styles.resultValue}>
                {analysisResult.output_schema?.type} - {analysisResult.output_schema?.description}
              </span>
            </div>
            {analysisResult.params_schema?.length > 0 && (
              <div style={{ marginTop: 8, borderTop: '1px solid #e0e0e0', paddingTop: 8 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 6 }}>
                  {t('tool.additionalParams', { count: analysisResult.params_schema.length })}
                </div>
                {analysisResult.params_schema.map((p, idx) => (
                  <div key={idx} style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                    <span style={{ fontWeight: 500 }}>{p.label}</span>
                    <span style={{ color: '#999' }}> ({p.key}, {p.type})</span>
                    {p.required && <span style={{ color: '#c0392b', marginLeft: 4 }}>{t('tool.required')}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 5: Register */}
      {analysisResult && (
        <div style={styles.section}>
          <label style={styles.label}>{t('tool.step5Register')}</label>
          <button
            style={styles.primaryBtn}
            onClick={handleRegister}
            disabled={registering}
          >
            {registering ? t('tool.registeringAdapter') : t('tool.registerBtn')}
          </button>
        </div>
      )}

      {error && <div style={styles.error}>{error}</div>}
    </div>
  );
}

const styles = {
  content: { padding: '16px', overflow: 'auto', flex: 1 },
  header: { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' },
  title: { margin: 0, fontSize: '16px', fontWeight: 'bold', flex: 1 },
  section: { marginBottom: '16px' },
  label: { display: 'block', fontSize: '13px', fontWeight: '600', color: '#555', marginBottom: '8px' },
  backBtn: { padding: '4px 10px', backgroundColor: 'transparent', color: '#4a90e2', border: '1px solid #4a90e2', borderRadius: '4px', fontSize: '12px', cursor: 'pointer' },
  secondaryBtn: { padding: '8px 16px', backgroundColor: '#f0f0f0', color: '#333', border: '1px solid #ccc', borderRadius: '4px', fontSize: '13px', cursor: 'pointer' },
  primaryBtn: { padding: '8px 16px', backgroundColor: '#4a90e2', color: 'white', border: 'none', borderRadius: '4px', fontSize: '13px', cursor: 'pointer', fontWeight: 'bold' },
  codePreview: { backgroundColor: '#f5f5f5', border: '1px solid #ddd', borderRadius: '4px', padding: '10px', fontSize: '11px', lineHeight: '1.4', overflow: 'auto', maxHeight: 'none', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace' },
  resultCard: { backgroundColor: '#f9f9f9', border: '1px solid #e0e0e0', borderRadius: '6px', padding: '12px' },
  resultRow: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px' },
  resultLabel: { fontWeight: '600', color: '#555', minWidth: '50px' },
  resultValue: { color: '#333' },
  input: { flex: 1, padding: '4px 8px', border: '1px solid #ddd', borderRadius: '3px', fontSize: '13px' },
  textarea: { width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '13px', resize: 'vertical', boxSizing: 'border-box', lineHeight: 1.5 },
  checkboxLabel: { display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#555', cursor: 'pointer' },
  error: { color: '#c0392b', backgroundColor: '#fdecea', padding: '8px 12px', fontSize: '13px', borderBottom: '1px solid #f5c6cb' },
};

export default ToolUploadView;
