import React from 'react';
import { useInspection } from '../../context/useInspection';
import './ModelSelector.css';

export default function ModelSelector() {
  const { modelChoice, setModelChoice, systemStatus } = useInspection();

  const models = systemStatus?.models_available || [
    { id: 'champion', name: 'Phase 5 Champion (Stage 5 - 98.81% mAP@50)' },
    { id: 'stage5', name: 'Stage 5 Model (100% Data - 98.81%)' },
    { id: 'stage4', name: 'Stage 4 Model (60% Data - 96.86%)' },
    { id: 'stage3', name: 'Stage 3 Model (30% Data - 95.27%)' },
  ];

  return (
    <div className="model-selector-container">
      <select
        id="modelSelect"
        className="google-select"
        value={modelChoice}
        onChange={(e) => setModelChoice(e.target.value)}
        aria-label="Detection Model"
      >
        {models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name}
          </option>
        ))}
      </select>
    </div>
  );
}
