import { useState } from 'react';
import useBopStore from '../store/bopStore';
import { api } from '../services/api';
import useTranslation from '../i18n/useTranslation';

function BopTable() {
  const {
    bopData,
    selectedProcessKey,
    setSelectedProcess,
    clearSelection,
    getEquipmentById,
    getWorkerById,
    getMaterialById,
    addProcess,
    updateProcess,
    deleteProcess,
    addParallelLine,
    removeParallelLine,
    addResourceToProcess,
    removeResourceFromProcess,
    linkProcesses,
    unlinkProcesses,
    updateProjectSettings
  } = useBopStore();
  const { t } = useTranslation();

  const [editingSettings, setEditingSettings] = useState(false);
  const [editProjectTitle, setEditProjectTitle] = useState('');
  const [editTargetUph, setEditTargetUph] = useState('');

  // Parse selection key: "P001:1" → { processId, parallelIndex }
  const parseSelectedKey = (key) => {
    if (!key) return null;
    const parts = key.split(':');
    return { processId: parts[0], parallelIndex: parseInt(parts[1], 10) || 1 };
  };

  const selectedInfo = parseSelectedKey(selectedProcessKey);

  if (!bopData) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <p>{t('bop.noData')}</p>
          <p style={styles.hint}>{t('bop.createHint')}</p>
        </div>
      </div>
    );
  }

  // Handle settings edit
  const handleEditSettings = () => {
    setEditProjectTitle(bopData.project_title || '');
    setEditTargetUph(String(bopData.target_uph || 60));
    setEditingSettings(true);
  };

  const handleSaveSettings = () => {
    updateProjectSettings({
      project_title: editProjectTitle,
      target_uph: editTargetUph
    });
    setEditingSettings(false);
  };

  const handleCancelSettings = () => {
    setEditingSettings(false);
  };

  if (!bopData.processes || bopData.processes.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
            <h2 style={styles.title}>{bopData.project_title}</h2>
            <div style={styles.uph}>{t('bop.target')}: {bopData.target_uph} UPH</div>
            <button
              style={styles.settingsButton}
              onClick={handleEditSettings}
              title={t('bop.editSettings')}
            >
              ⚙️
            </button>
          </div>
        </div>
        <div style={styles.emptyState}>
          <p>{t('bop.noProcess')}</p>
          <button
            style={styles.actionButton}
            onClick={() => addProcess()}
          >
            {t('bop.addProcess')}
          </button>
        </div>

        {editingSettings && (
          <div style={styles.modalOverlay} onClick={handleCancelSettings}>
            <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
              <h3 style={styles.modalTitle}>{t('bop.projectSettings')}</h3>
              <div style={styles.formGroup}>
                <label style={styles.label}>{t('bop.projectName')}</label>
                <input
                  type="text"
                  value={editProjectTitle}
                  onChange={(e) => setEditProjectTitle(e.target.value)}
                  style={styles.input}
                  placeholder={t('bop.projectNamePlaceholder')}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>{t('bop.targetUph')}</label>
                <input
                  type="number"
                  value={editTargetUph}
                  onChange={(e) => setEditTargetUph(e.target.value)}
                  style={styles.input}
                  min="1"
                  placeholder={t('bop.targetUphPlaceholder')}
                />
              </div>
              <div style={styles.modalActions}>
                <button style={styles.modalButtonCancel} onClick={handleCancelSettings}>
                  {t('bop.cancel')}
                </button>
                <button style={styles.modalButtonSave} onClick={handleSaveSettings}>
                  {t('bop.save')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Helper: get resources for a process instance from resource_assignments
  const getResourcesByType = (processId, parallelIndex) => {
    const equipments = [];
    const workers = [];
    const materials = [];

    const assignments = (bopData.resource_assignments || []).filter(
      r => r.process_id === processId && r.parallel_index === parallelIndex
    );

    assignments.forEach(resource => {
      if (resource.resource_type === 'equipment') {
        const eq = getEquipmentById(resource.resource_id);
        if (eq) equipments.push({ ...eq, quantity: resource.quantity });
      } else if (resource.resource_type === 'worker') {
        const worker = getWorkerById(resource.resource_id);
        if (worker) workers.push({ ...worker, quantity: resource.quantity });
      } else if (resource.resource_type === 'material') {
        const material = getMaterialById(resource.resource_id);
        if (material) materials.push({ ...material, quantity: resource.quantity });
      }
    });

    return { equipments, workers, materials };
  };

  // Calculate process bounding box size from resource_assignments
  const getProcessBBox = (processId, parallelIndex) => {
    const resources = (bopData.resource_assignments || []).filter(
      r => r.process_id === processId && r.parallel_index === parallelIndex
    );
    if (resources.length === 0) return null;

    let minX = Infinity, maxX = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;

    resources.forEach((resource) => {
      const relLoc = resource.relative_location || { x: 0, y: 0, z: 0 };
      const x = relLoc.x;
      const z = relLoc.z;
      const size = resource.computed_size || { width: 0.4, height: 0.4, depth: 0.4 };

      minX = Math.min(minX, x - size.width / 2);
      maxX = Math.max(maxX, x + size.width / 2);
      minZ = Math.min(minZ, z - size.depth / 2);
      maxZ = Math.max(maxZ, z + size.depth / 2);
    });

    return {
      width: +(maxX - minX).toFixed(1),
      depth: +(maxZ - minZ).toFixed(1)
    };
  };

  const formatResources = (resources, formatter) => {
    if (!resources || resources.length === 0) return '-';
    return resources.map(formatter).join(', ');
  };

  const renderResourceCell = (processId, parallelIndex, isSelected, resourceType, assignedResources, allResources, idField) => {
    if (!isSelected) {
      return (
        <div style={styles.resourcesCell}>
          {formatResources(assignedResources, r =>
            resourceType === 'material'
              ? `${r.name} (${r.quantity}${r.unit})`
              : r.name
          )}
        </div>
      );
    }

    const assignedIds = new Set(assignedResources.map(r => r[idField]));
    const available = (allResources || []).filter(r => !assignedIds.has(r[idField]));

    return (
      <div>
        {assignedResources.map(resource => (
          <div key={resource[idField]} style={styles.resourceTag}>
            <span>{resource.name}</span>
            <button
              style={styles.resourceTagRemove}
              onClick={(e) => {
                e.stopPropagation();
                removeResourceFromProcess(processId, parallelIndex, resourceType, resource[idField]);
              }}
            >
              ×
            </button>
          </div>
        ))}
        {available.length > 0 && (
          <select
            style={styles.resourceSelect}
            value=""
            onChange={(e) => {
              if (e.target.value) {
                addResourceToProcess(processId, parallelIndex, { resource_type: resourceType, resource_id: e.target.value });
              }
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <option value="">{t('bop.add')}</option>
            {available.map(r => (
              <option key={r[idField]} value={r[idField]}>{r.name}</option>
            ))}
          </select>
        )}
      </div>
    );
  };

  // Render predecessor/successor link cell
  const renderLinkCell = (routingProcess, isSelected, direction) => {
    const processId = routingProcess.process_id;
    const linkIds = direction === 'predecessor'
      ? (routingProcess.predecessor_ids || [])
      : (routingProcess.successor_ids || []);

    // Resolve link IDs to process detail names
    const linkedProcesses = linkIds.map(id => {
      const details = (bopData.process_details || []).filter(d => d.process_id === id);
      const name = details.length > 0 ? details[0].name : id;
      return { id, name };
    });

    if (!isSelected) {
      return (
        <div style={styles.resourcesCell}>
          {linkedProcesses.length === 0 ? '-' : linkedProcesses.map(p => p.name).join(', ')}
        </div>
      );
    }

    // All processes excluding self
    const available = bopData.processes.filter(p =>
      p.process_id !== processId && !linkIds.includes(p.process_id)
    );
    const availableWithNames = available.map(p => {
      const details = (bopData.process_details || []).filter(d => d.process_id === p.process_id);
      return { process_id: p.process_id, name: details.length > 0 ? details[0].name : p.process_id };
    });

    return (
      <div>
        {linkedProcesses.map(lp => (
          <div key={lp.id} style={styles.resourceTag}>
            <span>{lp.name}</span>
            <button
              style={styles.resourceTagRemove}
              onClick={(e) => {
                e.stopPropagation();
                if (direction === 'predecessor') {
                  unlinkProcesses(lp.id, processId);
                } else {
                  unlinkProcesses(processId, lp.id);
                }
              }}
            >
              ×
            </button>
          </div>
        ))}
        {availableWithNames.length > 0 && (
          <select
            style={styles.resourceSelect}
            value=""
            onChange={(e) => {
              if (e.target.value) {
                if (direction === 'predecessor') {
                  linkProcesses(e.target.value, processId);
                } else {
                  linkProcesses(processId, e.target.value);
                }
              }
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <option value="">{t('bop.add')}</option>
            {availableWithNames.map(p => (
              <option key={p.process_id} value={p.process_id}>{p.name}</option>
            ))}
          </select>
        )}
      </div>
    );
  };

  // Calculate bottleneck based on effective cycle time using process_details
  const getBottleneck = () => {
    let maxEffectiveTime = 0;
    let bottleneckInfo = null;

    bopData.processes.forEach(routing => {
      const details = (bopData.process_details || []).filter(d => d.process_id === routing.process_id);
      if (details.length === 0) return;

      const childCTs = details.map(d => d.cycle_time_sec || 0);
      const parallelCount = details.length;

      // Effective CT using harmonic mean: 1 / Σ(1/CT_i)
      const invSum = childCTs.reduce((sum, ct) => sum + (ct > 0 ? 1 / ct : 0), 0);
      const effectiveCT = invSum > 0 ? 1 / invSum : 0;
      const maxChildCT = Math.max(...childCTs);

      if (effectiveCT > maxEffectiveTime) {
        maxEffectiveTime = effectiveCT;
        bottleneckInfo = {
          processId: routing.process_id,
          name: details[0].name,
          effectiveCT,
          parallelCount,
          baseCT: maxChildCT
        };
      }
    });

    return {
      processId: bottleneckInfo?.processId || null,
      name: bottleneckInfo?.name || null,
      effectiveTime: maxEffectiveTime,
      parallelCount: bottleneckInfo?.parallelCount || 1,
      baseCT: bottleneckInfo?.baseCT || 0
    };
  };

  const bottleneck = getBottleneck();
  const expectedUPH = bottleneck.effectiveTime > 0 ? 3600 / bottleneck.effectiveTime : 0;

  // Group processes: each routing entry → its process_details
  const processGroups = bopData.processes.map(routing => {
    const details = (bopData.process_details || [])
      .filter(d => d.process_id === routing.process_id)
      .sort((a, b) => a.parallel_index - b.parallel_index);
    return { routing, details };
  }).filter(g => g.details.length > 0);

  // Check if selected parallel line can be removed
  const canRemoveParallel = selectedInfo != null && (() => {
    const details = (bopData.process_details || []).filter(d => d.process_id === selectedInfo.processId);
    return details.length > 1;
  })();

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
          <h2 style={styles.title}>{bopData.project_title}</h2>
          <div style={styles.uph}>{t('bop.target')}: {bopData.target_uph} UPH</div>
          <button
            style={styles.settingsButton}
            onClick={handleEditSettings}
            title={t('bop.editSettings')}
          >
            ⚙️
          </button>
        </div>
      </div>

      {/* Settings Edit Modal */}
      {editingSettings && (
        <div style={styles.modalOverlay} onClick={handleCancelSettings}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <h3 style={styles.modalTitle}>{t('bop.projectSettings')}</h3>
            <div style={styles.formGroup}>
              <label style={styles.label}>{t('bop.projectName')}</label>
              <input
                type="text"
                value={editProjectTitle}
                onChange={(e) => setEditProjectTitle(e.target.value)}
                style={styles.input}
                placeholder={t('bop.projectNamePlaceholder')}
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>{t('bop.targetUph')}</label>
              <input
                type="number"
                value={editTargetUph}
                onChange={(e) => setEditTargetUph(e.target.value)}
                style={styles.input}
                min="1"
                placeholder={t('bop.targetUphPlaceholder')}
              />
            </div>
            <div style={styles.modalActions}>
              <button style={styles.modalButtonCancel} onClick={handleCancelSettings}>
                {t('bop.cancel')}
              </button>
              <button style={styles.modalButtonSave} onClick={handleSaveSettings}>
                {t('bop.save')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action Bar */}
      <div style={styles.actionBar}>
        <button
          style={styles.actionButton}
          onClick={() => addProcess()}
        >
          {t('bop.addProcess')}
        </button>
        <button
          style={{
            ...styles.actionButton,
            ...(selectedInfo ? {} : styles.actionButtonDisabled)
          }}
          disabled={!selectedInfo}
          onClick={() => addProcess({ afterProcessId: selectedInfo?.processId })}
        >
          {t('bop.addAfter')}
        </button>
        <button
          style={{
            ...styles.actionButtonDanger,
            ...(selectedInfo ? {} : styles.actionButtonDisabled)
          }}
          disabled={!selectedInfo}
          onClick={() => {
            if (window.confirm(t('bop.confirmDeleteProcess'))) {
              deleteProcess(selectedInfo?.processId);
            }
          }}
        >
          {t('bop.deleteProcess')}
        </button>
        <button
          style={{
            ...styles.actionButton,
            ...(selectedInfo ? {} : styles.actionButtonDisabled)
          }}
          disabled={!selectedInfo}
          onClick={() => addParallelLine(selectedInfo?.processId)}
        >
          {t('bop.addParallel')}
        </button>
        <button
          style={{
            ...styles.actionButtonDanger,
            ...((selectedInfo && canRemoveParallel) ? {} : styles.actionButtonDisabled)
          }}
          disabled={!selectedInfo || !canRemoveParallel}
          onClick={() => {
            if (window.confirm(t('bop.confirmDeleteParallel'))) {
              removeParallelLine(selectedInfo?.processId, selectedInfo?.parallelIndex);
            }
          }}
        >
          {t('bop.deleteParallel')}
        </button>
      </div>

      {/* Table */}
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={{ ...styles.th, width: '80px' }}>ID</th>
              <th style={{ ...styles.th, minWidth: '150px' }}>{t('bop.colName')}</th>
              <th style={{ ...styles.th, minWidth: '100px' }}>{t('bop.colCycleTime')}</th>
              <th style={{ ...styles.th, minWidth: '80px' }}>{t('bop.colParallel')}</th>
              <th style={{ ...styles.th, minWidth: '150px' }}>{t('bop.colEquipments')}</th>
              <th style={{ ...styles.th, minWidth: '120px' }}>{t('bop.colWorkers')}</th>
              <th style={{ ...styles.th, minWidth: '200px' }}>{t('bop.colMaterials')}</th>
              <th style={{ ...styles.th, minWidth: '120px' }}>{t('bop.predecessor')}</th>
              <th style={{ ...styles.th, minWidth: '120px' }}>{t('bop.successor')}</th>
              <th style={{ ...styles.th, minWidth: '120px' }}>{t('bop.location')}</th>
              <th style={{ ...styles.th, minWidth: '80px' }}>{t('bop.size')}</th>
              <th style={{ ...styles.th, width: '80px' }}>{t('bop.rotation')}</th>
            </tr>
          </thead>
          <tbody>
            {processGroups.map((group) => {
              const rows = [];
              const isParallelGroup = group.details.length > 1;
              const isBottleneck = bottleneck.processId === group.routing.process_id;

              group.details.forEach((detail, detailIdx) => {
                const isFirstDetail = detailIdx === 0;
                const rowKey = `${detail.process_id}:${detail.parallel_index}`;
                const isThisRowSelected = selectedProcessKey === rowKey;

                const { equipments, workers, materials } = getResourcesByType(detail.process_id, detail.parallel_index);

                rows.push(
                  <tr
                    key={rowKey}
                    style={{
                      ...styles.processRow,
                      ...(isThisRowSelected ? styles.processRowSelected : {}),
                      ...(isBottleneck ? styles.bottleneckRow : {}),
                      ...(isFirstDetail ? {} : styles.parallelRow)
                    }}
                    onClick={() => setSelectedProcess(rowKey)}
                  >
                    {/* ID */}
                    <td style={styles.td}>
                      {isFirstDetail ? (
                        <strong>{detail.process_id}</strong>
                      ) : (
                        <span style={styles.parallelLabel}>{detail.process_id}</span>
                      )}
                    </td>

                    {/* Name */}
                    <td style={styles.td}>
                      {isThisRowSelected ? (
                        <>
                          <div style={styles.processName}>
                            <input
                              type="text"
                              style={{ ...styles.editInput, ...styles.editInputName }}
                              value={detail.name}
                              onChange={(e) => updateProcess(detail.process_id, detail.parallel_index, { name: e.target.value })}
                              onClick={(e) => e.stopPropagation()}
                            />
                            {isFirstDetail && isParallelGroup && (
                              <span style={styles.parallelBadge}>
                                {group.details.length}x
                              </span>
                            )}
                          </div>
                          <input
                            type="text"
                            style={styles.editInput}
                            value={detail.description || ''}
                            onChange={(e) => updateProcess(detail.process_id, detail.parallel_index, { description: e.target.value })}
                            onClick={(e) => e.stopPropagation()}
                            placeholder={t('bop.description')}
                          />
                        </>
                      ) : isFirstDetail ? (
                        <>
                          <div style={styles.processName}>
                            <strong>{detail.name}</strong>
                            {isParallelGroup && (
                              <span style={styles.parallelBadge}>
                                {group.details.length}x
                              </span>
                            )}
                            {isBottleneck && (
                              <span
                                style={styles.bottleneckBadge}
                                title={`Effective CT: ${bottleneck.effectiveTime.toFixed(1)}s`}
                              >
                                Bottleneck ({bottleneck.effectiveTime.toFixed(1)}s)
                              </span>
                            )}
                          </div>
                          <div style={styles.processDescription}>{detail.description}</div>
                        </>
                      ) : (
                        <>
                          <div style={styles.processName}>
                            <span style={styles.parallelLineText}>└ #{detail.parallel_index}</span>
                            {detail.name !== group.details[0]?.name && (
                              <span style={{ fontSize: '12px', color: '#666' }}> - {detail.name}</span>
                            )}
                          </div>
                          {detail.description && (
                            <div style={styles.processDescription}>{detail.description}</div>
                          )}
                        </>
                      )}
                    </td>

                    {/* Cycle Time */}
                    <td style={styles.td}>
                      {isThisRowSelected ? (
                        <input
                          type="text"
                          style={styles.editInput}
                          value={detail.cycle_time_sec ?? ''}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value);
                            if (!isNaN(val)) {
                              updateProcess(detail.process_id, detail.parallel_index, { cycle_time_sec: val });
                            }
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <div style={styles.cycleTimeInfo}>
                          <div><strong>{detail.cycle_time_sec?.toFixed(1) || 0}s</strong></div>
                          {isFirstDetail && isParallelGroup && (() => {
                            const childCTs = group.details.map(d => d.cycle_time_sec || 0);
                            const invSum = childCTs.reduce((sum, ct) => sum + (ct > 0 ? 1 / ct : 0), 0);
                            const effectiveCT = invSum > 0 ? 1 / invSum : 0;
                            const allSame = childCTs.every(ct => ct === childCTs[0]);
                            const detailText = allSame
                              ? `(${childCTs[0].toFixed(0)}s ÷ ${group.details.length} ${t('bop.lines')} = ${(childCTs[0] / group.details.length).toFixed(1)}s)`
                              : `(${t('bop.throughput')}: ${childCTs.map(ct => ct.toFixed(0)).join('s, ')}s)`;

                            return (
                              <div style={styles.effectiveTime}>
                                → Effective CT: {effectiveCT.toFixed(1)}s
                                <span style={{ fontSize: '9px', color: '#999', marginLeft: '4px' }}>
                                  {detailText}
                                </span>
                              </div>
                            );
                          })()}
                        </div>
                      )}
                    </td>

                    {/* Parallel */}
                    <td style={styles.td}>
                      <span style={styles.parallelCount}>#{detail.parallel_index}</span>
                    </td>

                    {/* Equipments */}
                    <td style={styles.td}>
                      {renderResourceCell(detail.process_id, detail.parallel_index, isThisRowSelected, 'equipment', equipments, bopData.equipments, 'equipment_id')}
                    </td>

                    {/* Workers */}
                    <td style={styles.td}>
                      {renderResourceCell(detail.process_id, detail.parallel_index, isThisRowSelected, 'worker', workers, bopData.workers, 'worker_id')}
                    </td>

                    {/* Materials */}
                    <td style={styles.td}>
                      {renderResourceCell(detail.process_id, detail.parallel_index, isThisRowSelected, 'material', materials, bopData.materials, 'material_id')}
                    </td>

                    {/* Predecessors */}
                    <td style={styles.td}>
                      {isFirstDetail
                        ? renderLinkCell(group.routing, isThisRowSelected, 'predecessor')
                        : <div style={styles.resourcesCell}>-</div>
                      }
                    </td>

                    {/* Successors */}
                    <td style={styles.td}>
                      {isFirstDetail
                        ? renderLinkCell(group.routing, isThisRowSelected, 'successor')
                        : <div style={styles.resourcesCell}>-</div>
                      }
                    </td>

                    {/* Location */}
                    <td style={styles.td}>
                      <div style={styles.locationCell}>
                        ({(detail.location?.x || 0).toFixed(1)}, {(detail.location?.z || 0).toFixed(1)})
                      </div>
                    </td>

                    {/* Size */}
                    <td style={styles.td}>
                      {(() => {
                        const bbox = getProcessBBox(detail.process_id, detail.parallel_index);
                        return bbox ? (
                          <div style={styles.locationCell}>
                            ({bbox.width.toFixed(1)}, {bbox.depth.toFixed(1)})
                          </div>
                        ) : <div style={styles.locationCell}>-</div>;
                      })()}
                    </td>

                    {/* Rotation */}
                    <td style={styles.td}>
                      <div style={styles.locationCell}>
                        {((detail.rotation_y || 0) * 180 / Math.PI).toFixed(1)}°
                      </div>
                    </td>
                  </tr>
                );
              });

              return rows;
            })}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      <div style={styles.summary}>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>{t('bop.summaryInstances')}</span>
          <span style={styles.summaryValue}>
            {(bopData.process_details || []).length}
          </span>
        </div>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>{t('bop.summaryEquipments')}</span>
          <span style={styles.summaryValue}>{bopData.equipments?.length || 0}</span>
        </div>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>{t('bop.summaryWorkers')}</span>
          <span style={styles.summaryValue}>{bopData.workers?.length || 0}</span>
        </div>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>{t('bop.summaryMaterials')}</span>
          <span style={styles.summaryValue}>{bopData.materials?.length || 0}</span>
        </div>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>{t('bop.summaryBottleneck')}</span>
          <span style={styles.summaryValue}>
            {bottleneck.processId ? (
              <>
                {bottleneck.effectiveTime.toFixed(1)}s
                {bottleneck.parallelCount > 1 && (
                  <span style={styles.summaryDetail}>
                    {' '}({bottleneck.parallelCount} {t('bop.lines')})
                  </span>
                )}
              </>
            ) : '-'}
          </span>
        </div>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>{t('bop.expectedUph')}</span>
          <span style={styles.summaryValue}>
            {expectedUPH > 0 ? (
              <>
                {Math.round(expectedUPH)}
                <span style={styles.summaryDetail}>
                  {' '}({t('bop.target')}: {bopData.target_uph})
                </span>
              </>
            ) : '-'}
          </span>
        </div>
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
  },
  hint: {
    fontSize: '12px',
    marginTop: '10px',
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
  editInput: {
    width: '100%',
    padding: '4px 6px',
    fontSize: '11px',
    border: '1px solid #ddd',
    borderRadius: '3px',
    fontFamily: 'monospace',
    boxSizing: 'border-box',
    marginBottom: '2px',
  },
  editInputName: {
    minWidth: '140px',
    fontFamily: 'inherit',
    fontWeight: 'bold',
    fontSize: '12px',
  },
  header: {
    padding: '20px',
    borderBottom: '2px solid #ddd',
    backgroundColor: '#f9f9f9',
  },
  title: {
    margin: '0 0 8px 0',
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#333',
  },
  uph: {
    fontSize: '14px',
    color: '#4a90e2',
    fontWeight: 'bold',
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
  processRow: {
    backgroundColor: '#f8f8f8',
    borderBottom: '1px solid #ddd',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  processRowSelected: {
    backgroundColor: '#e3f2fd',
    borderLeft: '4px solid #4a90e2',
  },
  bottleneckRow: {
    backgroundColor: '#fff3e0',
  },
  parallelRow: {
    backgroundColor: '#fafafa',
  },
  td: {
    padding: '10px 8px',
    verticalAlign: 'top',
  },
  processName: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
    marginBottom: '4px',
  },
  processDescription: {
    fontSize: '11px',
    color: '#666',
    fontStyle: 'italic',
  },
  parallelBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    backgroundColor: '#4a90e2',
    color: 'white',
    fontSize: '10px',
    borderRadius: '10px',
    fontWeight: 'bold',
  },
  bottleneckBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    backgroundColor: '#ff9800',
    color: 'white',
    fontSize: '10px',
    borderRadius: '10px',
    fontWeight: 'bold',
  },
  cycleTimeInfo: {
    fontSize: '12px',
  },
  effectiveTime: {
    color: '#4a90e2',
    marginTop: '2px',
    fontSize: '11px',
  },
  parallelCount: {
    display: 'inline-block',
    padding: '4px 8px',
    backgroundColor: '#e8f4f8',
    borderRadius: '4px',
    fontWeight: 'bold',
    color: '#4a90e2',
  },
  parallelLabel: {
    color: '#999',
    fontSize: '11px',
    fontFamily: 'monospace',
  },
  parallelLineText: {
    color: '#999',
    fontSize: '11px',
    fontStyle: 'italic',
  },
  resourcesCell: {
    fontSize: '12px',
    color: '#555',
  },
  resourceTag: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '4px',
    padding: '2px 6px',
    marginBottom: '2px',
    backgroundColor: '#e8f4f8',
    borderRadius: '3px',
    fontSize: '11px',
  },
  resourceTagRemove: {
    background: 'none',
    border: 'none',
    color: '#e74c3c',
    cursor: 'pointer',
    fontWeight: 'bold',
    fontSize: '13px',
    padding: '0 2px',
    lineHeight: 1,
  },
  resourceSelect: {
    width: '100%',
    padding: '3px 4px',
    fontSize: '11px',
    border: '1px solid #ddd',
    borderRadius: '3px',
    backgroundColor: 'white',
    cursor: 'pointer',
    marginTop: '2px',
  },
  locationCell: {
    fontSize: '11px',
    color: '#666',
    fontFamily: 'monospace',
  },
  summary: {
    display: 'flex',
    gap: '20px',
    padding: '15px 20px',
    borderTop: '2px solid #ddd',
    backgroundColor: '#f9f9f9',
    flexWrap: 'wrap',
  },
  summaryItem: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: '12px',
    color: '#666',
  },
  summaryValue: {
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#333',
  },
  summaryDetail: {
    fontSize: '12px',
    fontWeight: 'normal',
    color: '#888',
  },
  settingsButton: {
    backgroundColor: 'transparent',
    border: '1px solid #ddd',
    borderRadius: '4px',
    padding: '4px 8px',
    cursor: 'pointer',
    fontSize: '16px',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '24px',
    minWidth: '400px',
    maxWidth: '500px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
  },
  modalTitle: {
    margin: '0 0 20px 0',
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#333',
  },
  formGroup: {
    marginBottom: '16px',
  },
  label: {
    display: 'block',
    marginBottom: '6px',
    fontSize: '13px',
    fontWeight: 'bold',
    color: '#555',
  },
  input: {
    width: '100%',
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    boxSizing: 'border-box',
  },
  modalActions: {
    display: 'flex',
    gap: '10px',
    justifyContent: 'flex-end',
    marginTop: '24px',
  },
  modalButtonCancel: {
    padding: '8px 16px',
    backgroundColor: '#999',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  modalButtonSave: {
    padding: '8px 16px',
    backgroundColor: '#4a90e2',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
};

export default BopTable;
