import { create } from 'zustand';

// ===================================================================
// Helper: Resource Size (must match Viewer3D.jsx)
// ===================================================================

function getResourceSize(resourceType, equipmentType) {
  if (resourceType === 'equipment') {
    switch (equipmentType) {
      case 'robot':
        return { width: 1.4, height: 1.7, depth: 0.6 };
      case 'machine':
        return { width: 2.1, height: 1.9, depth: 1.0 };
      case 'manual_station':
        return { width: 1.6, height: 1.0, depth: 0.8 };
      default:
        return { width: 0.4, height: 0.4, depth: 0.4 };
    }
  } else if (resourceType === 'worker') {
    return { width: 0.5, height: 1.7, depth: 0.3 };
  } else if (resourceType === 'material') {
    return { width: 0.4, height: 0.25, depth: 0.4 };
  }
  return { width: 0.4, height: 0.4, depth: 0.4 };
}

function computeResourceSize(resource, equipments) {
  if (resource.resource_type === 'equipment') {
    const eq = (equipments || []).find(e => e.equipment_id === resource.resource_id);
    return getResourceSize('equipment', eq?.type);
  }
  return getResourceSize(resource.resource_type);
}

// Ensure all resource_assignments have computed_size
function ensureComputedSizes(bopData) {
  if (!bopData) return bopData;

  // 1) resource_assignments에 computed_size 보장
  const equipments = bopData.equipments || [];
  const updatedAssignments = (bopData.resource_assignments || []).map(ra => {
    if (ra.computed_size) return ra;
    return { ...ra, computed_size: computeResourceSize(ra, equipments) };
  });

  // 2) process_details에 computed_size (바운딩박스) 보장
  const updatedDetails = (bopData.process_details || []).map(pd => {
    const resources = updatedAssignments.filter(
      r => r.process_id === pd.process_id && (r.parallel_index || 1) === (pd.parallel_index || 1)
    );
    if (resources.length === 0) {
      return { ...pd, computed_size: { width: 0.5, height: 0.5, depth: 0.5 } };
    }
    let minX = Infinity, maxX = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    let maxHeight = 0;
    resources.forEach((r, idx) => {
      const relLoc = r.relative_location || { x: 0, y: 0, z: 0 };
      let x = relLoc.x, z = relLoc.z;
      // auto-layout 폴백 (Viewer3D와 동일)
      if (x === 0 && z === 0 && resources.length > 1) {
        const step = 0.9;
        z = idx * step - (resources.length - 1) * step / 2;
      }
      const size = r.computed_size || { width: 0.4, height: 0.4, depth: 0.4 };
      const scale = r.scale || { x: 1, y: 1, z: 1 };
      const aw = size.width * (scale.x || 1);
      const ad = size.depth * (scale.z || 1);
      const ah = size.height * (scale.y || 1);
      minX = Math.min(minX, x - aw / 2);
      maxX = Math.max(maxX, x + aw / 2);
      minZ = Math.min(minZ, z - ad / 2);
      maxZ = Math.max(maxZ, z + ad / 2);
      maxHeight = Math.max(maxHeight, ah);
    });
    return {
      ...pd,
      computed_size: {
        width: Math.round((maxX - minX) * 100) / 100,
        height: Math.round(maxHeight * 100) / 100,
        depth: Math.round((maxZ - minZ) * 100) / 100,
      }
    };
  });

  return { ...bopData, resource_assignments: updatedAssignments, process_details: updatedDetails };
}

// ===================================================================
// Helper: Effective Position (auto-layout fallback)
// ===================================================================

function getEffectivePosition(resource, resourceIndex, totalResources) {
  const relLoc = resource.relative_location || { x: 0, y: 0, z: 0 };

  if (relLoc.x !== 0 || relLoc.z !== 0) {
    return { x: relLoc.x, z: relLoc.z };
  }

  // Auto-layout: Z-axis vertical layout (fixed spacing)
  const step = 0.9;
  const z = resourceIndex * step - (totalResources - 1) * step / 2;

  return { x: 0, z: z };
}

// ===================================================================
// Helper: Bounding Box & Normalize
// ===================================================================

// Calculate bounding box center for a set of resources
function calculateBoundingBoxCenter(resources, equipments) {
  if (!resources || resources.length === 0) {
    return { centerX: 0, centerZ: 0 };
  }

  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;

  resources.forEach((resource, resourceIndex) => {
    const pos = getEffectivePosition(resource, resourceIndex, resources.length);
    const x = pos.x;
    const z = pos.z;
    const resourceRotation = resource.rotation_y || 0;
    const scale = resource.scale || { x: 1, y: 1, z: 1 };

    let equipmentType = null;
    if (resource.resource_type === 'equipment' && equipments) {
      const equipmentData = equipments.find(e => e.equipment_id === resource.resource_id);
      equipmentType = equipmentData?.type;
    }

    const baseSize = resource.computed_size || getResourceSize(resource.resource_type, equipmentType);
    const actualWidth = baseSize.width * scale.x;
    const actualDepth = baseSize.depth * scale.z;

    const halfWidth = actualWidth / 2;
    const halfDepth = actualDepth / 2;
    const corners = [
      { x: -halfWidth, z: -halfDepth },
      { x: halfWidth, z: -halfDepth },
      { x: halfWidth, z: halfDepth },
      { x: -halfWidth, z: halfDepth }
    ];

    corners.forEach(corner => {
      const rotatedX = corner.x * Math.cos(resourceRotation) + corner.z * Math.sin(resourceRotation);
      const rotatedZ = -corner.x * Math.sin(resourceRotation) + corner.z * Math.cos(resourceRotation);

      const finalX = x + rotatedX;
      const finalZ = z + rotatedZ;

      minX = Math.min(minX, finalX);
      maxX = Math.max(maxX, finalX);
      minZ = Math.min(minZ, finalZ);
      maxZ = Math.max(maxZ, finalZ);
    });
  });

  return { centerX: (minX + maxX) / 2, centerZ: (minZ + maxZ) / 2 };
}

