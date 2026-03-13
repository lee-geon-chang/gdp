import { useState, useEffect, useRef } from 'react';
import useBopStore from '../store/bopStore';
import { api } from '../services/api';
import * as XLSX from 'xlsx';
import useTranslation from '../i18n/useTranslation';

function ScenariosPanel() {
  const {
    exportBopData,
    setBopData,
    addMessage,
    normalizeAllProcesses,
    bopData,
    saveScenario,
    loadScenario,
    deleteScenario,
    listScenarios,
    createNewScenario
  } = useBopStore();

  // Scenario Management
  const [scenarios, setScenarios] = useState([]);
  const [scenarioName, setScenarioName] = useState('');
  const [showScenarioList, setShowScenarioList] = useState(false);

  // Scenario Comparison
  const [selectedForComparison, setSelectedForComparison] = useState([]);

  // Error
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const jsonUploadRef = useRef(null);
  const excelUploadRef = useRef(null);

  // Load scenario list on mount
  useEffect(() => {
    loadScenarioList();
  }, []);

  const loadScenarioList = () => {
    try {
      const list = listScenarios();
      setScenarios(list);
    } catch (err) {
      setError(t('sc.listError') + err.message);
    }
  };

  // === Scenario Management ===

  const handleSaveScenario = () => {
    if (!scenarioName.trim()) {
      setError(t('sc.enterName'));
      return;
    }

    if (!bopData) {
      setError(t('sc.noDataToSave'));
      return;
    }

    try {
      saveScenario(scenarioName.trim());
      loadScenarioList();
      setScenarioName('');
      addMessage('assistant', t('sc.savedMsg', { name: scenarioName.trim() }));
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLoadScenario = (id) => {
    try {
      loadScenario(id);
      const scenario = scenarios.find(s => s.id === id);
      addMessage('assistant', t('sc.loadedMsg', { name: scenario?.name }));
      setShowScenarioList(false);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteScenario = (id) => {
    const scenario = scenarios.find(s => s.id === id);
    if (!confirm(t('sc.confirmDelete', { name: scenario?.name }))) return;

    try {
      deleteScenario(id);
      loadScenarioList();
      addMessage('assistant', t('sc.deletedMsg', { name: scenario?.name }));
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleNewScenario = () => {
    if (bopData && !confirm(t('sc.confirmNew'))) {
      return;
    }

    createNewScenario();
    addMessage('assistant', t('sc.newStarted'));
    setError('');
  };

  // === Scenario Comparison ===

  const toggleComparisonSelection = (id) => {
    setSelectedForComparison(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const getScenarioMetrics = (scenarioData) => {
    if (!scenarioData) return null;

    const processes = scenarioData.processes || [];
    const processDetails = scenarioData.process_details || [];

    // 공정 수: process_details 인스턴스 수 (모든 병렬 라인 포함)
    const processCount = processDetails.length;

    // 예상 UPH 계산: 각 공정별 실질 CT를 구하고 병목 찾기
    let expectedUph = 0;
    let maxEffectiveTime = 0;

    // Group process_details by process_id to calculate effective CT per process
    const processGroups = new Map();
    processDetails.forEach(detail => {
      if (!processGroups.has(detail.process_id)) {
        processGroups.set(detail.process_id, []);
      }
      processGroups.get(detail.process_id).push(detail);
    });

    // For each process, calculate effective CT using harmonic mean (throughput sum)
    processGroups.forEach((details, processId) => {
      const cts = details.map(d => d.cycle_time_sec || 0);
      const invSum = cts.reduce((sum, ct) => sum + (ct > 0 ? 1 / ct : 0), 0);
      const effectiveCT = invSum > 0 ? 1 / invSum : 0;

      if (effectiveCT > maxEffectiveTime) {
        maxEffectiveTime = effectiveCT;
      }
    });

    // 예상 UPH = 3600초 / 병목 사이클타임
    expectedUph = maxEffectiveTime > 0 ? Math.round(3600 / maxEffectiveTime) : 0;

    return {
      processCount: processCount,
      expectedUph: expectedUph,
      equipmentCount: (scenarioData.equipments || []).length,
      workerCount: (scenarioData.workers || []).length,
      materialCount: (scenarioData.materials || []).length,
      obstacleCount: (scenarioData.obstacles || []).length,
    };
  };

  const renderComparisonChart = (label, values, maxValue, unit = '') => (
    <div style={styles.chartContainer}>
      <div style={styles.chartLabel}>{label}</div>
      <div style={styles.chartBars}>
        {values.map((item, index) => {
          const percentage = maxValue > 0 ? (item.value / maxValue) * 100 : 0;
          return (
            <div key={index} style={styles.chartRow}>
              <div style={styles.chartRowLabel}>{item.name}</div>
              <div style={styles.chartBarContainer}>
                <div
                  style={{
                    ...styles.chartBar,
                    width: `${percentage}%`,
                    backgroundColor: item.color || '#4a90e2'
                  }}
                />
                <span style={styles.chartValue}>{item.value}{unit}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderComparison = () => {
    const selectedScenarios = scenarios.filter(s => selectedForComparison.includes(s.id));

    if (selectedScenarios.length === 0) {
      return (
        <div style={styles.dataInfo}>
          {t('sc.selectToCompare')}
        </div>
      );
    }

    const colors = ['#4a90e2', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6'];
    const metricsData = selectedScenarios.map((scenario, index) => ({
      name: scenario.name,
      metrics: getScenarioMetrics(scenario.data),
      color: colors[index % colors.length]
    }));

    const processValues = metricsData.map(d => ({
      name: d.name,
      value: d.metrics?.processCount || 0,
      color: d.color
    }));
    const maxProcesses = Math.max(...processValues.map(v => v.value), 1);

    const uphValues = metricsData.map(d => ({
      name: d.name,
      value: d.metrics?.expectedUph || 0,
      color: d.color
    }));
    const maxUph = Math.max(...uphValues.map(v => v.value), 1);

    const equipmentValues = metricsData.map(d => ({
      name: d.name,
      value: d.metrics?.equipmentCount || 0,
      color: d.color
    }));
    const maxEquipment = Math.max(...equipmentValues.map(v => v.value), 1);

    const workerValues = metricsData.map(d => ({
      name: d.name,
      value: d.metrics?.workerCount || 0,
      color: d.color
    }));
    const maxWorkers = Math.max(...workerValues.map(v => v.value), 1);

    return (
      <div style={styles.comparisonContent}>
        <div style={styles.comparisonHeader}>
          <strong>{t('sc.selectedCount', { count: selectedScenarios.length })}</strong>
        </div>

        {renderComparisonChart(t('sc.processCount'), processValues, maxProcesses)}
        {renderComparisonChart(t('sc.expectedUph'), uphValues, maxUph)}
        {renderComparisonChart(t('sc.equipmentCount'), equipmentValues, maxEquipment)}
        {renderComparisonChart(t('sc.workerCount'), workerValues, maxWorkers)}
      </div>
    );
  };

  // === Data Import/Export ===

  const handleDownloadJSON = () => {
    const data = exportBopData();
    if (!data) {
      setError(t('sc.noDataToSave'));
      return;
    }

    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.project_title || 'bop'}_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);

    addMessage('assistant', t('sc.jsonDownloaded'));
    setError('');
  };

  const handleDownloadExcel = () => {
    const data = exportBopData();
    if (!data) {
      setError(t('sc.noDataToSave'));
      return;
    }

    try {
      api.exportExcel(data);
      addMessage('assistant', t('sc.excelDownloaded'));
      setError('');
    } catch (err) {
      setError(t('sc.excelGenError') + err.message);
    }
  };

  const handleUploadJSON = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = event.target.result;
        const data = JSON.parse(json);
        setBopData(data);
        setTimeout(() => normalizeAllProcesses(), 0);
        addMessage('assistant', t('sc.jsonLoaded', { name: file.name }));
        setError('');
      } catch (err) {
        setError(t('sc.jsonError') + err.message);
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleUploadExcel = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const binaryStr = event.target.result;
        const workbook = XLSX.read(binaryStr, { type: 'binary' });

        // Helper: read sheet data (empty array if not found), try English name first then Korean fallback
        const readSheet = (name, ...fallbacks) => {
          for (const n of [name, ...fallbacks]) {
            const sheet = workbook.Sheets[n];
            if (sheet) {
              const data = XLSX.utils.sheet_to_json(sheet);
              return data.filter(row => Object.values(row).some(v => v !== '' && v !== null && v !== undefined));
            }
          }
          return [];
        };
        // Helper: read column value with English key, Korean fallback
        const col = (row, en, ko) => row[en] ?? row[ko];

        // 1. Project Info
        const projectData = readSheet('Project Info', '프로젝트 정보');
        let project_title = '새 프로젝트';
        let target_uph = 60;
        projectData.forEach(row => {
          const item = col(row, 'Item', '항목');
          const value = col(row, 'Value', '값');
          if (item === 'Project Name' || item === '프로젝트명') project_title = value || project_title;
          if (item === 'Target UPH' || item === '목표 UPH') target_uph = parseInt(value) || target_uph;
        });

        // 2. Processes sheet (routing only)
        const processData = readSheet('Processes', '공정');
        if (processData.length === 0) {
          throw new Error('No data in "Processes" sheet.');
        }

        // 3. Process Details sheet (all parallel instances)
        // Backward compatible: supports legacy "병렬라인 상세" sheet
        const detailData = (() => {
          const d = readSheet('Process Details', '공정 상세');
          return d.length > 0 ? d : readSheet('병렬라인 상세');
        })();
        const process_details = [];
        const detailProcessIds = new Set();
        detailData.forEach(row => {
          const processId = col(row, 'Process ID', '공정 ID');
          if (!processId) return;
          detailProcessIds.add(processId);
          process_details.push({
            process_id: processId,
            parallel_index: parseInt(col(row, 'Parallel Index', '병렬 인덱스')) || 1,
            name: col(row, 'Name', '공정명') || processId,
            description: col(row, 'Description', '설명') || '',
            cycle_time_sec: parseFloat(col(row, 'Cycle Time (sec)', '사이클타임(초)')) || 60,
            location: {
              x: parseFloat(col(row, 'Location X', '위치 X')) || 0,
              y: parseFloat(col(row, 'Location Y', '위치 Y')) || 0,
              z: parseFloat(col(row, 'Location Z', '위치 Z')) || 0,
            },
            rotation_y: parseFloat(col(row, 'Rotation Y', '회전 Y')) || 0,
          });
        });

        // 4. Resource Assignments sheet -> flat resource_assignments
        const resourceData = readSheet('Resource Assignments', '리소스 배치');
        const resource_assignments = [];
        resourceData.forEach(row => {
          const processId = col(row, 'Process ID', '공정 ID');
          const resourceId = col(row, 'Resource ID', '리소스 ID');
          if (!processId || !resourceId) return;

          const pliRaw = col(row, 'Parallel Index', '병렬 인덱스') ?? row['병렬라인 인덱스'];
          const parallel_index = (pliRaw !== '' && pliRaw !== null && pliRaw !== undefined)
            ? parseInt(pliRaw)
            : 1;

          resource_assignments.push({
            process_id: processId,
            parallel_index,
            resource_type: col(row, 'Resource Type', '리소스 유형'),
            resource_id: resourceId,
            quantity: parseFloat(col(row, 'Quantity', '수량')) || 1,
            relative_location: {
              x: parseFloat(col(row, 'Offset X', '상대위치 X')) || 0,
              y: parseFloat(col(row, 'Offset Y', '상대위치 Y')) || 0,
              z: parseFloat(col(row, 'Offset Z', '상대위치 Z')) || 0,
            },
            rotation_y: parseFloat(col(row, 'Rotation Y', '회전 Y')) || 0,
            scale: {
              x: parseFloat(col(row, 'Scale X', '스케일 X')) || 1,
              y: parseFloat(col(row, 'Scale Y', '스케일 Y')) || 1,
              z: parseFloat(col(row, 'Scale Z', '스케일 Z')) || 1,
            },
          });
        });

        // 5. Assemble processes (routing only)
        const processes = processData.map(row => {
          const process_id = col(row, 'Process ID', '공정 ID');

          // If no detail exists, create a default one
          if (!detailProcessIds.has(process_id)) {
            process_details.push({
              process_id,
              parallel_index: 1,
              name: process_id,
              description: '',
              cycle_time_sec: 60,
              location: { x: 0, y: 0, z: 0 },
              rotation_y: 0,
            });
          }

          const predecessors = col(row, 'Predecessors', '선행 공정');
          const successors = col(row, 'Successors', '후행 공정');
          return {
            process_id,
            predecessor_ids: predecessors
              ? String(predecessors).split(',').map(s => s.trim()).filter(Boolean)
              : [],
            successor_ids: successors
              ? String(successors).split(',').map(s => s.trim()).filter(Boolean)
              : [],
          };
        });

        // 6. Equipment sheet
        const equipmentData = readSheet('Equipment', '장비');
        const equipments = equipmentData.map(row => ({
          equipment_id: col(row, 'Equipment ID', '장비 ID'),
          name: col(row, 'Name', '장비명') || col(row, 'Equipment ID', '장비 ID'),
          type: col(row, 'Type', '유형') || 'machine',
        })).filter(e => e.equipment_id);

        // 7. Workers sheet
        const workerData = readSheet('Workers', '작업자');
        const workers = workerData.map(row => ({
          worker_id: col(row, 'Worker ID', '작업자 ID'),
          name: col(row, 'Name', '이름') || col(row, 'Worker ID', '작업자 ID'),
          skill_level: col(row, 'Skill Level', '숙련도') || 'Mid',
        })).filter(w => w.worker_id);

        // 8. Materials sheet
        const materialData = readSheet('Materials', '자재');
        const materials = materialData.map(row => ({
          material_id: col(row, 'Material ID', '자재 ID'),
          name: col(row, 'Name', '자재명') || col(row, 'Material ID', '자재 ID'),
          unit: col(row, 'Unit', '단위') || 'ea',
        })).filter(m => m.material_id);

        // 9. Obstacles sheet
        const obstacleData = readSheet('Obstacles', '장애물');
        const obstacles = obstacleData.map(row => ({
          obstacle_id: col(row, 'Obstacle ID', '장애물 ID'),
          name: col(row, 'Name', '이름') || '',
          type: col(row, 'Type', '유형') || 'fence',
          position: {
            x: parseFloat(col(row, 'Location X', '위치 X')) || 0,
            y: parseFloat(col(row, 'Location Y', '위치 Y')) || 0,
            z: parseFloat(col(row, 'Location Z', '위치 Z')) || 0,
          },
          size: {
            width: parseFloat(col(row, 'Size X', '크기 X')) || 1,
            height: parseFloat(col(row, 'Size Y', '크기 Y')) || 1,
            depth: parseFloat(col(row, 'Size Z', '크기 Z')) || 1,
          },
          rotation_y: parseFloat(col(row, 'Rotation Y', '회전 Y')) || 0,
        })).filter(o => o.obstacle_id);

        // 최종 BOP 데이터 조립 (flat structure)
        const data = {
          project_title,
          target_uph,
          processes,
          process_details,
          resource_assignments,
          equipments,
          workers,
          materials,
          obstacles,
        };

        setBopData(data);
        setTimeout(() => normalizeAllProcesses(), 0);

        const summary = [
          t('sc.summaryProcesses', { count: processes.length, instances: process_details.length }),
          t('sc.summaryResources', { count: resource_assignments.length }),
          t('sc.summaryEquipment', { count: equipments.length }),
          t('sc.summaryWorkers', { count: workers.length }),
          t('sc.summaryMaterials', { count: materials.length }),
          t('sc.summaryObstacles', { count: obstacles.length }),
        ].join(', ');
        addMessage('assistant', t('sc.excelLoaded', { name: file.name, summary }));
        setError('');
      } catch (err) {
        setError(t('sc.excelError') + err.message);
      }
    };
    reader.readAsBinaryString(file);
    e.target.value = '';
  };

  return (
    <div style={styles.container}>
      {/* Scenario Management Section */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionTitle}>💾 {t('sc.management')}</span>
        </div>

        {/* New Scenario */}
        <div style={{ marginBottom: '12px' }}>
          <button style={styles.newScenarioBtn} onClick={handleNewScenario}>
            ➕ {t('sc.newScenario')}
          </button>
        </div>

        {/* Save Scenario */}
        <div style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              style={styles.scenarioInput}
              type="text"
              placeholder={t('sc.namePlaceholder')}
              value={scenarioName}
              onChange={(e) => setScenarioName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSaveScenario()}
            />
            <button
              style={styles.saveScenarioBtn}
              onClick={handleSaveScenario}
              disabled={!scenarioName.trim() || !bopData}
            >
              💾 {t('sc.save')}
            </button>
          </div>
        </div>

        {/* Load Scenario */}
        <div style={{ marginBottom: '12px' }}>
          <button
            style={styles.loadScenarioBtn}
            onClick={() => setShowScenarioList(!showScenarioList)}
          >
            📂 {t('sc.load', { count: scenarios.length })}
          </button>
        </div>

        {/* Scenario List */}
        {showScenarioList && scenarios.length > 0 && (
          <div style={styles.scenarioList}>
            {scenarios.map(scenario => (
              <div key={scenario.id} style={styles.scenarioItem}>
                <div style={styles.scenarioInfo}>
                  <div style={styles.scenarioName}>{scenario.name}</div>
                  <div style={styles.scenarioDate}>
                    {new Date(scenario.updatedAt).toLocaleDateString('ko-KR')}
                  </div>
                </div>
                <div style={styles.scenarioActions}>
                  <button
                    style={styles.scenarioLoadBtn}
                    onClick={() => handleLoadScenario(scenario.id)}
                  >
                    {t('sc.open')}
                  </button>
                  <button
                    style={styles.scenarioDeleteBtn}
                    onClick={() => handleDeleteScenario(scenario.id)}
                  >
                    {t('sc.delete')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {showScenarioList && scenarios.length === 0 && (
          <div style={styles.dataInfo}>{t('sc.noSaved')}</div>
        )}
      </div>

      {/* Scenario Comparison Section */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionTitle}>📊 {t('sc.comparison')}</span>
        </div>

        {/* Scenario Selection */}
        {scenarios.length > 0 && (
          <div style={styles.comparisonList}>
            {scenarios.map(scenario => (
              <div key={scenario.id} style={styles.comparisonItem}>
                <label style={styles.comparisonLabel}>
                  <input
                    type="checkbox"
                    checked={selectedForComparison.includes(scenario.id)}
                    onChange={() => toggleComparisonSelection(scenario.id)}
                    style={styles.checkbox}
                  />
                  <span style={styles.comparisonName}>{scenario.name}</span>
                  <span style={styles.comparisonDate}>
                    {new Date(scenario.updatedAt).toLocaleDateString('ko-KR')}
                  </span>
                </label>
              </div>
            ))}
          </div>
        )}

        {scenarios.length === 0 && (
          <div style={styles.dataInfo}>{t('sc.noSaved')}</div>
        )}

        {/* Comparison Results */}
        {selectedForComparison.length > 0 && renderComparison()}
      </div>

      {/* Data Import/Export Section */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionTitle}>📂 {t('sc.dataManagement')}</span>
        </div>
        <div style={styles.dataButtons}>
          <div style={styles.dataButtonGroup}>
            <span style={styles.dataButtonLabel}>{t('sc.export')}</span>
            <button style={styles.dataBtn} onClick={handleDownloadJSON}>
              {t('sc.downloadJSON')}
            </button>
            <button style={styles.dataBtn} onClick={handleDownloadExcel}>
              {t('sc.downloadExcel')}
            </button>
          </div>
          <div style={styles.dataButtonGroup}>
            <span style={styles.dataButtonLabel}>{t('sc.import')}</span>
            <input
              ref={jsonUploadRef}
              type="file"
              accept=".json"
              onChange={handleUploadJSON}
              style={{ display: 'none' }}
            />
            <button style={styles.dataBtn} onClick={() => jsonUploadRef.current?.click()}>
              {t('sc.uploadJSON')}
            </button>
            <input
              ref={excelUploadRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={handleUploadExcel}
              style={{ display: 'none' }}
            />
            <button style={styles.dataBtn} onClick={() => excelUploadRef.current?.click()}>
              {t('sc.uploadExcel')}
            </button>
          </div>
        </div>
        <div style={styles.dataInfo}>
          {t('sc.dataInfo')}
        </div>
      </div>

      {error && <div style={styles.error}>{error}</div>}
    </div>
  );
}

const styles = {
  container: {
    height: '100%',
    overflow: 'auto',
    padding: '16px',
    backgroundColor: '#fff',
  },
  section: {
    backgroundColor: '#f0f8ff',
    border: '1px solid #b3d9ff',
    borderRadius: '6px',
    padding: '14px',
    marginBottom: '16px',
  },
  sectionHeader: {
    marginBottom: '12px',
    paddingBottom: '8px',
    borderBottom: '2px solid #4a90e2',
  },
  sectionTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
  },
  newScenarioBtn: {
    width: '100%',
    padding: '8px 12px',
    backgroundColor: '#50c878',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: '600',
  },
  scenarioInput: {
    flex: 1,
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '13px',
  },
  saveScenarioBtn: {
    padding: '8px 16px',
    backgroundColor: '#4a90e2',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: '600',
  },
  loadScenarioBtn: {
    width: '100%',
    padding: '8px 12px',
    backgroundColor: '#fff',
    color: '#4a90e2',
    border: '1px solid #4a90e2',
    borderRadius: '4px',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: '600',
  },
  scenarioList: {
    marginTop: '12px',
    maxHeight: '300px',
    overflowY: 'auto',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: 'white',
  },
  scenarioItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 12px',
    borderBottom: '1px solid #f0f0f0',
  },
  scenarioInfo: {
    flex: 1,
  },
  scenarioName: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '4px',
  },
  scenarioDate: {
    fontSize: '11px',
    color: '#888',
  },
  scenarioActions: {
    display: 'flex',
    gap: '6px',
  },
  scenarioLoadBtn: {
    padding: '4px 12px',
    backgroundColor: '#4a90e2',
    color: 'white',
    border: 'none',
    borderRadius: '3px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  scenarioDeleteBtn: {
    padding: '4px 12px',
    backgroundColor: '#e74c3c',
    color: 'white',
    border: 'none',
    borderRadius: '3px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  comparisonList: {
    marginTop: '12px',
    marginBottom: '12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: 'white',
    maxHeight: '200px',
    overflowY: 'auto',
  },
  comparisonItem: {
    padding: '8px 12px',
    borderBottom: '1px solid #f0f0f0',
  },
  comparisonLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
    fontSize: '13px',
  },
  comparisonName: {
    flex: 1,
    fontWeight: '500',
    color: '#333',
  },
  comparisonDate: {
    fontSize: '11px',
    color: '#888',
  },
  checkbox: {
    cursor: 'pointer',
  },
  comparisonContent: {
    marginTop: '16px',
    padding: '12px',
    backgroundColor: 'white',
    border: '1px solid #ddd',
    borderRadius: '4px',
  },
  comparisonHeader: {
    marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '2px solid #4a90e2',
    fontSize: '14px',
    color: '#333',
  },
  chartContainer: {
    marginBottom: '20px',
  },
  chartLabel: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '10px',
  },
  chartBars: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  chartRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  chartRowLabel: {
    minWidth: '120px',
    fontSize: '12px',
    color: '#555',
    fontWeight: '500',
  },
  chartBarContainer: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    position: 'relative',
    height: '24px',
  },
  chartBar: {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.3s ease',
    minWidth: '2px',
  },
  chartValue: {
    position: 'absolute',
    right: '8px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#333',
  },
  dataButtons: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    marginBottom: '12px',
  },
  dataButtonGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  dataButtonLabel: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#555',
    minWidth: '70px',
  },
  dataBtn: {
    padding: '6px 12px',
    backgroundColor: '#4a90e2',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: '500',
  },
  dataInfo: {
    fontSize: '12px',
    color: '#666',
    lineHeight: '1.5',
    padding: '8px',
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
    borderRadius: '4px',
  },
  error: {
    padding: '12px',
    backgroundColor: '#fee',
    border: '1px solid #fcc',
    borderRadius: '4px',
    color: '#c00',
    fontSize: '13px',
    marginTop: '12px',
  },
};

export default ScenariosPanel;
