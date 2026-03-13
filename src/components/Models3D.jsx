import { useLoader } from '@react-three/fiber';
import { useMemo, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';

// Custom hook to load GLTF with KHR_materials_pbrSpecularGlossiness extension support
function useGLTFWithExtensions(path) {
  const gltf = useLoader(GLTFLoader, path, (loader) => {
    // Register the deprecated extension manually
    loader.register((parser) => {
      return new GLTFMaterialsSpecularGlossinessExtension(parser);
    });
  });
  return gltf;
}

// Polyfill for KHR_materials_pbrSpecularGlossiness extension
class GLTFMaterialsSpecularGlossinessExtension {
  constructor(parser) {
    this.parser = parser;
    this.name = 'KHR_materials_pbrSpecularGlossiness';
  }

  getMaterialType() {
    return THREE.MeshStandardMaterial;
  }

  extendParams(materialParams, materialDef) {
    const extension = materialDef.extensions?.[this.name];
    if (!extension) return Promise.resolve();

    const pending = [];

    // diffuseFactor - base color
    if (extension.diffuseFactor !== undefined) {
      const color = extension.diffuseFactor;
      materialParams.color = new THREE.Color(color[0], color[1], color[2]);
      if (color[3] !== undefined && color[3] < 1) {
        materialParams.opacity = color[3];
        materialParams.transparent = true;
      }
    }

    // diffuseTexture - main color/albedo map
    if (extension.diffuseTexture !== undefined) {
      pending.push(
        this.parser.assignTexture(materialParams, 'map', extension.diffuseTexture)
      );
    }

    // specularGlossinessTexture
    if (extension.specularGlossinessTexture !== undefined) {
      pending.push(
        this.parser.assignTexture(materialParams, 'roughnessMap', extension.specularGlossinessTexture)
      );
    }

    // specularFactor - convert to metalness approximation
    if (extension.specularFactor !== undefined) {
      const spec = extension.specularFactor;
      const specIntensity = (spec[0] + spec[1] + spec[2]) / 3;
      materialParams.metalness = Math.min(specIntensity, 1.0);
    } else {
      materialParams.metalness = 0.0;
    }

    // glossinessFactor - convert to roughness (roughness = 1 - glossiness)
    if (extension.glossinessFactor !== undefined) {
      materialParams.roughness = 1.0 - extension.glossinessFactor;
    } else {
      materialParams.roughness = 1.0;
    }

    return Promise.all(pending);
  }
}

// Model paths (from public folder)
const MODEL_PATHS = {
  // New models (gltf format)
  robot: '/models/new/kuka_robot_arm/scene.gltf',
  conveyor: '/models/new/simple_rubber_conveyor/scene.gltf',
  box: '/models/new/larger_resource_box/scene.gltf',
  machine: '/models/new/ventis_machine/scene.gltf',
  worker: '/models/new/avatar_safety_uniform/scene.gltf',
  // Legacy model paths (fallback)
  robotLegacy: '/models/conveyor/robot-arm-a.glb',
  robotB: '/models/conveyor/robot-arm-b.glb',
  conveyorLegacy: '/models/conveyor/conveyor.glb',
  conveyorLong: '/models/conveyor/conveyor-long.glb',
  boxSmall: '/models/conveyor/box-small.glb',
  boxLarge: '/models/conveyor/box-large.glb',
  scanner: '/models/conveyor/scanner-high.glb',
  structure: '/models/conveyor/structure-medium.glb',
  // Character models (fbx)
  character: '/models/characters/characterMedium.fbx',
};

// Character skin textures
const SKIN_PATHS = {
  criminal: '/models/characters/criminalMaleA.png',
  cyborg: '/models/characters/cyborgFemaleA.png',
  skaterFemale: '/models/characters/skaterFemaleA.png',
  skaterMale: '/models/characters/skaterMaleA.png',
};

// Preload function for models with extension support
function preloadGLTF(path) {
  useLoader.preload(GLTFLoader, path, (loader) => {
    loader.register((parser) => {
      return new GLTFMaterialsSpecularGlossinessExtension(parser);
    });
  });
}

// Preload GLTF/GLB models
Object.entries(MODEL_PATHS).forEach(([key, path]) => {
  if (path.endsWith('.glb') || path.endsWith('.gltf')) {
    preloadGLTF(path);
  }
});

// Robot Arm Model Component (KUKA Robot)
// Target size from getResourceSize: { width: 1.4, height: 1.7, depth: 0.6 }
export function RobotModel({ color = '#4a90e2', scale = 1, highlighted = false, ...props }) {
  const { scene } = useGLTFWithExtensions(MODEL_PATHS.robot);
  const groupRef = useRef();

  const { clonedScene, scaleVec, offset } = useMemo(() => {
    // Deep clone using SkeletonUtils (preserves materials and textures)
    const clone = SkeletonUtils.clone(scene);

    // Deep clone materials to prevent shared state between instances
    clone.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material = Array.isArray(child.material)
          ? child.material.map(m => m.clone())
          : child.material.clone();
      }
    });

    // Calculate original bounding box
    const box = new THREE.Box3().setFromObject(clone);
    const originalSize = new THREE.Vector3();
    box.getSize(originalSize);
    const center = new THREE.Vector3();
    box.getCenter(center);

    // Target size - match exactly with basic geometry
    const targetSize = { width: 1.4, height: 1.7, depth: 0.6 };

    // Scale each axis independently to match target size exactly
    const scaleX = targetSize.width / originalSize.x;
    const scaleY = targetSize.height / originalSize.y;
    const scaleZ = targetSize.depth / originalSize.z;

    // Calculate offset to center on X/Z and place bottom at y=0
    const xOffset = -center.x * scaleX;
    const yOffset = -box.min.y * scaleY;
    const zOffset = -center.z * scaleZ;

    return { clonedScene: clone, scaleVec: [scaleX, scaleY, scaleZ], offset: [xOffset, yOffset, zOffset] };
  }, [scene]);

  // Apply highlight effect
  useEffect(() => {
    if (clonedScene) {
      clonedScene.traverse((child) => {
        if (child.isMesh && child.material) {
          const mats = Array.isArray(child.material) ? child.material : [child.material];
          mats.forEach(mat => {
            mat.emissive = highlighted ? new THREE.Color('#ffeb3b') : new THREE.Color('#000000');
            mat.emissiveIntensity = highlighted ? 0.5 : 0;
            mat.needsUpdate = true;
          });
        }
      });
    }
  }, [clonedScene, highlighted]);

  return (
    <primitive
      ref={groupRef}
      object={clonedScene}
      scale={[scaleVec[0] * scale, scaleVec[1] * scale, scaleVec[2] * scale]}
      position={[offset[0] * scale, offset[1] * scale, offset[2] * scale]}
      {...props}
    />
  );
}

