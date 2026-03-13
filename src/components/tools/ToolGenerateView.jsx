import { useState } from 'react';
import { api } from '../../services/api';
import useBopStore from '../../store/bopStore';
import useTranslation from '../../i18n/useTranslation';

function ToolGenerateView({ onNavigate, onGenerateComplete }) {
  const { addMessage } = useBopStore();
  const { t } = useTranslation();

  const [genDescription, setGenDescription] = useState('');
  const [generatingSchema, setGeneratingSchema] = useState(false);
  const [generatedSchema, setGeneratedSchema] = useState(null);
  const [editedInputSchema, setEditedInputSchema] = useState(null);
  const [editedOutputSchema, setEditedOutputSchema] = useState(null);
  const [editedParams, setEditedParams] = useState([]);
  const [improveFeedback, setImproveFeedback] = useState('');
  const [improvingSchema, setImprovingSchema] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatedResult, setGeneratedResult] = useState(null);
  const [editedCode, setEditedCode] = useState('');
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState('');

  const handleGenerateSchema = async () => {
    if (!genDescription.trim()) return;
    setGeneratingSchema(true);
    setError('');
    setGeneratedSchema(null);
    try {
      const result = await api.generateSchema(genDescription);
      if (result.success) {
        setGeneratedSchema(result); // AI가 생성한 example_input, example_output 포함
        setEditedInputSchema(result.input_schema);
        setEditedOutputSchema(result.output_schema);
        setEditedParams(result.suggested_params || []);
      } else {
        setError(result.message || t('tool.schemaFailed'));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGeneratingSchema(false);
    }
  };

  const handleImproveSchema = async () => {
    if (!improveFeedback.trim() || !generatedSchema) return;
    setImprovingSchema(true);
    setError('');
    try {
      const result = await api.improveSchema(
        generatedSchema.tool_name,
        generatedSchema.description,
        editedInputSchema,
        editedOutputSchema,
        editedParams,
        improveFeedback
      );
      if (result.success) {
        setGeneratedSchema(result);
        setEditedInputSchema(result.input_schema);
        setEditedOutputSchema(result.output_schema);
        setEditedParams(result.suggested_params || []);
        setImproveFeedback('');
        if (result.changes_summary && result.changes_summary.length > 0) {
          addMessage('system', t('tool.schemaImprovedMsg', { changes: result.changes_summary.map(c => `• ${c}`).join('\n') }));
        }
      } else {
        setError(result.message || t('tool.schemaImproveFailed'));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setImprovingSchema(false);
    }
  };

  const handleGenerateScript = async () => {
    if (!genDescription.trim() || !editedInputSchema || !editedOutputSchema) return;
    setGenerating(true);
    setError('');
    setGeneratedResult(null);
    try {
      const result = await api.generateScript(genDescription, editedInputSchema, editedOutputSchema);
      if (result.success) {
        setGeneratedResult(result);
        setEditedCode(result.script_code || '');
      } else {
        setError(result.message || t('tool.scriptFailed'));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleRegister = async () => {
    if (!generatedResult || !editedCode || !editedInputSchema || !editedOutputSchema) return;
    setRegistering(true);
    setError('');
    try {
      const analysisRes = await api.analyzeScript(
        editedCode,
        `${generatedResult.tool_name}.py`,
        null,
        editedInputSchema,
        editedOutputSchema
      );

      await api.registerTool({
        tool_name: analysisRes.tool_name || generatedResult.tool_name,
        description: analysisRes.description || generatedResult.description,
        execution_type: analysisRes.execution_type || 'python',
        file_name: `${generatedResult.tool_name}.py`,
        source_code: editedCode,
        input_schema: editedInputSchema,
        output_schema: editedOutputSchema,
        params_schema: editedParams.length > 0 ? editedParams : null,
      });

      addMessage('assistant', t('tool.generatedMsg', { name: generatedResult.tool_name }));
      onGenerateComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setRegistering(false);
    }
  };

  const addParam = () => {
    setEditedParams([...editedParams, { key: '', label: '', type: 'string', required: false, default: null }]);
  };

  const updateParam = (idx, field, value) => {
    const updated = [...editedParams];
    updated[idx][field] = value;
    setEditedParams(updated);
  };

  const removeParam = (idx) => {
    setEditedParams(editedParams.filter((_, i) => i !== idx));
  };

  const generateSampleData = (schema) => {
    if (!schema) return null;

    const generateValueByName = (name) => {
      const lowerName = (name || '').toLowerCase();

      // 배열 타입
      if (lowerName.includes('processes') || lowerName.includes('process_ids')) {
        return [{ process_id: 'P001', name: '공정1', cycle_time_sec: 120 }, { process_id: 'P002', name: '공정2', cycle_time_sec: 180 }];
      }
      if (lowerName.includes('obstacles')) {
        return [{ obstacle_id: 'OBS001', type: 'fence', position: { x: 0, y: 0, z: 0 } }];
      }
      if (lowerName.includes('area') || lowerName.includes('polygon') || lowerName.includes('boundary')) {
        return [[0, 0], [10, 0], [10, 10], [0, 10]];
      }
      if (lowerName.includes('points') || lowerName.includes('coordinates')) {
        return [[0, 0], [5, 5], [10, 0]];
      }

      // 위치 관련
      if (lowerName.includes('location') || lowerName.includes('position') || lowerName.includes('pos')) {
        return { x: 0, y: 0, z: 0 };
      }

      // 숫자 타입
      if (lowerName.includes('count') || lowerName.includes('parallel')) return 2;
      if (lowerName.includes('uph') || lowerName.includes('target')) return 120;
      if (lowerName.includes('time') || lowerName.includes('sec')) return 120.0;
      if (lowerName.includes('distance') || lowerName.includes('width') || lowerName.includes('height')) return 5.0;
      if (lowerName.includes('offset') || lowerName.includes('margin')) return 1.0;
      if (lowerName.includes('rotation') || lowerName.includes('angle')) return 0;

      // 문자열 타입
      if (lowerName.includes('id')) return 'ID001';
      if (lowerName.includes('name')) return '이름';
      if (lowerName.includes('type')) return 'type';
      if (lowerName.includes('description')) return '설명';

      return 'value';
    };

    const generateFromStructure = (struct, parentKey = '') => {
      if (!struct || typeof struct !== 'object') return struct;

      if (Array.isArray(struct)) {
        // 배열 타입 힌트가 있으면 첫 번째 요소를 기반으로 생성
        if (struct.length > 0) {
          return [generateFromStructure(struct[0], parentKey)];
        }
        return [];
      }

      const result = {};
      Object.keys(struct).forEach(key => {
        const value = struct[key];
        const fullKey = parentKey ? `${parentKey}.${key}` : key;

        if (typeof value === 'string') {
          // 타입 힌트가 있는 경우
          if (value === 'array') {
            result[key] = generateValueByName(key);
          } else if (value === 'object') {
            result[key] = generateValueByName(key);
          } else {
            result[key] = generateValueByName(key);
          }
        } else if (typeof value === 'object' && value !== null) {
          result[key] = generateFromStructure(value, fullKey);
        } else {
          result[key] = generateValueByName(key);
        }
      });
      return result;
    };

    // CSV 타입
    if (schema.type === 'csv' && schema.columns) {
      const row = {};
      schema.columns.forEach(col => {
        row[col] = generateValueByName(col);
      });
      return [row];
    }

    // Args 타입
    if (schema.type === 'args' && schema.args_format) {
      return `명령줄 예시: ${schema.args_format.replace('{input_file}', 'input.json').replace('{output_file}', 'output.json')}`;
    }

    // JSON 타입 - structure 기반
    if (schema.structure) {
      return generateFromStructure(schema.structure);
    }

    // fields 기반 (간단한 구조)
    if (schema.fields && Array.isArray(schema.fields)) {
      const sample = {};
      schema.fields.forEach(field => {
        sample[field] = generateValueByName(field);
      });
      return sample;
    }

    // description만 있는 경우 - 설명을 분석해서 예시 생성
    if (schema.description && !schema.structure && !schema.fields) {
      const desc = schema.description.toLowerCase();

      // Type 기반 기본 예시
      if (schema.type === 'list' || schema.type === 'array') {
        // 리스트 타입 - 설명에서 유추
        if (desc.includes('process')) {
          return [{ process_id: 'P001', name: '공정1' }, { process_id: 'P002', name: '공정2' }];
        }
        if (desc.includes('area') || desc.includes('polygon') || desc.includes('point')) {
          return [[0, 0], [10, 0], [10, 10], [0, 10]];
        }
        if (desc.includes('coordinate')) {
          return [[0, 0], [5, 5], [10, 0]];
        }
        return ['item1', 'item2', 'item3'];
      }

      if (schema.type === 'dict' || schema.type === 'json') {
        // Dict/JSON 타입 - 설명에서 필드 유추
        const sample = {};

        if (desc.includes('process')) {
          sample.processes = [{ process_id: 'P001', name: '공정1' }];
        }
        if (desc.includes('area') || desc.includes('boundary')) {
          sample.area = [[0, 0], [10, 0], [10, 10], [0, 10]];
        }
        if (desc.includes('location') || desc.includes('position')) {
          sample.location = { x: 0, y: 0, z: 0 };
        }
        if (desc.includes('target') || desc.includes('uph')) {
          sample.target_uph = 120;
        }
        if (desc.includes('distance') || desc.includes('offset')) {
          sample.distance = 5.0;
        }

        // 기본 예시가 없으면 일반적인 구조
        if (Object.keys(sample).length === 0) {
          sample.data = 'value';
          sample.parameters = {};
        }

        return sample;
      }

      if (schema.type === 'string') {
        // String 타입
        if (desc.includes('json')) return '{"key": "value"}';
        if (desc.includes('path') || desc.includes('file')) return '/path/to/file.txt';
        if (desc.includes('name')) return '이름';
        return 'text value';
      }

      if (schema.type === 'number') {
        // Number 타입
        if (desc.includes('uph') || desc.includes('target')) return 120;
        if (desc.includes('distance') || desc.includes('size')) return 5.0;
        if (desc.includes('count')) return 10;
        return 0;
      }

      // 타입 정보가 없으면 설명만 표시
      return `📝 ${schema.description}\n\n타입: ${schema.type || 'unknown'}\n(구체적인 예시를 보려면 structure 또는 fields를 추가하세요)`;
    }

    return null;
  };

  return (
    <div style={styles.content}>
      <div style={styles.header}>
        <button style={styles.backBtn} onClick={() => onNavigate('main')}>← {t('tool.backToList')}</button>
        <h3 style={styles.title}>{t('tool.aiGenerateTitle')}</h3>
      </div>

      {/* Step 1: Description Input */}
      <div style={styles.section}>
        <label style={styles.label}>{t('tool.step1Label')}</label>
        <textarea
          style={styles.textarea}
          placeholder={t('tool.step1Placeholder')}
          value={genDescription}
          onChange={e => setGenDescription(e.target.value)}
          rows={4}
          disabled={generatedSchema}
        />
        {!generatedSchema && (
          <button
            style={{ ...styles.aiBtn, marginTop: 8 }}
            onClick={handleGenerateSchema}
            disabled={generatingSchema || !genDescription.trim()}
          >
            {generatingSchema ? t('tool.generatingSchema') : `✨ ${t('tool.generateSchema')}`}
          </button>
        )}
        {generatedSchema && (
          <div style={{ ...styles.completedStep, marginTop: 8 }}>
            <div style={{ fontWeight: 600, color: '#2d7a3a' }}>✅ {t('tool.step1Done')}</div>
          </div>
        )}
        <div style={{ fontSize: 11, color: '#888', marginTop: 6 }}>
          {t('tool.step1Hint')}
        </div>
      </div>

      {/* Step 2: Schema Review */}
      {generatedSchema && !generatedResult && (
        <>
          <div style={styles.section}>
            <label style={styles.label}>{t('tool.step2Label')}</label>
            <div style={styles.resultCard}>
              <div style={styles.resultRow}>
                <span style={styles.resultLabel}>{t('tool.toolName')}</span>
                <span style={styles.resultValue}>{generatedSchema.tool_name}</span>
              </div>
              <div style={styles.resultRow}>
                <span style={styles.resultLabel}>{t('tool.description')}</span>
                <span style={styles.resultValue}>{generatedSchema.description}</span>
              </div>
            </div>
          </div>

          <div style={styles.section}>
            <label style={styles.label}>{t('tool.inputSchema')}</label>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
              {t('tool.inputSchemaHint')}
            </div>
            <textarea
              style={{ ...styles.textarea, fontFamily: 'monospace', fontSize: 11, minHeight: 180 }}
              value={JSON.stringify(editedInputSchema, null, 2)}
              onChange={e => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  setEditedInputSchema(parsed);
                  setError('');
                } catch (err) {
                  setError(t('tool.inputSchemaError') + err.message);
                }
              }}
            />

            {/* 입력 예시 데이터 (AI 생성) */}
            {generatedSchema?.example_input && (
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#555', marginBottom: 4 }}>
                  📝 {t('tool.inputExample')}
                </div>
                <pre style={{ ...styles.codePreview, backgroundColor: '#f0f8ff', maxHeight: '200px' }}>
                  {typeof generatedSchema.example_input === 'string'
                    ? generatedSchema.example_input
                    : JSON.stringify(generatedSchema.example_input, null, 2)}
                </pre>
              </div>
            )}
          </div>

          <div style={styles.section}>
            <label style={styles.label}>{t('tool.outputSchema')}</label>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
              {t('tool.outputSchemaHint')}
            </div>
            <textarea
              style={{ ...styles.textarea, fontFamily: 'monospace', fontSize: 11, minHeight: 180 }}
              value={JSON.stringify(editedOutputSchema, null, 2)}
              onChange={e => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  setEditedOutputSchema(parsed);
                  setError('');
                } catch (err) {
                  setError(t('tool.outputSchemaError') + err.message);
                }
              }}
            />

            {/* 출력 예시 데이터 (AI 생성) */}
            {generatedSchema?.example_output && (
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#555', marginBottom: 4 }}>
                  📝 {t('tool.outputExample')}
                </div>
                <pre style={{ ...styles.codePreview, backgroundColor: '#f0f8ff', maxHeight: '200px' }}>
                  {typeof generatedSchema.example_output === 'string'
                    ? generatedSchema.example_output
                    : JSON.stringify(generatedSchema.example_output, null, 2)}
                </pre>
              </div>
            )}
          </div>

          <div style={styles.section}>
            <label style={styles.label}>{t('tool.paramsOptional')}</label>
            <div style={styles.resultCard}>
              {editedParams.map((param, idx) => (
                <div key={idx} style={{ marginBottom: 12, paddingBottom: 12, borderBottom: '1px solid #e0e0e0' }}>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                    <input
                      style={{ ...styles.input, flex: 1 }}
                      placeholder={t('tool.paramKey')}
                      value={param.key}
                      onChange={e => updateParam(idx, 'key', e.target.value)}
                    />
                    <input
                      style={{ ...styles.input, flex: 1 }}
                      placeholder={t('tool.paramLabel')}
                      value={param.label}
                      onChange={e => updateParam(idx, 'label', e.target.value)}
                    />
                    <select
                      style={{ ...styles.input, width: 100, cursor: 'pointer' }}
                      value={param.type}
                      onChange={e => updateParam(idx, 'type', e.target.value)}
                    >
                      <option value="string">string</option>
                      <option value="number">number</option>
                      <option value="boolean">boolean</option>
                    </select>
                    <button
                      style={{ ...styles.dangerBtn, padding: '4px 8px', fontSize: 11 }}
                      onClick={() => removeParam(idx)}
                    >
                      {t('tool.paramDelete')}
                    </button>
                  </div>
                </div>
              ))}
              <button style={styles.secondaryBtn} onClick={addParam}>
                {t('tool.addParam')}
              </button>
            </div>
          </div>

          {/* Schema Improvement Section */}
          <div style={styles.section}>
            <label style={styles.label}>{t('tool.schemaImproveLabel')}</label>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
              {t('tool.schemaImproveHint')}
            </div>
            <textarea
              style={{ ...styles.textarea, minHeight: 60 }}
              placeholder={t('tool.schemaImprovePlaceholder')}
              value={improveFeedback}
              onChange={e => setImproveFeedback(e.target.value)}
              rows={2}
            />
            <button
              style={{ ...styles.aiBtn, marginTop: 8 }}
              onClick={handleImproveSchema}
              disabled={improvingSchema || !improveFeedback.trim()}
            >
              {improvingSchema ? t('tool.improvingSchema') : `✨ ${t('tool.improveSchema')}`}
            </button>
          </div>

          <div style={styles.section}>
            <label style={styles.label}>{t('tool.step3Label')}</label>
            <button
              style={styles.aiBtn}
              onClick={handleGenerateScript}
              disabled={generating}
            >
              {generating ? t('tool.generatingScript') : `✨ ${t('tool.generateScript')}`}
            </button>
            <div style={{ fontSize: 11, color: '#888', marginTop: 6 }}>
              {t('tool.step3Hint')}
            </div>
          </div>
        </>
      )}

      {/* Step 4-5: Script Review & Register */}
      {generatedResult && (
        <>
          <div style={styles.completedStep}>
            <div style={{ fontWeight: 600, color: '#2d7a3a' }}>✅ {t('tool.step3Done')}</div>
            <div style={{ fontSize: 13, marginTop: 4, color: '#555' }}>{generatedResult.tool_name}</div>
          </div>

          <div style={styles.section}>
            <label style={styles.label}>{t('tool.step4Label')}</label>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
              {t('tool.step4Hint')}
            </div>
            <textarea
              style={{ ...styles.textarea, fontFamily: 'monospace', fontSize: 11, minHeight: 300 }}
              value={editedCode}
              onChange={e => setEditedCode(e.target.value)}
            />
          </div>

          <div style={styles.section}>
            <label style={styles.label}>{t('tool.step5Label')}</label>
            <button
              style={styles.primaryBtn}
              onClick={handleRegister}
              disabled={registering || !editedCode.trim()}
            >
              {registering ? t('tool.registering') : t('tool.register')}
            </button>
            <div style={{ fontSize: 11, color: '#888', marginTop: 6 }}>
              {t('tool.registerHint')}
            </div>
          </div>
        </>
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
  aiBtn: { padding: '10px 20px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', border: 'none', borderRadius: '4px', fontSize: '13px', cursor: 'pointer', fontWeight: 'bold' },
  dangerBtn: { padding: '8px 16px', backgroundColor: '#ff6b6b', color: 'white', border: 'none', borderRadius: '4px', fontSize: '13px', cursor: 'pointer', fontWeight: 'bold' },
  textarea: { width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '13px', resize: 'vertical', boxSizing: 'border-box', lineHeight: 1.5 },
  resultCard: { backgroundColor: '#f9f9f9', border: '1px solid #e0e0e0', borderRadius: '6px', padding: '12px' },
  resultRow: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px' },
  resultLabel: { fontWeight: '600', color: '#555', minWidth: '50px' },
  resultValue: { color: '#333' },
  input: { flex: 1, padding: '4px 8px', border: '1px solid #ddd', borderRadius: '3px', fontSize: '13px' },
  codePreview: { backgroundColor: '#f5f5f5', border: '1px solid #ddd', borderRadius: '4px', padding: '10px', fontSize: '11px', lineHeight: '1.4', overflow: 'auto', maxHeight: '200px', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace' },
  completedStep: { backgroundColor: '#e7f5e7', border: '1px solid #b7ddb7', borderRadius: '6px', padding: '12px', marginBottom: '16px' },
  error: { color: '#c0392b', backgroundColor: '#fdecea', padding: '8px 12px', fontSize: '13px', borderBottom: '1px solid #f5c6cb' },
};

export default ToolGenerateView;
