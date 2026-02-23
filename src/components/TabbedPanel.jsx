import BopTable from './BopTable';
import EquipmentsTable from './EquipmentsTable';
import WorkersTable from './WorkersTable';
import MaterialsTable from './MaterialsTable';
import ObstacleTable from './ObstacleTable';
import ScenariosPanel from './ScenariosPanel';
import ToolsPanel from './ToolsPanel';
import useBopStore from '../store/bopStore';
import useTranslation from '../i18n/useTranslation';

function TabbedPanel() {
  const { activeTab, setActiveTab } = useBopStore();
  const { t } = useTranslation();

  const tabs = [
    { id: 'bop', label: 'BOP', icon: '📋' },
    { id: 'equipments', label: t('tab.equipment'), icon: '🤖' },
    { id: 'workers', label: t('tab.workers'), icon: '👷' },
    { id: 'materials', label: t('tab.materials'), icon: '📦' },
    { id: 'obstacles', label: t('tab.obstacles'), icon: '🚧' },
    { id: 'tools', label: t('tab.tools'), icon: '🔧' },
    { id: 'scenarios', label: t('tab.scenarios'), icon: '📁' },
  ];

  return (
    <div style={styles.container}>
      {/* Tab Buttons */}
      <div style={styles.tabBar}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            style={{
              ...styles.tabButton,
              ...(activeTab === tab.id ? styles.tabButtonActive : {}),
            }}
            onClick={() => setActiveTab(tab.id)}
          >
            <span style={styles.tabIcon}>{tab.icon}</span>
            <span style={styles.tabLabel}>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content - 모든 탭을 렌더링하되 비활성 탭은 숨김 (상태 유지) */}
      <div style={styles.tabContent}>
        <div style={{ display: activeTab === 'bop' ? 'block' : 'none', height: '100%' }}>
          <BopTable />
        </div>
        <div style={{ display: activeTab === 'equipments' ? 'block' : 'none', height: '100%' }}>
          <EquipmentsTable />
        </div>
        <div style={{ display: activeTab === 'workers' ? 'block' : 'none', height: '100%' }}>
          <WorkersTable />
        </div>
        <div style={{ display: activeTab === 'materials' ? 'block' : 'none', height: '100%' }}>
          <MaterialsTable />
        </div>
        <div style={{ display: activeTab === 'obstacles' ? 'block' : 'none', height: '100%' }}>
          <ObstacleTable />
        </div>
        <div style={{ display: activeTab === 'tools' ? 'block' : 'none', height: '100%' }}>
          <ToolsPanel />
        </div>
        <div style={{ display: activeTab === 'scenarios' ? 'block' : 'none', height: '100%' }}>
          <ScenariosPanel />
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
  tabBar: {
    display: 'flex',
    borderBottom: '2px solid #ddd',
    backgroundColor: '#fafafa',
  },
  tabButton: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '12px 16px',
    border: 'none',
    backgroundColor: 'transparent',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    color: '#666',
    transition: 'all 0.2s',
    borderBottom: '3px solid transparent',
  },
  tabButtonActive: {
    color: '#4a90e2',
    backgroundColor: 'white',
    borderBottom: '3px solid #4a90e2',
  },
  tabIcon: {
    fontSize: '16px',
  },
  tabLabel: {
    fontSize: '13px',
    fontWeight: '600',
  },
  tabContent: {
    flex: 1,
    overflow: 'hidden',
  },
};

export default TabbedPanel;