// Conveyor Model Component (Rubber Conveyor) - used for 'manual_station' type
// Target size from getResourceSize (manual_station): { width: 1.6, height: 1.0, depth: 0.8 }
// Note: Model is rotated 90° on Y axis, so width/depth are swapped in targetSize
export function ConveyorModel({ color = '#ff6b6b', scale = 1, highlighted = false, ...props }) {
  const { scene } = useGLTFWithExtensions(MODEL_PATHS.conveyor);
  const groupRef = useRef();

  const { clonedScene, scaleVec, offset } = useMemo(() => {
    // Deep clone using SkeletonUtils (preserves materials and textures)
    const clone = SkeletonUtils.clone(scene);

    // 간단한 색상 material로 교체 (텍스처 문제 디버깅용)
    clone.traverse((child) => {
      if (child.isMesh) {
        const isBelt = child.name.includes('Belt');
        child.material = new THREE.MeshStandardMaterial({
          color: isBelt ? 0x222222 : 0x4488cc, // 벨트는 검정, 프레임은 파랑
          metalness: isBelt ? 0.1 : 0.6,
          roughness: isBelt ? 0.8 : 0.4,
        });
      }
    });

    // Calculate original bounding box
    const box = new THREE.Box3().setFromObject(clone);
    const originalSize = new THREE.Vector3();
    box.getSize(originalSize);
    const center = new THREE.Vector3();
    box.getCenter(center);

    // Target size - swapped width/depth because model is rotated 90° on Y axis
    // Final result after rotation: width=1.6, height=1.0, depth=0.8
    const targetSize = { width: 0.8, height: 1.0, depth: 1.6 };

    // Scale each axis independently to match target size exactly
    const scaleX = targetSize.width / originalSize.x;
    const scaleY = targetSize.height / originalSize.y;
    const scaleZ = targetSize.depth / originalSize.z;

    // Calculate offset to center on X/Z and place bottom at y=0
    const xOffset = -center.x * scaleX;
    const yOffset = -box.min.y * scaleY;
    const zOffset = -center.z * scaleZ;

    return { clonedScene: clone, scaleVec: [scaleX, scaleY, scaleZ], offset: [xOffset, yOffset, zOffset] };
  }, [scene]);

  // Apply highlight effect
  useEffect(() => {
    if (clonedScene) {
      clonedScene.traverse((child) => {
        if (child.isMesh && child.material) {
          const mats = Array.isArray(child.material) ? child.material : [child.material];
          mats.forEach(mat => {
            mat.emissive = highlighted ? new THREE.Color('#ffeb3b') : new THREE.Color('#000000');
            mat.emissiveIntensity = highlighted ? 0.5 : 0;
            mat.needsUpdate = true;
          });
        }
      });
    }
  }, [clonedScene, highlighted]);

  return (
    <primitive
      ref={groupRef}
      object={clonedScene}
      scale={[scaleVec[0] * scale, scaleVec[1] * scale, scaleVec[2] * scale]}
      position={[offset[0] * scale, offset[1] * scale, offset[2] * scale]}
      rotation={[0, Math.PI / 2, 0]}
      {...props}
    />
  );
}