// Normalize process center: adjust detail.location and resource relative_locations
// so that boundingBox.center is always (0, 0)
function normalizeProcessCenter(bopData, processId, parallelIndex) {
  const detail = (bopData.process_details || []).find(
    d => d.process_id === processId && d.parallel_index === parallelIndex
  );
  if (!detail) return bopData;

  const resources = (bopData.resource_assignments || []).filter(
    r => r.process_id === processId && r.parallel_index === parallelIndex
  );

  const { centerX, centerZ } = calculateBoundingBoxCenter(resources, bopData.equipments);

  if (Math.abs(centerX) < 0.001 && Math.abs(centerZ) < 0.001) {
    return bopData;
  }

  const processRotation = detail.rotation_y || 0;
  const rotatedOffsetX = centerX * Math.cos(processRotation) + centerZ * Math.sin(processRotation);
  const rotatedOffsetZ = -centerX * Math.sin(processRotation) + centerZ * Math.cos(processRotation);

  const newLocation = {
    x: (detail.location?.x || 0) + rotatedOffsetX,
    y: detail.location?.y || 0,
    z: (detail.location?.z || 0) + rotatedOffsetZ
  };

  const updatedDetails = bopData.process_details.map(d => {
    if (d.process_id === processId && d.parallel_index === parallelIndex) {
      return { ...d, location: newLocation };
    }
    return d;
  });

  const updatedAssignments = bopData.resource_assignments.map(r => {
    if (r.process_id === processId && r.parallel_index === parallelIndex) {
      const resourceIdx = resources.indexOf(r);
      const effectivePos = getEffectivePosition(r, resourceIdx, resources.length);
      return {
        ...r,
        relative_location: {
          x: effectivePos.x - centerX,
          y: r.relative_location?.y || 0,
          z: effectivePos.z - centerZ
        }
      };
    }
    return r;
  });

  return { ...bopData, process_details: updatedDetails, resource_assignments: updatedAssignments };
}

// ===================================================================
// ID Generation Helpers
// ===================================================================

function generateNextProcessId(processes) {
  let maxNum = 0;
  processes.forEach(p => {
    const match = p.process_id.match(/^P(\d+)/);
    if (match) maxNum = Math.max(maxNum, parseInt(match[1], 10));
  });
  return `P${String(maxNum + 1).padStart(3, '0')}`;
}

function generateNextEquipmentId(equipments) {
  let maxNum = 0;
  (equipments || []).forEach(e => {
    const match = e.equipment_id.match(/^EQ(\d+)$/);
    if (match) maxNum = Math.max(maxNum, parseInt(match[1], 10));
  });
  return `EQ${String(maxNum + 1).padStart(3, '0')}`;
}

function generateNextWorkerId(workers) {
  let maxNum = 0;
  (workers || []).forEach(w => {
    const match = w.worker_id.match(/^W(\d+)/);
    if (match) maxNum = Math.max(maxNum, parseInt(match[1], 10));
  });
  return `W${String(maxNum + 1).padStart(3, '0')}`;
}

function generateNextMaterialId(materials) {
  let maxNum = 0;
  (materials || []).forEach(m => {
    const match = m.material_id.match(/^M(\d+)$/);
    if (match) maxNum = Math.max(maxNum, parseInt(match[1], 10));
  });
  return `M${String(maxNum + 1).padStart(3, '0')}`;
}

function generateNextObstacleId(obstacles) {
  let maxNum = 0;
  (obstacles || []).forEach(o => {
    const match = o.obstacle_id.match(/^OBS(\d+)/);
    if (match) maxNum = Math.max(maxNum, parseInt(match[1], 10));
  });
  return `OBS${String(maxNum + 1).padStart(3, '0')}`;
}

// Clone resources for a new parallel line:
// - equipment: create new master entry with new ID (1:1)
// - worker: create new master entry with new ID (1:1)
// - material: share same ID (1:N)
// Returns cloned resources WITHOUT process_id/parallel_index (caller sets those)
function cloneResourcesForNewLine(sourceResources, bopData) {
  const newEquipments = [];
  const newWorkers = [];
  let allEquipments = [...(bopData.equipments || [])];
  let allWorkers = [...(bopData.workers || [])];

  const clonedResources = (sourceResources || []).map(r => {
    // Strip process_id and parallel_index - caller will set these
    const { process_id, parallel_index, ...rest } = r;

    if (r.resource_type === 'equipment') {
      const original = allEquipments.find(e => e.equipment_id === r.resource_id);
      const newId = generateNextEquipmentId(allEquipments);
      const idNumber = newId.match(/\d+/)?.[0] || '';
      const defaultName = idNumber ? `장비 ${idNumber}` : `장비 ${newId}`;
      const newEquip = {
        equipment_id: newId,
        name: original ? `${original.name} (복제)` : defaultName,
        type: original ? original.type : 'machine'
      };
      newEquipments.push(newEquip);
      allEquipments.push(newEquip);
      return { ...rest, resource_id: newId };
    }

    if (r.resource_type === 'worker') {
      const original = allWorkers.find(w => w.worker_id === r.resource_id);
      const newId = generateNextWorkerId(allWorkers);
      const idNumber = newId.match(/\d+/)?.[0] || '';
      const defaultName = idNumber ? `작업자 ${idNumber}` : `작업자 ${newId}`;
      const newWorker = {
        worker_id: newId,
        name: original ? `${original.name} (복제)` : defaultName,
        skill_level: original ? original.skill_level : 'Mid'
      };
      newWorkers.push(newWorker);
      allWorkers.push(newWorker);
      return { ...rest, resource_id: newId };
    }

    // material: share same ID
    return { ...rest };
  });

  return { clonedResources, newEquipments, newWorkers };
}

// ===================================================================
// Helper: query functions for new flat structure
// ===================================================================

function getDetailsForProcess(bopData, processId) {
  return (bopData.process_details || []).filter(d => d.process_id === processId);
}

function getResourcesForDetail(bopData, processId, parallelIndex) {
  return (bopData.resource_assignments || []).filter(
    r => r.process_id === processId && r.parallel_index === parallelIndex
  );
}

function getParallelCount(bopData, processId) {
  return getDetailsForProcess(bopData, processId).length;
}

// ===================================================================
// Migration: convert old format (parallel_lines) to new flat format
// ===================================================================

