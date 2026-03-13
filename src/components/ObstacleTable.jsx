import { useEffect, useRef, useState } from 'react';
import useBopStore from '../store/bopStore';
import useTranslation from '../i18n/useTranslation';

function ObstacleTable() {
  const {
    bopData,
    selectedObstacleId,
    setSelectedObstacle,
    addObstacle,
    updateObstacle,
    deleteObstacle,
    obstacleCreationMode,
    setObstacleCreationMode,
    pendingObstacleType,
    setPendingObstacleType
  } = useBopStore();
  const { t } = useTranslation();
  const selectedRowRef = useRef(null);
  const [selectedIds, setSelectedIds] = useState([]);

  const obstacleTypes = [
    { id: 'fence', label: t('obs.fence'), icon: '🚧', color: '#ff9800' },
    { id: 'zone', label: t('obs.zone'), icon: '⚠️', color: '#f44336' },
    { id: 'pillar', label: t('obs.pillar'), icon: '🏛️', color: '#795548' },
    { id: 'wall', label: t('obs.wall'), icon: '🧱', color: '#607d8b' },
  ];

  // Auto-scroll to selected row
  useEffect(() => {
    if (selectedRowRef.current && selectedObstacleId) {
      selectedRowRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  }, [selectedObstacleId]);

  const handleAddObstacle = () => {
    addObstacle();
  };

  const handleDeleteObstacle = () => {
    if (!selectedObstacleId) return;
    if (window.confirm(t('obs.confirmDelete'))) {
      deleteObstacle(selectedObstacleId);
    }
  };

  const handleDeleteSelected = () => {
    if (selectedIds.length === 0) return;
    if (window.confirm(t('obs.confirmDeleteMulti', { count: selectedIds.length }))) {
      selectedIds.forEach(id => deleteObstacle(id));
      setSelectedIds([]);
    }
  };

  const handleToggleSelect = (obstacleId) => {
    setSelectedIds(prev =>
      prev.includes(obstacleId)
        ? prev.filter(id => id !== obstacleId)
        : [...prev, obstacleId]
    );
  };

  const handleToggleSelectAll = () => {
    const obstacles = bopData?.obstacles || [];
    if (selectedIds.length === obstacles.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(obstacles.map(o => o.obstacle_id));
    }
  };

  const handleToggleCreationMode = () => {
    setObstacleCreationMode(!obstacleCreationMode);
  };

  const obstacles = bopData?.obstacles || [];

  if (obstacles.length === 0 && !obstacleCreationMode) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>{t('obs.title')}</h2>
          <div style={styles.count}>{t('obs.total', { count: 0 })}</div>
        </div>
        {/* Type Selection Bar */}
        <div style={styles.typeSelectionBar}>
          <span style={styles.typeSelectionLabel}>{t('obs.typeSelect')}</span>
          <div style={styles.typeButtonGroup}>
            {obstacleTypes.map((type) => (
              <button
                key={type.id}
                style={{
                  ...styles.typeButton,
                  ...(pendingObstacleType === type.id ? {
                    ...styles.typeButtonActive,
                    borderColor: type.color,
                    backgroundColor: `${type.color}20`,
                  } : {}),
                }}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setPendingObstacleType(type.id)}
              >
                <span style={styles.typeButtonIcon}>{type.icon}</span>
                <span>{type.label}</span>
              </button>
            ))}
          </div>
        </div>
        <div style={styles.actionBar}>
          <button style={styles.actionButton} onClick={handleAddObstacle}>
            {obstacleTypes.find(tp => tp.id === pendingObstacleType)?.label
              ? t('obs.add', { type: obstacleTypes.find(tp => tp.id === pendingObstacleType).label })
              : t('obs.addDefault')}
          </button>
          <button
            style={{
              ...styles.actionButtonSecondary,
              ...(obstacleCreationMode ? styles.actionButtonActive : {})
            }}
            onClick={handleToggleCreationMode}
          >
            {obstacleCreationMode ? t('obs.exitCreation') : t('obs.createIn3D')}
          </button>
        </div>
        <div style={styles.emptyState}>
          <p>{t('obs.noData')}</p>
          <p style={{ fontSize: '12px', color: '#999', whiteSpace: 'pre-line' }}>
            {t('obs.createGuide')}
          </p>
        </div>
      </div>
    );
  }

  const getObstacleTypeLabel = (type) => {
    switch (type) {
      case 'fence': return t('obs.fence');
      case 'zone': return t('obs.zone');
      case 'pillar': return t('obs.pillar');
      case 'wall': return t('obs.wall');
      default: return type;
    }
  };

  const getObstacleTypeColor = (type) => {
    switch (type) {
      case 'fence': return '#ff9800';
      case 'zone': return '#f44336';
      case 'pillar': return '#795548';
      case 'wall': return '#607d8b';
      default: return '#888';
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>{t('obs.title')}</h2>
        <div style={styles.count}>{t('obs.total', { count: obstacles.length })}</div>
      </div>

      {/* Type Selection Bar */}
      <div style={styles.typeSelectionBar}>
        <span style={styles.typeSelectionLabel}>{t('obs.typeSelect')}</span>
        <div style={styles.typeButtonGroup}>
          {obstacleTypes.map((type) => (
            <button
              key={type.id}
              style={{
                ...styles.typeButton,
                ...(pendingObstacleType === type.id ? {
                  ...styles.typeButtonActive,
                  borderColor: type.color,
                  backgroundColor: `${type.color}20`,
                } : {}),
              }}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => setPendingObstacleType(type.id)}
            >
              <span style={styles.typeButtonIcon}>{type.icon}</span>
              <span>{type.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Action Bar */}
      <div style={styles.actionBar}>
        <button style={styles.actionButton} onClick={handleAddObstacle}>
          {obstacleTypes.find(tp => tp.id === pendingObstacleType)?.label
            ? t('obs.add', { type: obstacleTypes.find(tp => tp.id === pendingObstacleType).label })
            : t('obs.addDefault')}
        </button>
        <button
          style={{
            ...styles.actionButtonSecondary,
            ...(obstacleCreationMode ? styles.actionButtonActive : {})
          }}
          onClick={handleToggleCreationMode}
        >
          {obstacleCreationMode ? t('obs.exitCreation') : t('obs.createIn3D')}
        </button>
        <button
          style={{
            ...styles.actionButtonDanger,
            ...(selectedIds.length === 0 ? styles.actionButtonDisabled : {})
          }}
          disabled={selectedIds.length === 0}
          onClick={handleDeleteSelected}
        >
          {t('obs.deleteSelected', { count: selectedIds.length })}
        </button>
      </div>

      {/* Creation Mode Notice */}
      {obstacleCreationMode && (
        <div style={styles.creationModeNotice}>
          <strong>{obstacleTypes.find(tp => tp.id === pendingObstacleType)?.icon} {obstacleTypes.find(tp => tp.id === pendingObstacleType)?.label}</strong> {t('obs.creationNotice')}
        </div>
      )}

      {/* Table */}
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={{ ...styles.th, width: '40px' }}>
                <input
                  type="checkbox"
                  checked={obstacles.length > 0 && selectedIds.length === obstacles.length}
                  onChange={handleToggleSelectAll}
                  style={styles.checkbox}
                />
              </th>
              <th style={{ ...styles.th, width: '80px' }}>ID</th>
              <th style={{ ...styles.th, minWidth: '120px' }}>{t('obs.obstName')}</th>
              <th style={{ ...styles.th, width: '70px' }}>{t('obs.obstType')}</th>
              <th style={{ ...styles.th, width: '100px' }}>{t('common.location')}</th>
              <th style={{ ...styles.th, width: '140px' }}>{t('common.sizeWHD')}</th>
              <th style={{ ...styles.th, width: '70px' }}>{t('common.rotation')}</th>
            </tr>
          </thead>
          <tbody>
            {obstacles.map((obstacle) => {
              const isSelected = selectedObstacleId === obstacle.obstacle_id;
              const pos = obstacle.position || { x: 0, y: 0, z: 0 };
              const size = obstacle.size || { width: 1, height: 1, depth: 1 };
              const rotationY = obstacle.rotation_y || 0;

              return (
                <tr
                  key={obstacle.obstacle_id}
                  ref={isSelected ? selectedRowRef : null}
                  style={{
                    ...styles.row,
                    ...(isSelected ? styles.rowSelected : {}),
                  }}
                  onClick={() => setSelectedObstacle(obstacle.obstacle_id)}
                >
                  <td style={styles.td} onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(obstacle.obstacle_id)}
                      onChange={() => handleToggleSelect(obstacle.obstacle_id)}
                      style={styles.checkbox}
                    />
                  </td>
                  <td style={styles.td}>
                    <strong>{obstacle.obstacle_id}</strong>
                  </td>
                  <td style={styles.td}>
                    {isSelected ? (
                      <input
                        type="text"
                        style={styles.editInput}
                        value={obstacle.name}
                        onChange={(e) => updateObstacle(obstacle.obstacle_id, { name: e.target.value })}
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : obstacle.name}
                  </td>
                  <td style={styles.td}>
                    {isSelected ? (
                      <select
                        style={styles.editSelect}
                        value={obstacle.type}
                        onChange={(e) => updateObstacle(obstacle.obstacle_id, { type: e.target.value })}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <option value="fence">{t('obs.fence')}</option>
                        <option value="zone">{t('obs.zone')}</option>
                        <option value="pillar">{t('obs.pillar')}</option>
                        <option value="wall">{t('obs.wall')}</option>
                      </select>
                    ) : (
                      <span style={{ ...styles.typeBadge, backgroundColor: getObstacleTypeColor(obstacle.type) }}>
                        {getObstacleTypeLabel(obstacle.type)}
                      </span>
                    )}
                  </td>
                  <td style={styles.td}>
                    <div style={styles.locationCell}>
                      ({pos.x.toFixed(1)}, {pos.z.toFixed(1)})
                    </div>
                  </td>
                  <td style={styles.td}>
                    {isSelected ? (
                      <div style={styles.sizeInputGroup}>
                        <input
                          type="number"
                          style={styles.sizeInput}
                          value={size.width}
                          step="0.1"
                          min="0.1"
                          onChange={(e) => updateObstacle(obstacle.obstacle_id, {
                            size: { ...size, width: parseFloat(e.target.value) || 0.1 }
                          })}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <input
                          type="number"
                          style={styles.sizeInput}
                          value={size.height}
                          step="0.1"
                          min="0.1"
                          onChange={(e) => updateObstacle(obstacle.obstacle_id, {
                            size: { ...size, height: parseFloat(e.target.value) || 0.1 }
                          })}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <input
                          type="number"
                          style={styles.sizeInput}
                          value={size.depth}
                          step="0.1"
                          min="0.1"
                          onChange={(e) => updateObstacle(obstacle.obstacle_id, {
                            size: { ...size, depth: parseFloat(e.target.value) || 0.1 }
                          })}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                    ) : (
                      <div style={styles.locationCell}>
                        ({size.width.toFixed(1)}, {size.height.toFixed(1)}, {size.depth.toFixed(1)})
                      </div>
                    )}
                  </td>
                  <td style={styles.td}>
                    <div style={styles.locationCell}>
                      {(rotationY * 180 / Math.PI).toFixed(1)}°
                    </div>
                  </td>
                </tr>
              );
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
    gap: '8px',
    textAlign: 'center',
    lineHeight: '1.6',
  },
  typeSelectionBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 20px',
    borderBottom: '1px solid #eee',
    backgroundColor: '#fafafa',
  },
  typeSelectionLabel: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#555',
  },
  typeButtonGroup: {
    display: 'flex',
    gap: '8px',
  },
  typeButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    border: '2px solid #ddd',
    borderColor: '#ddd',
    borderRadius: '8px',
    backgroundColor: 'white',
    fontSize: '12px',
    fontWeight: '500',
    color: '#555',
    cursor: 'pointer',
    transition: 'all 0.2s',
    outline: 'none',
    boxShadow: 'none',
    WebkitTapHighlightColor: 'transparent',
  },
  typeButtonActive: {
    fontWeight: '700',
    color: '#333',
  },
  typeButtonIcon: {
    fontSize: '14px',
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
    color: '#ff9800',
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
    backgroundColor: '#ff9800',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  actionButtonSecondary: {
    padding: '6px 14px',
    backgroundColor: '#607d8b',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  actionButtonActive: {
    backgroundColor: '#4caf50',
    boxShadow: '0 0 8px rgba(76, 175, 80, 0.5)',
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
  creationModeNotice: {
    padding: '12px 20px',
    backgroundColor: '#e8f5e9',
    color: '#2e7d32',
    fontSize: '13px',
    fontWeight: '500',
    borderBottom: '1px solid #c8e6c9',
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
  td: {
    padding: '8px 6px',
    verticalAlign: 'middle',
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
    border: '1px solid #ff9800',
    borderRadius: '3px',
    boxSizing: 'border-box',
    backgroundColor: '#fff3e0',
  },
  editSelect: {
    width: '100%',
    padding: '4px 6px',
    fontSize: '11px',
    border: '1px solid #ff9800',
    borderRadius: '3px',
    backgroundColor: '#fff3e0',
    cursor: 'pointer',
  },
  sizeInputGroup: {
    display: 'flex',
    gap: '4px',
  },
  sizeInput: {
    width: '40px',
    padding: '2px 4px',
    fontSize: '11px',
    border: '1px solid #ff9800',
    borderRadius: '3px',
    backgroundColor: '#fff3e0',
    fontFamily: 'monospace',
  },
  typeBadge: {
    display: 'inline-block',
    padding: '4px 10px',
    color: 'white',
    fontSize: '11px',
    borderRadius: '12px',
    fontWeight: 'bold',
  },
  checkbox: {
    cursor: 'pointer',
    width: '16px',
    height: '16px',
  },
};

export default ObstacleTable;
