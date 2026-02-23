import { useState } from 'react';
import useBopStore from '../store/bopStore';
import { api } from '../services/api';

function ExportButtons() {
  const [error, setError] = useState('');
  const { bopData, exportBopData } = useBopStore();

  const handleExportExcel = () => {
    if (!bopData || !bopData.processes || bopData.processes.length === 0) {
      setError('먼저 BOP를 생성해주세요');
      return;
    }
    setError('');
    try {
      api.exportExcel(exportBopData());
    } catch (err) {
      setError(err.message);
    }
  };

  const handleExport3D = () => {
    if (!bopData || !bopData.processes || bopData.processes.length === 0) {
      setError('먼저 BOP를 생성해주세요');
      return;
    }
    setError('');
    try {
      api.export3D(exportBopData());
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>내보내기</h2>
      {error && <div style={styles.error}>{error}</div>}
      <div style={styles.buttonGroup}>
        <button
          style={styles.button}
          onClick={handleExportExcel}
          disabled={loading}
        >
          Excel 내보내기
        </button>
        <button
          style={{ ...styles.button, ...styles.buttonSecondary }}
          onClick={handleExport3D}
          disabled={loading}
        >
          3D JSON 내보내기
        </button>
      </div>
    </div>
  );
}

const styles = {
  container: {
    padding: '20px',
    backgroundColor: '#f5f5f5',
    borderRadius: '8px',
  },
  title: {
    margin: '0 0 15px 0',
    fontSize: '18px',
    fontWeight: 'bold',
  },
  buttonGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  button: {
    padding: '10px',
    backgroundColor: '#4a90e2',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  buttonSecondary: {
    backgroundColor: '#888',
  },
  error: {
    color: '#ff6b6b',
    fontSize: '14px',
    marginBottom: '10px',
  },
};

export default ExportButtons;