function migrateOldFormat(data) {
  // If data already has process_details, it's new format
  if (data.process_details && data.process_details.length > 0) {
    return data;
  }

  // Check if old format (processes with parallel_lines or nested resources)
  const hasOldFormat = (data.processes || []).some(
    p => p.parallel_lines || p.resources || p.name || p.parallel_count
  );

  if (!hasOldFormat) {
    // Empty or already minimal processes - ensure new fields exist
    return {
      ...data,
      process_details: data.process_details || [],
      resource_assignments: data.resource_assignments || []
    };
  }

  // Migrate old format to new flat format
  const newProcesses = [];
  const newDetails = [];
  const newAssignments = [];
  const additionalEquipments = [];
  const additionalWorkers = [];

  const mutableBopData = {
    equipments: [...(data.equipments || [])],
    workers: [...(data.workers || [])]
  };

  (data.processes || []).forEach(process => {
    // Skip parent/child markers from expanded format
    if (process.is_parent) return;
    if (process.parent_id) return;

    const parallelCount = process.parallel_count || 1;
    const parallelLines = process.parallel_lines || [];

    // Create routing entry (connection info only)
    newProcesses.push({
      process_id: process.process_id,
      predecessor_ids: process.predecessor_ids || [],
      successor_ids: process.successor_ids || []
    });

    // Create detail entries
    for (let i = 0; i < parallelCount; i++) {
      const lineInfo = parallelLines[i] || {};
      const baseLocation = (parallelLines[0] || {}).location || process.location || { x: 0, y: 0, z: 0 };

      newDetails.push({
        process_id: process.process_id,
        parallel_index: i + 1,
        name: lineInfo.name || process.name || process.process_id,
        description: lineInfo.description ?? process.description ?? '',
        cycle_time_sec: lineInfo.cycle_time_sec ?? process.cycle_time_sec ?? 60,
        location: lineInfo.location || {
          x: baseLocation.x,
          y: baseLocation.y || 0,
          z: baseLocation.z + i * 5
        },
        rotation_y: lineInfo.rotation_y ?? process.rotation_y ?? 0
      });

      // Create resource assignments for this parallel index
      const lineResources = (process.resources || []).filter(r => {
        const isUnindexed = r.parallel_line_index === undefined || r.parallel_line_index === null;
        if (r.resource_type === 'material' && isUnindexed) return true;
        if (i === 0) return isUnindexed || r.parallel_line_index === 0;
        return r.parallel_line_index === i;
      });

      // If line i>0 has no eq/workers, clone from line 0
      let resources = lineResources;
      if (i > 0 && !resources.some(r => r.resource_type === 'equipment' || r.resource_type === 'worker')) {
        const line0Res = (process.resources || [])
          .filter(r => {
            const isUnindexed = r.parallel_line_index === undefined || r.parallel_line_index === null;
            return isUnindexed || r.parallel_line_index === 0;
          })
          .filter(r => r.resource_type !== 'material');

        const { clonedResources, newEquipments, newWorkers } =
          cloneResourcesForNewLine(line0Res.map(r => ({ ...r })), mutableBopData);

        const materialCopies = !resources.some(r => r.resource_type === 'material')
          ? (process.resources || [])
              .filter(r => r.resource_type === 'material' && (r.parallel_line_index === undefined || r.parallel_line_index === null || r.parallel_line_index === 0))
              .map(r => ({ ...r }))
          : [];

        resources = [...clonedResources, ...materialCopies, ...resources];
        additionalEquipments.push(...newEquipments);
        additionalWorkers.push(...newWorkers);
        mutableBopData.equipments.push(...newEquipments);
        mutableBopData.workers.push(...newWorkers);
      }

      resources.forEach(r => {
        const { parallel_line_index, ...rest } = r;
        newAssignments.push({
          ...rest,
          process_id: process.process_id,
          parallel_index: i + 1,
          relative_location: rest.relative_location || { x: 0, y: 0, z: 0 },
          rotation_y: rest.rotation_y || 0,
          scale: rest.scale || { x: 1, y: 1, z: 1 }
        });
      });
    }
  });

  return {
    project_title: data.project_title || '새 프로젝트',
    target_uph: data.target_uph || 60,
    processes: newProcesses,
    process_details: newDetails,
    resource_assignments: newAssignments,
    equipments: [...(data.equipments || []), ...additionalEquipments],
    workers: [...(data.workers || []), ...additionalWorkers],
    materials: data.materials || [],
    obstacles: data.obstacles || []
  };
}

// ===================================================================
// Store
// ===================================================================

