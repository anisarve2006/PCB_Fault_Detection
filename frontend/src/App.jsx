import React, { useState, useCallback, useEffect } from 'react';
import { InspectionProvider } from './context/InspectionContext';
import Header from './components/Header/Header';
import LeftPanel from './components/LeftPanel/LeftPanel';
import LeftRail from './components/LeftPanel/LeftRail';
import CenterPanel from './components/CenterPanel/CenterPanel';
import RightPanel from './components/RightPanel/RightPanel';
import RightRail from './components/RightPanel/RightRail';
import PanelResizer from './components/PanelResizer/PanelResizer';
import BenchmarkModal from './components/BenchmarkModal/BenchmarkModal';
import Toast from './components/Toast/Toast';
import './App.css';

const DEFAULT_LEFT_WIDTH = 320;
const DEFAULT_RIGHT_WIDTH = 380;

export default function App() {
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(() => {
    try {
      return localStorage.getItem('pcb_aoi_left_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const [isRightCollapsed, setIsRightCollapsed] = useState(() => {
    try {
      return localStorage.getItem('pcb_aoi_right_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const [leftWidth, setLeftWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('pcb_aoi_left_width');
      if (saved) {
        const parsed = parseInt(saved, 10);
        if (!isNaN(parsed) && parsed >= 200 && parsed <= 650) return parsed;
      }
    } catch {
      // Ignore
    }
    return DEFAULT_LEFT_WIDTH;
  });

  const [rightWidth, setRightWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('pcb_aoi_right_width');
      if (saved) {
        const parsed = parseInt(saved, 10);
        if (!isNaN(parsed) && parsed >= 260 && parsed <= 750) return parsed;
      }
    } catch {
      // Ignore
    }
    return DEFAULT_RIGHT_WIDTH;
  });

  const toggleLeftCollapse = useCallback((collapsed) => {
    setIsLeftCollapsed(collapsed);
    try {
      localStorage.setItem('pcb_aoi_left_collapsed', String(collapsed));
    } catch {
      // Ignore
    }
  }, []);

  const toggleRightCollapse = useCallback((collapsed) => {
    setIsRightCollapsed(collapsed);
    try {
      localStorage.setItem('pcb_aoi_right_collapsed', String(collapsed));
    } catch {
      // Ignore
    }
  }, []);

  const handleLeftResize = useCallback((newWidth) => {
    // If dragged too close to boundary (< 140px), auto-collapse into docked boundary rail
    if (newWidth < 140) {
      toggleLeftCollapse(true);
      return;
    }
    setLeftWidth(newWidth);
    try {
      localStorage.setItem('pcb_aoi_left_width', String(newWidth));
    } catch {
      // Ignore
    }
  }, [toggleLeftCollapse]);

  const handleRightResize = useCallback((newWidth) => {
    // If dragged too close to boundary (< 140px), auto-collapse into docked boundary rail
    if (newWidth < 140) {
      toggleRightCollapse(true);
      return;
    }
    setRightWidth(newWidth);
    try {
      localStorage.setItem('pcb_aoi_right_width', String(newWidth));
    } catch {
      // Ignore
    }
  }, [toggleRightCollapse]);

  const handleLeftReset = useCallback(() => {
    handleLeftResize(DEFAULT_LEFT_WIDTH);
  }, [handleLeftResize]);

  const handleRightReset = useCallback(() => {
    handleRightResize(DEFAULT_RIGHT_WIDTH);
  }, [handleRightResize]);

  // Global Keyboard Shortcuts for Sidebar Collapse: Ctrl+[ (Left) and Ctrl+] (Right)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.key === '[') {
        e.preventDefault();
        toggleLeftCollapse(!isLeftCollapsed);
      } else if (e.ctrlKey && e.key === ']') {
        e.preventDefault();
        toggleRightCollapse(!isRightCollapsed);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isLeftCollapsed, isRightCollapsed, toggleLeftCollapse, toggleRightCollapse]);

  return (
    <InspectionProvider>
      <Header />
      <main className="workspace-grid">
        {/* Left Side: Expanded Panel or Docked Boundary Rail */}
        {isLeftCollapsed ? (
          <LeftRail onExpand={() => toggleLeftCollapse(false)} />
        ) : (
          <>
            <LeftPanel width={leftWidth} onCollapse={() => toggleLeftCollapse(true)} />
            <PanelResizer
              side="left"
              currentWidth={leftWidth}
              minWidth={100}
              maxWidth={650}
              onResize={handleLeftResize}
              onReset={handleLeftReset}
            />
          </>
        )}

        {/* Center PCB Inspection Workspace */}
        <CenterPanel />

        {/* Right Side: Expanded Panel or Docked Boundary Rail */}
        {isRightCollapsed ? (
          <RightRail onExpand={() => toggleRightCollapse(false)} />
        ) : (
          <>
            <PanelResizer
              side="right"
              currentWidth={rightWidth}
              minWidth={100}
              maxWidth={750}
              onResize={handleRightResize}
              onReset={handleRightReset}
            />
            <RightPanel width={rightWidth} onCollapse={() => toggleRightCollapse(true)} />
          </>
        )}
      </main>
      <BenchmarkModal />
      <Toast />
    </InspectionProvider>
  );
}
