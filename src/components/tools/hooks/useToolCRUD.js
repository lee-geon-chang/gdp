import { useState, useEffect } from 'react';
import { api } from '../../../services/api';

/**
 * 도구 CRUD(Create, Read, Update, Delete) 관리 훅
 */
export function useToolCRUD() {
  const [tools, setTools] = useState([]);
  const [listLoading, setListLoading] = useState(false);
  const [selectedToolIds, setSelectedToolIds] = useState([]);
  const [error, setError] = useState('');

  // 도구 목록 로드
  const loadTools = async () => {
    setListLoading(true);
    try {
      const list = await api.listTools();
      setTools(list);
      setSelectedToolIds([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setListLoading(false);
    }
  };

  // 도구 삭제
  const deleteTool = async (toolId) => {
    try {
      await api.deleteTool(toolId);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  };

  // 다중 삭제
  const deleteSelectedTools = async (toolIds) => {
    if (toolIds.length === 0) return false;
    try {
      setListLoading(true);
      await Promise.all(toolIds.map(id => api.deleteTool(id)));
      setSelectedToolIds([]);
      await loadTools();
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setListLoading(false);
    }
  };

  // 체크박스 토글
  const toggleToolSelection = (toolId) => {
    setSelectedToolIds(prev =>
      prev.includes(toolId)
        ? prev.filter(id => id !== toolId)
        : [...prev, toolId]
    );
  };

  // 전체 선택/해제
  const toggleSelectAll = () => {
    if (selectedToolIds.length === tools.length) {
      setSelectedToolIds([]);
    } else {
      setSelectedToolIds(tools.map(t => t.tool_id));
    }
  };

  return {
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
  };
}