// Box/Material Model Component (Legacy Small Box - GLB)
// Target size from getResourceSize (material): { width: 0.4, height: 0.25, depth: 0.4 }
export function BoxModel({ color = '#ffa500', scale = 1, highlighted = false, ...props }) {
  const { scene } = useGLTFWithExtensions(MODEL_PATHS.boxSmall);
  const groupRef = useRef();

  const { clonedScene, scaleVec, offset } = useMemo(() => {
    // Deep clone using SkeletonUtils (preserves materials and textures)
    const clone = SkeletonUtils.clone(scene);

    // Deep clone materials to prevent shared state between instances
    clone.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material = Array.isArray(child.material)
          ? child.material.map(m => m.clone())
          : child.material.clone();
      }
    });

    // Calculate original bounding box
    const box = new THREE.Box3().setFromObject(clone);
    const originalSize = new THREE.Vector3();
    box.getSize(originalSize);
    const center = new THREE.Vector3();
    box.getCenter(center);

    // Target size - match exactly with basic geometry
    const targetSize = { width: 0.4, height: 0.25, depth: 0.4 };

    // Scale each axis independently to match target size exactly
    const scaleX = targetSize.width / originalSize.x;
    const scaleY = targetSize.height / originalSize.y;
    const scaleZ = targetSize.depth / originalSize.z;

    // Calculate offset to center on X/Z and place bottom at y=0
    const xOffset = -center.x * scaleX;
    const yOffset = -box.min.y * scaleY;
    const zOffset = -center.z * scaleZ;

    return { clonedScene: clone, scaleVec: [scaleX, scaleY, scaleZ], offset: [xOffset, yOffset, zOffset] };
  }, [scene]);

  // Apply highlight effect
  useEffect(() => {
    if (clonedScene) {
      clonedScene.traverse((child) => {
        if (child.isMesh && child.material) {
          const mats = Array.isArray(child.material) ? child.material : [child.material];
          mats.forEach(mat => {
            mat.emissive = highlighted ? new THREE.Color('#ffeb3b') : new THREE.Color('#000000');
            mat.emissiveIntensity = highlighted ? 0.5 : 0;
            mat.needsUpdate = true;
          });
        }
      });
    }
  }, [clonedScene, highlighted]);

  return (
    <primitive
      ref={groupRef}
      object={clonedScene}
      scale={[scaleVec[0] * scale, scaleVec[1] * scale, scaleVec[2] * scale]}
      position={[offset[0] * scale, offset[1] * scale, offset[2] * scale]}
      {...props}
    />
  );
}

