import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Text, Line, TransformControls } from '@react-three/drei';
import useBopStore from '../store/bopStore';
import { useState, useMemo, useCallback, useRef, useEffect, Suspense } from 'react';
import { RobotModel, ConveyorModel, BoxModel, ScannerModel, WorkerModel, CustomModel } from './Models3D';
import useTranslation from '../i18n/useTranslation';

// Helper function: Normalize angle to [-π, π] range
function normalizeAngle(angle) {
  while (angle > Math.PI) angle -= 2 * Math.PI;
  while (angle < -Math.PI) angle += 2 * Math.PI;
  return angle;
}

// Helper: 5도 스냅 (라디안)
const ROTATION_SNAP_ANGLE = Math.PI / 36; // 5 degrees
function snapRotation(angle) {
  return Math.round(angle / ROTATION_SNAP_ANGLE) * ROTATION_SNAP_ANGLE;
}

// Helper function: Get resource size based on type (exported for tables)
export function getResourceSize(resourceType, equipmentType) {
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
  return { width: 0.4, height: 0.4, depth: 0.4 };  // default
}

// Process Box Component
function ProcessBox({ process, isSelected, onSelect, onTransformMouseDown, onTransformMouseUp, isDraggingTransformRef }) {
  const [hovered, setHovered] = useState(false);
  const [transformMode, setTransformMode] = useState('translate'); // 'translate', 'rotate'
  const [activeAxis, setActiveAxis] = useState(null); // 현재 드래그 중인 축 ('X', 'Y', 'Z', 'XY', etc.)
  const [hoveredAxis, setHoveredAxis] = useState(null); // 마우스 hover 중인 축
  const [rotationRingHovered, setRotationRingHovered] = useState(false); // 회전 링 hover 상태
  const [isRotating, setIsRotating] = useState(false); // 회전 중 상태 (UI용)
  const { bopData, updateProcessLocation, updateProcessRotation, obstacleCreationMode } = useBopStore();

  const groupRef = useRef();
  const transformControlsRef = useRef();

  // 커스텀 회전을 위한 refs
  const isRotatingRef = useRef(false);
  const rotationStartValueRef = useRef(0);  // 드래그 시작 시 저장된 회전값
  const mouseStartXRef = useRef(0);  // 드래그 시작 시 마우스 X 위치
  const currentRotationRef = useRef(0);  // 현재 회전값 (드래그 중 업데이트)

  // Three.js 좌표계:
  // X축: 좌우 (right = +) - 공정 흐름 방향 (왼쪽에서 오른쪽)
  // Y축: 상하 (up = +) - 높이
  // Z축: 앞뒤 (toward camera = +, away = -)
  //
  // 공장 레이아웃:
  // X축: 공정 흐름 방향 (0, 5, 10, 15...)
  // Y축: 높이 (height) - 바닥은 0
  // Z축: 병렬 공정 분리 방향 (parallel processes are now separated into individual processes)

  const color = isSelected ? '#ffeb3b' : (hovered ? '#ffd54f' : '#e0e0e0');

  // 바운딩 박스 계산: 이 공정의 모든 리소스를 포함
  const calculateBoundingBox = () => {
    const resources = (bopData?.resource_assignments || []).filter(
      r => r.process_id === process.process_id && r.parallel_index === process.parallel_index
    );

    if (resources.length === 0) {
      // 리소스가 없으면 아주 작은 크기
      return { width: 0.5, depth: 0.5, centerX: 0, centerZ: 0 };
    }

    // 모든 리소스의 relative_location과 rotation을 고려하여 min/max 계산
    let minX = Infinity;
    let maxX = -Infinity;
    let minZ = Infinity;
    let maxZ = -Infinity;

    resources.forEach((resource, resourceIndex) => {
      const relLoc = resource.relative_location || { x: 0, y: 0, z: 0 };

      // ResourceMarker와 동일한 로직으로 위치 계산
      let x, z;
      if (relLoc.x !== 0 || relLoc.z !== 0) {
        // 명시적 위치가 있으면 사용
        x = relLoc.x;
        z = relLoc.z;
      } else {
        // Auto-layout: Z축 수직 배치 (고정 간격) - bopStore.js와 동일
        const totalResources = resources.length;
        const step = 0.9; // depth(0.6) + spacing(0.3)
        x = 0;
        z = resourceIndex * step - (totalResources - 1) * step / 2;
      }

      const resourceRotation = resource.rotation_y || 0;
      const scale = resource.scale || { x: 1, y: 1, z: 1 };

      // 리소스 타입별 실제 크기 가져오기
      let equipmentType = null;
      if (resource.resource_type === 'equipment' && bopData?.equipments) {
        const equipmentData = bopData.equipments.find(e => e.equipment_id === resource.resource_id);
        equipmentType = equipmentData?.type;
        if (!equipmentData) {
          console.warn(`[ProcessBox] Equipment not found: ${resource.resource_id} for process ${process.process_id}`);
        }
      }

      const baseSize = resource.computed_size || getResourceSize(resource.resource_type, equipmentType);

      // 실제 크기 = 기본 크기 × scale
      const actualWidth = baseSize.width * scale.x;
      const actualDepth = baseSize.depth * scale.z;

      // 리소스의 4개 코너 계산 (회전 전, scale 적용 후)
      const halfWidth = actualWidth / 2;
      const halfDepth = actualDepth / 2;
      const corners = [
        { x: -halfWidth, z: -halfDepth },
        { x: halfWidth, z: -halfDepth },
        { x: halfWidth, z: halfDepth },
        { x: -halfWidth, z: halfDepth }
      ];

      // 각 코너를 리소스 rotation만큼 회전 후 리소스 위치에 더함
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

    // 리소스 바운더리와 정확히 일치
    const margin = 0; // 마진 없음
    const width = (maxX - minX) + margin;
    const depth = (maxZ - minZ) + margin;
    const centerX = (minX + maxX) / 2;
    const centerZ = (minZ + maxZ) / 2;

    return { width, depth, centerX, centerZ };
  };

  const boundingBox = calculateBoundingBox();

  // group을 process.location에 고정
  const position = [
    process.location.x,
    0,
    process.location.z
  ];

  // Get rotation from process data (with default)
  const rotationY = process.rotation_y || 0;

  // Transform 시작 시 초기값 저장
  const handleTransformStart = () => {
    if (transformMode === 'rotate') {
      // 회전은 커스텀 핸들러에서 처리하므로 여기서는 아무것도 하지 않음
    }
  };

  // Transform change handler - 드래그 중에는 제약만 적용
  const handleObjectChange = () => {
    if (!groupRef.current) return;

    // 현재 드래그 중인 축 감지
    if (transformControlsRef.current) {
      const axis = transformControlsRef.current.axis;
      if (axis !== activeAxis) {
        setActiveAxis(axis);
      }
    }

    if (transformMode === 'translate') {
      // Y축 고정
      groupRef.current.position.y = 0;
    } else if (transformMode === 'rotate') {
      // 회전은 커스텀 핸들러에서 처리
      // TransformControls의 회전값을 무시하고 커스텀 값 적용
      groupRef.current.rotation.x = 0;
      groupRef.current.rotation.z = 0;
      if (isRotatingRef.current) {
        groupRef.current.rotation.y = currentRotationRef.current;
      }
    }
  };

  // Transform 종료 시 최종 값을 store에 저장
  const handleTransformEnd = () => {
    if (!groupRef.current) return;

    if (transformMode === 'translate') {
      // 새 위치 저장
      const newLocation = {
        x: groupRef.current.position.x,
        y: 0,
        z: groupRef.current.position.z
      };
      updateProcessLocation(process.process_id, process.parallel_index, newLocation);
    } else if (transformMode === 'rotate' && isRotatingRef.current) {
      // 커스텀 회전값 저장
      const finalRotation = normalizeAngle(currentRotationRef.current);
      updateProcessRotation(process.process_id, process.parallel_index, finalRotation);
      isRotatingRef.current = false;
    }

    // 축 선택 초기화
    setActiveAxis(null);
  };

  // 커스텀 회전 핸들러 - 마우스 드래그로 직접 회전 계산 (5도 스냅 적용)
  const handleRotationMouseDown = useCallback((e) => {
    if (transformMode !== 'rotate') return;
    e.stopPropagation();

    isRotatingRef.current = true;
    setIsRotating(true);
    rotationStartValueRef.current = rotationY;
    currentRotationRef.current = rotationY;
    mouseStartXRef.current = e.clientX;

    const handleMouseMove = (moveEvent) => {
      if (!isRotatingRef.current) return;

      const deltaX = moveEvent.clientX - mouseStartXRef.current;
      // 마우스 200px 이동 = 180도 회전
      const rotationDelta = (deltaX / 200) * Math.PI;
      // 5도 스냅 적용
      currentRotationRef.current = snapRotation(rotationStartValueRef.current + rotationDelta);

      if (groupRef.current) {
        groupRef.current.rotation.y = currentRotationRef.current;
      }
    };

    const handleMouseUp = () => {
      if (isRotatingRef.current) {
        const finalRotation = normalizeAngle(currentRotationRef.current);
        updateProcessRotation(process.process_id, process.parallel_index, finalRotation);
        isRotatingRef.current = false;
        setIsRotating(false);
      }
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      onTransformMouseUp?.();
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    onTransformMouseDown?.();
  }, [transformMode, rotationY, process.process_id, process.parallel_index, updateProcessRotation, onTransformMouseDown, onTransformMouseUp]);

  // 커스텀 회전 중 회전값 유지
  useFrame(() => {
    if (isRotatingRef.current && groupRef.current) {
      groupRef.current.rotation.y = currentRotationRef.current;
    }
  });

  // Keyboard shortcuts for switching transform mode (T, R)
  useEffect(() => {
    if (!isSelected) return;

    const handleKeyDown = (e) => {
      if (e.key === 't' || e.key === 'T') {
        setTransformMode('translate');
      } else if (e.key === 'r' || e.key === 'R') {
        setTransformMode('rotate');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSelected]);

  // Set plane material properties when mode changes
  useEffect(() => {
    if (transformControlsRef.current && isSelected) {
      const controls = transformControlsRef.current;

      // 즉시 설정 시도
      const setupPlanes = () => {
        if (controls.children && controls.children.length > 0) {
          controls.traverse((child) => {
            if (child.material && child.name && (child.name === 'XY' || child.name === 'YZ' || child.name === 'XZ')) {
              child.material.transparent = true;
              child.material.opacity = 0.6; // 더 높은 기본 opacity
              child.material.depthTest = true;
              child.material.depthWrite = false;
              child.material.needsUpdate = true;
              child.visible = true;
            }
          });
        }
      };

      setupPlanes();

      // 모드 전환 후에도 다시 설정
      const timerId = setTimeout(setupPlanes, 100);
      return () => clearTimeout(timerId);
    }
  }, [transformMode, isSelected]);

  // Detect hovered axis and update colors using useFrame
  useFrame(() => {
    if (transformControlsRef.current && isSelected) {
      const controls = transformControlsRef.current;
      const currentAxis = controls.axis;

      if (currentAxis !== hoveredAxis) {
        setHoveredAxis(currentAxis);
      }

      // Update colors every frame to ensure they're applied even after mode changes
      const highlightAxis = activeAxis || currentAxis;

      if (controls.children && controls.children.length > 0) {
        controls.traverse((child) => {
          if (child.material) {
            const isActive = activeAxis === highlightAxis;
            const intensity = isActive ? 0.7 : 0.3;

            // 평면 색상 기본값 설정 및 강조
            if (child.name && (child.name === 'XY' || child.name === 'YZ' || child.name === 'XZ')) {
              if (highlightAxis === child.name) {
                child.material.color.set(isActive ? '#ffcc00' : '#ffeb3b');
                if (child.material.emissive) child.material.emissive.set('#ffaa00');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
                // 평면 opacity 대폭 증가 (hover 시 명확하게)
                if (child.material.opacity !== undefined) {
                  child.material.opacity = 0.9;
                }
                child.material.needsUpdate = true;
              } else {
                child.material.color.set('#00BFFF');
                if (child.material.emissive) child.material.emissive.set('#000000');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = 0;
                }
                // 기본 평면 opacity 증가 (hover 전에도 잘 보이도록)
                if (child.material.opacity !== undefined) {
                  child.material.opacity = 0.6;
                }
                child.material.needsUpdate = true;
              }
            }

            // 축 색상 강조 (단일 축 또는 평면 포함 축)
            if (highlightAxis && child.name && child.name.length === 1) {
              // X축: highlightAxis가 'X' 또는 'XY' 또는 'XZ'일 때
              if (child.name === 'X' && highlightAxis.includes('X')) {
                child.material.color.set(isActive ? '#ff3333' : '#ff6666');
                if (child.material.emissive) child.material.emissive.set('#ff0000');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              }
              // Y축: highlightAxis가 'Y' 또는 'XY' 또는 'YZ'일 때
              else if (child.name === 'Y' && highlightAxis.includes('Y')) {
                child.material.color.set(isActive ? '#33ff33' : '#66ff66');
                if (child.material.emissive) child.material.emissive.set('#00ff00');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              }
              // Z축: highlightAxis가 'Z' 또는 'YZ' 또는 'XZ'일 때
              else if (child.name === 'Z' && highlightAxis.includes('Z')) {
                child.material.color.set(isActive ? '#3333ff' : '#6666ff');
                if (child.material.emissive) child.material.emissive.set('#0000ff');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              }
            }
          }
        });
      }
    }
  });

  return (
    <>
      <group ref={groupRef} position={position} rotation={[0, rotationY, 0]}>
      {/* Process plane - 바운딩 박스 중심에 배치 */}
      <mesh
        position={[boundingBox.centerX, 0.01, boundingBox.centerZ]}
        rotation={[-Math.PI / 2, 0, 0]}
        renderOrder={-10}
        onPointerOver={() => {
          if (!isDraggingTransformRef.current && !obstacleCreationMode) {
            setHovered(true);
          }
        }}
        onPointerOut={() => {
          // 항상 hovered를 해제 (드래그 중에도)
          setHovered(false);
        }}
        onClick={(e) => {
          if (!isDraggingTransformRef.current && !obstacleCreationMode) {
            e.stopPropagation();
            onSelect();
          }
        }}
      >
        <planeGeometry args={[boundingBox.width, boundingBox.depth]} />
        <meshStandardMaterial
          color={color}
          emissive={isSelected ? '#ffeb3b' : '#000000'}
          emissiveIntensity={isSelected ? 0.6 : 0}
          transparent={true}
          opacity={isSelected ? 0.7 : 0.3}
          side={2}
          depthWrite={false}
        />
      </mesh>

      {/* Process label */}
      <Text
        position={[boundingBox.centerX, 2.5, boundingBox.centerZ]}
        fontSize={0.25}
        color="#333"
        anchorX="center"
        anchorY="middle"
      >
        {process.name}
      </Text>

      {/* Process ID and cycle time */}
      <Text
        position={[0, 2.2, 0]}
        fontSize={0.15}
        color="#666"
        anchorX="center"
        anchorY="middle"
      >
        {process.process_id} | {process.cycle_time_sec.toFixed(1)}s
      </Text>

      {/* Parallel indicator */}
      {process.parallel_index > 1 && (
        <Text
          position={[0, 1.9, 0]}
          fontSize={0.12}
          color="#999"
          anchorX="center"
          anchorY="middle"
        >
          (병렬 #{process.parallel_index})
        </Text>
      )}

      {/* Transform mode indicator - 선택된 경우에만 표시 */}
      {isSelected && (
        <Text
          position={[0, 3.0, 0]}
          fontSize={0.2}
          color={
            (activeAxis || hoveredAxis) === 'X' ? '#ff0000' :
            (activeAxis || hoveredAxis) === 'Y' ? '#00cc00' :
            (activeAxis || hoveredAxis) === 'Z' ? '#0000ff' :
            (activeAxis || hoveredAxis) === 'XY' || (activeAxis || hoveredAxis) === 'YZ' || (activeAxis || hoveredAxis) === 'XZ' ? '#ff9800' :
            transformMode === 'translate' ? '#4a90e2' : '#ff6b6b'
          }
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.02}
          outlineColor="#ffffff"
        >
          {transformMode === 'translate' ? '이동 (T)' :
           isRotating ? `회전 중: ${Math.round(currentRotationRef.current * 180 / Math.PI)}°` :
           '회전 (R) - 링 드래그'}
          {transformMode === 'translate' && (activeAxis || hoveredAxis) && ` - ${activeAxis || hoveredAxis}${(activeAxis || hoveredAxis).length > 1 ? ' 평면' : '축'}${activeAxis ? ' [드래그 중]' : ' [hover]'}`}
        </Text>
      )}

      {/* 커스텀 회전 핸들 - 회전 모드에서만 표시 */}
      {/* 회전 중심(0,0,0)에 링 배치 - 실제 회전 피벗 포인트, 바닥에 배치 */}
      {isSelected && transformMode === 'rotate' && (() => {
        const ringRadius = Math.max(boundingBox.width, boundingBox.depth) * 0.6 + 0.3;
        const ringColor = isRotating ? '#ffaa00' : (rotationRingHovered ? '#00cc00' : '#44ff44');
        const ringOpacity = isRotating ? 1.0 : (rotationRingHovered ? 0.95 : 0.85);
        return (
          <>
            {/* 회전 링 - 바닥(y=0.02)에 배치, 두꺼운 링 */}
            <mesh
              position={[0, 0.02, 0]}
              rotation={[-Math.PI / 2, 0, 0]}
              onPointerDown={handleRotationMouseDown}
              onPointerOver={() => setRotationRingHovered(true)}
              onPointerOut={() => setRotationRingHovered(false)}
            >
              <ringGeometry args={[ringRadius, ringRadius + 0.35, 64]} />
              <meshBasicMaterial color={ringColor} transparent opacity={ringOpacity} side={2} />
            </mesh>
            {/* 회전 중심 표시 마커 */}
            <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
              <circleGeometry args={[0.2, 32]} />
              <meshBasicMaterial color={ringColor} transparent opacity={ringOpacity} side={2} />
            </mesh>
          </>
        );
      })()}
      </group>

      {/* TransformControls - 이동 모드에서만 표시 */}
      {isSelected && transformMode === 'translate' && (
        <TransformControls
          ref={transformControlsRef}
          object={groupRef}
          mode="translate"
          space="world"
          size={1.5}
          showX={true}
          showY={false}
          showZ={true}
          onObjectChange={handleObjectChange}
          onMouseDown={(e) => {
            handleTransformStart();
            onTransformMouseDown(e);
          }}
          onMouseUp={(e) => {
            handleTransformEnd();
            onTransformMouseUp(e);
          }}
        />
      )}
    </>
  );
}

// Resource Marker Component with auto-layout
function ResourceMarker({ resource, processLocation, processBoundingCenter, processRotation, parallelIndex, equipmentData, workerData, materialData, resourceIndex, totalResources, processId, onTransformMouseDown, onTransformMouseUp, isDraggingTransformRef }) {
  const [hovered, setHovered] = useState(false);
  const [transformMode, setTransformMode] = useState('translate'); // 'translate', 'rotate', 'scale'
  const [activeAxis, setActiveAxis] = useState(null); // 현재 드래그 중인 축 ('X', 'Y', 'Z', 'XY', etc.)
  const [hoveredAxis, setHoveredAxis] = useState(null); // 마우스 hover 중인 축
  const [rotationRingHovered, setRotationRingHovered] = useState(false); // 회전 링 hover 상태
  const [isRotating, setIsRotating] = useState(false); // 회전 중 상태 (UI용)
  const { selectedResourceKey, setSelectedResource, updateResourceLocation, updateResourceRotation, updateResourceScale, obstacleCreationMode, use3DModels, customModels } = useBopStore();

  const groupRef = useRef();
  const transformControlsRef = useRef();

  // 커스텀 회전을 위한 refs
  const isRotatingRef = useRef(false);
  const rotationStartValueRef = useRef(0);
  const mouseStartXRef = useRef(0);
  const currentRotationRef = useRef(0);

  // 리소스 위치 계산: relative_location이 명시적으로 설정되었으면 사용, 아니면 auto-layout
  const getPosition = () => {
    const relLoc = resource.relative_location || { x: 0, y: 0, z: 0 };

    // 명시적 위치가 있으면 사용
    if (relLoc.x !== 0 || relLoc.z !== 0) {
      return {
        x: relLoc.x,
        z: relLoc.z
      };
    }

    // Auto-layout: Z축 수직 배치 (고정 간격) - bopStore.js와 동일
    const step = 0.9; // depth(0.6) + spacing(0.3)
    const z = resourceIndex * step - (totalResources - 1) * step / 2;

    return { x: 0, z: z };
  };

  const autoPos = getPosition();

  // 공정 회전을 고려한 좌표 변환
  // 1. relative_location (autoPos)는 이미 process.location 기준
  // 2. 회전 변환 적용 (Three.js Y축 회전과 동일한 방향)
  const rotatedX = autoPos.x * Math.cos(processRotation) + autoPos.z * Math.sin(processRotation);
  const rotatedZ = -autoPos.x * Math.sin(processRotation) + autoPos.z * Math.cos(processRotation);

  // 3. 월드 좌표로 변환: process.location + 회전된 좌표
  const actualX = processLocation.x + rotatedX;
  const actualZ = processLocation.z + rotatedZ;

  const getColor = () => {
    if (resource.resource_type === 'equipment' && equipmentData) {
      switch (equipmentData.type) {
        case 'robot': return '#4a90e2';
        case 'machine': return '#ff6b6b';
        case 'manual_station': return '#50c878';
        default: return '#888888';
      }
    } else if (resource.resource_type === 'worker') {
      return '#50c878';
    } else if (resource.resource_type === 'material') {
      return '#ffa500';
    }
    return '#888888';
  };

  const getGeometry = () => {
    // Custom model check
    const customKey = `${resource.resource_type}:${resource.resource_id}`;
    const customUrl = customModels?.[customKey];
    if (use3DModels && customUrl) {
      const baseSize = resource.computed_size || getResourceSize(resource.resource_type, equipmentData?.type);
      return { type: 'glb', model: 'custom', customUrl, args: [baseSize.width, baseSize.height, baseSize.depth], yOffset: 0, actualHeight: baseSize.height };
    }

    // 3D 모델 사용 시 - actualHeight 추가 (라벨 위치 계산용)
    if (use3DModels) {
      if (resource.resource_type === 'equipment' && equipmentData) {
        switch (equipmentData.type) {
          case 'robot':
            return { type: 'glb', model: 'robot', args: [1.4, 1.7, 0.6], yOffset: 0, actualHeight: 1.7 };
          case 'machine':
            return { type: 'glb', model: 'scanner', args: [2.1, 1.9, 1.0], yOffset: 0, actualHeight: 1.9 };
          case 'manual_station':
            return { type: 'glb', model: 'conveyor', args: [1.6, 1.0, 0.8], yOffset: 0, actualHeight: 1.0 };
          default:
            return { type: 'box', args: [0.4, 0.4, 0.4], yOffset: 0.2, actualHeight: 0.4 };
        }
      } else if (resource.resource_type === 'worker') {
        return { type: 'glb', model: 'worker', args: [0.5, 1.7, 0.3], yOffset: 0, actualHeight: 1.7 };
      } else if (resource.resource_type === 'material') {
        return { type: 'glb', model: 'box', args: [0.4, 0.25, 0.4], yOffset: 0, actualHeight: 0.25 };
      }
    }

    // 기본 도형 사용 시
    if (resource.resource_type === 'equipment' && equipmentData) {
      switch (equipmentData.type) {
        case 'robot':
          return { type: 'box', args: [1.4, 1.7, 0.6], yOffset: 0.85, actualHeight: 1.7 };
        case 'machine':
          return { type: 'box', args: [2.1, 1.9, 1.0], yOffset: 0.95, actualHeight: 1.9 };
        case 'manual_station':
          return { type: 'box', args: [1.6, 1.0, 0.8], yOffset: 0.5, actualHeight: 1.0 };
        default:
          return { type: 'box', args: [0.4, 0.4, 0.4], yOffset: 0.2, actualHeight: 0.4 };
      }
    } else if (resource.resource_type === 'worker') {
      return { type: 'box', args: [0.5, 1.7, 0.3], yOffset: 0.85, actualHeight: 1.7 };
    } else if (resource.resource_type === 'material') {
      return { type: 'box', args: [0.4, 0.25, 0.4], yOffset: 0.125, actualHeight: 0.25 };
    }
    return { type: 'box', args: [0.4, 0.4, 0.4], yOffset: 0.2, actualHeight: 0.4 };
  };

  const getName = () => {
    if (resource.resource_type === 'equipment' && equipmentData) {
      return equipmentData.name;
    } else if (resource.resource_type === 'worker' && workerData) {
      return workerData.name;
    } else if (resource.resource_type === 'material' && materialData) {
      return `${materialData.name} (${resource.quantity}${materialData.unit})`;
    }
    return resource.resource_id;
  };

  // Calculate resource key and check if selected
  // Use ':' separator (format: type:resourceId:processId:parallelIndex)
  const resourceKey = `${resource.resource_type}:${resource.resource_id}:${processId}:${parallelIndex}`;
  const isSelected = selectedResourceKey === resourceKey;

  // 디버깅 로그 (선택된 리소스만)
  if (isSelected) {
    console.log(`[ResourceMarker ${resource.resource_id}] processId=${processId}`);
    console.log(`  processLocation: (${processLocation.x.toFixed(2)}, ${processLocation.z.toFixed(2)})`);
    console.log(`  relative_location (autoPos): (${autoPos.x.toFixed(2)}, ${autoPos.z.toFixed(2)})`);
    console.log(`  processRotation: ${(processRotation * 180 / Math.PI).toFixed(1)}°`);
    console.log(`  after rotation: (${rotatedX.toFixed(2)}, ${rotatedZ.toFixed(2)})`);
    console.log(`  final actualPosition: (${actualX.toFixed(2)}, ${actualZ.toFixed(2)})`);
    console.log(`  expected (no rotation): (${(processLocation.x + autoPos.x).toFixed(2)}, ${(processLocation.z + autoPos.z).toFixed(2)})`);
  }

  // Click handler
  const handleClick = (e) => {
    if (obstacleCreationMode) return; // 장애물 생성 모드에서는 선택 불가
    e.stopPropagation();
    setSelectedResource(resource.resource_type, resource.resource_id, processId, parallelIndex);
  };

  const color = isSelected ? '#ffeb3b' : (hovered ? '#ffeb3b' : getColor());
  const geometry = getGeometry();

  // Get rotation and scale from resource data (with defaults)
  // 객체의 최종 회전 = 공정 회전 + 객체 자체 회전
  const resourceRotationY = resource.rotation_y || 0;
  const rotationY = processRotation + resourceRotationY;
  const scale = resource.scale || { x: 1, y: 1, z: 1 };

  // Transform 시작 시 초기값 저장
  const handleTransformStart = () => {
    // 회전은 커스텀 핸들러에서 처리
  };

  // Transform change handler - 드래그 중에는 제약만 적용
  const handleObjectChange = () => {
    if (!groupRef.current) return;

    // 현재 드래그 중인 축 감지
    if (transformControlsRef.current) {
      const axis = transformControlsRef.current.axis;
      if (axis !== activeAxis) {
        setActiveAxis(axis);
      }
    }

    if (transformMode === 'translate') {
      // Y축 고정
      groupRef.current.position.y = 0;
    } else if (transformMode === 'rotate') {
      // 커스텀 회전 핸들러에서 처리
      groupRef.current.rotation.x = 0;
      groupRef.current.rotation.z = 0;
      if (isRotatingRef.current) {
        groupRef.current.rotation.y = currentRotationRef.current;
      }
    }
  };

  // Transform 종료 시 최종 값을 store에 저장
  const handleTransformEnd = () => {
    if (!groupRef.current) return;

    if (transformMode === 'translate') {
      // 1. 월드 좌표 → process.location 기준 좌표
      const worldOffsetX = groupRef.current.position.x - processLocation.x;
      const worldOffsetZ = groupRef.current.position.z - processLocation.z;

      // 2. 역회전 변환
      const relX = worldOffsetX * Math.cos(processRotation) - worldOffsetZ * Math.sin(processRotation);
      const relZ = worldOffsetX * Math.sin(processRotation) + worldOffsetZ * Math.cos(processRotation);

      const newRelativeLocation = {
        x: relX,
        y: 0,
        z: relZ
      };

      updateResourceLocation(
        processId,
        parallelIndex,
        resource.resource_type,
        resource.resource_id,
        newRelativeLocation
      );
    } else if (transformMode === 'rotate' && isRotatingRef.current) {
      // 커스텀 회전값에서 공정 회전을 빼서 리소스 자체 회전만 저장
      const resourceOwnRotation = normalizeAngle(currentRotationRef.current - processRotation);
      isRotatingRef.current = false;

      updateResourceRotation(
        processId,
        parallelIndex,
        resource.resource_type,
        resource.resource_id,
        resourceOwnRotation
      );
    } else if (transformMode === 'scale') {
      // Scale 업데이트
      updateResourceScale(
        processId,
        parallelIndex,
        resource.resource_type,
        resource.resource_id,
        {
          x: groupRef.current.scale.x,
          y: groupRef.current.scale.y,
          z: groupRef.current.scale.z
        }
      );
    }

    // 축 선택 초기화
    setActiveAxis(null);
  };

  // 커스텀 회전 핸들러 - 마우스 드래그로 직접 회전 계산 (5도 스냅 적용)
  const handleRotationMouseDown = useCallback((e) => {
    if (transformMode !== 'rotate') return;
    e.stopPropagation();

    isRotatingRef.current = true;
    setIsRotating(true);
    rotationStartValueRef.current = rotationY;
    currentRotationRef.current = rotationY;
    mouseStartXRef.current = e.clientX;

    const handleMouseMove = (moveEvent) => {
      if (!isRotatingRef.current) return;

      const deltaX = moveEvent.clientX - mouseStartXRef.current;
      // 마우스 200px 이동 = 180도 회전
      const rotationDelta = (deltaX / 200) * Math.PI;
      // 5도 스냅 적용
      currentRotationRef.current = snapRotation(rotationStartValueRef.current + rotationDelta);

      if (groupRef.current) {
        groupRef.current.rotation.y = currentRotationRef.current;
      }
    };

    const handleMouseUp = () => {
      if (isRotatingRef.current) {
        // 리소스 자체 회전만 저장 (공정 회전 빼기)
        const resourceOwnRotation = normalizeAngle(currentRotationRef.current - processRotation);
        updateResourceRotation(
          processId,
          parallelIndex,
          resource.resource_type,
          resource.resource_id,
          resourceOwnRotation
        );
        isRotatingRef.current = false;
        setIsRotating(false);
      }
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      onTransformMouseUp?.();
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    onTransformMouseDown?.();
  }, [transformMode, rotationY, processRotation, processId, parallelIndex, resource.resource_type, resource.resource_id, updateResourceRotation, onTransformMouseDown, onTransformMouseUp]);

  // 커스텀 회전 중 회전값 유지
  useFrame(() => {
    if (isRotatingRef.current && groupRef.current) {
      groupRef.current.rotation.y = currentRotationRef.current;
    }
  });

  // Change TransformControls colors based on active/hovered axis
  useEffect(() => {
    if (transformControlsRef.current && isSelected) {
      const controls = transformControlsRef.current;
      const highlightAxis = activeAxis || hoveredAxis; // 드래그 중이면 activeAxis, 아니면 hoveredAxis

      // Access the gizmo object
      if (controls.children && controls.children.length > 0) {
        controls.traverse((child) => {
          if (child.material) {
            const isActive = activeAxis === highlightAxis; // 드래그 중인지 여부
            const intensity = isActive ? 0.7 : 0.3; // 드래그 중이면 더 밝게

            // 평면 색상 기본값 설정 및 강조
            if (child.name && (child.name === 'XY' || child.name === 'YZ' || child.name === 'XZ')) {
              // 평면이 highlight되는지 확인
              if (highlightAxis === child.name) {
                // 선택된 평면 강조
                child.material.color.set(isActive ? '#ffcc00' : '#ffeb3b'); // 노란색
                child.material.emissive?.set('#ffaa00');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              } else {
                // 기본 평면 색상 (리소스용 - 연두색)
                child.material.color.set('#7FFF00');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = 0;
                }
              }
            }

            // 축 색상 강조 - highlightAxis에 따라
            if (highlightAxis && child.name) {
              // X축 강조
              if (highlightAxis === 'X' && child.name.includes('X') && child.name.length === 1) {
                child.material.color.set(isActive ? '#ff3333' : '#ff6666'); // 밝은 빨강
                child.material.emissive?.set('#ff0000');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              }
              // Y축 강조
              else if (highlightAxis === 'Y' && child.name.includes('Y') && child.name.length === 1) {
                child.material.color.set(isActive ? '#33ff33' : '#66ff66'); // 밝은 초록
                child.material.emissive?.set('#00ff00');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              }
              // Z축 강조
              else if (highlightAxis === 'Z' && child.name.includes('Z') && child.name.length === 1) {
                child.material.color.set(isActive ? '#3333ff' : '#6666ff'); // 밝은 파랑
                child.material.emissive?.set('#0000ff');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              }
            }
          }
        });
      }
    }
  }, [isSelected, activeAxis, hoveredAxis]);

  // Keyboard shortcuts for switching transform mode (T, R, S)
  useEffect(() => {
    if (!isSelected) return;

    const handleKeyDown = (e) => {
      if (e.key === 't' || e.key === 'T') {
        setTransformMode('translate');
      } else if (e.key === 'r' || e.key === 'R') {
        setTransformMode('rotate');
      } else if (e.key === 's' || e.key === 'S') {
        setTransformMode('scale');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSelected]);

  // Set plane material properties when mode changes
  useEffect(() => {
    if (transformControlsRef.current && isSelected) {
      const controls = transformControlsRef.current;

      // 즉시 설정 시도
      const setupPlanes = () => {
        if (controls.children && controls.children.length > 0) {
          controls.traverse((child) => {
            if (child.material && child.name && (child.name === 'XY' || child.name === 'YZ' || child.name === 'XZ')) {
              child.material.transparent = true;
              child.material.opacity = 0.6; // 더 높은 기본 opacity
              child.material.depthTest = true;
              child.material.depthWrite = false;
              child.material.needsUpdate = true;
              child.visible = true;
            }
          });
        }
      };

      setupPlanes();

      // 모드 전환 후에도 다시 설정
      const timerId = setTimeout(setupPlanes, 100);
      return () => clearTimeout(timerId);
    }
  }, [transformMode, isSelected]);

  // Detect hovered axis and update colors using useFrame
  useFrame(() => {
    if (transformControlsRef.current && isSelected) {
      const controls = transformControlsRef.current;
      const currentAxis = controls.axis;

      if (currentAxis !== hoveredAxis) {
        setHoveredAxis(currentAxis);
      }

      // Update colors every frame to ensure they're applied even after mode changes
      const highlightAxis = activeAxis || currentAxis;

      if (controls.children && controls.children.length > 0) {
        controls.traverse((child) => {
          if (child.material) {
            const isActive = activeAxis === highlightAxis;
            const intensity = isActive ? 0.7 : 0.3;

            // 평면 색상 기본값 설정 및 강조
            if (child.name && (child.name === 'XY' || child.name === 'YZ' || child.name === 'XZ')) {
              if (highlightAxis === child.name) {
                child.material.color.set(isActive ? '#ffcc00' : '#ffeb3b');
                if (child.material.emissive) child.material.emissive.set('#ffaa00');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
                // 평면 opacity 대폭 증가 (hover 시 명확하게)
                if (child.material.opacity !== undefined) {
                  child.material.opacity = 0.9;
                }
                child.material.needsUpdate = true;
              } else {
                child.material.color.set('#7FFF00');
                if (child.material.emissive) child.material.emissive.set('#000000');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = 0;
                }
                // 기본 평면 opacity 증가 (hover 전에도 잘 보이도록)
                if (child.material.opacity !== undefined) {
                  child.material.opacity = 0.6;
                }
                child.material.needsUpdate = true;
              }
            }

            // 축 색상 강조 (단일 축 또는 평면 포함 축)
            if (highlightAxis && child.name && child.name.length === 1) {
              // X축: highlightAxis가 'X' 또는 'XY' 또는 'XZ'일 때
              if (child.name === 'X' && highlightAxis.includes('X')) {
                child.material.color.set(isActive ? '#ff3333' : '#ff6666');
                if (child.material.emissive) child.material.emissive.set('#ff0000');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              }
              // Y축: highlightAxis가 'Y' 또는 'XY' 또는 'YZ'일 때
              else if (child.name === 'Y' && highlightAxis.includes('Y')) {
                child.material.color.set(isActive ? '#33ff33' : '#66ff66');
                if (child.material.emissive) child.material.emissive.set('#00ff00');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              }
              // Z축: highlightAxis가 'Z' 또는 'YZ' 또는 'XZ'일 때
              else if (child.name === 'Z' && highlightAxis.includes('Z')) {
                child.material.color.set(isActive ? '#3333ff' : '#6666ff');
                if (child.material.emissive) child.material.emissive.set('#0000ff');
                if (child.material.emissiveIntensity !== undefined) {
                  child.material.emissiveIntensity = intensity;
                }
              }
            }
          }
        });
      }
    }
  });

  return (
    <>
      <group
        ref={groupRef}
        position={[actualX, 0, actualZ]}
        rotation={[0, rotationY, 0]}
        scale={[scale.x, scale.y, scale.z]}
      >
      {/* Resource mesh */}
      {geometry.type === 'glb' ? (
        <group
          position={[0, geometry.yOffset, 0]}
          onPointerOver={() => {
            if (!isDraggingTransformRef?.current && !obstacleCreationMode) setHovered(true);
          }}
          onPointerOut={() => {
            setHovered(false);
          }}
          onClick={handleClick}
        >
          <Suspense fallback={
            <mesh>
              <boxGeometry args={[0.5, 0.5, 0.5]} />
              <meshStandardMaterial color="#888888" />
            </mesh>
          }>
            {geometry.model === 'custom' && geometry.customUrl && (
              <CustomModel
                url={geometry.customUrl}
                targetSize={{ width: geometry.args[0], height: geometry.args[1], depth: geometry.args[2] }}
                highlighted={isSelected || hovered}
              />
            )}
            {geometry.model === 'robot' && (
              <RobotModel highlighted={isSelected || hovered} />
            )}
            {geometry.model === 'conveyor' && (
              <ConveyorModel highlighted={isSelected || hovered} />
            )}
            {geometry.model === 'scanner' && (
              <ScannerModel highlighted={isSelected || hovered} />
            )}
            {geometry.model === 'box' && (
              <BoxModel highlighted={isSelected || hovered} />
            )}
            {geometry.model === 'worker' && (
              <WorkerModel highlighted={isSelected || hovered} />
            )}
          </Suspense>
        </group>
      ) : (
        <mesh
          position={[0, geometry.yOffset, 0]}
          renderOrder={1}
          onPointerOver={() => {
            if (!isDraggingTransformRef?.current && !obstacleCreationMode) setHovered(true);
          }}
          onPointerOut={() => {
            setHovered(false);
          }}
          onClick={handleClick}
        >
          {geometry.type === 'cylinder' ? (
            <cylinderGeometry args={geometry.args} />
          ) : (
            <boxGeometry args={geometry.args} />
          )}
          <meshStandardMaterial
            color={color}
            emissive={isSelected || hovered ? '#ffeb3b' : '#000000'}
            emissiveIntensity={isSelected ? 0.8 : (hovered ? 0.5 : 0)}
            metalness={0.3}
            roughness={0.7}
          />
        </mesh>
      )}

      {/* Resource label - actualHeight 사용하여 라벨 위치 계산 */}
      {(isSelected || hovered) && (
        <>
          <Text
            position={[0, geometry.actualHeight + 0.5, 0]}
            fontSize={0.15}
            color="#333"
            anchorX="center"
            anchorY="middle"
            maxWidth={2}
            scale={[1/scale.x, 1/scale.y, 1/scale.z]}
          >
            {getName()}
          </Text>
        </>
      )}

      {/* Transform mode indicator - 선택된 경우에만 표시 */}
      {isSelected && (
        <Text
          position={[0, geometry.actualHeight + 1.0, 0]}
          fontSize={0.18}
          color={
            (activeAxis || hoveredAxis) === 'X' ? '#ff0000' :
            (activeAxis || hoveredAxis) === 'Y' ? '#00ff00' :
            (activeAxis || hoveredAxis) === 'Z' ? '#0000ff' :
            (activeAxis || hoveredAxis) === 'XY' || (activeAxis || hoveredAxis) === 'YZ' || (activeAxis || hoveredAxis) === 'XZ' ? '#ffeb3b' :
            transformMode === 'translate' ? '#4a90e2' :
            transformMode === 'rotate' ? '#ff6b6b' :
            '#50c878'
          }
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.02}
          outlineColor="#ffffff"
          scale={[1/scale.x, 1/scale.y, 1/scale.z]}
        >
          {transformMode === 'translate' ? '이동 (T)' :
           transformMode === 'rotate' ?
             (isRotating ? `회전 중: ${Math.round(currentRotationRef.current * 180 / Math.PI)}°` : '회전 (R) - 링 드래그') :
           '크기 (S)'}
          {transformMode !== 'rotate' && (activeAxis || hoveredAxis) && ` - ${activeAxis || hoveredAxis}${(activeAxis || hoveredAxis).length > 1 ? ' 평면' : '축'}${activeAxis ? ' [드래그 중]' : ' [hover]'}`}
        </Text>
      )}

      {/* 커스텀 회전 핸들 - 회전 모드에서만 표시, 바닥에 배치 */}
      {isSelected && transformMode === 'rotate' && (() => {
        // 리소스 크기 기반 링 반경 계산
        const resourceWidth = geometry.args[0] * scale.x;
        const resourceDepth = geometry.args[2] * scale.z;
        const ringRadius = Math.max(resourceWidth, resourceDepth) * 0.6 + 0.2;
        const ringColor = isRotating ? '#ffaa00' : (rotationRingHovered ? '#00cc00' : '#44ff44');
        const ringOpacity = isRotating ? 1.0 : (rotationRingHovered ? 0.95 : 0.85);
        return (
          <>
            {/* 회전 링 - 바닥에 배치, 두꺼운 링 */}
            <mesh
              position={[0, 0.02, 0]}
              rotation={[-Math.PI / 2, 0, 0]}
              onPointerDown={handleRotationMouseDown}
              onPointerOver={() => setRotationRingHovered(true)}
              onPointerOut={() => setRotationRingHovered(false)}
            >
              <ringGeometry args={[ringRadius, ringRadius + 0.25, 64]} />
              <meshBasicMaterial color={ringColor} transparent opacity={ringOpacity} side={2} />
            </mesh>
            {/* 회전 중심 표시 마커 */}
            <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
              <circleGeometry args={[0.12, 32]} />
              <meshBasicMaterial color={ringColor} transparent opacity={ringOpacity} side={2} />
            </mesh>
          </>
        );
      })()}
      </group>

      {/* TransformControls - 이동/크기 모드에서만 표시 (회전은 커스텀 핸들 사용) */}
      {isSelected && transformMode !== 'rotate' && (
        <TransformControls
          ref={transformControlsRef}
          object={groupRef}
          mode={transformMode}
          space="world"
          size={1.2}
          showX={true}
          showY={transformMode === 'scale'}
          showZ={true}
          onObjectChange={handleObjectChange}
          onMouseDown={(e) => {
            handleTransformStart();
            onTransformMouseDown(e);
          }}
          onMouseUp={(e) => {
            handleTransformEnd();
            onTransformMouseUp(e);
          }}
        />
      )}
    </>
  );
}

// Process Flow Arrow Component with arrowhead
function ProcessFlowArrow({ fromProcess, toProcess }) {
  const { bopData } = useBopStore();

  // 각 공정의 바운딩 박스 계산 (ProcessBox와 동일한 로직)
  const calculateBoundingBox = (process) => {
    const resources = (bopData?.resource_assignments || []).filter(
      r => r.process_id === process.process_id && r.parallel_index === process.parallel_index
    );

    if (resources.length === 0) {
      return { width: 0.5, depth: 0.5, centerX: 0, centerZ: 0 };
    }

    let minX = Infinity;
    let maxX = -Infinity;
    let minZ = Infinity;
    let maxZ = -Infinity;

    resources.forEach(resource => {
      const relLoc = resource.relative_location || { x: 0, y: 0, z: 0 };
      const x = relLoc.x;
      const z = relLoc.z;

      // 리소스 타입별 실제 크기 가져오기
      let equipmentType = null;
      if (resource.resource_type === 'equipment' && bopData?.equipments) {
        const equipmentData = bopData.equipments.find(e => e.equipment_id === resource.resource_id);
        equipmentType = equipmentData?.type;
      }
      const resourceSize = resource.computed_size || getResourceSize(resource.resource_type, equipmentType);

      // 실제 리소스 크기로 바운더리 계산
      minX = Math.min(minX, x - resourceSize.width / 2);
      maxX = Math.max(maxX, x + resourceSize.width / 2);
      minZ = Math.min(minZ, z - resourceSize.depth / 2);
      maxZ = Math.max(maxZ, z + resourceSize.depth / 2);
    });

    const width = (maxX - minX) + 0.2;
    const depth = (maxZ - minZ) + 0.2;
    const centerX = (minX + maxX) / 2;
    const centerZ = (minZ + maxZ) / 2;

    return { width, depth, centerX, centerZ };
  };

  const fromBBox = calculateBoundingBox(fromProcess);
  const toBBox = calculateBoundingBox(toProcess);

  // 공정 회전 고려
  const fromRotation = fromProcess.rotation_y || 0;
  const toRotation = toProcess.rotation_y || 0;

  // From 공정의 출구점 (로컬 좌표계에서 오른쪽 끝)
  const fromLocalX = fromBBox.centerX + (fromBBox.width / 2);
  const fromLocalZ = fromBBox.centerZ;

  // 회전 변환 적용 (Y축 회전, 부호 반대)
  const fromRotatedX = fromLocalX * Math.cos(fromRotation) + fromLocalZ * Math.sin(fromRotation);
  const fromRotatedZ = -fromLocalX * Math.sin(fromRotation) + fromLocalZ * Math.cos(fromRotation);

  // 월드 좌표로 변환
  const startX = fromProcess.location.x + fromRotatedX;
  const startZ = fromProcess.location.z + fromRotatedZ;

  // To 공정의 입구점 (로컬 좌표계에서 왼쪽 끝)
  const toLocalX = toBBox.centerX - (toBBox.width / 2);
  const toLocalZ = toBBox.centerZ;

  // 회전 변환 적용 (Y축 회전, 부호 반대)
  const toRotatedX = toLocalX * Math.cos(toRotation) + toLocalZ * Math.sin(toRotation);
  const toRotatedZ = -toLocalX * Math.sin(toRotation) + toLocalZ * Math.cos(toRotation);

  // 월드 좌표로 변환
  const endX = toProcess.location.x + toRotatedX;
  const endZ = toProcess.location.z + toRotatedZ;

  const points = [
    [startX, 1, startZ],
    [endX, 1, endZ]
  ];

  // Calculate arrow direction for the arrowhead
  const dx = endX - startX;
  const dz = endZ - startZ;
  const angle = Math.atan2(dz, dx); // XZ 평면에서의 각도 (X축 기준)

  return (
    <group>
      {/* Arrow line */}
      <Line
        points={points}
        color="#888888"
        lineWidth={2}
        dashed={false}
      />

      {/* Arrowhead (cone) pointing in arrow direction */}
      <mesh
        position={[endX, 1, endZ]}
        rotation={[0, -angle, -Math.PI / 2]}  // Z축으로 -90도(+X 방향으로 눕힘), Y축으로 -angle(방향 조정)
      >
        <coneGeometry args={[0.15, 0.4, 8]} />
        <meshStandardMaterial color="#888888" />
      </mesh>
    </group>
  );
}

// Obstacle Box Component
function ObstacleBox({ obstacle, isSelected, onSelect, onTransformMouseDown, onTransformMouseUp, isDraggingTransformRef }) {
  const [hovered, setHovered] = useState(false);
  const [transformMode, setTransformMode] = useState('translate'); // 'translate', 'rotate'
  const [rotationRingHovered, setRotationRingHovered] = useState(false); // 회전 링 hover 상태
  const [isRotating, setIsRotating] = useState(false); // 회전 중 상태 (UI용)
  const { updateObstacle, obstacleCreationMode } = useBopStore();

  const groupRef = useRef();
  const transformControlsRef = useRef();

  // 커스텀 회전을 위한 refs
  const isRotatingRef = useRef(false);
  const rotationStartValueRef = useRef(0);
  const mouseStartXRef = useRef(0);
  const currentRotationRef = useRef(0);

  const pos = obstacle.position || { x: 0, y: 0, z: 0 };
  const size = obstacle.size || { width: 1, height: 1, depth: 1 };
  const rotationY = obstacle.rotation_y || 0;

  // Color based on obstacle type
  const getColor = () => {
    if (isSelected) return '#ffeb3b';
    if (hovered) return '#ffd54f';
    switch (obstacle.type) {
      case 'fence': return '#ff9800';
      case 'zone': return '#f44336';
      case 'pillar': return '#795548';
      case 'wall': return '#607d8b';
      default: return '#ff9800';
    }
  };

  // Opacity based on type (zones are more transparent)
  const getOpacity = () => {
    if (obstacle.type === 'zone') return 0.4;
    return 0.8;
  };

  // Transform change handler (이동 모드에서만 사용)
  const handleObjectChange = () => {
    if (!groupRef.current) return;

    if (transformMode === 'translate') {
      groupRef.current.position.y = 0; // Keep on floor
    }
  };

  // Transform end handler (이동 모드에서만 사용)
  const handleTransformEnd = () => {
    if (!groupRef.current) return;

    if (transformMode === 'translate') {
      const newPosition = {
        x: groupRef.current.position.x,
        y: 0,
        z: groupRef.current.position.z
      };
      updateObstacle(obstacle.obstacle_id, { position: newPosition });
    }
  };

  // 커스텀 회전 핸들러 - 마우스 드래그로 직접 회전 계산 (5도 스냅 적용)
  const handleRotationMouseDown = useCallback((e) => {
    if (transformMode !== 'rotate') return;
    e.stopPropagation();

    isRotatingRef.current = true;
    setIsRotating(true);
    rotationStartValueRef.current = rotationY;
    currentRotationRef.current = rotationY;
    mouseStartXRef.current = e.clientX;

    const handleMouseMove = (moveEvent) => {
      if (!isRotatingRef.current) return;

      const deltaX = moveEvent.clientX - mouseStartXRef.current;
      // 마우스 200px 이동 = 180도 회전
      const rotationDelta = (deltaX / 200) * Math.PI;
      // 5도 스냅 적용
      currentRotationRef.current = snapRotation(rotationStartValueRef.current + rotationDelta);

      if (groupRef.current) {
        groupRef.current.rotation.y = currentRotationRef.current;
      }
    };

    const handleMouseUp = () => {
      if (isRotatingRef.current) {
        const finalRotation = normalizeAngle(currentRotationRef.current);
        updateObstacle(obstacle.obstacle_id, { rotation_y: finalRotation });
        isRotatingRef.current = false;
        setIsRotating(false);
      }
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      onTransformMouseUp?.();
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    onTransformMouseDown?.();
  }, [transformMode, rotationY, obstacle.obstacle_id, updateObstacle, onTransformMouseDown, onTransformMouseUp]);

  // 커스텀 회전 중 회전값 유지
  useFrame(() => {
    if (isRotatingRef.current && groupRef.current) {
      groupRef.current.rotation.y = currentRotationRef.current;
    }
  });

  // Keyboard shortcuts
  useEffect(() => {
    if (!isSelected) return;

    const handleKeyDown = (e) => {
      if (e.key === 't' || e.key === 'T') {
        setTransformMode('translate');
      } else if (e.key === 'r' || e.key === 'R') {
        setTransformMode('rotate');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSelected]);

  return (
    <>
      <group
        ref={groupRef}
        position={[pos.x, 0, pos.z]}
        rotation={[0, rotationY, 0]}
      >
        {/* Obstacle mesh */}
        <mesh
          position={[0, size.height / 2, 0]}
          onPointerOver={() => {
            if (!isDraggingTransformRef?.current && !obstacleCreationMode) setHovered(true);
          }}
          onPointerOut={() => {
            // 항상 hovered를 해제 (드래그 중에도)
            setHovered(false);
          }}
          onClick={(e) => {
            if (!isDraggingTransformRef?.current && !obstacleCreationMode) {
              e.stopPropagation();
              onSelect();
            }
          }}
        >
          <boxGeometry args={[size.width, size.height, size.depth]} />
          <meshStandardMaterial
            color={getColor()}
            transparent={true}
            opacity={getOpacity()}
            emissive={isSelected ? '#ffeb3b' : '#000000'}
            emissiveIntensity={isSelected ? 0.5 : 0}
          />
        </mesh>

        {/* Obstacle label */}
        {(isSelected || hovered) && (
          <Text
            position={[0, size.height + 0.3, 0]}
            fontSize={0.2}
            color="#333"
            anchorX="center"
            anchorY="middle"
          >
            {obstacle.name}
          </Text>
        )}

        {/* Transform mode indicator */}
        {isSelected && (
          <Text
            position={[0, size.height + 0.6, 0]}
            fontSize={0.18}
            color={transformMode === 'translate' ? '#4a90e2' : (isRotating ? '#ffaa00' : '#ff6b6b')}
            anchorX="center"
            anchorY="middle"
            outlineWidth={0.02}
            outlineColor="#ffffff"
          >
            {transformMode === 'translate' ? '이동 (T)' :
             isRotating ? `회전 중: ${Math.round(currentRotationRef.current * 180 / Math.PI)}°` :
             '회전 (R) - 링 드래그'}
          </Text>
        )}

        {/* 커스텀 회전 핸들 - 회전 모드에서만 표시, 바닥에 배치 */}
        {isSelected && transformMode === 'rotate' && (() => {
          const ringRadius = Math.max(size.width, size.depth) * 0.6 + 0.2;
          const ringColor = isRotating ? '#ffaa00' : (rotationRingHovered ? '#00cc00' : '#44ff44');
          const ringOpacity = isRotating ? 1.0 : (rotationRingHovered ? 0.95 : 0.85);
          return (
            <>
              {/* 회전 링 - 바닥에 배치, 두꺼운 링 */}
              <mesh
                position={[0, 0.02, 0]}
                rotation={[-Math.PI / 2, 0, 0]}
                onPointerDown={handleRotationMouseDown}
                onPointerOver={() => setRotationRingHovered(true)}
                onPointerOut={() => setRotationRingHovered(false)}
              >
                <ringGeometry args={[ringRadius, ringRadius + 0.25, 64]} />
                <meshBasicMaterial color={ringColor} transparent opacity={ringOpacity} side={2} />
              </mesh>
              {/* 회전 중심 표시 마커 */}
              <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <circleGeometry args={[0.12, 32]} />
                <meshBasicMaterial color={ringColor} transparent opacity={ringOpacity} side={2} />
              </mesh>
            </>
          );
        })()}
      </group>

      {/* TransformControls - 이동 모드에서만 표시 */}
      {isSelected && transformMode === 'translate' && (
        <TransformControls
          ref={transformControlsRef}
          object={groupRef}
          mode="translate"
          space="world"
          size={1.2}
          showX={true}
          showY={false}
          showZ={true}
          onObjectChange={handleObjectChange}
          onMouseDown={(e) => {
            onTransformMouseDown(e);
          }}
          onMouseUp={(e) => {
            handleTransformEnd();
            onTransformMouseUp(e);
          }}
        />
      )}
    </>
  );
}

// Obstacle Preview Component (for Two-Click creation)
function ObstaclePreview({ firstClick, currentPointer, obstacleType }) {
  if (!firstClick || !currentPointer) return null;

  const centerX = (firstClick.x + currentPointer.x) / 2;
  const centerZ = (firstClick.z + currentPointer.z) / 2;
  const width = Math.abs(currentPointer.x - firstClick.x);
  const depth = Math.abs(currentPointer.z - firstClick.z);

  // Height based on obstacle type
  const getHeight = () => {
    switch (obstacleType) {
      case 'fence': return 1.5;
      case 'zone': return 0.05;
      case 'pillar': return 3;
      case 'wall': return 2.5;
      default: return 2;
    }
  };

  // Color based on obstacle type
  const getColor = () => {
    switch (obstacleType) {
      case 'fence': return '#ff9800';
      case 'zone': return '#f44336';
      case 'pillar': return '#795548';
      case 'wall': return '#607d8b';
      default: return '#ff9800';
    }
  };

  const height = getHeight();
  const color = getColor();

  return (
    <mesh position={[centerX, height / 2, centerZ]}>
      <boxGeometry args={[Math.max(0.5, width), height, Math.max(0.5, depth)]} />
      <meshStandardMaterial
        color={color}
        transparent={true}
        opacity={0.4}
        wireframe={false}
      />
    </mesh>
  );
}

// Background plane for click detection
function BackgroundPlane({ onBackgroundClick, onPointerMove, gridSize, centerX, centerZ }) {
  return (
    <mesh
      position={[centerX, -0.01, centerZ]}
      rotation={[-Math.PI / 2, 0, 0]}
      onClick={onBackgroundClick}
      onPointerMove={onPointerMove}
    >
      <planeGeometry args={[gridSize * 2, gridSize * 2]} />
      <meshBasicMaterial transparent opacity={0} />
    </mesh>
  );
}

function Scene() {
  const {
    bopData,
    selectedProcessKey,
    selectedResourceKey,
    selectedObstacleId,
    setSelectedProcess,
    setSelectedObstacle,
    clearSelection,
    getEquipmentById,
    getWorkerById,
    getMaterialById,
    obstacleCreationMode,
    obstacleCreationFirstClick,
    setObstacleCreationFirstClick,
    createObstacleFromTwoClicks,
    pendingObstacleType
  } = useBopStore();

  const [currentPointer, setCurrentPointer] = useState(null);

  const orbitControlsRef = useRef();
  const isDraggingTransform = useRef(false);

  // 빈 공간 클릭 시 선택 해제 또는 장애물 생성
  const handleBackgroundClick = useCallback((e) => {
    e.stopPropagation();

    // Obstacle creation mode: Two-Click logic
    if (obstacleCreationMode) {
      const point = { x: e.point.x, z: e.point.z };

      if (!obstacleCreationFirstClick) {
        // First click: save the starting corner
        setObstacleCreationFirstClick(point);
      } else {
        // Second click: create obstacle
        createObstacleFromTwoClicks(obstacleCreationFirstClick, point);
      }
      return;
    }

    clearSelection();
  }, [clearSelection, obstacleCreationMode, obstacleCreationFirstClick, setObstacleCreationFirstClick, createObstacleFromTwoClicks]);

  // Pointer move handler for obstacle preview
  const handlePointerMove = useCallback((e) => {
    if (obstacleCreationMode && obstacleCreationFirstClick) {
      setCurrentPointer({ x: e.point.x, z: e.point.z });
    }
  }, [obstacleCreationMode, obstacleCreationFirstClick]);

  // TransformControls 드래그 시작/종료 시 OrbitControls 제어
  const handleTransformMouseDown = useCallback(() => {
    isDraggingTransform.current = true;
    if (orbitControlsRef.current) {
      orbitControlsRef.current.enabled = false;
    }
  }, []);

  const handleTransformMouseUp = useCallback(() => {
    if (orbitControlsRef.current) {
      // 즉시 활성화하지 않고 약간의 지연 후 활성화
      setTimeout(() => {
        if (orbitControlsRef.current) {
          orbitControlsRef.current.enabled = true;
        }
      }, 200);
    }
    // 드래그 종료 후 짧은 시간 동안 hover 이벤트 무시
    setTimeout(() => {
      isDraggingTransform.current = false;
    }, 300);
  }, []);

  // 동적 그리드 크기 및 중심 계산 - 전체 콘텐츠 바운딩 박스 + 마진
  const { size: gridSize, width: gridWidth, depth: gridDepth, centerX: gridCenterX, centerZ: gridCenterZ } = useMemo(() => {
    const MARGIN_X = 3; // X축 마진 (미터)
    const MARGIN_Z = 3; // Z축 마진 (미터)
    const MIN_SIZE = 30;

    const processDetails = bopData?.process_details || [];
    if (!bopData || processDetails.length === 0) {
      return { size: MIN_SIZE, width: MIN_SIZE, depth: MIN_SIZE, centerX: 0, centerZ: 0 };
    }

    // 전체 콘텐츠의 바운딩 박스 계산
    let maxX = -Infinity;
    let minX = Infinity;
    let maxZ = -Infinity;
    let minZ = Infinity;

    processDetails.forEach(detail => {
      const loc = detail.location;
      maxX = Math.max(maxX, loc.x + 2);
      minX = Math.min(minX, loc.x - 2);
      maxZ = Math.max(maxZ, loc.z + 2);
      minZ = Math.min(minZ, loc.z - 2);
    });

    (bopData.obstacles || []).forEach(obstacle => {
      const pos = obstacle.position || { x: 0, z: 0 };
      const size = obstacle.size || { width: 1, depth: 1 };
      maxX = Math.max(maxX, pos.x + size.width / 2);
      minX = Math.min(minX, pos.x - size.width / 2);
      maxZ = Math.max(maxZ, pos.z + size.depth / 2);
      minZ = Math.min(minZ, pos.z - size.depth / 2);
    });

    // 바운딩 박스가 유효하지 않으면 기본값
    if (!isFinite(maxX) || !isFinite(minX)) {
      return { size: MIN_SIZE, width: MIN_SIZE, depth: MIN_SIZE, centerX: 0, centerZ: 0 };
    }

    // 마진 추가 (X, Z 별도)
    minX -= MARGIN_X;
    maxX += MARGIN_X;
    minZ -= MARGIN_Z;
    maxZ += MARGIN_Z;

    // 중심과 크기 계산
    const centerX = (maxX + minX) / 2;
    const centerZ = (maxZ + minZ) / 2;
    const width = Math.max(MIN_SIZE, Math.ceil(maxX - minX));
    const depth = Math.max(MIN_SIZE, Math.ceil(maxZ - minZ));
    const size = Math.max(width, depth); // 카메라 거리 등에 사용

    return { size, width, depth, centerX, centerZ };
  }, [bopData]);

  // Render processes and their resources
  const renderedElements = useMemo(() => {
    const elements = [];
    const arrows = [];

    if (!bopData || !bopData.process_details) {
      return [];
    }

    const processDetails = bopData.process_details || [];
    const resourceAssignments = bopData.resource_assignments || [];
    const routingProcesses = bopData.processes || [];

    // Render each process detail (each is a renderable instance)
    processDetails.forEach((detail) => {
      const key = `process-${detail.process_id}:${detail.parallel_index}`;
      const processKey = `${detail.process_id}:${detail.parallel_index}`;
      const isSelected = selectedProcessKey === processKey;

      // Process box
      elements.push(
        <ProcessBox
          key={key}
          process={detail}
          isSelected={isSelected}
          onSelect={() => setSelectedProcess(processKey)}
          onTransformMouseDown={handleTransformMouseDown}
          onTransformMouseUp={handleTransformMouseUp}
          isDraggingTransformRef={isDraggingTransform}
        />
      );

      // Resources for this process detail from resource_assignments
      const resources = resourceAssignments.filter(
        r => r.process_id === detail.process_id && r.parallel_index === detail.parallel_index
      );

      // 공정의 실제 중심 좌표 계산 (ProcessBox와 동일한 로직)
      let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
      resources.forEach(resource => {
        const relLoc = resource.relative_location || { x: 0, y: 0, z: 0 };
        const x = relLoc.x;
        const z = relLoc.z;

        let equipmentType = null;
        if (resource.resource_type === 'equipment' && bopData?.equipments) {
          const equipmentData = bopData.equipments.find(e => e.equipment_id === resource.resource_id);
          equipmentType = equipmentData?.type;
        }
        const resourceSize = resource.computed_size || getResourceSize(resource.resource_type, equipmentType);

        minX = Math.min(minX, x - resourceSize.width / 2);
        maxX = Math.max(maxX, x + resourceSize.width / 2);
        minZ = Math.min(minZ, z - resourceSize.depth / 2);
        maxZ = Math.max(maxZ, z + resourceSize.depth / 2);
      });

      const centerX = resources.length > 0 ? (minX + maxX) / 2 : 0;
      const centerZ = resources.length > 0 ? (minZ + maxZ) / 2 : 0;

      // Bounding center (회전 중심 오프셋)
      const boundingCenter = { x: centerX, z: centerZ };

      // Render resources
      resources.forEach((resource, resIdx) => {
        const resKey = `${key}-resource-${resIdx}`;

        let equipmentData = null;
        let workerData = null;
        let materialData = null;

        if (resource.resource_type === 'equipment') {
          equipmentData = getEquipmentById(resource.resource_id);
        } else if (resource.resource_type === 'worker') {
          workerData = getWorkerById(resource.resource_id);
        } else if (resource.resource_type === 'material') {
          materialData = getMaterialById(resource.resource_id);
        }

        elements.push(
          <ResourceMarker
            key={resKey}
            resource={resource}
            processLocation={detail.location}
            processBoundingCenter={boundingCenter}
            processRotation={detail.rotation_y || 0}
            parallelIndex={detail.parallel_index}
            processId={detail.process_id}
            equipmentData={equipmentData}
            workerData={workerData}
            materialData={materialData}
            resourceIndex={resIdx}
            totalResources={resources.length}
            onTransformMouseDown={handleTransformMouseDown}
            onTransformMouseUp={handleTransformMouseUp}
            isDraggingTransformRef={isDraggingTransform}
          />
        );
      });
    });

    // Process flow arrows: use routing processes for predecessor/successor info,
    // and process_details for location lookup
    routingProcesses.forEach((routingProcess) => {
      if (Array.isArray(routingProcess.successor_ids) && routingProcess.successor_ids.length > 0) {
        routingProcess.successor_ids.forEach(successorId => {
          if (!successorId) return;

          // Find all detail instances for the source process
          const fromDetails = processDetails.filter(d => d.process_id === routingProcess.process_id);
          // Find all detail instances for the successor process
          const toDetails = processDetails.filter(d => d.process_id === successorId);

          // Draw arrows between all instances of from and to
          fromDetails.forEach(fromDetail => {
            toDetails.forEach(toDetail => {
              arrows.push(
                <ProcessFlowArrow
                  key={`arrow-${fromDetail.process_id}:${fromDetail.parallel_index}-${toDetail.process_id}:${toDetail.parallel_index}`}
                  fromProcess={fromDetail}
                  toProcess={toDetail}
                />
              );
            });
          });
        });
      }
    });

    // Render obstacles
    const obstacles = bopData.obstacles || [];
    obstacles.forEach((obstacle) => {
      const obstacleKey = `obstacle-${obstacle.obstacle_id}`;
      const isObstacleSelected = selectedObstacleId === obstacle.obstacle_id;

      elements.push(
        <ObstacleBox
          key={obstacleKey}
          obstacle={obstacle}
          isSelected={isObstacleSelected}
          onSelect={() => setSelectedObstacle(obstacle.obstacle_id)}
          onTransformMouseDown={handleTransformMouseDown}
          onTransformMouseUp={handleTransformMouseUp}
          isDraggingTransformRef={isDraggingTransform}
        />
      );
    });

    return [...elements, ...arrows];
  }, [bopData, selectedProcessKey, selectedResourceKey, selectedObstacleId, setSelectedProcess, setSelectedObstacle, getEquipmentById, getWorkerById, getMaterialById, handleTransformMouseDown, handleTransformMouseUp]);

  // Empty state - no data (only show when both process_details AND obstacles are empty AND not in creation mode)
  const hasProcesses = bopData && bopData.process_details && bopData.process_details.length > 0;
  const hasObstacles = bopData && bopData.obstacles && bopData.obstacles.length > 0;

  if (!bopData || (!hasProcesses && !hasObstacles && !obstacleCreationMode)) {
    return (
      <>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <Grid
          position={[0, 0, 0]}
          args={[20, 20]}
          cellSize={1}
          cellColor="#dddddd"
          sectionColor="#aaaaaa"
        />
        <Text position={[0, 1, 0]} fontSize={0.5} color="#999">
          No BOP Data
        </Text>
        <OrbitControls />
      </>
    );
  }

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 10, 5]} intensity={0.8} />
      <directionalLight position={[-10, 10, -5]} intensity={0.4} />

      {/* Background plane for click detection */}
      <BackgroundPlane
        onBackgroundClick={handleBackgroundClick}
        onPointerMove={handlePointerMove}
        gridSize={gridSize}
        centerX={gridCenterX}
        centerZ={gridCenterZ}
      />

      {/* Obstacle creation preview */}
      {obstacleCreationMode && obstacleCreationFirstClick && (
        <ObstaclePreview
          firstClick={obstacleCreationFirstClick}
          currentPointer={currentPointer}
          obstacleType={pendingObstacleType}
        />
      )}

      {/* Obstacle creation mode indicator */}
      {obstacleCreationMode && (
        <group position={[gridCenterX, 5, gridCenterZ]}>
          <Text
            position={[0, 0.3, 0]}
            fontSize={0.3}
            color="#ff9800"
            anchorX="center"
            anchorY="middle"
            outlineWidth={0.02}
            outlineColor="#ffffff"
          >
            {pendingObstacleType === 'fence' ? '🚧 펜스' :
             pendingObstacleType === 'zone' ? '⚠️ 구역' :
             pendingObstacleType === 'pillar' ? '🏛️ 기둥' :
             pendingObstacleType === 'wall' ? '🧱 벽' : '장애물'} 생성 모드
          </Text>
          <Text
            position={[0, -0.2, 0]}
            fontSize={0.35}
            color="#4caf50"
            anchorX="center"
            anchorY="middle"
            outlineWidth={0.03}
            outlineColor="#ffffff"
          >
            {obstacleCreationFirstClick
              ? '두 번째 꼭지점을 클릭하세요'
              : '첫 번째 꼭지점을 클릭하세요'}
          </Text>
        </group>
      )}

      {/* Grid - 객체들의 중심에 배치 */}
      <Grid
        position={[gridCenterX, 0, gridCenterZ]}
        args={[gridWidth, gridDepth]}
        cellSize={1}
        cellColor="#dddddd"
        sectionColor="#aaaaaa"
        sectionThickness={1}
        fadeDistance={gridSize * 0.8}
        fadeStrength={1}
      />

      {/* Processes and Resources */}
      {renderedElements}

      {/* Axis Helper for debugging
      <axesHelper args={[10]} />
      <Text position={[5, 0, 0]} fontSize={0.5} color="red">+X</Text>
      <Text position={[0, 5, 0]} fontSize={0.5} color="green">+Y</Text>
      <Text position={[0, 0, 5]} fontSize={0.5} color="blue">+Z</Text>
      */}

      {/* Legend - positioned near the first process */}
      <group position={[-3, 0, -5]}>
        <Text position={[0, 3.2, 0]} fontSize={0.25} color="#333" anchorX="left">
          구성요소:
        </Text>

        {/* Robot */}
        <mesh position={[0, 2.5, 0]}>
          <cylinderGeometry args={[0.15, 0.15, 0.6, 8]} />
          <meshStandardMaterial color="#4a90e2" />
        </mesh>
        <Text position={[0.5, 2.5, 0]} fontSize={0.15} color="#333" anchorX="left">
          Robot
        </Text>

        {/* Machine */}
        <mesh position={[0, 2.0, 0]}>
          <boxGeometry args={[0.3, 0.4, 0.3]} />
          <meshStandardMaterial color="#ff6b6b" />
        </mesh>
        <Text position={[0.5, 2.0, 0]} fontSize={0.15} color="#333" anchorX="left">
          Machine
        </Text>

        {/* Manual Station */}
        <mesh position={[0, 1.5, 0]}>
          <boxGeometry args={[0.25, 0.3, 0.25]} />
          <meshStandardMaterial color="#50c878" />
        </mesh>
        <Text position={[0.5, 1.5, 0]} fontSize={0.15} color="#333" anchorX="left">
          Manual
        </Text>

        {/* Worker */}
        <mesh position={[0, 1.0, 0]}>
          <cylinderGeometry args={[0.1, 0.1, 0.5, 8]} />
          <meshStandardMaterial color="#50c878" />
        </mesh>
        <Text position={[0.5, 1.0, 0]} fontSize={0.15} color="#333" anchorX="left">
          Worker
        </Text>

        {/* Material */}
        <mesh position={[0, 0.5, 0]}>
          <boxGeometry args={[0.15, 0.1, 0.15]} />
          <meshStandardMaterial color="#ffa500" />
        </mesh>
        <Text position={[0.5, 0.5, 0]} fontSize={0.15} color="#333" anchorX="left">
          Material
        </Text>

        {/* Obstacle */}
        <mesh position={[0, 0.1, 0]}>
          <boxGeometry args={[0.3, 0.15, 0.05]} />
          <meshStandardMaterial color="#ff9800" transparent opacity={0.8} />
        </mesh>
        <Text position={[0.5, 0.1, 0]} fontSize={0.15} color="#333" anchorX="left">
          Obstacle
        </Text>
      </group>

      {/* Camera controls - 타겟 고정 (0, 0, 0) */}
      <OrbitControls
        ref={orbitControlsRef}
        target={[0, 0, 0]}
        enableDamping={false}
        minDistance={5}
        maxDistance={gridSize * 1.5}
      />
    </>
  );
}

function Viewer3D() {
  const { use3DModels, toggleUse3DModels, selectedResourceKey, customModels, setCustomModel, removeCustomModel, getSelectedResourceInfo, bopData } = useBopStore();
  const { t } = useTranslation();
  const [showModelPopup, setShowModelPopup] = useState(false);
  const fileInputRef = useRef(null);

  // Get display name for selected resource
  const getResourceDisplayName = () => {
    const info = getSelectedResourceInfo();
    if (!info) return '';
    const { resourceType, resourceId } = info;
    if (resourceType === 'equipment') {
      const eq = bopData?.equipments?.find(e => e.equipment_id === resourceId);
      return eq ? `${resourceId} (${eq.name})` : resourceId;
    } else if (resourceType === 'worker') {
      const wk = bopData?.workers?.find(w => w.worker_id === resourceId);
      return wk ? `${resourceId} (${wk.name})` : resourceId;
    } else if (resourceType === 'material') {
      const mt = bopData?.materials?.find(m => m.material_id === resourceId);
      return mt ? `${resourceId} (${mt.name})` : resourceId;
    }
    return resourceId;
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const info = getSelectedResourceInfo();
    if (!info) return;

    // Only .glb supported (self-contained binary; .gltf references external files that can't be resolved from blob URLs)
    if (!file.name.toLowerCase().endsWith('.glb')) {
      alert(t('v3d.glbOnly'));
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    const blobUrl = URL.createObjectURL(file);
    setCustomModel(info.resourceType, info.resourceId, blobUrl);
    setShowModelPopup(false);
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleResetModel = () => {
    const info = getSelectedResourceInfo();
    if (!info) return;
    removeCustomModel(info.resourceType, info.resourceId);
    setShowModelPopup(false);
  };

  const selectedInfo = getSelectedResourceInfo();
  const hasCustomModel = selectedInfo && customModels?.[`${selectedInfo.resourceType}:${selectedInfo.resourceId}`];

  return (
    <div style={{ width: '100%', height: '100%', backgroundColor: '#f5f5f5', position: 'relative' }}>
      <Canvas camera={{ position: [15, 10, 15], fov: 50 }}>
        <Suspense fallback={null}>
          <Scene />
        </Suspense>
      </Canvas>

      {/* 3D 모델 토글 버튼 */}
      <div style={{ position: 'absolute', top: 10, right: 10, display: 'flex', gap: 6 }}>
        {use3DModels && selectedResourceKey && (
          <button
            onClick={() => setShowModelPopup(true)}
            style={{
              padding: '8px 12px',
              backgroundColor: '#e67e22',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              fontSize: 12,
              cursor: 'pointer',
              boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
            }}
          >
            {t('v3d.editModel')}
          </button>
        )}
        <button
          onClick={toggleUse3DModels}
          style={{
            padding: '8px 12px',
            backgroundColor: use3DModels ? '#4a90e2' : '#666',
            color: 'white',
            border: 'none',
            borderRadius: 4,
            fontSize: 12,
            cursor: 'pointer',
            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
          }}
        >
          {use3DModels ? t('v3d.modelOn') : t('v3d.modelOff')}
        </button>
      </div>

      {/* 3D 객체 수정 모달 */}
      {showModelPopup && (
        <div style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 100,
        }}>
          <div
            onClick={() => setShowModelPopup(false)}
            style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.3)' }}
          />
          <div style={{
            position: 'relative',
            backgroundColor: 'white',
            borderRadius: 8,
            padding: '20px 24px',
            minWidth: 300,
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            zIndex: 101,
          }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontWeight: 'bold', fontSize: 15 }}>{t('v3d.editModelTitle')}</span>
              <button
                onClick={() => setShowModelPopup(false)}
                style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: '#666', padding: '0 4px' }}
              >
                ✕
              </button>
            </div>

            {/* Resource label */}
            <div style={{ fontSize: 13, color: '#555', marginBottom: 16 }}>
              {t('v3d.resourceLabel', { name: getResourceDisplayName() })}
            </div>

            {/* Supported formats */}
            <div style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>
              {t('v3d.supportedFormats')}
            </div>

            {/* File upload */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".glb"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                width: '100%',
                padding: '10px 16px',
                backgroundColor: '#4a90e2',
                color: 'white',
                border: 'none',
                borderRadius: 4,
                fontSize: 13,
                cursor: 'pointer',
                marginBottom: 10,
              }}
            >
              {t('v3d.selectFile')}
            </button>

            {/* Reset button */}
            {hasCustomModel && (
              <button
                onClick={handleResetModel}
                style={{
                  width: '100%',
                  padding: '10px 16px',
                  backgroundColor: '#e0e0e0',
                  color: '#333',
                  border: 'none',
                  borderRadius: 4,
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                {t('v3d.resetModel')}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Viewer3D;
