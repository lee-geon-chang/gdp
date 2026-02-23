import { useState, useEffect } from 'react';
import { useToolCRUD } from './tools/hooks/useToolCRUD';
import ToolListView from './tools/ToolListView';
import ToolUploadView from './tools/ToolUploadView';
import ToolGenerateView from './tools/ToolGenerateView';
import ToolDetailView from './tools/ToolDetailView';

function ToolsPanel() {
  const [view, setView] = useState('main'); // 'main' | 'upload' | 'generate' | 'detail'
  const [selectedTool, setSelectedTool] = useState(null);

  const {
    tools,
    listLoading,
    selectedToolIds,
    error,
    setError,
    loadTools,
    deleteTool,
    deleteSelectedTools,
    toggleToolSelection,
    toggleSelectAll,
  } = useToolCRUD();

  // 컴포넌트 마운트 및 view 변경 시 도구 목록 로드
  useEffect(() => {
    if (view === 'main') {
      loadTools();
    }
  }, [view]);

  // View 네비게이션
  const handleNavigate = (targetView) => {
    setView(targetView);
    setError('');
  };

  // 도구 클릭 (상세 페이지로 이동)
  const handleToolClick = (tool) => {
    setSelectedTool(tool);
    setView('detail');
  };

  // 다중 삭제
  const handleDeleteSelected = async () => {
    const success = await deleteSelectedTools(selectedToolIds);
    if (success) {
      await loadTools();
    }
  };

  // 단일 삭제
  const handleDeleteTool = async (toolId) => {
    const success = await deleteTool(toolId);
    if (success) {
      await loadTools();
      return true;
    }
    return false;
  };

  // 업로드 완료
  const handleUploadComplete = () => {
    setView('main');
  };

  // AI 생성 완료
  const handleGenerateComplete = () => {
    setView('main');
  };

  return (
    <div style={styles.container}>
      {/* Main View - 도구 목록 */}
      {view === 'main' && (
        <ToolListView
          tools={tools}
          listLoading={listLoading}
          selectedToolIds={selectedToolIds}
          error={error}
          onToolClick={handleToolClick}
          onToggleSelection={toggleToolSelection}
          onToggleSelectAll={toggleSelectAll}
          onDeleteSelected={handleDeleteSelected}
          onNavigate={handleNavigate}
        />
      )}

      {/* Upload View - 파일 업로드 */}
      {view === 'upload' && (
        <ToolUploadView
          onNavigate={handleNavigate}
          onUploadComplete={handleUploadComplete}
        />
      )}

      {/* Generate View - AI 생성 (2단계) */}
      {view === 'generate' && (
        <ToolGenerateView
          onNavigate={handleNavigate}
          onGenerateComplete={handleGenerateComplete}
        />
      )}

      {/* Detail View - 도구 상세 + 실행 */}
      {view === 'detail' && selectedTool && (
        <ToolDetailView
          tool={selectedTool}
          onNavigate={handleNavigate}
          onDelete={handleDeleteTool}
        />
      )}
    </div>
  );
}

const styles = {
  container: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#fff',
  },
};

export default ToolsPanel;
