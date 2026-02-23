import { useEffect, useRef, useState } from 'react';
import useBopStore from '../store/bopStore';
import { getResourceSize } from './Viewer3D';
import useTranslation from '../i18n/useTranslation';

function EquipmentsTable() {
  const { bopData, selectedResourceKey, setSelectedResource,
    updateResourceLocation, updateResourceScale, updateResourceRotation,
    addEquipment, updateEquipment, deleteEquipment } = useBopStore();
  const selectedRowRef = useRef(null);
  const [editingCell, setEditingCell] = useState(null);
  const [selectedMasterId, setSelectedMasterId] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const { t } = useTranslation();

  // Auto-scroll to selected row
  useEffect(() => {
    if (selectedRowRef.current && selectedResourceKey) {
      selectedRowRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  }, [selectedResourceKey]);

  const handleAddEquipment = () => {
    addEquipment();
    const equipments = useBopStore.getState().bopData?.equipments;
    if (equipments && equipments.length > 0) {
      setSelectedMasterId(equipments[equipments.length - 1].equipment_id);
    }
  };

  const handleDeleteEquipment = () => {
    if (!selectedMasterId) return;
    if (window.confirm(t('eq.confirmDelete'))) {
      deleteEquipment(selectedMasterId);
      setSelectedMasterId(null);
    }
  };

  const handleDeleteSelected = () => {
    if (selectedIds.length === 0) return;
    if (window.confirm(t('eq.confirmDeleteMulti', { count: selectedIds.length }))) {
      selectedIds.forEach(id => deleteEquipment(id));
      setSelectedIds([]);
      setSelectedMasterId(null);
    }
  };

  const handleToggleSelect = (equipmentId) => {
    setSelectedIds(prev =>
      prev.includes(equipmentId)
        ? prev.filter(id => id !== equipmentId)
        : [...prev, equipmentId]
    );
  };

  const handleToggleSelectAll = () => {
    const equipments = bopData?.equipments || [];
    if (selectedIds.length === equipments.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(equipments.map(e => e.equipment_id));
    }
  };

  if (!bopData || !bopData.equipments || bopData.equipments.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>{t('eq.title')}</h2>
          <div style={styles.count}>{t('eq.total', { count: 0 })}</div>
        </div>
        <div style={styles.actionBar}>
          <button style={styles.actionButton} onClick={handleAddEquipment}>
            {t('eq.add')}
          </button>
        </div>
        <div style={styles.emptyState}>
          <p>{t('eq.noData')}</p>
          <button style={styles.actionButton} onClick={handleAddEquipment}>
            {t('eq.add')}
          </button>
        </div>
      </div>
    );
  }

  const getEquipmentTypeLabel = (type) => {
    switch (type) {
      case 'robot': return t('eq.robot');
      case 'machine': return t('eq.machine');
      case 'manual_station': return t('eq.manualStation');
      default: return type;
    }
  };

  const getEquipmentTypeColor = (type) => {
    switch (type) {
      case 'robot': return '#4a90e2';
      case 'machine': return '#ff6b6b';
      case 'manual_station': return '#50c878';
      default: return '#888';
    }
  };

  // 각 장비가 사용되는 공정 찾기 및 위치 정보
  const getProcessesUsingEquipment = (equipmentId) => {
    if (!bopData.resource_assignments) return [];
    const result = [];

    bopData.resource_assignments.forEach(ra => {
      if (ra.resource_type === 'equipment' && ra.resource_id === equipmentId) {
        // Look up process detail for location info
        const detail = (bopData.process_details || []).find(
          d => d.process_id === ra.process_id && d.parallel_index === ra.parallel_index
        );
        const processLocation = detail?.location || { x: 0, y: 0, z: 0 };

        // 실제 위치 = 공정 위치 + 상대 위치
        const relLoc = ra.relative_location || { x: 0, y: 0, z: 0 };
        const actualLocation = {
          x: processLocation.x + relLoc.x,
          y: processLocation.y + relLoc.y,
          z: processLocation.z + relLoc.z,
        };

        result.push({
          assignment: ra,
          detail,
          actualLocation,
        });
      }
    });

    return result;
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>{t('eq.title')}</h2>
        <div style={styles.count}>{t('eq.total', { count: bopData.equipments.length })}</div>
      </div>

      {/* Action Bar */}
      <div style={styles.actionBar}>
        <button style={styles.actionButton} onClick={handleAddEquipment}>
          {t('eq.add')}
        </button>
        <button
          style={{
            ...styles.actionButtonDanger,
            ...(selectedIds.length === 0 ? styles.actionButtonDisabled : {})
          }}
          disabled={selectedIds.length === 0}
          onClick={handleDeleteSelected}
        >
          {t('eq.deleteSelected', { count: selectedIds.length })}
        </button>
      </div>

      {/* Table */}
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={{ ...styles.th, width: '40px' }}>
                <input
                  type="checkbox"
                  checked={bopData.equipments.length > 0 && selectedIds.length === bopData.equipments.length}
                  onChange={handleToggleSelectAll}
                  style={styles.checkbox}
                />
              </th>
              <th style={{ ...styles.th, width: '100px' }}>{t('eq.id')}</th>
              <th style={{ ...styles.th, minWidth: '150px' }}>{t('eq.name')}</th>
              <th style={{ ...styles.th, width: '80px' }}>{t('eq.type')}</th>
              <th style={{ ...styles.th, width: '100px' }}>{t('eq.usedIn')}</th>
              <th style={{ ...styles.th, width: '120px' }}>{t('common.location')}</th>
              <th style={{ ...styles.th, width: '150px' }}>{t('common.sizeWHD')}</th>
              <th style={{ ...styles.th, width: '80px' }}>{t('common.rotation')}</th>
            </tr>
          </thead>
          <tbody>
            {bopData.equipments.flatMap((equipment) => {
              const usedProcesses = getProcessesUsingEquipment(equipment.equipment_id);
              const isMasterSelected = selectedMasterId === equipment.equipment_id;

              if (usedProcesses.length === 0) {
                return (
                  <tr
                    key={equipment.equipment_id}
                    style={{
                      ...styles.row,
                      ...(isMasterSelected ? styles.rowMasterSelected : {}),
                    }}
                    onClick={() => setSelectedMasterId(equipment.equipment_id)}
                  >
                    <td style={styles.td} onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(equipment.equipment_id)}
                        onChange={() => handleToggleSelect(equipment.equipment_id)}
                        style={styles.checkbox}
                      />
                    </td>
                    <td style={styles.td}><strong>{equipment.equipment_id}</strong></td>
                    <td style={styles.td}>
                      {isMasterSelected ? (
                        <input
                          type="text"
                          style={styles.editInput}
                          value={equipment.name}
                          onChange={(e) => updateEquipment(equipment.equipment_id, { name: e.target.value })}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : equipment.name}
                    </td>
                    <td style={styles.td}>
                      {isMasterSelected ? (
                        <select
                          style={styles.editSelect}
                          value={equipment.type}
                          onChange={(e) => updateEquipment(equipment.equipment_id, { type: e.target.value })}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <option value="robot">{t('eq.robot')}</option>
                          <option value="machine">{t('eq.machine')}</option>
                          <option value="manual_station">{t('eq.manualStation')}</option>
                        </select>
                      ) : (
                        <span style={{ ...styles.typeBadge, backgroundColor: getEquipmentTypeColor(equipment.type) }}>
                          {getEquipmentTypeLabel(equipment.type)}
                        </span>
                      )}
                    </td>
                    <td style={styles.td} colSpan={4}><span style={styles.notUsed}>{t('eq.notUsed')}</span></td>
                  </tr>
                );
              }

              return usedProcesses.map(({ assignment, detail }, idx) => {
                const lineLabel = `${assignment.process_id}:${assignment.parallel_index}`;
                const resourceKey = `equipment:${equipment.equipment_id}:${assignment.process_id}:${assignment.parallel_index}`;
                const isSelected = selectedResourceKey === resourceKey;

                const relLoc = assignment.relative_location || { x: 0, y: 0, z: 0 };
                const scale = assignment.scale || { x: 1, y: 1, z: 1 };
                const rotationY = assignment.rotation_y || 0;

                // Effective position 계산 (auto-layout 적용)
                const processResources = (bopData.resource_assignments || []).filter(
                  r => r.process_id === assignment.process_id && r.parallel_index === assignment.parallel_index
                );
                const resourceIndex = processResources.findIndex(r =>
                  r.resource_type === assignment.resource_type && r.resource_id === assignment.resource_id
                );
                const totalResources = processResources.length;
                const effectivePos = (relLoc.x !== 0 || relLoc.z !== 0)
                  ? { x: relLoc.x, z: relLoc.z }
                  : { x: 0, z: resourceIndex * 0.9 - (totalResources - 1) * 0.9 / 2 };

                const baseSize = getResourceSize('equipment', equipment.type);
                const actualSize = {
                  x: baseSize.width * scale.x,
                  y: baseSize.height * scale.y,
                  z: baseSize.depth * scale.z
                };

                return (
                  <tr
                    key={`${equipment.equipment_id}-${assignment.process_id}-${assignment.parallel_index}`}
                    ref={isSelected ? selectedRowRef : null}
                    style={{
                      ...styles.row,
                      ...(isSelected ? styles.rowSelected : {}),
                      ...(isMasterSelected && !isSelected ? styles.rowMasterSelected : {}),
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedResource('equipment', equipment.equipment_id, assignment.process_id, assignment.parallel_index);
                      setSelectedMasterId(equipment.equipment_id);
                    }}
                  >
                    {idx === 0 && (
                      <>
                        <td style={styles.td} rowSpan={usedProcesses.length} onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(equipment.equipment_id)}
                            onChange={() => handleToggleSelect(equipment.equipment_id)}
                            style={styles.checkbox}
                          />
                        </td>
                        <td style={styles.td} rowSpan={usedProcesses.length}>
                          <strong>{equipment.equipment_id}</strong>
                        </td>
                        <td style={styles.td} rowSpan={usedProcesses.length}>
                          {isMasterSelected ? (
                            <input
                              type="text"
                              style={styles.editInput}
                              value={equipment.name}
                              onChange={(e) => updateEquipment(equipment.equipment_id, { name: e.target.value })}
                              onClick={(e) => e.stopPropagation()}
                            />
                          ) : equipment.name}
                        </td>
                        <td style={styles.td} rowSpan={usedProcesses.length}>
                          {isMasterSelected ? (
                            <select
                              style={styles.editSelect}
                              value={equipment.type}
                              onChange={(e) => updateEquipment(equipment.equipment_id, { type: e.target.value })}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <option value="robot">로봇</option>
                              <option value="machine">기계</option>
                              <option value="manual_station">수작업대</option>
                            </select>
                          ) : (
                            <span style={{ ...styles.typeBadge, backgroundColor: getEquipmentTypeColor(equipment.type) }}>
                              {getEquipmentTypeLabel(equipment.type)}
                            </span>
                          )}
                        </td>
                      </>
                    )}
                    <td style={styles.td}>
                      <span style={styles.processChip}>{lineLabel}</span>
                    </td>
                    <td style={styles.td}>
                      <div style={styles.locationCell}>
                        ({effectivePos.x.toFixed(1)}, {effectivePos.z.toFixed(1)})
                      </div>
                    </td>
                    <td style={styles.td}>
                      <div style={styles.locationCell}>
                        ({actualSize.x.toFixed(1)}, {actualSize.y.toFixed(1)}, {actualSize.z.toFixed(1)})
                      </div>
                    </td>
                    <td style={styles.td}>
                      <div style={styles.locationCell}>
                        {(rotationY * 180 / Math.PI).toFixed(1)}°
                      </div>
                    </td>
                  </tr>
                );
              });
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const styles = {
  container: {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: 'white',
    overflow: 'hidden',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#999',
    fontSize: '14px',
    gap: '12px',
  },
  header: {
    padding: '20px',
    borderBottom: '2px solid #ddd',
    backgroundColor: '#f9f9f9',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#333',
  },
  count: {
    fontSize: '14px',
    color: '#4a90e2',
    fontWeight: 'bold',
  },
  actionBar: {
    display: 'flex',
    gap: '8px',
    padding: '10px 20px',
    borderBottom: '1px solid #ddd',
    backgroundColor: '#fafafa',
  },
  actionButton: {
    padding: '6px 14px',
    backgroundColor: '#4a90e2',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  actionButtonDanger: {
    padding: '6px 14px',
    backgroundColor: '#e74c3c',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  actionButtonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  tableWrapper: {
    flex: 1,
    overflow: 'auto',
    padding: '0',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    position: 'sticky',
    top: 0,
    backgroundColor: '#f5f5f5',
    padding: '12px 8px',
    textAlign: 'left',
    fontWeight: 'bold',
    borderBottom: '2px solid #ddd',
    fontSize: '12px',
    color: '#555',
    zIndex: 1,
  },
  row: {
    backgroundColor: 'white',
    borderBottom: '1px solid #ddd',
    transition: 'background-color 0.2s',
    cursor: 'pointer',
  },
  rowSelected: {
    backgroundColor: '#e3f2fd',
    borderLeft: '3px solid #4a90e2',
  },
  rowMasterSelected: {
    backgroundColor: '#f3e5f5',
    borderLeft: '3px solid #9c27b0',
  },
  td: {
    padding: '8px 6px',
    verticalAlign: 'middle',
  },
  input: {
    width: '100%',
    padding: '4px 6px',
    fontSize: '11px',
    border: '1px solid #ddd',
    borderRadius: '3px',
    fontFamily: 'monospace',
  },
  locationCell: {
    fontSize: '11px',
    color: '#666',
    fontFamily: 'monospace',
  },
  editInput: {
    width: '100%',
    padding: '4px 6px',
    fontSize: '12px',
    border: '1px solid #9c27b0',
    borderRadius: '3px',
    boxSizing: 'border-box',
    backgroundColor: '#fce4ec',
  },
  editSelect: {
    width: '100%',
    padding: '4px 6px',
    fontSize: '11px',
    border: '1px solid #9c27b0',
    borderRadius: '3px',
    backgroundColor: '#fce4ec',
    cursor: 'pointer',
  },
  typeBadge: {
    display: 'inline-block',
    padding: '4px 12px',
    color: 'white',
    fontSize: '11px',
    borderRadius: '12px',
    fontWeight: 'bold',
  },
  processList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  processItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 8px',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  processItemSelected: {
    backgroundColor: '#e3f2fd',
    borderLeft: '3px solid #4a90e2',
  },
  processChip: {
    display: 'inline-block',
    padding: '2px 8px',
    backgroundColor: '#e3f2fd',
    color: '#1976d2',
    fontSize: '11px',
    borderRadius: '8px',
    fontWeight: '500',
  },
  locationText: {
    fontSize: '10px',
    color: '#666',
    fontFamily: 'monospace',
  },
  notUsed: {
    color: '#999',
    fontSize: '12px',
    fontStyle: 'italic',
  },
  checkbox: {
    cursor: 'pointer',
    width: '16px',
    height: '16px',
  },
};

export default EquipmentsTable;