// Machine Model Component (Ventis Laser Machine - for 'machine' type)
// Target size from getResourceSize (machine): { width: 2.1, height: 1.9, depth: 1.0 }
export function ScannerModel({ color = '#50c878', scale = 1, highlighted = false, ...props }) {
  const { scene } = useGLTFWithExtensions(MODEL_PATHS.machine);
  const groupRef = useRef();

  const { clonedScene, scaleVec, offset } = useMemo(() => {
    // Deep clone using SkeletonUtils (preserves materials and textures)
    const clone = SkeletonUtils.clone(scene);

    // Deep clone materials to prevent shared state between instances
    clone.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material = Array.isArray(child.material)
          ? child.material.map(m => m.clone())
          : child.material.clone();
      }
    });

    // Calculate original bounding box
    const box = new THREE.Box3().setFromObject(clone);
    const originalSize = new THREE.Vector3();
    box.getSize(originalSize);
    const center = new THREE.Vector3();
    box.getCenter(center);

    // Target size - match exactly with basic geometry
    const targetSize = { width: 2.1, height: 1.9, depth: 1.0 };

    // Scale each axis independently to match target size exactly
    const scaleX = targetSize.width / originalSize.x;
    const scaleY = targetSize.height / originalSize.y;
    const scaleZ = targetSize.depth / originalSize.z;

    // Calculate offset to center on X/Z and place bottom at y=0
    const xOffset = -center.x * scaleX;
    const yOffset = -box.min.y * scaleY;
    const zOffset = -center.z * scaleZ;

    return { clonedScene: clone, scaleVec: [scaleX, scaleY, scaleZ], offset: [xOffset, yOffset, zOffset] };
  }, [scene]);

  // Apply highlight effect
  useEffect(() => {
    if (clonedScene) {
      clonedScene.traverse((child) => {
        if (child.isMesh && child.material) {
          const mats = Array.isArray(child.material) ? child.material : [child.material];
          mats.forEach(mat => {
            mat.emissive = highlighted ? new THREE.Color('#ffeb3b') : new THREE.Color('#000000');
            mat.emissiveIntensity = highlighted ? 0.5 : 0;
            mat.needsUpdate = true;
          });
        }
      });
    }
  }, [clonedScene, highlighted]);

  return (
    <primitive
      ref={groupRef}
      object={clonedScene}
      scale={[scaleVec[0] * scale, scaleVec[1] * scale, scaleVec[2] * scale]}
      position={[offset[0] * scale, offset[1] * scale, offset[2] * scale]}
      {...props}
    />
  );
}

// Structure Model Component (for obstacles like pillars)
export function StructureModel({ color = '#795548', scale = 1, ...props }) {
  const { scene } = useGLTFWithExtensions(MODEL_PATHS.structure);

  const clonedScene = useMemo(() => {
    const clone = scene.clone();
    clone.traverse((child) => {
      if (child.isMesh) {
        child.material = child.material.clone();
        child.material.metalness = 0.2;
        child.material.roughness = 0.7;
      }
    });
    return clone;
  }, [scene, color]);

  return (
    <primitive
      object={clonedScene}
      scale={scale * 1.0}
      {...props}
    />
  );
}

// Generic GLB Model loader
export function GLBModel({ path, color, scale = 1, ...props }) {
  const { scene } = useGLTFWithExtensions(path);

  const clonedScene = useMemo(() => {
    const clone = scene.clone();
    if (color) {
      clone.traverse((child) => {
        if (child.isMesh) {
          child.material = child.material.clone();
          child.material.color.set(color);
        }
      });
    }
    return clone;
  }, [scene, color]);

  return (
    <primitive
      object={clonedScene}
      scale={scale}
      {...props}
    />
  );
}

