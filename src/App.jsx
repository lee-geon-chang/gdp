import { useEffect, useState, useCallback, useRef } from 'react';
import Viewer3D from './components/Viewer3D';
import TabbedPanel from './components/TabbedPanel';
import UnifiedChatPanel from './components/UnifiedChatPanel';
import useBopStore from './store/bopStore';
import { mockBopData } from './data/mockBopData';

const MIN_LEFT = 200;
const MIN_CENTER = 300;
const MIN_RIGHT = 200;
const DIVIDER_WIDTH = 4;

function App() {
  const { bopData, setBopData, initialLoadDone, setInitialLoadDone } = useBopStore();

  const [leftWidth, setLeftWidth] = useState(400);
  const [rightWidth, setRightWidth] = useState(400);
  const [dragging, setDragging] = useState(null); // 'left' | 'right' | null
  const containerRef = useRef(null);

  // Set initial panel widths based on 4:4:2 ratio
  useEffect(() => {
    if (containerRef.current) {
      const totalWidth = containerRef.current.offsetWidth;
      // Ratio 4:4:2 = left:center:right
      // Total parts = 4 + 4 + 2 = 10
      const leftRatio = 0.4; // 4/10
      const rightRatio = 0.2; // 2/10
      setLeftWidth(Math.floor(totalWidth * leftRatio));
      setRightWidth(Math.floor(totalWidth * rightRatio));
    }
  }, []); // Run once on mount

  // Load mock data on initial mount if no BOP data exists (only on first app load)
  useEffect(() => {
    if (!bopData && !initialLoadDone) {
      console.log('[APP] Loading mock BOP data...');
      setBopData(mockBopData);
      setInitialLoadDone(true);
      console.log('[APP] BOP data loaded and parallel processes expanded');
    }
  }, [bopData, initialLoadDone, setBopData, setInitialLoadDone]);

  const handleMouseMove = useCallback((e) => {
    if (!dragging || !containerRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const totalWidth = containerRect.width;

    if (dragging === 'left') {
      let newLeft = e.clientX - containerRect.left;
      newLeft = Math.max(MIN_LEFT, newLeft);
      const maxLeft = totalWidth - DIVIDER_WIDTH * 2 - MIN_CENTER - rightWidth;
      newLeft = Math.min(newLeft, maxLeft);
      setLeftWidth(newLeft);
    } else if (dragging === 'right') {
      let newRight = containerRect.right - e.clientX;
      newRight = Math.max(MIN_RIGHT, newRight);
      const maxRight = totalWidth - DIVIDER_WIDTH * 2 - MIN_CENTER - leftWidth;
      newRight = Math.min(newRight, maxRight);
      setRightWidth(newRight);
    }
  }, [dragging, leftWidth, rightWidth]);

  const handleMouseUp = useCallback(() => {
    setDragging(null);
  }, []);

  useEffect(() => {
    if (!dragging) return;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [dragging, handleMouseMove, handleMouseUp]);

  return (
    <div style={styles.container} ref={containerRef}>
      {/* 왼쪽: 탭 패널 (BOP, 장비, 작업자, 자재) */}
      <div style={{ ...styles.tableSection, width: leftWidth }}>
        <TabbedPanel />
      </div>

      {/* 좌측 디바이더 */}
      <div
        data-divider
        style={styles.divider}
        onMouseDown={() => setDragging('left')}
      />

      {/* 중간: 3D 뷰어 */}
      <div style={styles.viewerSection}>
        <Viewer3D />
      </div>

      {/* 우측 디바이더 */}
      <div
        data-divider
        style={styles.divider}
        onMouseDown={() => setDragging('right')}
      />

      {/* 오른쪽: AI 어시스턴트 패널 */}
      <div style={{ ...styles.controlSection, width: rightWidth }}>
        <UnifiedChatPanel />
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    width: '100vw',
    height: '100vh',
    overflow: 'hidden',
  },
  viewerSection: {
    flex: 1,
    position: 'relative',
    minWidth: MIN_CENTER,
    overflow: 'hidden',
  },
  tableSection: {
    flexShrink: 0,
    borderRight: '1px solid #ddd',
    minWidth: MIN_LEFT,
    overflow: 'hidden',
  },
  controlSection: {
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: 'white',
    borderLeft: '1px solid #ddd',
    overflow: 'hidden',
  },
  divider: {
    width: DIVIDER_WIDTH,
    cursor: 'col-resize',
    backgroundColor: 'transparent',
    flexShrink: 0,
    zIndex: 10,
    transition: 'background-color 0.15s',
  },
};

// Add hover effect via CSS-in-JS workaround: handled inline with onMouseEnter/Leave
// Instead, we use a simple CSS class injected once
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  [data-divider]:hover {
    background-color: rgba(59, 130, 246, 0.5) !important;
  }
`;
document.head.appendChild(styleSheet);

export default App
