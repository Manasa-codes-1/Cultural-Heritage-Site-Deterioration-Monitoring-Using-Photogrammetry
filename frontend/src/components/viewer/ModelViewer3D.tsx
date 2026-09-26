import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';
import {
  RotateCcw,
  Maximize2,
  Minimize2,
  Box,
  Eye,
  Camera,
  Grid,
  AlertTriangle,
  CheckCircle2,
  Layers,
  Sparkles,
  Crosshair,
} from 'lucide-react';
import type { CameraPose, BoundingBox3D, Deterioration3DMappingItem, TemporalChangeRecordItem } from '../../types';

interface ModelViewer3DProps {
  modelUrl: string;
  isDemo: boolean;
  modelType?: 'mesh' | 'dense' | 'sparse';
  cameraPoses?: CameraPose[];
  boundingBox?: BoundingBox3D;
  pointCount?: number;
  vertexCount?: number;
  triangleCount?: number;
  reprojectionError?: number | null;
  onRefresh?: () => void;
  // Phase 6: 2D-to-3D Damage Mapping Props
  damageMappings?: Deterioration3DMappingItem[];
  selectedMappingId?: string | null;
  onSelectDamagePoint?: (item: Deterioration3DMappingItem) => void;
  showDamageMarkers?: boolean;
  // Phase 7: Multi-Temporal Monitoring Props
  comparisonModelUrl?: string;
  temporalMode?: 't1_only' | 't2_only' | 'both' | 'difference';
  temporalChangeRecords?: TemporalChangeRecordItem[];
  selectedChangeRecordId?: string | null;
  onSelectChangeRecord?: (record: TemporalChangeRecordItem) => void;
}

type RenderMode = 'mesh' | 'wireframe' | 'points' | 'hybrid';

