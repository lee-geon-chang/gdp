import * as XLSX from 'xlsx';
import { getResourceSize } from '../components/Viewer3D';

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  /**
   * 통합 채팅 API 호출 (생성/수정/QA 통합)
   * @param {string} message - 사용자 메시지
   * @param {Object|null} currentBop - 현재 BOP 데이터 (collapsed 형식)
   * @param {Array} messages - 대화 히스토리 배열 (currently unused)
   * @param {string|null} model - LLM 모델 (null이면 기본 모델 사용)
   * @returns {Promise<Object>} { message: string, bop_data: Object|null }
   */
  async unifiedChat(message, currentBop = null, messages = [], model = null, language = null) {
    const body = { message, current_bop: currentBop };
    if (model) body.model = model;
    if (language) body.language = language;

    const res = await fetch('/api/chat/unified', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      console.error('[API Error] Status:', res.status, 'Detail:', err);
      const errorMsg = typeof err.detail === 'string'
        ? err.detail
        : JSON.stringify(err.detail || err) || `채팅 실패 (${res.status})`;
      throw new Error(errorMsg);
    }

    return res.json();
  },

  /**
   * Excel 내보내기 (클라이언트 측 생성)
   * @param {Object} bopData - BOP 데이터 (collapsed 형식)
   */
  exportExcel(bopData) {
    const wb = XLSX.utils.book_new();

    // Sheet 1: Project Info
    const projectRows = [
      { 'Item': 'Project Name', 'Value': bopData.project_title || '' },
      { 'Item': 'Target UPH', 'Value': bopData.target_uph || '' },
      { 'Item': 'Process Count', 'Value': (bopData.processes || []).length },
      { 'Item': 'Equipment Count', 'Value': (bopData.equipments || []).length },
      { 'Item': 'Worker Count', 'Value': (bopData.workers || []).length },
      { 'Item': 'Material Count', 'Value': (bopData.materials || []).length },
      { 'Item': 'Obstacle Count', 'Value': (bopData.obstacles || []).length },
    ];
    const wsProject = XLSX.utils.json_to_sheet(projectRows);
    wsProject['!cols'] = [{ wch: 18 }, { wch: 30 }];
    XLSX.utils.book_append_sheet(wb, wsProject, 'Project Info');

    // Sheet 2: Processes (routing only)
    const processRows = (bopData.processes || []).map(p => {
      const details = (bopData.process_details || []).filter(d => d.process_id === p.process_id);
      const parallelCount = details.length || 1;
      const cts = details.map(d => d.cycle_time_sec || 0);
      const invSum = cts.reduce((sum, ct) => sum + (ct > 0 ? 1 / ct : 0), 0);
      const effectiveCT = invSum > 0 ? +(1 / invSum).toFixed(1) : 0;

      return {
        'Process ID': p.process_id,
        'Parallel Count': parallelCount,
        'Cycle Time (sec)': cts[0] ?? 0,
        'Effective Cycle Time (sec)': effectiveCT,
        'Predecessors': (p.predecessor_ids || []).join(', '),
        'Successors': (p.successor_ids || []).join(', '),
      };
    });
    const wsProcesses = XLSX.utils.json_to_sheet(processRows.length ? processRows : [{}]);
    XLSX.utils.book_append_sheet(wb, wsProcesses, 'Processes');

    // Sheet 3: Process Details (directly from process_details)
    const detailRows = (bopData.process_details || []).map(d => {
      const lineResources = (bopData.resource_assignments || []).filter(
        r => r.process_id === d.process_id && r.parallel_index === d.parallel_index
      );
      let sizeX = 0, sizeY = 0, sizeZ = 0;
      if (lineResources.length > 0) {
        let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
        let maxH = 0;
        lineResources.forEach(r => {
          const x = r.relative_location?.x ?? 0;
          const z = r.relative_location?.z ?? 0;
          const cs = r.computed_size || { width: 0.4, height: 0.4, depth: 0.4 };
          minX = Math.min(minX, x - cs.width / 2);
          maxX = Math.max(maxX, x + cs.width / 2);
          minZ = Math.min(minZ, z - cs.depth / 2);
          maxZ = Math.max(maxZ, z + cs.depth / 2);
          maxH = Math.max(maxH, cs.height || 0);
        });
        sizeX = +(maxX - minX).toFixed(2);
        sizeY = +maxH.toFixed(2);
        sizeZ = +(maxZ - minZ).toFixed(2);
      }

      return {
        'Process ID': d.process_id,
        'Parallel Index': d.parallel_index,
        'Name': d.name,
        'Description': d.description ?? '',
        'Cycle Time (sec)': d.cycle_time_sec,
        'Location X': d.location?.x ?? 0,
        'Location Y': d.location?.y ?? 0,
        'Location Z': d.location?.z ?? 0,
        'Size X': sizeX,
        'Size Y': sizeY,
        'Size Z': sizeZ,
        'Rotation Y': d.rotation_y ?? 0,
      };
    });
    const wsDetail = XLSX.utils.json_to_sheet(detailRows.length ? detailRows : [{}]);
    XLSX.utils.book_append_sheet(wb, wsDetail, 'Process Details');

    // Sheet 4: Resource Assignments (directly from resource_assignments)
    const equipmentTypeMap = {};
    (bopData.equipments || []).forEach(e => { equipmentTypeMap[e.equipment_id] = e.type; });

    const resourceRows = (bopData.resource_assignments || []).map(r => {
      const cs = r.computed_size
        || getResourceSize(r.resource_type, r.resource_type === 'equipment' ? equipmentTypeMap[r.resource_id] : null);

      return {
        'Process ID': r.process_id,
        'Parallel Index': r.parallel_index,
        'Resource Type': r.resource_type,
        'Resource ID': r.resource_id,
        'Quantity': r.quantity ?? 1,
        'Offset X': r.relative_location?.x ?? 0,
        'Offset Y': r.relative_location?.y ?? 0,
        'Offset Z': r.relative_location?.z ?? 0,
        'Size X': cs.width,
        'Size Y': cs.height,
        'Size Z': cs.depth,
        'Scale X': r.scale?.x ?? 1,
        'Scale Y': r.scale?.y ?? 1,
        'Scale Z': r.scale?.z ?? 1,
        'Rotation Y': r.rotation_y ?? 0,
      };
    });
    const wsResources = XLSX.utils.json_to_sheet(resourceRows.length ? resourceRows : [{}]);
    XLSX.utils.book_append_sheet(wb, wsResources, 'Resource Assignments');

    // Sheet 5: Equipment
    const eqRows = (bopData.equipments || []).map(e => ({
      'Equipment ID': e.equipment_id,
      'Name': e.name,
      'Type': e.type,
    }));
    const wsEquip = XLSX.utils.json_to_sheet(eqRows.length ? eqRows : [{}]);
    XLSX.utils.book_append_sheet(wb, wsEquip, 'Equipment');

    // Sheet 6: Workers
    const wkRows = (bopData.workers || []).map(w => ({
      'Worker ID': w.worker_id,
      'Name': w.name,
      'Skill Level': w.skill_level || '',
    }));
    const wsWorkers = XLSX.utils.json_to_sheet(wkRows.length ? wkRows : [{}]);
    XLSX.utils.book_append_sheet(wb, wsWorkers, 'Workers');

    // Sheet 7: Materials
    const mtRows = (bopData.materials || []).map(m => ({
      'Material ID': m.material_id,
      'Name': m.name,
      'Unit': m.unit,
    }));
    const wsMaterials = XLSX.utils.json_to_sheet(mtRows.length ? mtRows : [{}]);
    XLSX.utils.book_append_sheet(wb, wsMaterials, 'Materials');

    // Sheet 8: Obstacles
    const obsRows = (bopData.obstacles || []).map(o => ({
      'Obstacle ID': o.obstacle_id,
      'Name': o.name || '',
      'Type': o.type || '',
      'Location X': o.position?.x ?? 0,
      'Location Y': o.position?.y ?? 0,
      'Location Z': o.position?.z ?? 0,
      'Size X': o.size?.width ?? 0,
      'Size Y': o.size?.height ?? 0,
      'Size Z': o.size?.depth ?? 0,
      'Rotation Y': o.rotation_y ?? 0,
    }));
    const wsObstacles = XLSX.utils.json_to_sheet(obsRows.length ? obsRows : [{}]);
    XLSX.utils.book_append_sheet(wb, wsObstacles, 'Obstacles');

    const buf = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([buf], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const dateStr = new Date().toISOString().split('T')[0];
    downloadBlob(blob, `${bopData.project_title || 'BOP'}_${dateStr}.xlsx`);
  },

  /**
   * 3D JSON 내보내기 (클라이언트 측 생성)
   * @param {Object} bopData - BOP 데이터 (collapsed 형식)
   */
  export3D(bopData) {
    const json = JSON.stringify(bopData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    downloadBlob(blob, `${bopData.project_title || 'BOP'}_3d.json`);
  },

  // === Tool Management API (FastAPI backend) ===

  async analyzeScript(sourceCode, fileName, sampleInput = null, inputSchemaOverride = null, outputSchemaOverride = null) {
    const body = { source_code: sourceCode, file_name: fileName };
    if (sampleInput) body.sample_input = sampleInput;
    if (inputSchemaOverride) body.input_schema_override = inputSchemaOverride;
    if (outputSchemaOverride) body.output_schema_override = outputSchemaOverride;

    const res = await fetch('/api/tools/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `분석 실패 (${res.status})`);
    }
    return res.json();
  },

  async registerTool(toolData) {
    const res = await fetch('/api/tools/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toolData),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `등록 실패 (${res.status})`);
    }
    return res.json();
  },

  async registerSchemaOnly(schemaData) {
    const res = await fetch('/api/tools/register-schema-only', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(schemaData),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `스키마 등록 실패 (${res.status})`);
    }
    return res.json();
  },

  async updateToolScript(toolId, fileName, sourceCode) {
    const res = await fetch(`/api/tools/${toolId}/script`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_name: fileName, source_code: sourceCode }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `스크립트 업데이트 실패 (${res.status})`);
    }
    return res.json();
  },

  async listTools() {
    const res = await fetch('/api/tools/');
    if (!res.ok) throw new Error(`도구 목록 조회 실패 (${res.status})`);
    return res.json();
  },

  async getToolDetail(toolId) {
    const res = await fetch(`/api/tools/${toolId}`);
    if (!res.ok) throw new Error(`도구 상세 조회 실패 (${res.status})`);
    return res.json();
  },

  async deleteTool(toolId) {
    const res = await fetch(`/api/tools/${toolId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`삭제 실패 (${res.status})`);
    return res.json();
  },

  async executeTool(toolId, bopData, params = null) {
    const body = { tool_id: toolId, bop_data: bopData };
    if (params) body.params = params;
    const res = await fetch('/api/tools/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      // HTTP 오류 시에도 백엔드가 제공한 상세 정보 보존
      const error = new Error(data.detail || `실행 실패 (${res.status})`);
      // 백엔드 응답에 오류 정보가 있으면 에러 객체에 추가
      if (data.stdout) error.stdout = data.stdout;
      if (data.stderr) error.stderr = data.stderr;
      if (data.tool_output) error.tool_output = data.tool_output;
      throw error;
    }
    return data;
  },

  async generateSchema(description, model = null) {
    const body = { description };
    if (model) body.model = model;
    const res = await fetch('/api/tools/generate-schema', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `스키마 생성 실패 (${res.status})`);
    }
    return res.json();
  },

  async improveSchema(toolName, description, inputSchema, outputSchema, params, userFeedback, model = null) {
    const body = {
      tool_name: toolName,
      description: description,
      current_input_schema: inputSchema,
      current_output_schema: outputSchema,
      current_params: params,
      user_feedback: userFeedback,
    };
    if (model) body.model = model;
    const res = await fetch('/api/tools/improve-schema', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `스키마 개선 실패 (${res.status})`);
    }
    return res.json();
  },

  async generateScript(description, inputSchema = null, outputSchema = null, model = null) {
    const body = { description };
    if (inputSchema) body.input_schema = inputSchema;
    if (outputSchema) body.output_schema = outputSchema;
    if (model) body.model = model;
    const res = await fetch('/api/tools/generate-script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `스크립트 생성 실패 (${res.status})`);
    }
    return res.json();
  },

  async improveTool(toolId, { userFeedback, executionContext, modifyAdapter, modifyParams, modifyScript }) {
    const res = await fetch(`/api/tools/${toolId}/improve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_feedback: userFeedback,
        execution_context: executionContext,
        modify_adapter: modifyAdapter,
        modify_params: modifyParams,
        modify_script: modifyScript,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `개선 실패 (${res.status})`);
    }
    return res.json();
  },

  async applyImprovement(toolId, { preProcessCode, postProcessCode, paramsSchema, scriptCode, createNewVersion }) {
    const res = await fetch(`/api/tools/${toolId}/apply-improvement`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pre_process_code: preProcessCode,
        post_process_code: postProcessCode,
        params_schema: paramsSchema,
        script_code: scriptCode,
        create_new_version: createNewVersion,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `적용 실패 (${res.status})`);
    }
    return res.json();
  },
};