// Worker/Character Model Component (Avatar with Safety Uniform - GLTF)
// Target size from getResourceSize: { width: 0.5, height: 1.7, depth: 0.3 }
export function WorkerModel({ color = '#50c878', scale = 1, highlighted = false, ...props }) {
  const { scene } = useGLTFWithExtensions(MODEL_PATHS.worker);
  const groupRef = useRef();

  // 목표 크기에 맞게 스케일 계산
  const { clonedScene, scaleVec, offset } = useMemo(() => {
    // Deep clone using SkeletonUtils (preserves materials and textures)
    const clone = SkeletonUtils.clone(scene);

    // Deep clone materials to prevent shared state between instances
    clone.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material = Array.isArray(child.material)
          ? child.material.map(m => m.clone())
          : child.material.clone();
      }
    });

    // 바운딩 박스 계산
    const box = new THREE.Box3().setFromObject(clone);
    const size = new THREE.Vector3();
    box.getSize(size);
    const center = new THREE.Vector3();
    box.getCenter(center);

    // 목표 크기 - match exactly with basic geometry
    const targetSize = { width: 0.5, height: 1.7, depth: 0.3 };

    // Scale each axis independently to match target size exactly
    const scaleX = targetSize.width / size.x;
    const scaleY = targetSize.height / size.y;
    const scaleZ = targetSize.depth / size.z;

    // Calculate offset to center on X/Z and place bottom at y=0
    const xOffset = -center.x * scaleX;
    const yOffset = -box.min.y * scaleY;
    const zOffset = -center.z * scaleZ;

    return { clonedScene: clone, scaleVec: [scaleX, scaleY, scaleZ], offset: [xOffset, yOffset, zOffset] };
  }, [scene]);

  // Apply highlight effect
  useEffect(() => {
    if (clonedScene) {
      clonedScene.traverse((child) => {
        if (child.isMesh && child.material) {
          const mats = Array.isArray(child.material) ? child.material : [child.material];
          mats.forEach(mat => {
            mat.emissive = highlighted ? new THREE.Color('#ffeb3b') : new THREE.Color('#000000');
            mat.emissiveIntensity = highlighted ? 0.5 : 0;
            mat.needsUpdate = true;
          });
        }
      });
    }
  }, [clonedScene, highlighted]);

  return (
    <primitive
      ref={groupRef}
      object={clonedScene}
      scale={[scaleVec[0] * scale, scaleVec[1] * scale, scaleVec[2] * scale]}
      position={[offset[0] * scale, offset[1] * scale, offset[2] * scale]}
      {...props}
    />
  );
}

// Custom Model Component (user-uploaded .glb/.gltf via blob URL)
// Uses useLoader (same proven pattern as RobotModel, ConveyorModel, etc.)
export function CustomModel({ url, targetSize = { width: 1, height: 1, depth: 1 }, highlighted = false }) {
  const { scene } = useLoader(GLTFLoader, url);
  const groupRef = useRef();

  const { clonedScene, scaleVec, offset } = useMemo(() => {
    const clone = SkeletonUtils.clone(scene);

    // Deep clone materials to prevent shared state between instances
    clone.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material = Array.isArray(child.material)
          ? child.material.map(m => m.clone())
          : child.material.clone();
      }
    });

    // Calculate original bounding box
    const box = new THREE.Box3().setFromObject(clone);
    const originalSize = new THREE.Vector3();
    box.getSize(originalSize);
    const center = new THREE.Vector3();
    box.getCenter(center);

    // Scale each axis independently to match target size exactly
    const scaleX = targetSize.width / (originalSize.x || 1);
    const scaleY = targetSize.height / (originalSize.y || 1);
    const scaleZ = targetSize.depth / (originalSize.z || 1);

    // Calculate offset to center on X/Z and place bottom at y=0
    const xOffset = -center.x * scaleX;
    const yOffset = -box.min.y * scaleY;
    const zOffset = -center.z * scaleZ;

    return { clonedScene: clone, scaleVec: [scaleX, scaleY, scaleZ], offset: [xOffset, yOffset, zOffset] };
  }, [scene, targetSize.width, targetSize.height, targetSize.depth]);

  // Apply highlight effect
  useEffect(() => {
    if (clonedScene) {
      clonedScene.traverse((child) => {
        if (child.isMesh && child.material) {
          const mats = Array.isArray(child.material) ? child.material : [child.material];
          mats.forEach(mat => {
            mat.emissive = highlighted ? new THREE.Color('#ffeb3b') : new THREE.Color('#000000');
            mat.emissiveIntensity = highlighted ? 0.5 : 0;
            mat.needsUpdate = true;
          });
        }
      });
    }
  }, [clonedScene, highlighted]);

  return (
    <primitive
      ref={groupRef}
      object={clonedScene}
      scale={scaleVec}
      position={offset}
    />
  );
}

export default {
  RobotModel,
  ConveyorModel,
  BoxModel,
  ScannerModel,
  StructureModel,
  GLBModel,
  WorkerModel,
  CustomModel,
  MODEL_PATHS,
  SKIN_PATHS,
};
