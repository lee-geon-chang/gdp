import { useEffect, useRef, useState } from 'react';
import useBopStore from '../store/bopStore';
import { getResourceSize } from './Viewer3D';
import useTranslation from '../i18n/useTranslation';

function MaterialsTable() {
  const { bopData, selectedResourceKey, setSelectedResource,
    updateResourceLocation, updateResourceScale, updateResourceRotation,
    updateResourceQuantity,
    addMaterial, updateMaterial, deleteMaterial } = useBopStore();
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

  const handleAddMaterial = () => {
    addMaterial();
    const materials = useBopStore.getState().bopData?.materials;
    if (materials && materials.length > 0) {
      setSelectedMasterId(materials[materials.length - 1].material_id);
    }
  };

  const handleDeleteMaterial = () => {
    if (!selectedMasterId) return;
    if (window.confirm(t('mt.confirmDelete'))) {
      deleteMaterial(selectedMasterId);
      setSelectedMasterId(null);
    }
  };

  const handleDeleteSelected = () => {
    if (selectedIds.length === 0) return;
    if (window.confirm(t('mt.confirmDeleteMulti', { count: selectedIds.length }))) {
      selectedIds.forEach(id => deleteMaterial(id));
      setSelectedIds([]);
      setSelectedMasterId(null);
    }
  };

  const handleToggleSelect = (materialId) => {
    setSelectedIds(prev =>
      prev.includes(materialId)
        ? prev.filter(id => id !== materialId)
        : [...prev, materialId]
    );
  };

  const handleToggleSelectAll = () => {
    const materials = bopData?.materials || [];
    if (selectedIds.length === materials.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(materials.map(m => m.material_id));
    }
  };

  if (!bopData || !bopData.materials || bopData.materials.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>{t('mt.title')}</h2>
          <div style={styles.count}>{t('mt.total', { count: 0 })}</div>
        </div>
        <div style={styles.actionBar}>
          <button style={styles.actionButton} onClick={handleAddMaterial}>
            {t('mt.add')}
          </button>
        </div>
        <div style={styles.emptyState}>
          <p>{t('mt.noData')}</p>
          <button style={styles.actionButton} onClick={handleAddMaterial}>
            {t('mt.add')}
          </button>
        </div>
      </div>
    );
  }

  // 각 자재가 사용되는 공정 찾기
  const getMaterialUsage = (materialId) => {
    if (!bopData.resource_assignments) return [];

    const usage = [];

    bopData.resource_assignments.forEach(ra => {
      if (ra.resource_type === 'material' && ra.resource_id === materialId) {
        const detail = (bopData.process_details || []).find(
          d => d.process_id === ra.process_id && d.parallel_index === ra.parallel_index
        );

        usage.push({
          assignment: ra,
          detail,
        });
      }
    });

    return usage;
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>{t('mt.title')}</h2>
        <div style={styles.count}>{t('mt.total', { count: bopData.materials.length })}</div>
      </div>

      {/* Action Bar */}
      <div style={styles.actionBar}>
        <button style={styles.actionButton} onClick={handleAddMaterial}>
          {t('mt.add')}
        </button>
        <button
          style={{
            ...styles.actionButtonDanger,
            ...(selectedIds.length === 0 ? styles.actionButtonDisabled : {})
          }}
          disabled={selectedIds.length === 0}
          onClick={handleDeleteSelected}
        >
          {t('mt.deleteSelected', { count: selectedIds.length })}
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
                  checked={bopData.materials.length > 0 && selectedIds.length === bopData.materials.length}
                  onChange={handleToggleSelectAll}
                  style={styles.checkbox}
                />
              </th>
              <th style={{ ...styles.th, width: '100px' }}>{t('mt.id')}</th>
              <th style={{ ...styles.th, minWidth: '150px' }}>{t('mt.name')}</th>
              <th style={{ ...styles.th, width: '60px' }}>{t('mt.unit')}</th>
              <th style={{ ...styles.th, width: '80px' }}>{t('mt.quantity')}</th>
              <th style={{ ...styles.th, width: '100px' }}>{t('mt.usedIn')}</th>
              <th style={{ ...styles.th, width: '120px' }}>{t('common.location')}</th>
              <th style={{ ...styles.th, width: '150px' }}>{t('common.sizeWHD')}</th>
              <th style={{ ...styles.th, width: '80px' }}>{t('common.rotation')}</th>
            </tr>
          </thead>
          <tbody>
            {bopData.materials.flatMap((material) => {
              const usage = getMaterialUsage(material.material_id);
              const isMasterSelected = selectedMasterId === material.material_id;

              if (usage.length === 0) {
                return (
                  <tr
                    key={material.material_id}
                    style={{
                      ...styles.row,
                      ...(isMasterSelected ? styles.rowMasterSelected : {}),
                    }}
                    onClick={() => setSelectedMasterId(material.material_id)}
                  >
                    <td style={styles.td} onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(material.material_id)}
                        onChange={() => handleToggleSelect(material.material_id)}
                        style={styles.checkbox}
                      />
                    </td>
                    <td style={styles.td}><strong>{material.material_id}</strong></td>
                    <td style={styles.td}>
                      {isMasterSelected ? (
                        <input
                          type="text"
                          style={styles.editInput}
                          value={material.name}
                          onChange={(e) => updateMaterial(material.material_id, { name: e.target.value })}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : material.name}
                    </td>
                    <td style={styles.td}>
                      {isMasterSelected ? (
                        <input
                          type="text"
                          style={styles.editInput}
                          value={material.unit}
                          onChange={(e) => updateMaterial(material.material_id, { unit: e.target.value })}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <span style={styles.unit}>{material.unit}</span>
                      )}
                    </td>
                    <td style={styles.td} colSpan={5}><span style={styles.notUsed}>{t('mt.notUsed')}</span></td>
                  </tr>
                );
              }

              return usage.map(({ assignment, detail }, idx) => {
                const lineLabel = `${assignment.process_id}:${assignment.parallel_index}`;
                const resourceKey = `material:${material.material_id}:${assignment.process_id}:${assignment.parallel_index}`;
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

                const baseSize = getResourceSize('material', null);
                const actualSize = {
                  x: baseSize.width * scale.x,
                  y: baseSize.height * scale.y,
                  z: baseSize.depth * scale.z
                };

                return (
                  <tr
                    key={`${material.material_id}-${assignment.process_id}-${assignment.parallel_index}`}
                    ref={isSelected ? selectedRowRef : null}
                    style={{
                      ...styles.row,
                      ...(isSelected ? styles.rowSelected : {}),
                      ...(isMasterSelected && !isSelected ? styles.rowMasterSelected : {}),
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedResource('material', material.material_id, assignment.process_id, assignment.parallel_index);
                      setSelectedMasterId(material.material_id);
                    }}
                  >
                    {idx === 0 && (
                      <>
                        <td style={styles.td} rowSpan={usage.length} onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(material.material_id)}
                            onChange={() => handleToggleSelect(material.material_id)}
                            style={styles.checkbox}
                          />
                        </td>
                        <td style={styles.td} rowSpan={usage.length}>
                          <strong>{material.material_id}</strong>
                        </td>
                        <td style={styles.td} rowSpan={usage.length}>
                          {isMasterSelected ? (
                            <input
                              type="text"
                              style={styles.editInput}
                              value={material.name}
                              onChange={(e) => updateMaterial(material.material_id, { name: e.target.value })}
                              onClick={(e) => e.stopPropagation()}
                            />
                          ) : material.name}
                        </td>
                        <td style={styles.td} rowSpan={usage.length}>
                          {isMasterSelected ? (
                            <input
                              type="text"
                              style={styles.editInput}
                              value={material.unit}
                              onChange={(e) => updateMaterial(material.material_id, { unit: e.target.value })}
                              onClick={(e) => e.stopPropagation()}
                            />
                          ) : (
                            <span style={styles.unit}>{material.unit}</span>
                          )}
                        </td>
                      </>
                    )}
                    <td style={styles.td}>
                      {isSelected ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <input
                            type="number"
                            style={{ ...styles.editInput, width: '60px' }}
                            value={assignment.quantity || 0}
                            onChange={(e) => {
                              const val = parseFloat(e.target.value);
                              if (!isNaN(val) && val >= 0) {
                                updateResourceQuantity(assignment.process_id, assignment.parallel_index, 'material', material.material_id, val);
                              }
                            }}
                            onClick={(e) => e.stopPropagation()}
                            step="0.1"
                            min="0"
                          />
                          <span style={styles.unit}>{material.unit}</span>
                        </div>
                      ) : (
                        <span style={styles.quantity}>{assignment.quantity} {material.unit}</span>
                      )}
                    </td>
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
    backgroundColor: '#fff3e0',
    borderLeft: '3px solid #ff9800',
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
  unit: {
    color: '#666',
    fontSize: '12px',
    fontWeight: '500',
  },
  quantity: {
    fontSize: '12px',
    color: '#666',
  },
  processChip: {
    display: 'inline-block',
    padding: '2px 8px',
    backgroundColor: '#fff3e0',
    color: '#e65100',
    fontSize: '11px',
    borderRadius: '8px',
    fontWeight: '500',
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

export default MaterialsTable;