export const ModelViewer3D: React.FC<ModelViewer3DProps> = ({
  modelUrl,
  isDemo,
  cameraPoses = [],
  boundingBox,
  pointCount = 0,
  vertexCount = 0,
  triangleCount = 0,
  reprojectionError,
  damageMappings = [],
  selectedMappingId,
  onSelectDamagePoint,
  showDamageMarkers = true,
  comparisonModelUrl,
  temporalMode = 't1_only',
  temporalChangeRecords = [],
  selectedChangeRecordId,
  onSelectChangeRecord,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadProgress, setLoadProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  // Display toggles
  const [renderMode, setRenderMode] = useState<RenderMode>('mesh');
  const [showCameras, setShowCameras] = useState<boolean>(true);
  const [showBoundingBox, setShowBoundingBox] = useState<boolean>(true);
  const [showGrid, setShowGrid] = useState<boolean>(true);
  const [pointSize, setPointSize] = useState<number>(3);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showDamage, setShowDamage] = useState<boolean>(showDamageMarkers);

  // Three.js internal references
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const modelGroupRef = useRef<THREE.Group | null>(null);
  const camerasGroupRef = useRef<THREE.Group | null>(null);
  const helpersGroupRef = useRef<THREE.Group | null>(null);
  const damageMarkersGroupRef = useRef<THREE.Group | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const onSelectDamagePointRef = useRef(onSelectDamagePoint);
  const onSelectChangeRecordRef = useRef(onSelectChangeRecord);

  useEffect(() => {
    onSelectDamagePointRef.current = onSelectDamagePoint;
  }, [onSelectDamagePoint]);

  useEffect(() => {
    onSelectChangeRecordRef.current = onSelectChangeRecord;
  }, [onSelectChangeRecord]);

  // Reset Camera View
  const resetCamera = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    cameraRef.current.position.set(0, 0.5, 3.8);
    controlsRef.current.target.set(0, 0, 0);
    controlsRef.current.update();
  }, []);

  // Set View Preset
  const setViewPreset = (view: 'front' | 'iso' | 'top' | 'side') => {
    if (!cameraRef.current || !controlsRef.current) return;
    if (view === 'front') {
      cameraRef.current.position.set(0, 0, 3.5);
    } else if (view === 'iso') {
      cameraRef.current.position.set(2.5, 2.0, 2.8);
    } else if (view === 'top') {
      cameraRef.current.position.set(0, 4.0, 0.01);
    } else if (view === 'side') {
      cameraRef.current.position.set(3.5, 0, 0);
    }
    controlsRef.current.target.set(0, 0, 0);
    controlsRef.current.update();
  };

  // Toggle Fullscreen
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  // Initialize Three.js Scene
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a); // Slate-900 background
    sceneRef.current = scene;

    // 2. Camera
    const aspect = container.clientWidth / Math.max(1, container.clientHeight);
    const camera = new THREE.PerspectiveCamera(45, aspect, 0.05, 100);
    camera.position.set(0, 0.5, 3.8);
    cameraRef.current = camera;

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;
    controls.minDistance = 0.2;
    controls.maxDistance = 25.0;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffeedd, 1.2);
    dirLight1.position.set(5, 10, 7);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xddeeff, 0.6);
    dirLight2.position.set(-5, -3, -5);
    scene.add(dirLight2);

    // 6. Sub-groups
    const modelGroup = new THREE.Group();
    const camerasGroup = new THREE.Group();
    const helpersGroup = new THREE.Group();
    const damageMarkersGroup = new THREE.Group();

    scene.add(modelGroup);
    scene.add(camerasGroup);
    scene.add(helpersGroup);
    scene.add(damageMarkersGroup);

    modelGroupRef.current = modelGroup;
    camerasGroupRef.current = camerasGroup;
    helpersGroupRef.current = helpersGroup;
    damageMarkersGroupRef.current = damageMarkersGroup;

    // 7. Ground Grid & Axes
    const gridHelper = new THREE.GridHelper(6, 12, 0xd97706, 0x334155);
    gridHelper.position.y = -1.0;
    helpersGroup.add(gridHelper);

    const axesHelper = new THREE.AxesHelper(0.5);
    axesHelper.position.set(-1.8, -0.9, 0);
    helpersGroup.add(axesHelper);

    // 8. Damage Point Raycasting Click Handler
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handleCanvasClick = (e: MouseEvent) => {
      if (!cameraRef.current || !damageMarkersGroupRef.current) return;
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, cameraRef.current);
      const intersects = raycaster.intersectObjects(damageMarkersGroupRef.current.children, true);
      if (intersects.length > 0) {
        let obj: THREE.Object3D | null = intersects[0].object;
        while (obj && !obj.userData?.mapping && !obj.userData?.temporalRecord) {
          obj = obj.parent;
        }
        if (obj && obj.userData?.temporalRecord && onSelectChangeRecordRef.current) {
          onSelectChangeRecordRef.current(obj.userData.temporalRecord);
        } else if (obj && obj.userData?.mapping && onSelectDamagePointRef.current) {
          onSelectDamagePointRef.current(obj.userData.mapping);
        }
      }
    };
    renderer.domElement.addEventListener('click', handleCanvasClick);

    // 9. Animation loop
    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 10. Resize observer
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const width = container.clientWidth;
      const height = container.clientHeight;
      camera.aspect = width / Math.max(1, height);
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      renderer.domElement.removeEventListener('click', handleCanvasClick);
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
      }
      controls.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  // Update render mode visibility
  const updateRenderModeVisibility = useCallback(
    (
      mode: RenderMode,
      mesh?: THREE.Object3D,
      wire?: THREE.Object3D,
      pts?: THREE.Object3D,
      hasFaces: boolean = true
    ) => {
      const modelGroup = modelGroupRef.current;
      if (!modelGroup) return;

      const m = mesh || modelGroup.getObjectByName('meshObject');
      const w = wire || modelGroup.getObjectByName('wireframeObject');
      const p = pts || modelGroup.getObjectByName('pointsObject');

      if (m) m.visible = (mode === 'mesh' || mode === 'hybrid') && hasFaces;
      if (w) w.visible = mode === 'wireframe' || (mode === 'hybrid' && hasFaces);
      if (p) p.visible = mode === 'points' || !hasFaces;
    },
    []
  );

  // Load 3D PLY Asset
  useEffect(() => {
    const activeUrl = (temporalMode === 't2_only' && comparisonModelUrl) ? comparisonModelUrl : modelUrl;
    if (!activeUrl) return;

    setLoading(true);
    setError(null);
    setLoadProgress(10);

    const loader = new PLYLoader();

    loader.load(
      activeUrl,
      (geometry) => {
        setLoadProgress(100);
        setLoading(false);

        const modelGroup = modelGroupRef.current;
        if (!modelGroup) return;

        // Clear existing model children
        while (modelGroup.children.length > 0) {
          const obj = modelGroup.children[0];
          modelGroup.remove(obj);
        }

        // Center and normalize geometry
        geometry.computeVertexNormals();
        geometry.center();

        const hasVertexColors = geometry.hasAttribute('color');
        const hasFaces = geometry.index !== null || geometry.attributes.position.count % 3 === 0;

        // 1. Shaded Mesh
        const meshMaterial = new THREE.MeshStandardMaterial({
          vertexColors: hasVertexColors,
          color: hasVertexColors ? 0xffffff : 0xd8b589, // Warm sandstone
          roughness: 0.85,
          metalness: 0.05,
          side: THREE.DoubleSide,
        });
        const mesh = new THREE.Mesh(geometry, meshMaterial);
        mesh.name = 'meshObject';

        // 2. Wireframe Overlay
        const wireMaterial = new THREE.MeshBasicMaterial({
          color: 0x38bdf8,
          wireframe: true,
          transparent: true,
          opacity: 0.4,
        });
        const wireMesh = new THREE.Mesh(geometry, wireMaterial);
        wireMesh.name = 'wireframeObject';

        // 3. Points Cloud
        const pointsMaterial = new THREE.PointsMaterial({
          vertexColors: hasVertexColors,
          color: hasVertexColors ? 0xffffff : 0xf59e0b,
          size: pointSize * 0.008,
          sizeAttenuation: true,
        });
        const points = new THREE.Points(geometry, pointsMaterial);
        points.name = 'pointsObject';

        modelGroup.add(mesh);
        modelGroup.add(wireMesh);
        modelGroup.add(points);

        // Adjust visibility according to current renderMode
        updateRenderModeVisibility(renderMode, mesh, wireMesh, points, hasFaces);

        // Compute Bounding Box Helper if enabled
        geometry.computeBoundingBox();
        if (geometry.boundingBox && helpersGroupRef.current) {
          // Remove old bbox
          const oldBbox = helpersGroupRef.current.getObjectByName('bboxHelper');
          if (oldBbox) helpersGroupRef.current.remove(oldBbox);

          const bboxHelper = new THREE.Box3Helper(geometry.boundingBox, new THREE.Color(0xf59e0b));
          bboxHelper.name = 'bboxHelper';
          bboxHelper.visible = showBoundingBox;
          helpersGroupRef.current.add(bboxHelper);
        }
      },
      (xhr) => {
        if (xhr.total > 0) {
          const pct = Math.round((xhr.loaded / xhr.total) * 100);
          setLoadProgress(pct);
        }
      },
      (err: unknown) => {
        setLoading(false);
        const error = err as Error;
        setError(`Failed to load 3D model: ${error?.message || 'Network or parse error'}`);
      }
    );

  }, [modelUrl, comparisonModelUrl, temporalMode, pointSize, showBoundingBox]);

  // Sync render mode changes

  useEffect(() => {
    updateRenderModeVisibility(renderMode);
  }, [renderMode]);

  // Sync Point Size
  useEffect(() => {
    const modelGroup = modelGroupRef.current;
    if (!modelGroup) return;
    const pts = modelGroup.getObjectByName('pointsObject') as THREE.Points | undefined;
    if (pts && pts.material instanceof THREE.PointsMaterial) {
      pts.material.size = pointSize * 0.008;
      pts.material.needsUpdate = true;
    }
  }, [pointSize]);

  // Sync Bounding Box Helper
  useEffect(() => {
    if (!helpersGroupRef.current) return;
    const bbox = helpersGroupRef.current.getObjectByName('bboxHelper');
    if (bbox) bbox.visible = showBoundingBox;
  }, [showBoundingBox]);

  // Sync Grid Helper
  useEffect(() => {
    if (!helpersGroupRef.current) return;
    helpersGroupRef.current.visible = showGrid;
  }, [showGrid]);

  // Build Camera Frustums / Stations
  useEffect(() => {
    const camGroup = camerasGroupRef.current;
    if (!camGroup) return;

    // Clear old cameras
    while (camGroup.children.length > 0) {
      camGroup.remove(camGroup.children[0]);
    }

    if (!showCameras || cameraPoses.length === 0) return;

    cameraPoses.forEach((pose, idx) => {
      const marker = new THREE.Group();

      // Camera body (small box)
      const bodyGeo = new THREE.BoxGeometry(0.08, 0.06, 0.05);
      const bodyMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
      const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
      marker.add(bodyMesh);

      // Frustum pyramid pointing forward
      const coneGeo = new THREE.ConeGeometry(0.06, 0.12, 4);
      coneGeo.rotateX(Math.PI / 2);
      const coneMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, wireframe: true });
      const coneMesh = new THREE.Mesh(coneGeo, coneMat);
      coneMesh.position.z = -0.08;
      marker.add(coneMesh);

      // Set position
      marker.position.set(pose.position[0], pose.position[1], pose.position[2]);

      // Set orientation if quaternion provided
      if (pose.rotation_quaternion && pose.rotation_quaternion.length === 4) {
        const q = pose.rotation_quaternion;
        marker.quaternion.set(q[0], q[1], q[2], q[3]);
      } else {
        // Point toward origin
        marker.lookAt(0, 0, 0);
      }

      marker.name = `camera_${idx + 1}`;
      camGroup.add(marker);
    });
  }, [cameraPoses, showCameras]);

  // Synchronize 3D Deterioration Damage Markers & Temporal Change Markers
  useEffect(() => {
    const group = damageMarkersGroupRef.current;
    if (!group) return;

    // Clear old markers
    while (group.children.length > 0) {
      group.remove(group.children[0]);
    }

    if (!showDamage) return;

    // 1. If temporal change records are provided, prioritize rendering temporal evolution markers
    if (temporalChangeRecords.length > 0) {
      const getTemporalColor = (status: string): number => {
        switch (status) {
          case 'NEW_DETERIORATION': return 0x06b6d4; // Cyan
          case 'PERSISTING_DETERIORATION': return 0xf43f5e; // Rose / Crimson
          case 'POSSIBLY_RESOLVED_OR_UNDETECTED': return 0x6366f1; // Indigo
          case 'GEOMETRIC_CHANGE_WITHOUT_DETERIORATION_LABEL': return 0xf59e0b; // Amber
          case 'NO_SIGNIFICANT_CHANGE': return 0x10b981; // Emerald
          default: return 0x64748b; // Slate
        }
      };

      temporalChangeRecords.forEach((rec) => {
        const x = rec.comparison_x ?? rec.baseline_x;
        const y = rec.comparison_y ?? rec.baseline_y;
        const z = rec.comparison_z ?? rec.baseline_z;
        if (x == null || y == null || z == null) return;

        const isSelected = selectedChangeRecordId === rec.id;
        const marker = new THREE.Group();
        marker.position.set(x, y, z);
        marker.userData = { temporalRecord: rec };

        const colorHex = getTemporalColor(rec.change_status);

        const sphereGeo = new THREE.SphereGeometry(isSelected ? 0.058 : 0.040, 16, 16);
        const sphereMat = new THREE.MeshStandardMaterial({
          color: colorHex,
          emissive: colorHex,
          emissiveIntensity: isSelected ? 0.75 : 0.35,
          roughness: 0.3,
          metalness: 0.2,
        });
        const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
        sphereMesh.userData = { temporalRecord: rec };
        marker.add(sphereMesh);

        if (isSelected) {
          const ringGeo = new THREE.RingGeometry(0.07, 0.09, 32);
          const ringMat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide });
          const ringMesh = new THREE.Mesh(ringGeo, ringMat);
          ringMesh.lookAt(cameraRef.current ? cameraRef.current.position : new THREE.Vector3(0, 0, 1));
          marker.add(ringMesh);
        }

        group.add(marker);
      });
      return;
    }

    if (damageMappings.length === 0) return;

    const getColorForType = (type: string): number => {
      switch (type.toLowerCase()) {
        case 'crack': return 0xef4444; // red
        case 'erosion': return 0xf97316; // orange
        case 'spalling': return 0xeab308; // yellow
        case 'discoloration': return 0xa855f7; // purple
        case 'biological_growth': return 0x22c55e; // green
        default: return 0x38bdf8; // sky blue
      }
    };

    damageMappings.forEach((mapping) => {
      if (!mapping.world_point) return;
      const { x, y, z } = mapping.world_point;
      const isSelected = selectedMappingId === mapping.id;

      const marker = new THREE.Group();
      marker.position.set(x, y, z);
      marker.userData = { mapping };

      const colorHex = getColorForType(mapping.deterioration_type);

      // Core sphere marker
      const sphereGeo = new THREE.SphereGeometry(isSelected ? 0.055 : 0.038, 16, 16);
      const sphereMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        emissive: colorHex,
        emissiveIntensity: isSelected ? 0.6 : 0.25,
        roughness: 0.3,
        metalness: 0.2,
      });
      const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
      sphereMesh.userData = { mapping };
      marker.add(sphereMesh);

      // Highlight halo ring if selected
      if (isSelected) {
        const ringGeo = new THREE.RingGeometry(0.07, 0.088, 32);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide });
        const ringMesh = new THREE.Mesh(ringGeo, ringMat);
        ringMesh.lookAt(cameraRef.current ? cameraRef.current.position : new THREE.Vector3(0, 0, 1));
        marker.add(ringMesh);
      }

      group.add(marker);
    });
  }, [damageMappings, selectedMappingId, temporalChangeRecords, selectedChangeRecordId, showDamage]);

  return (
    <div className={`model-viewer-wrapper ${isFullscreen ? 'viewer-fullscreen' : ''}`}>
      {/* Research Safety Banner */}
      <div className={`research-disclaimer-banner ${isDemo ? 'banner-demo' : 'banner-real'}`}>
        <div className="flex items-center gap-2">
          {isDemo ? (
            <AlertTriangle size={18} className="text-amber-400 shrink-0" />
          ) : (
            <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
          )}
          <span className="banner-title font-semibold uppercase tracking-wider text-xs">
            {isDemo
              ? 'DEMO MODEL — NOT A REAL PHOTOGRAMMETRIC RECONSTRUCTION'
              : 'CERTIFIED PHOTOGRAMMETRIC RECONSTRUCTION'}
          </span>
        </div>
        <p className="banner-caption text-xs opacity-90">
          {isDemo
            ? 'COLMAP was not available on this machine or synthetic demo engine was requested. Geometry generated procedurally for CPU pipeline testing.'
            : 'Reconstructed via calibrated Structure-from-Motion and Multi-View Stereo photogrammetric pipelines.'}
        </p>
      </div>

      {/* 3D Canvas Viewport */}
      <div className="viewer-viewport-container" ref={containerRef}>
        {loading && (
          <div className="viewer-overlay-loading">
            <div className="loading-spinner mb-3" />
            <p className="text-slate-200 font-medium">Streaming 3D Photogrammetric Asset...</p>
            <div className="loading-progress-bar">
              <div className="progress-fill" style={{ width: `${loadProgress}%` }} />
            </div>
            <span className="text-xs text-slate-400 mt-1">{loadProgress}% loaded</span>
          </div>
        )}

        {error && (
          <div className="viewer-overlay-error">
            <AlertTriangle size={32} className="text-rose-400 mb-2" />
            <p className="text-rose-200 font-medium">{error}</p>
            <p className="text-xs text-slate-400 mt-1">
              Ensure survey reconstruction has completed and 3D output files exist.
            </p>
          </div>
        )}

        {/* HUD Statistics Overlay */}
        <div className="viewer-hud-overlay">
          <div className="hud-metric">
            <span className="hud-label">Points / Vertices:</span>
            <span className="hud-value font-mono">
              {(pointCount || vertexCount).toLocaleString()}
            </span>
          </div>
          {triangleCount > 0 && (
            <div className="hud-metric">
              <span className="hud-label">Triangles:</span>
              <span className="hud-value font-mono">{triangleCount.toLocaleString()}</span>
            </div>
          )}
          {cameraPoses.length > 0 && (
            <div className="hud-metric">
              <span className="hud-label">Registered Cams:</span>
              <span className="hud-value font-mono">{cameraPoses.length}</span>
            </div>
          )}
          {reprojectionError != null && (
            <div className="hud-metric">
              <span className="hud-label">Mean Reproj Error:</span>
              <span className="hud-value font-mono">{reprojectionError.toFixed(2)} px</span>
            </div>
          )}
          {damageMappings.length > 0 && (
            <div className="hud-metric">
              <span className="hud-label">Mapped Defects:</span>
              <span className="hud-value font-mono text-amber-400 font-bold">{damageMappings.length}</span>
            </div>
          )}
          {boundingBox && (
            <div className="hud-metric">
              <span className="hud-label">Dimensions:</span>
              <span className="hud-value font-mono text-xs">
                {boundingBox.dimensions[0]}m × {boundingBox.dimensions[1]}m × {boundingBox.dimensions[2]}m
              </span>
            </div>
          )}
        </div>

        {/* Floating View Presets */}
        <div className="viewer-view-presets">
          <button onClick={() => setViewPreset('front')} className="preset-btn" title="Front Elevation View">
            Front
          </button>
          <button onClick={() => setViewPreset('iso')} className="preset-btn" title="Isometric Perspective">
            Iso
          </button>
          <button onClick={() => setViewPreset('top')} className="preset-btn" title="Top Down Plan View">
            Top
          </button>
          <button onClick={() => setViewPreset('side')} className="preset-btn" title="Side Profile View">
            Side
          </button>
          <button onClick={resetCamera} className="preset-btn" title="Reset View">
            <RotateCcw size={12} />
          </button>
        </div>
      </div>

      {/* Viewer Toolbar */}
      <div className="viewer-controls-toolbar">
        {/* Render Mode Group */}
        <div className="toolbar-group">
          <span className="toolbar-group-label">Shading:</span>
          <div className="toolbar-segmented-control">
            <button
              onClick={() => setRenderMode('mesh')}
              className={`seg-btn ${renderMode === 'mesh' ? 'seg-active' : ''}`}
              title="Shaded Surface Mesh"
            >
              <Box size={14} />
              <span>Mesh</span>
            </button>
            <button
              onClick={() => setRenderMode('wireframe')}
              className={`seg-btn ${renderMode === 'wireframe' ? 'seg-active' : ''}`}
              title="Wireframe Triangles"
            >
              <Layers size={14} />
              <span>Wire</span>
            </button>
            <button
              onClick={() => setRenderMode('points')}
              className={`seg-btn ${renderMode === 'points' ? 'seg-active' : ''}`}
              title="Dense Point Cloud"
            >
              <Sparkles size={14} />
              <span>Points</span>
            </button>
            <button
              onClick={() => setRenderMode('hybrid')}
              className={`seg-btn ${renderMode === 'hybrid' ? 'seg-active' : ''}`}
              title="Combined Mesh & Wireframe"
            >
              <Eye size={14} />
              <span>Hybrid</span>
            </button>
          </div>
        </div>

        {/* Feature Toggles */}
        <div className="toolbar-group">
          <button
            onClick={() => setShowCameras((prev) => !prev)}
            className={`toolbar-toggle-btn ${showCameras ? 'toggle-active' : ''}`}
            title="Toggle Estimated Camera Frustums"
          >
            <Camera size={14} />
            <span>Cameras ({cameraPoses.length})</span>
          </button>
          <button
            onClick={() => setShowBoundingBox((prev) => !prev)}
            className={`toolbar-toggle-btn ${showBoundingBox ? 'toggle-active' : ''}`}
            title="Toggle Bounding Dimensions"
          >
            <Box size={14} />
            <span>Bounds</span>
          </button>
          <button
            onClick={() => setShowGrid((prev) => !prev)}
            className={`toolbar-toggle-btn ${showGrid ? 'toggle-active' : ''}`}
            title="Toggle 1-meter Ground Grid & Axes"
          >
            <Grid size={14} />
            <span>Grid</span>
          </button>
          {damageMappings.length > 0 && (
            <button
              onClick={() => setShowDamage((prev) => !prev)}
              className={`toolbar-toggle-btn ${showDamage ? 'toggle-active' : ''}`}
              title="Toggle 3D Deterioration Defect Markers"
            >
              <Crosshair size={14} />
              <span>Defects ({damageMappings.length})</span>
            </button>
          )}
        </div>

        {/* Point Size Control (when in point cloud mode) */}
        {(renderMode === 'points' || renderMode === 'hybrid') && (
          <div className="toolbar-group">
            <span className="toolbar-group-label">Size:</span>
            <input
              type="range"
              min="1"
              max="8"
              value={pointSize}
              onChange={(e) => setPointSize(Number(e.target.value))}
              className="toolbar-slider"
              title="Point Size"
            />
            <span className="text-xs text-slate-400 font-mono">{pointSize}px</span>
          </div>
        )}

        {/* Fullscreen Button */}
        <div className="toolbar-group ml-auto">
          <button onClick={toggleFullscreen} className="toolbar-icon-btn" title="Toggle Fullscreen">
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
};