const useBopStore = create((set) => ({
  // BOP data - flat structure
  bopData: {
    project_title: "새 프로젝트",
    target_uph: 60,
    processes: [],
    process_details: [],
    resource_assignments: [],
    equipments: [],
    workers: [],
    materials: [],
    obstacles: []
  },

  // Flag to track if initial data load has happened
  initialLoadDone: true,

  // Selection state: "processId:parallelIndex" format (e.g., "P001:1")
  selectedProcessKey: null,

  // Resource selection: "type:resourceId:processId:parallelIndex" format
  selectedResourceKey: null,

  // Active tab state
  activeTab: 'bop',

  // Obstacle selection state
  selectedObstacleId: null,

  // Obstacle creation mode (Two-Click)
  obstacleCreationMode: false,
  obstacleCreationFirstClick: null,
  pendingObstacleType: 'fence',

  // 3D Model toggle
  use3DModels: false,

  // Custom 3D models (key: "resource_type:resource_id", value: blob URL)
  customModels: {},

  // Chat messages
  messages: [],

  // LLM Model Selection
  selectedModel: 'gemini-2.5-flash',
  supportedModels: {},

  // Language Selection
  selectedLanguage: 'ko',

  // Actions
  setSelectedModel: (model) => set({ selectedModel: model }),
  setSupportedModels: (models) => set({ supportedModels: models }),
  setSelectedLanguage: (lang) => set({ selectedLanguage: lang }),

  setBopData: (data) => {
    console.log('[STORE] setBopData called');
    // Migrate old format if needed
    const migrated = migrateOldFormat(data);
    // Ensure all resources have computed_size
    const withSizes = ensureComputedSizes(migrated);
    set({ bopData: withSizes });
    console.log('[STORE] bopData updated');
  },

  setInitialLoadDone: (done) => set({ initialLoadDone: done }),

  // Update project settings (project_title, target_uph)
  updateProjectSettings: (fields) => set((state) => {
    if (!state.bopData) return state;

    const updates = {};
    if (fields.project_title !== undefined) {
      updates.project_title = fields.project_title;
    }
    if (fields.target_uph !== undefined) {
      const uph = parseInt(fields.target_uph, 10);
      if (isNaN(uph) || uph <= 0) {
        console.error('[STORE] Invalid target_uph:', fields.target_uph);
        return state;
      }
      updates.target_uph = uph;
    }

    return {
      bopData: { ...state.bopData, ...updates }
    };
  }),

  // Export BOP data (direct - no collapse needed)
  exportBopData: () => {
    const state = useBopStore.getState();
    return state.bopData || null;
  },

  // ===================================================================
  // Selection
  // ===================================================================

  setSelectedProcess: (processKey) => {
    // processKey format: "processId:parallelIndex" (e.g., "P001:1")
    set({ selectedProcessKey: processKey, selectedResourceKey: null, activeTab: 'bop' });
  },

  clearSelection: () => set({ selectedProcessKey: null, selectedResourceKey: null, selectedObstacleId: null }),

  setActiveTab: (tab) => set({ activeTab: tab }),

  setSelectedResource: (resourceType, resourceId, processId, parallelIndex) => {
    // Format: type:resourceId:processId:parallelIndex
    const key = `${resourceType}:${resourceId}:${processId}:${parallelIndex}`;
    const tabMap = {
      'equipment': 'equipments',
      'worker': 'workers',
      'material': 'materials'
    };
    set({
      selectedResourceKey: key,
      selectedProcessKey: null,
      activeTab: tabMap[resourceType] || 'bop'
    });
  },

  clearResourceSelection: () => set({ selectedResourceKey: null }),

  // Helper to get selected process info
  getSelectedProcessInfo: () => {
    const state = useBopStore.getState();
    if (!state.selectedProcessKey) return null;

    const parts = state.selectedProcessKey.split(':');
    if (parts.length < 2) return { processId: state.selectedProcessKey, parallelIndex: 1 };

    return {
      processId: parts[0],
      parallelIndex: parseInt(parts[1], 10) || 1
    };
  },

  // Helper to parse selectedResourceKey
  getSelectedResourceInfo: () => {
    const state = useBopStore.getState();
    if (!state.selectedResourceKey) return null;

    // Format: type:resourceId:processId:parallelIndex
    const parts = state.selectedResourceKey.split(':');
    if (parts.length < 4) return null;

    return {
      resourceType: parts[0],
      resourceId: parts[1],
      processId: parts[2],
      parallelIndex: parseInt(parts[3], 10) || 1
    };
  },

  addMessage: (role, content) => set((state) => ({
    messages: [...state.messages, { role, content, timestamp: new Date() }]
  })),

  clearMessages: () => set({ messages: [] }),

  // ===================================================================
  // Lookup helpers
  // ===================================================================

  getEquipmentById: (equipmentId) => {
    const state = useBopStore.getState();
    if (!state.bopData || !state.bopData.equipments) return null;
    return state.bopData.equipments.find(e => e.equipment_id === equipmentId);
  },

  getWorkerById: (workerId) => {
    const state = useBopStore.getState();
    if (!state.bopData || !state.bopData.workers) return null;
    return state.bopData.workers.find(w => w.worker_id === workerId);
  },

  getMaterialById: (materialId) => {
    const state = useBopStore.getState();
    if (!state.bopData || !state.bopData.materials) return null;
    return state.bopData.materials.find(m => m.material_id === materialId);
  },

  getProcessById: (processId) => {
    const state = useBopStore.getState();
    if (!state.bopData || !state.bopData.processes) return null;
    return state.bopData.processes.find(p => p.process_id === processId);
  },

  // ===================================================================
  // Process Detail Location/Rotation
  // ===================================================================

  updateProcessLocation: (processId, parallelIndex, newLocation) => set((state) => {
    if (!state.bopData) return state;

    const updatedDetails = state.bopData.process_details.map(d => {
      if (d.process_id === processId && d.parallel_index === parallelIndex) {
        return { ...d, location: { ...newLocation } };
      }
      return d;
    });

    return {
      bopData: { ...state.bopData, process_details: updatedDetails }
    };
  }),

  updateProcessRotation: (processId, parallelIndex, rotationY) => set((state) => {
    if (!state.bopData) return state;

    const updatedDetails = state.bopData.process_details.map(d => {
      if (d.process_id === processId && d.parallel_index === parallelIndex) {
        return { ...d, rotation_y: rotationY };
      }
      return d;
    });

    return {
      bopData: { ...state.bopData, process_details: updatedDetails }
    };
  }),

  // ===================================================================
  // Resource Location/Rotation/Scale/Quantity
  // ===================================================================

  updateResourceLocation: (processId, parallelIndex, resourceType, resourceId, newRelativeLocation) => set((state) => {
    if (!state.bopData) return state;

    const updatedAssignments = state.bopData.resource_assignments.map(r => {
      if (r.process_id === processId && r.parallel_index === parallelIndex &&
          r.resource_type === resourceType && r.resource_id === resourceId) {
        return { ...r, relative_location: { ...newRelativeLocation } };
      }
      return r;
    });

    let bopData = { ...state.bopData, resource_assignments: updatedAssignments };
    bopData = normalizeProcessCenter(bopData, processId, parallelIndex);

    return { bopData };
  }),

  updateResourceRotation: (processId, parallelIndex, resourceType, resourceId, rotationY) => set((state) => {
    if (!state.bopData) return state;

    const updatedAssignments = state.bopData.resource_assignments.map(r => {
      if (r.process_id === processId && r.parallel_index === parallelIndex &&
          r.resource_type === resourceType && r.resource_id === resourceId) {
        return { ...r, rotation_y: rotationY };
      }
      return r;
    });

    let bopData = { ...state.bopData, resource_assignments: updatedAssignments };
    bopData = normalizeProcessCenter(bopData, processId, parallelIndex);

    return { bopData };
  }),

  updateResourceScale: (processId, parallelIndex, resourceType, resourceId, scale) => set((state) => {
    if (!state.bopData) return state;

    const updatedAssignments = state.bopData.resource_assignments.map(r => {
      if (r.process_id === processId && r.parallel_index === parallelIndex &&
          r.resource_type === resourceType && r.resource_id === resourceId) {
        return { ...r, scale: { ...scale } };
      }
      return r;
    });

    let bopData = { ...state.bopData, resource_assignments: updatedAssignments };
    bopData = normalizeProcessCenter(bopData, processId, parallelIndex);

    return { bopData };
  }),

  updateResourceQuantity: (processId, parallelIndex, resourceType, resourceId, quantity) => set((state) => {
    if (!state.bopData) return state;

    const updatedAssignments = state.bopData.resource_assignments.map(r => {
      if (r.process_id === processId && r.parallel_index === parallelIndex &&
          r.resource_type === resourceType && r.resource_id === resourceId) {
        return { ...r, quantity };
      }
      return r;
    });

    return {
      bopData: { ...state.bopData, resource_assignments: updatedAssignments }
    };
  }),

  // Normalize all process instances
  normalizeAllProcesses: () => set((state) => {
    if (!state.bopData) return state;
    let bopData = { ...state.bopData };
    for (const detail of (bopData.process_details || [])) {
      bopData = normalizeProcessCenter(bopData, detail.process_id, detail.parallel_index);
    }
    return { bopData };
  }),

  // ===================================================================
  // Process CRUD
  // ===================================================================

  addProcess: (options = {}) => set((state) => {
    if (!state.bopData) return state;

    const {
      name = '새 공정',
      description = '',
      cycle_time_sec = 60.0,
      afterProcessId = null
    } = options;

    const processes = state.bopData.processes;
    const processDetails = state.bopData.process_details || [];
    const newId = generateNextProcessId(processes);

    // Default position: rightmost detail x + 5
    let newX = 0;
    processDetails.forEach(d => {
      if (d.location) {
        newX = Math.max(newX, d.location.x);
      }
    });
    newX += 5;

    // Create routing entry
    const newProcess = {
      process_id: newId,
      predecessor_ids: [],
      successor_ids: []
    };

    // Create detail entry
    const newDetail = {
      process_id: newId,
      parallel_index: 1,
      name,
      description,
      cycle_time_sec,
      location: { x: newX, y: 0, z: 0 },
      rotation_y: 0
    };

    let updatedProcesses = [...processes];

    if (afterProcessId) {
      const afterProc = processes.find(p => p.process_id === afterProcessId);
      if (afterProc) {
        const oldSuccIds = [...(afterProc.successor_ids || [])];

        newProcess.predecessor_ids = [afterProcessId];
        newProcess.successor_ids = oldSuccIds;

        // Position after the reference process
        const refDetails = processDetails.filter(d => d.process_id === afterProcessId);
        if (refDetails.length > 0 && refDetails[0].location) {
          newDetail.location.x = refDetails[0].location.x + 5;
        }

        // Reconnect links
        updatedProcesses = updatedProcesses.map(p => {
          if (p.process_id === afterProcessId) {
            return { ...p, successor_ids: [newId] };
          }
          if (oldSuccIds.includes(p.process_id)) {
            return {
              ...p,
              predecessor_ids: (p.predecessor_ids || []).map(pid =>
                pid === afterProcessId ? newId : pid
              )
            };
          }
          return p;
        });
      }
    }

    updatedProcesses.push(newProcess);

    return {
      bopData: {
        ...state.bopData,
        processes: updatedProcesses,
        process_details: [...processDetails, newDetail]
      },
      selectedProcessKey: `${newId}:1`,
      activeTab: 'bop'
    };
  }),

  // Update process detail properties (name, description, cycle_time_sec, location, rotation_y)
  updateProcess: (processId, parallelIndex, fields) => set((state) => {
    if (!state.bopData) return state;

    const allowedFields = ['name', 'description', 'cycle_time_sec', 'location', 'rotation_y'];

    const updates = {};
    for (const key of allowedFields) {
      if (fields[key] !== undefined) updates[key] = fields[key];
    }

    if (Object.keys(updates).length === 0) return state;

    const updatedDetails = state.bopData.process_details.map(d => {
      if (d.process_id === processId && d.parallel_index === parallelIndex) {
        return { ...d, ...updates };
      }
      return d;
    });

    return {
      bopData: { ...state.bopData, process_details: updatedDetails }
    };
  }),

  // Delete an entire process (all parallel instances)
  deleteProcess: (processId) => set((state) => {
    if (!state.bopData) return state;

    const processes = state.bopData.processes;
    const target = processes.find(p => p.process_id === processId);
    if (!target) return state;

    const predIds = target.predecessor_ids || [];
    const succIds = target.successor_ids || [];

    // Remove from processes and reconnect links
    const updatedProcesses = processes
      .filter(p => p.process_id !== processId)
      .map(p => {
        let newSucc = p.successor_ids || [];
        let newPred = p.predecessor_ids || [];
        let changed = false;

        if (newSucc.includes(processId)) {
          newSucc = newSucc.flatMap(s => s === processId ? succIds : [s]);
          changed = true;
        }
        if (newPred.includes(processId)) {
          newPred = newPred.flatMap(pid => pid === processId ? predIds : [pid]);
          changed = true;
        }

        return changed ? { ...p, successor_ids: newSucc, predecessor_ids: newPred } : p;
      });

    // Remove from process_details and resource_assignments
    const updatedDetails = (state.bopData.process_details || []).filter(d => d.process_id !== processId);
    const updatedAssignments = (state.bopData.resource_assignments || []).filter(r => r.process_id !== processId);

    // Update selection
    const isDeleted = state.selectedProcessKey?.startsWith(`${processId}:`);

    return {
      bopData: {
        ...state.bopData,
        processes: updatedProcesses,
        process_details: updatedDetails,
        resource_assignments: updatedAssignments
      },
      selectedProcessKey: isDeleted ? null : state.selectedProcessKey,
      selectedResourceKey: null
    };
  }),

  // Add a parallel instance to a process
  addParallelLine: (processId) => set((state) => {
    if (!state.bopData) return state;

    const details = getDetailsForProcess(state.bopData, processId);
    if (details.length === 0) return state;

    const sortedDetails = [...details].sort((a, b) => a.parallel_index - b.parallel_index);
    const firstDetail = sortedDetails[0];
    const nextIndex = Math.max(...details.map(d => d.parallel_index)) + 1;

    // Clone resources from first instance
    const firstResources = getResourcesForDetail(state.bopData, processId, firstDetail.parallel_index);
    const { clonedResources, newEquipments, newWorkers } =
      cloneResourcesForNewLine(firstResources, state.bopData);

    // New detail
    const newDetail = {
      process_id: processId,
      parallel_index: nextIndex,
      name: firstDetail.name,
      description: firstDetail.description || '',
      cycle_time_sec: firstDetail.cycle_time_sec,
      location: {
        x: firstDetail.location?.x || 0,
        y: firstDetail.location?.y || 0,
        z: (firstDetail.location?.z || 0) + (nextIndex - 1) * 5
      },
      rotation_y: firstDetail.rotation_y || 0
    };

    // New resource assignments with correct process_id and parallel_index
    const newAssignments = clonedResources.map(r => ({
      ...r,
      process_id: processId,
      parallel_index: nextIndex
    }));

    return {
      bopData: {
        ...state.bopData,
        process_details: [...(state.bopData.process_details || []), newDetail],
        resource_assignments: [...(state.bopData.resource_assignments || []), ...newAssignments],
        equipments: [...(state.bopData.equipments || []), ...newEquipments],
        workers: [...(state.bopData.workers || []), ...newWorkers]
      },
      selectedProcessKey: `${processId}:${nextIndex}`,
      activeTab: 'bop'
    };
  }),

  // Remove a parallel instance from a process
  removeParallelLine: (processId, parallelIndex) => set((state) => {
    if (!state.bopData) return state;

    const details = getDetailsForProcess(state.bopData, processId);
    if (details.length <= 1) return state; // Can't remove last one

    // Remove detail and assignments for this index
    let updatedDetails = (state.bopData.process_details || []).filter(
      d => !(d.process_id === processId && d.parallel_index === parallelIndex)
    );
    let updatedAssignments = (state.bopData.resource_assignments || []).filter(
      r => !(r.process_id === processId && r.parallel_index === parallelIndex)
    );

    // Re-index remaining parallel_indexes to be sequential (1-based)
    const remainingDetails = updatedDetails
      .filter(d => d.process_id === processId)
      .sort((a, b) => a.parallel_index - b.parallel_index);

    const indexMap = {}; // oldIndex -> newIndex
    remainingDetails.forEach((d, idx) => {
      indexMap[d.parallel_index] = idx + 1;
    });

    updatedDetails = updatedDetails.map(d => {
      if (d.process_id === processId && indexMap[d.parallel_index] !== undefined) {
        return { ...d, parallel_index: indexMap[d.parallel_index] };
      }
      return d;
    });

    updatedAssignments = updatedAssignments.map(r => {
      if (r.process_id === processId && indexMap[r.parallel_index] !== undefined) {
        return { ...r, parallel_index: indexMap[r.parallel_index] };
      }
      return r;
    });

    // Update selection
    let newSelectedProcess = state.selectedProcessKey;
    if (newSelectedProcess === `${processId}:${parallelIndex}`) {
      newSelectedProcess = null;
    } else if (newSelectedProcess?.startsWith(`${processId}:`)) {
      const oldIdx = parseInt(newSelectedProcess.split(':')[1], 10);
      if (indexMap[oldIdx] !== undefined) {
        newSelectedProcess = `${processId}:${indexMap[oldIdx]}`;
      }
    }

    // Update resource selection
    let newSelectedResource = state.selectedResourceKey;
    if (newSelectedResource) {
      const parts = newSelectedResource.split(':');
      if (parts.length >= 4 && parts[2] === processId) {
        const resParIdx = parseInt(parts[3], 10);
        if (resParIdx === parallelIndex) {
          newSelectedResource = null;
        } else if (indexMap[resParIdx] !== undefined) {
          parts[3] = String(indexMap[resParIdx]);
          newSelectedResource = parts.join(':');
        }
      }
    }

    return {
      bopData: {
        ...state.bopData,
        process_details: updatedDetails,
        resource_assignments: updatedAssignments
      },
      selectedProcessKey: newSelectedProcess,
      selectedResourceKey: newSelectedResource
    };
  }),

  // ===================================================================
  // Process Link (predecessor / successor) editing
  // ===================================================================

  linkProcesses: (fromId, toId) => set((state) => {
    if (!state.bopData || fromId === toId) return state;
    const processes = state.bopData.processes;

    const fromProc = processes.find(p => p.process_id === fromId);
    if (!fromProc) return state;
    if ((fromProc.successor_ids || []).includes(toId)) return state;

    const updatedProcesses = processes.map(p => {
      if (p.process_id === fromId) {
        return { ...p, successor_ids: [...(p.successor_ids || []), toId] };
      }
      if (p.process_id === toId) {
        return { ...p, predecessor_ids: [...(p.predecessor_ids || []), fromId] };
      }
      return p;
    });

    return { bopData: { ...state.bopData, processes: updatedProcesses } };
  }),

  unlinkProcesses: (fromId, toId) => set((state) => {
    if (!state.bopData) return state;
    const processes = state.bopData.processes;

    const updatedProcesses = processes.map(p => {
      if (p.process_id === fromId) {
        return { ...p, successor_ids: (p.successor_ids || []).filter(id => id !== toId) };
      }
      if (p.process_id === toId) {
        return { ...p, predecessor_ids: (p.predecessor_ids || []).filter(id => id !== fromId) };
      }
      return p;
    });

    return { bopData: { ...state.bopData, processes: updatedProcesses } };
  }),

  // ===================================================================
  // Resource CRUD (resource ↔ process instance assignment)
  // ===================================================================

  addResourceToProcess: (processId, parallelIndex, resourceData) => set((state) => {
    if (!state.bopData) return state;

    const { resource_type, resource_id, quantity = 1 } = resourceData;
    if (!resource_type || !resource_id) return state;

    // Prevent duplicates
    const exists = (state.bopData.resource_assignments || []).some(
      r => r.process_id === processId && r.parallel_index === parallelIndex &&
           r.resource_type === resource_type && r.resource_id === resource_id
    );
    if (exists) return state;

    const newAssignment = {
      process_id: processId,
      parallel_index: parallelIndex,
      resource_type,
      resource_id,
      quantity,
      relative_location: { x: 0, y: 0, z: 0 },
      rotation_y: 0,
      scale: { x: 1, y: 1, z: 1 },
      computed_size: computeResourceSize({ resource_type, resource_id }, state.bopData.equipments)
    };

    return {
      bopData: {
        ...state.bopData,
        resource_assignments: [...(state.bopData.resource_assignments || []), newAssignment]
      }
    };
  }),

  updateResourceInProcess: (processId, parallelIndex, resourceType, resourceId, fields) => set((state) => {
    if (!state.bopData) return state;

    const allowedFields = ['quantity'];

    const updatedAssignments = (state.bopData.resource_assignments || []).map(r => {
      if (r.process_id === processId && r.parallel_index === parallelIndex &&
          r.resource_type === resourceType && r.resource_id === resourceId) {
        const updates = {};
        for (const key of allowedFields) {
          if (fields[key] !== undefined) updates[key] = fields[key];
        }
        return { ...r, ...updates };
      }
      return r;
    });

    return {
      bopData: { ...state.bopData, resource_assignments: updatedAssignments }
    };
  }),

  removeResourceFromProcess: (processId, parallelIndex, resourceType, resourceId) => set((state) => {
    if (!state.bopData) return state;

    const updatedAssignments = (state.bopData.resource_assignments || []).filter(
      r => !(r.process_id === processId && r.parallel_index === parallelIndex &&
             r.resource_type === resourceType && r.resource_id === resourceId)
    );

    if (updatedAssignments.length === (state.bopData.resource_assignments || []).length) {
      return state; // Nothing removed
    }

    let bopData = { ...state.bopData, resource_assignments: updatedAssignments };
    bopData = normalizeProcessCenter(bopData, processId, parallelIndex);

    const resourceKey = `${resourceType}:${resourceId}:${processId}:${parallelIndex}`;

    return {
      bopData,
      selectedResourceKey: state.selectedResourceKey === resourceKey ? null : state.selectedResourceKey
    };
  }),

  // ===================================================================
  // Equipment Master CRUD
  // ===================================================================

  addEquipment: (data = {}) => set((state) => {
    if (!state.bopData) return state;

    const equipments = state.bopData.equipments || [];
    const newId = data.equipment_id || generateNextEquipmentId(equipments);

    if (equipments.some(e => e.equipment_id === newId)) return state;

    const idNumber = newId.match(/\d+/)?.[0] || '';
    const defaultName = idNumber ? `새 장비 ${idNumber}` : '새 장비';

    const newEquipment = {
      equipment_id: newId,
      name: data.name || defaultName,
      type: data.type || 'manual_station'
    };

    return {
      bopData: { ...state.bopData, equipments: [...equipments, newEquipment] }
    };
  }),

  updateEquipment: (equipmentId, fields) => set((state) => {
    if (!state.bopData) return state;

    const allowedFields = ['name', 'type'];
    const updatedEquipments = (state.bopData.equipments || []).map(eq => {
      if (eq.equipment_id === equipmentId) {
        const updates = {};
        for (const key of allowedFields) {
          if (fields[key] !== undefined) updates[key] = fields[key];
        }
        return { ...eq, ...updates };
      }
      return eq;
    });

    // If type changed, recalculate computed_size for all resource_assignments referencing this equipment
    let updatedAssignments = state.bopData.resource_assignments || [];
    if (fields.type !== undefined) {
      const newSize = getResourceSize('equipment', fields.type);
      updatedAssignments = updatedAssignments.map(r => {
        if (r.resource_type === 'equipment' && r.resource_id === equipmentId) {
          return { ...r, computed_size: newSize };
        }
        return r;
      });
    }

    return {
      bopData: { ...state.bopData, equipments: updatedEquipments, resource_assignments: updatedAssignments }
    };
  }),

  deleteEquipment: (equipmentId) => set((state) => {
    if (!state.bopData) return state;

    const updatedEquipments = (state.bopData.equipments || []).filter(
      eq => eq.equipment_id !== equipmentId
    );

    // Find affected instances before removing
    const affectedInstances = new Set();
    (state.bopData.resource_assignments || []).forEach(r => {
      if (r.resource_type === 'equipment' && r.resource_id === equipmentId) {
        affectedInstances.add(`${r.process_id}:${r.parallel_index}`);
      }
    });

    const updatedAssignments = (state.bopData.resource_assignments || []).filter(
      r => !(r.resource_type === 'equipment' && r.resource_id === equipmentId)
    );

    let bopData = { ...state.bopData, equipments: updatedEquipments, resource_assignments: updatedAssignments };

    // Normalize affected instances
    for (const key of affectedInstances) {
      const [pid, pidxStr] = key.split(':');
      bopData = normalizeProcessCenter(bopData, pid, parseInt(pidxStr, 10));
    }

    return { bopData, selectedResourceKey: null };
  }),

  // ===================================================================
  // Worker Master CRUD
  // ===================================================================

  addWorker: (data = {}) => set((state) => {
    if (!state.bopData) return state;

    const workers = state.bopData.workers || [];
    const newId = data.worker_id || generateNextWorkerId(workers);

    if (workers.some(w => w.worker_id === newId)) return state;

    const idNumber = newId.match(/\d+/)?.[0] || '';
    const defaultName = idNumber ? `새 작업자 ${idNumber}` : '새 작업자';

    const newWorker = {
      worker_id: newId,
      name: data.name || defaultName,
      skill_level: data.skill_level || 'Mid'
    };

    return {
      bopData: { ...state.bopData, workers: [...workers, newWorker] }
    };
  }),

  updateWorker: (workerId, fields) => set((state) => {
    if (!state.bopData) return state;

    const allowedFields = ['name', 'skill_level'];
    const updatedWorkers = (state.bopData.workers || []).map(w => {
      if (w.worker_id === workerId) {
        const updates = {};
        for (const key of allowedFields) {
          if (fields[key] !== undefined) updates[key] = fields[key];
        }
        return { ...w, ...updates };
      }
      return w;
    });

    return {
      bopData: { ...state.bopData, workers: updatedWorkers }
    };
  }),

  deleteWorker: (workerId) => set((state) => {
    if (!state.bopData) return state;

    const updatedWorkers = (state.bopData.workers || []).filter(
      w => w.worker_id !== workerId
    );

    const affectedInstances = new Set();
    (state.bopData.resource_assignments || []).forEach(r => {
      if (r.resource_type === 'worker' && r.resource_id === workerId) {
        affectedInstances.add(`${r.process_id}:${r.parallel_index}`);
      }
    });

    const updatedAssignments = (state.bopData.resource_assignments || []).filter(
      r => !(r.resource_type === 'worker' && r.resource_id === workerId)
    );

    let bopData = { ...state.bopData, workers: updatedWorkers, resource_assignments: updatedAssignments };

    for (const key of affectedInstances) {
      const [pid, pidxStr] = key.split(':');
      bopData = normalizeProcessCenter(bopData, pid, parseInt(pidxStr, 10));
    }

    return { bopData, selectedResourceKey: null };
  }),

  // ===================================================================
  // Material Master CRUD
  // ===================================================================

  addMaterial: (data = {}) => set((state) => {
    if (!state.bopData) return state;

    const materials = state.bopData.materials || [];
    const newId = data.material_id || generateNextMaterialId(materials);

    if (materials.some(m => m.material_id === newId)) return state;

    const idNumber = newId.match(/\d+/)?.[0] || '';
    const defaultName = idNumber ? `새 자재 ${idNumber}` : '새 자재';

    const newMaterial = {
      material_id: newId,
      name: data.name || defaultName,
      unit: data.unit || 'ea'
    };

    return {
      bopData: { ...state.bopData, materials: [...materials, newMaterial] }
    };
  }),

  updateMaterial: (materialId, fields) => set((state) => {
    if (!state.bopData) return state;

    const allowedFields = ['name', 'unit'];
    const updatedMaterials = (state.bopData.materials || []).map(m => {
      if (m.material_id === materialId) {
        const updates = {};
        for (const key of allowedFields) {
          if (fields[key] !== undefined) updates[key] = fields[key];
        }
        return { ...m, ...updates };
      }
      return m;
    });

    return {
      bopData: { ...state.bopData, materials: updatedMaterials }
    };
  }),

  deleteMaterial: (materialId) => set((state) => {
    if (!state.bopData) return state;

    const updatedMaterials = (state.bopData.materials || []).filter(
      m => m.material_id !== materialId
    );

    const affectedInstances = new Set();
    (state.bopData.resource_assignments || []).forEach(r => {
      if (r.resource_type === 'material' && r.resource_id === materialId) {
        affectedInstances.add(`${r.process_id}:${r.parallel_index}`);
      }
    });

    const updatedAssignments = (state.bopData.resource_assignments || []).filter(
      r => !(r.resource_type === 'material' && r.resource_id === materialId)
    );

    let bopData = { ...state.bopData, materials: updatedMaterials, resource_assignments: updatedAssignments };

    for (const key of affectedInstances) {
      const [pid, pidxStr] = key.split(':');
      bopData = normalizeProcessCenter(bopData, pid, parseInt(pidxStr, 10));
    }

    return { bopData, selectedResourceKey: null };
  }),

  // ===================================================================
  // Obstacle CRUD
  // ===================================================================

  setSelectedObstacle: (obstacleId) => set({
    selectedObstacleId: obstacleId,
    selectedProcessKey: null,
    selectedResourceKey: null,
    activeTab: 'obstacles'
  }),

  clearObstacleSelection: () => set({ selectedObstacleId: null }),

  getObstacleById: (obstacleId) => {
    const state = useBopStore.getState();
    if (!state.bopData || !state.bopData.obstacles) return null;
    return state.bopData.obstacles.find(o => o.obstacle_id === obstacleId);
  },

  addObstacle: (data = {}) => set((state) => {
    if (!state.bopData) return state;

    const obstacles = state.bopData.obstacles || [];
    const newId = data.obstacle_id || generateNextObstacleId(obstacles);

    if (obstacles.some(o => o.obstacle_id === newId)) return state;

    const obstacleType = data.type || state.pendingObstacleType || 'fence';

    const getDefaultSize = (type) => {
      switch (type) {
        case 'fence': return { width: 3, height: 1.5, depth: 0.1 };
        case 'zone': return { width: 3, height: 0.05, depth: 3 };
        case 'pillar': return { width: 0.5, height: 3, depth: 0.5 };
        case 'wall': return { width: 4, height: 2.5, depth: 0.2 };
        default: return { width: 2, height: 2, depth: 0.1 };
      }
    };

    const getDefaultName = (type) => {
      switch (type) {
        case 'fence': return '안전 펜스';
        case 'zone': return '위험 구역';
        case 'pillar': return '기둥';
        case 'wall': return '벽';
        default: return '새 장애물';
      }
    };

    const newObstacle = {
      obstacle_id: newId,
      name: data.name || getDefaultName(obstacleType),
      type: obstacleType,
      position: data.position || { x: 0, y: 0, z: 0 },
      size: data.size || getDefaultSize(obstacleType),
      rotation_y: data.rotation_y || 0
    };

    return {
      bopData: { ...state.bopData, obstacles: [...obstacles, newObstacle] },
      selectedObstacleId: newId,
      activeTab: 'obstacles'
    };
  }),

  updateObstacle: (obstacleId, fields) => set((state) => {
    if (!state.bopData) return state;

    const allowedFields = ['name', 'type', 'position', 'size', 'rotation_y'];
    const updatedObstacles = (state.bopData.obstacles || []).map(obstacle => {
      if (obstacle.obstacle_id === obstacleId) {
        const updates = {};
        for (const key of allowedFields) {
          if (fields[key] !== undefined) updates[key] = fields[key];
        }
        return { ...obstacle, ...updates };
      }
      return obstacle;
    });

    return {
      bopData: { ...state.bopData, obstacles: updatedObstacles }
    };
  }),

  deleteObstacle: (obstacleId) => set((state) => {
    if (!state.bopData) return state;

    const updatedObstacles = (state.bopData.obstacles || []).filter(
      o => o.obstacle_id !== obstacleId
    );

    return {
      bopData: { ...state.bopData, obstacles: updatedObstacles },
      selectedObstacleId: state.selectedObstacleId === obstacleId ? null : state.selectedObstacleId
    };
  }),

  // ===================================================================
  // Obstacle Two-Click Creation
  // ===================================================================

  setObstacleCreationMode: (enabled, type = null) => set((state) => ({
    obstacleCreationMode: enabled,
    obstacleCreationFirstClick: null,
    pendingObstacleType: type || state.pendingObstacleType
  })),

  toggleUse3DModels: () => set((state) => ({
    use3DModels: !state.use3DModels
  })),

  setCustomModel: (resourceType, resourceId, blobUrl) => set((state) => {
    const key = `${resourceType}:${resourceId}`;
    // Revoke old blob URL if replacing
    const oldUrl = state.customModels[key];
    if (oldUrl) URL.revokeObjectURL(oldUrl);
    return { customModels: { ...state.customModels, [key]: blobUrl } };
  }),

  removeCustomModel: (resourceType, resourceId) => set((state) => {
    const key = `${resourceType}:${resourceId}`;
    const oldUrl = state.customModels[key];
    if (oldUrl) URL.revokeObjectURL(oldUrl);
    const { [key]: _removed, ...rest } = state.customModels;
    return { customModels: rest };
  }),

  setPendingObstacleType: (type) => set({ pendingObstacleType: type }),

  setObstacleCreationFirstClick: (point) => set({
    obstacleCreationFirstClick: point
  }),

  createObstacleFromTwoClicks: (corner1, corner2) => set((state) => {
    if (!state.bopData) return state;

    const obstacles = state.bopData.obstacles || [];
    const newId = generateNextObstacleId(obstacles);
    const obstacleType = state.pendingObstacleType || 'fence';

    const centerX = (corner1.x + corner2.x) / 2;
    const centerZ = (corner1.z + corner2.z) / 2;
    const width = Math.abs(corner2.x - corner1.x);
    const depth = Math.abs(corner2.z - corner1.z);

    const getDefaultHeight = (type) => {
      switch (type) {
        case 'fence': return 1.5;
        case 'zone': return 0.05;
        case 'pillar': return 3;
        case 'wall': return 2.5;
        default: return 2;
      }
    };

    const getDefaultName = (type) => {
      switch (type) {
        case 'fence': return '안전 펜스';
        case 'zone': return '위험 구역';
        case 'pillar': return '기둥';
        case 'wall': return '벽';
        default: return '새 장애물';
      }
    };

    const newObstacle = {
      obstacle_id: newId,
      name: getDefaultName(obstacleType),
      type: obstacleType,
      position: { x: centerX, y: 0, z: centerZ },
      size: { width: Math.max(0.5, width), height: getDefaultHeight(obstacleType), depth: Math.max(0.5, depth) },
      rotation_y: 0
    };

    return {
      bopData: { ...state.bopData, obstacles: [...obstacles, newObstacle] },
      selectedObstacleId: newId,
      activeTab: 'obstacles',
      obstacleCreationMode: false,
      obstacleCreationFirstClick: null
    };
  }),

  // ===================================================================
  // Scenario Management (localStorage)
  // ===================================================================

  saveScenario: (name) => {
    const state = useBopStore.getState();
    if (!state.bopData) {
      throw new Error('저장할 BOP 데이터가 없습니다.');
    }

    // Save directly (no collapse needed - flat structure)
    const scenarios = JSON.parse(localStorage.getItem('bop_scenarios') || '[]');
    const now = new Date().toISOString();

    const existingIndex = scenarios.findIndex(s => s.name === name);

    if (existingIndex >= 0) {
      scenarios[existingIndex] = {
        ...scenarios[existingIndex],
        updatedAt: now,
        data: state.bopData
      };
    } else {
      const newScenario = {
        id: `scenario-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        name,
        createdAt: now,
        updatedAt: now,
        data: state.bopData
      };
      scenarios.push(newScenario);
    }

    localStorage.setItem('bop_scenarios', JSON.stringify(scenarios));
    return scenarios;
  },

  loadScenario: (id) => set((state) => {
    const scenarios = JSON.parse(localStorage.getItem('bop_scenarios') || '[]');
    const scenario = scenarios.find(s => s.id === id);

    if (!scenario) {
      throw new Error('시나리오를 찾을 수 없습니다.');
    }

    // Migrate old format if needed, then load directly
    const migrated = migrateOldFormat(scenario.data);
    const withSizes = ensureComputedSizes(migrated);

    return {
      bopData: withSizes,
      selectedProcessKey: null,
      selectedResourceKey: null,
      selectedObstacleId: null
    };
  }),

  deleteScenario: (id) => {
    const scenarios = JSON.parse(localStorage.getItem('bop_scenarios') || '[]');
    const filtered = scenarios.filter(s => s.id !== id);
    localStorage.setItem('bop_scenarios', JSON.stringify(filtered));
    return filtered;
  },

  listScenarios: () => {
    return JSON.parse(localStorage.getItem('bop_scenarios') || '[]');
  },

  createNewScenario: () => set(() => ({
    bopData: {
      project_title: "새 프로젝트",
      target_uph: 60,
      processes: [],
      process_details: [],
      resource_assignments: [],
      equipments: [],
      workers: [],
      materials: [],
      obstacles: []
    },
    selectedProcessKey: null,
    selectedResourceKey: null,
    selectedObstacleId: null,
    activeTab: 'bop'
  }))
}));

export default useBopStore;
