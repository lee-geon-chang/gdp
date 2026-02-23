import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { useToolExecution } from './hooks/useToolExecution';
import useBopStore from '../../store/bopStore';
import useTranslation from '../../i18n/useTranslation';

function ToolDetailView({ tool, onNavigate, onDelete }) {
  const { addMessage } = useBopStore();
  const { t } = useTranslation();
  const [toolDetail, setToolDetail] = useState(null);
  const [error, setError] = useState('');

  // AI 개선
  const [showImprove, setShowImprove] = useState(false);
  const [improveFeedback, setImproveFeedback] = useState('');
  const [improveScope, setImproveScope] = useState({ adapter: true, params: true, script: false });
  const [improving, setImproving] = useState(false);
  const [improveResult, setImproveResult] = useState(null);
  const [applying, setApplying] = useState(false);


  const {
    executing,
    execResult,
    toolParams,
    setToolParams,
    pendingResult,
    bopChanges,
    executeTool,
    applyToBop,
    cancelApply,
  } = useToolExecution();

  useEffect(() => {
    loadToolDetail();
    initializeParams();
  }, [tool]);

  const loadToolDetail = async () => {
    try {
      const detail = await api.getToolDetail(tool.tool_id);
      setToolDetail(detail);
    } catch (err) {
      console.error('[ToolDetailView] 도구 상세 조회 실패:', err);
    }
  };

  const initializeParams = () => {
    const defaults = {};
    (tool.params_schema || []).forEach(p => {
      if (p.default != null) {
        defaults[p.key] = p.default;
      }
    });
    setToolParams(defaults);
  };

  const handleExecute = async () => {
    const cleanParams = {};
    const schema = tool.params_schema || [];
    schema.forEach(p => {
      const val = toolParams[p.key];
      if (val !== '' && val != null) {
        cleanParams[p.key] = p.type === 'number' ? Number(val) : val;
      }
    });
    await executeTool(tool.tool_id, cleanParams);
  };

  const handleApplyToBop = () => {
    applyToBop(tool.tool_name);
  };

  const handleDelete = async () => {
    if (!confirm(t('tool.confirmDelete', { name: tool.tool_name }))) return;
    const success = await onDelete(tool.tool_id);
    if (success) {
      onNavigate('main');
    }
  };

  // AI 개선
  const handleImprove = async () => {
    if (!improveFeedback.trim()) return;
    setImproving(true);
    setError('');
    setImproveResult(null);

    // 디버깅: execution_context 확인
    console.log('[DEBUG] ===== 개선 요청 시작 =====');
    console.log('[DEBUG] execResult:', JSON.stringify(execResult, null, 2));
    const ctx = execResult ? {
      success: execResult.success,
      stdout: execResult.stdout,
      stderr: execResult.stderr,
      tool_output: execResult.tool_output,
    } : null;
    console.log('[DEBUG] executionContext:', JSON.stringify(ctx, null, 2));
    console.log('[DEBUG] stdout 길이:', execResult?.stdout?.length || 0);
    console.log('[DEBUG] stderr 길이:', execResult?.stderr?.length || 0);
    console.log('[DEBUG] tool_output 길이:', execResult?.tool_output?.length || 0);
    console.log('[DEBUG] ==============================');

    try {
      const result = await api.improveTool(tool.tool_id, {
        userFeedback: improveFeedback,
        executionContext: execResult ? {
          success: execResult.success,
          stdout: execResult.stdout,
          stderr: execResult.stderr,
          tool_output: execResult.tool_output,
        } : null,
        modifyAdapter: improveScope.adapter,
        modifyParams: improveScope.params,
        modifyScript: improveScope.script,
      });

      if (result.success) {
        setImproveResult(result);
      } else {
        setError(result.message || t('tool.improveFailed'));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setImproving(false);
    }
  };

  const handleApplyImprovement = async (createNewVersion) => {
    if (!improveResult?.preview) return;
    setApplying(true);
    setError('');

    try {
      const result = await api.applyImprovement(tool.tool_id, {
        preProcessCode: improveResult.preview.pre_process_code,
        postProcessCode: improveResult.preview.post_process_code,
        paramsSchema: improveResult.preview.params_schema,
        scriptCode: improveResult.preview.script_code,
        createNewVersion,
      });

      if (result.success) {
        addMessage('assistant', t('tool.improvedMsg', { name: tool.tool_name, detail: createNewVersion ? `${result.tool_name} ` : '' }));
        setImproveResult(null);
        setImproveFeedback('');
        setShowImprove(false);
        onNavigate('main');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setApplying(false);
    }
  };

  const getNextVersionLabel = (toolId) => {
    if (!toolId) return 'v2';
    const match = toolId.match(/_v(\d+)$/);
    if (match) {
      const currentVersion = parseInt(match[1], 10);
      return `v${currentVersion + 1}`;
    }
    return 'v2';
  };

  const renderToolOutput = (toolOutput) => {
    if (!toolOutput) return null;
    try {
      const parsed = JSON.parse(toolOutput);
      return (
        <pre style={{ ...styles.codePreview, maxHeight: '400px', overflow: 'auto', fontSize: 11, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {JSON.stringify(parsed, null, 2)}
        </pre>
      );
    } catch {
      return (
        <pre style={{ ...styles.codePreview, maxHeight: '400px', overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {toolOutput}
        </pre>
      );
    }
  };

  return (
    <div style={styles.content}>
      <div style={styles.header}>
        <button style={styles.backBtn} onClick={() => onNavigate('main')}>← {t('tool.backToList')}</button>
        <h3 style={styles.title}>{tool.tool_name}</h3>
      </div>

      {/* 기본 정보 */}
      <div style={styles.section}>
        <div style={styles.resultCard}>
          <div style={styles.resultRow}>
            <span style={styles.resultLabel}>ID:</span>
            <span style={styles.resultValue}>{tool.tool_id}</span>
          </div>
          <div style={styles.resultRow}>
            <span style={styles.resultLabel}>{t('tool.description')}</span>
            <span style={styles.resultValue}>{tool.description}</span>
          </div>
          <div style={styles.resultRow}>
            <span style={styles.resultLabel}>{t('tool.type')}</span>
            <span style={styles.badge}>{tool.execution_type}</span>
          </div>
        </div>
      </div>

      {/* 파라미터 입력 */}
      {tool.params_schema?.length > 0 && (
        <div style={styles.section}>
          <label style={styles.label}>{t('tool.paramSettings')}</label>
          <div style={styles.resultCard}>
            {tool.params_schema.map(p => (
              <div key={p.key} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#333' }}>{p.label}</span>
                  {p.required && <span style={{ color: '#c0392b', fontSize: 11 }}>*</span>}
                </div>
                {p.description && (
                  <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>{p.description}</div>
                )}
                <input
                  style={styles.paramInput}
                  type={p.type === 'number' ? 'number' : 'text'}
                  placeholder={p.default != null ? t('tool.defaultValue', { value: p.default }) : (p.required ? '' : t('tool.optional'))}
                  value={toolParams[p.key] ?? ''}
                  onChange={e => setToolParams(prev => ({ ...prev, [p.key]: e.target.value }))}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 실행 버튼 */}
      <div style={styles.section}>
        <button style={styles.primaryBtn} onClick={handleExecute} disabled={executing}>
          {executing ? t('tool.executing') : t('tool.execute')}
        </button>
      </div>

      {/* 실행 결과 */}
      {execResult && (
        <div style={styles.section}>
          <label style={styles.label}>{t('tool.execResult')}</label>
          <div style={{
            ...styles.resultCard,
            borderLeft: `4px solid ${execResult.success ? '#50c878' : '#ff6b6b'}`,
          }}>
            <div style={{ fontWeight: 'bold', marginBottom: 6, color: execResult.success ? '#2d7a3a' : '#c0392b' }}>
              {execResult.success ? t('tool.success') : t('tool.failure')}
            </div>
            <div style={{ fontSize: 13, marginBottom: 6 }}>{execResult.message}</div>
            {execResult.execution_time_sec != null && (
              <div style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>
                {t('tool.execTime', { time: execResult.execution_time_sec.toFixed(1) })}
              </div>
            )}

            {toolDetail?.adapter?.pre_process_code && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666', fontWeight: 600 }}>
                  🔧 {t('tool.preProcess')}
                </summary>
                <pre style={{ ...styles.codePreview, maxHeight: '300px', overflow: 'auto', fontSize: 11 }}>
                  {toolDetail.adapter.pre_process_code}
                </pre>
              </details>
            )}

            {execResult.tool_input && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666', fontWeight: 600 }}>
                  📥 {t('tool.toolInput')}
                </summary>
                {renderToolOutput(execResult.tool_input)}
              </details>
            )}

            {toolDetail?.source_code && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666', fontWeight: 600 }}>
                  📜 {t('tool.scriptCode')}
                </summary>
                <pre style={{ ...styles.codePreview, maxHeight: '400px', overflow: 'auto', fontSize: 11 }}>
                  {toolDetail.source_code}
                </pre>
              </details>
            )}

            {execResult.tool_output && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666', fontWeight: 600 }}>
                  📤 {t('tool.toolOutput')}
                </summary>
                {renderToolOutput(execResult.tool_output)}
              </details>
            )}

            {toolDetail?.adapter?.post_process_code && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666', fontWeight: 600 }}>
                  🔧 {t('tool.postProcess')}
                </summary>
                <pre style={{ ...styles.codePreview, maxHeight: '300px', overflow: 'auto', fontSize: 11 }}>
                  {toolDetail.adapter.post_process_code}
                </pre>
              </details>
            )}

            {execResult.stdout && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666' }}>stdout</summary>
                <pre style={styles.codePreview}>{execResult.stdout}</pre>
              </details>
            )}
            {execResult.stderr && (
              <details style={{ marginTop: 4 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666' }}>{t('tool.execLog')}</summary>
                <pre style={styles.codePreview}>{execResult.stderr}</pre>
              </details>
            )}
          </div>
        </div>
      )}

      {/* BOP 변경사항 */}
      {pendingResult && bopChanges && (
        <div style={styles.section}>
          <label style={styles.label}>{t('tool.bopChanges')}</label>
          <div style={{ ...styles.resultCard, borderLeft: '4px solid #f39c12', marginBottom: 12 }}>
            {bopChanges.map((change, idx) => (
              <div key={idx} style={{ fontSize: 13, marginBottom: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{
                    display: 'inline-block',
                    padding: '2px 6px',
                    borderRadius: 3,
                    fontSize: 11,
                    fontWeight: 600,
                    backgroundColor: change.type === 'add' ? '#d4edda' : change.type === 'remove' ? '#f8d7da' : '#fff3cd',
                    color: change.type === 'add' ? '#155724' : change.type === 'remove' ? '#721c24' : '#856404',
                  }}>
                    {change.type === 'add' ? t('tool.changeAdd') : change.type === 'remove' ? t('tool.changeRemove') : t('tool.changeModify')}
                  </span>
                  <span>{change.field} {change.count}개</span>
                </div>
                {change.details && change.details.length > 0 && (
                  <div style={{ marginLeft: 8, marginTop: 4, fontSize: 11, color: '#666' }}>
                    {change.details.slice(0, 5).map((detail, i) => (
                      <div key={i}>• {detail}</div>
                    ))}
                    {change.details.length > 5 && <div>• {t('tool.andMore', { count: change.details.length - 5 })}</div>}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button style={styles.applyBtn} onClick={handleApplyToBop}>
              {t('tool.apply')}
            </button>
            <button style={styles.secondaryBtn} onClick={cancelApply}>
              {t('tool.cancelApply')}
            </button>
          </div>
        </div>
      )}

      {/* AI 개선 */}
      {execResult && (
        <div style={{ ...styles.section, borderTop: '1px solid #e0e0e0', paddingTop: 16, marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <label style={{ ...styles.label, marginBottom: 0 }}>{t('tool.aiImprove')}</label>
            <button
              style={showImprove ? styles.secondaryBtn : styles.aiBtn}
              onClick={() => { setShowImprove(!showImprove); setImproveResult(null); setImproveFeedback(''); }}
            >
              {showImprove ? t('tool.collapse') : `✨ ${t('tool.startImprove')}`}
            </button>
          </div>

          {showImprove && (
            <>
              {/* 수정 범위 선택 */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>{t('tool.scopeSelect')}</div>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <label style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={improveScope.adapter}
                      onChange={e => setImproveScope(prev => ({ ...prev, adapter: e.target.checked }))}
                    />
                    {t('tool.scopeAdapter')}
                  </label>
                  <label style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={improveScope.params}
                      onChange={e => setImproveScope(prev => ({ ...prev, params: e.target.checked }))}
                    />
                    {t('tool.scopeParams')}
                  </label>
                  <label style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={improveScope.script}
                      onChange={e => setImproveScope(prev => ({ ...prev, script: e.target.checked }))}
                    />
                    {t('tool.scopeScript')}
                  </label>
                </div>
              </div>

              {/* 피드백 입력 */}
              <textarea
                style={{ ...styles.textarea, marginBottom: 8 }}
                placeholder={t('tool.improvePlaceholder')}
                value={improveFeedback}
                onChange={e => setImproveFeedback(e.target.value)}
                rows={3}
              />
              <button
                style={styles.primaryBtn}
                onClick={handleImprove}
                disabled={improving || !improveFeedback.trim() || (!improveScope.adapter && !improveScope.params && !improveScope.script)}
              >
                {improving ? t('tool.improving') : t('tool.improveRequest')}
              </button>

              {/* 개선 결과 미리보기 */}
              {improveResult && improveResult.success && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ ...styles.resultCard, borderLeft: '4px solid #667eea' }}>
                    <div style={{ fontWeight: 600, marginBottom: 8, color: '#667eea' }}>{t('tool.improvePreview')}</div>
                    <div style={{ fontSize: 13, marginBottom: 8 }}>{improveResult.explanation}</div>

                    {improveResult.changes_summary?.length > 0 && (
                      <div style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>{t('tool.changes')}</div>
                        {improveResult.changes_summary.map((change, idx) => (
                          <div key={idx} style={{ fontSize: 12, color: '#666', marginLeft: 8 }}>• {change}</div>
                        ))}
                      </div>
                    )}

                    {/* 코드 미리보기 */}
                    {improveResult.preview?.pre_process_code && (
                      <details style={{ marginTop: 8 }}>
                        <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666' }}>Pre-process 코드</summary>
                        <pre style={{ ...styles.codePreview, maxHeight: 150 }}>{improveResult.preview.pre_process_code}</pre>
                      </details>
                    )}
                    {improveResult.preview?.post_process_code && (
                      <details style={{ marginTop: 4 }}>
                        <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666' }}>Post-process 코드</summary>
                        <pre style={{ ...styles.codePreview, maxHeight: 150 }}>{improveResult.preview.post_process_code}</pre>
                      </details>
                    )}
                    {improveResult.preview?.params_schema && (
                      <details style={{ marginTop: 4 }}>
                        <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666' }}>{t('tool.scopeParams')}</summary>
                        <pre style={{ ...styles.codePreview, maxHeight: 150 }}>{JSON.stringify(improveResult.preview.params_schema, null, 2)}</pre>
                      </details>
                    )}
                    {improveResult.preview?.script_code && (
                      <details style={{ marginTop: 4 }}>
                        <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666' }}>{t('tool.scopeScript')}</summary>
                        <pre style={{ ...styles.codePreview, maxHeight: 200 }}>{improveResult.preview.script_code}</pre>
                      </details>
                    )}
                  </div>

                  {/* 적용 버튼 */}
                  <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                    <button
                      style={styles.applyBtn}
                      onClick={() => handleApplyImprovement(true)}
                      disabled={applying}
                    >
                      {applying ? t('tool.applying') : t('tool.saveAsNew', { version: getNextVersionLabel(tool.tool_id) })}
                    </button>
                    <button
                      style={styles.dangerBtn}
                      onClick={() => handleApplyImprovement(false)}
                      disabled={applying}
                    >
                      {t('tool.overwrite')}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* 삭제 */}
      <div style={{ ...styles.section, borderTop: '1px solid #eee', paddingTop: 16, marginTop: 16 }}>
        <button style={styles.dangerBtn} onClick={handleDelete}>{t('tool.deleteTool')}</button>
      </div>

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
  primaryBtn: { padding: '8px 16px', backgroundColor: '#4a90e2', color: 'white', border: 'none', borderRadius: '4px', fontSize: '13px', cursor: 'pointer', fontWeight: 'bold' },
  secondaryBtn: { padding: '8px 16px', backgroundColor: '#f0f0f0', color: '#333', border: '1px solid #ccc', borderRadius: '4px', fontSize: '13px', cursor: 'pointer' },
  applyBtn: { padding: '10px 20px', backgroundColor: '#50c878', color: 'white', border: 'none', borderRadius: '4px', fontSize: '14px', cursor: 'pointer', fontWeight: 'bold', flex: 1 },
  dangerBtn: { padding: '8px 16px', backgroundColor: '#ff6b6b', color: 'white', border: 'none', borderRadius: '4px', fontSize: '13px', cursor: 'pointer', fontWeight: 'bold' },
  badge: { fontSize: '11px', padding: '2px 8px', borderRadius: '10px', backgroundColor: '#e3f2fd', color: '#1565c0', fontWeight: '500' },
  resultCard: { backgroundColor: '#f9f9f9', border: '1px solid #e0e0e0', borderRadius: '6px', padding: '12px' },
  resultRow: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px' },
  resultLabel: { fontWeight: '600', color: '#555', minWidth: '50px' },
  resultValue: { color: '#333' },
  input: { flex: 1, padding: '4px 8px', border: '1px solid #ddd', borderRadius: '3px', fontSize: '13px', width: '100%', boxSizing: 'border-box' },
  paramInput: { width: '100%', padding: '6px 10px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '13px', boxSizing: 'border-box' },
  textarea: { width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '13px', resize: 'vertical', boxSizing: 'border-box', lineHeight: 1.5 },
  codePreview: { backgroundColor: '#f5f5f5', border: '1px solid #ddd', borderRadius: '4px', padding: '10px', fontSize: '11px', lineHeight: '1.4', overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace' },
  checkboxLabel: { display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#555', cursor: 'pointer' },
  aiBtn: { padding: '8px 16px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', border: 'none', borderRadius: '4px', fontSize: '13px', cursor: 'pointer', fontWeight: 'bold' },
  error: { color: '#c0392b', backgroundColor: '#fdecea', padding: '8px 12px', fontSize: '13px', borderBottom: '1px solid #f5c6cb' },
};

export default ToolDetailView;
