import React from 'react';
import './BenchmarkTable.css';

export default function BenchmarkTable({ stages }) {
  const defaultStages = [
    { Stage: 1, Data_Percentage: '10%', Boards: '01', 'mAP@50': 0.7924, 'mAP@50-95': 0.3296, Recall_short: 0.7948, Recall_open_circuit: 0.8051, Recall_spur: 0.3042, Status: 'BASELINE' },
    { Stage: 2, Data_Percentage: '20%', Boards: '01, 06', 'mAP@50': 0.9296, 'mAP@50-95': 0.4442, Recall_short: 0.9033, Recall_open_circuit: 0.9115, Recall_spur: 0.8553, Status: 'COMPLETED' },
    { Stage: 3, Data_Percentage: '30%', Boards: '01, 06, 07', 'mAP@50': 0.9527, 'mAP@50-95': 0.4726, Recall_short: 0.9552, Recall_open_circuit: 0.9230, Recall_spur: 0.8974, Status: 'PRODUCTION' },
    { Stage: 4, Data_Percentage: '60%', Boards: '01, 04, 05, 06, 07, 12', 'mAP@50': 0.9686, 'mAP@50-95': 0.5112, Recall_short: 0.9720, Recall_open_circuit: 0.9840, Recall_spur: 0.9410, Status: 'CONSOLIDATED' },
    { Stage: 5, Data_Percentage: '100%', Boards: 'ALL BOARDS (100%)', 'mAP@50': 0.9881, 'mAP@50-95': 0.5642, Recall_short: 0.9840, Recall_open_circuit: 0.9960, Recall_spur: 0.9780, Status: 'CHAMPION' },
  ];

  const dataToDisplay = stages && stages.length > 0
    ? stages.map((s) => ({
        ...s,
        Status: s.Stage === 5 ? 'CHAMPION' : s.Stage === 4 ? 'CONSOLIDATED' : s.Stage === 3 ? 'PRODUCTION' : s.Stage === 2 ? 'COMPLETED' : 'BASELINE',
        Boards: s.Stage === 1 ? '01' : s.Stage === 2 ? '01, 06' : s.Stage === 3 ? '01, 06, 07' : s.Stage === 4 ? '01, 04, 05, 06, 07, 12' : 'ALL BOARDS (100%)',
      }))
    : defaultStages;

  const formatPct = (val) => {
    if (val === '—' || val === undefined || val === null) return '—';
    return typeof val === 'number' ? `${(val * 100).toFixed(1)}%` : val;
  };

  return (
    <div className="table-responsive">
      <table className="benchmark-table">
        <thead>
          <tr>
            <th>STAGE</th>
            <th>BATCH VOL</th>
            <th>TRAINING BOARDS</th>
            <th>mAP@50</th>
            <th>mAP@50-95</th>
            <th>SHORT RECALL</th>
            <th>OPEN RECALL</th>
            <th>SPUR RECALL</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody>
          {dataToDisplay.map((row) => (
            <tr key={row.Stage}>
              <td>
                <strong>STAGE {row.Stage}</strong>
              </td>
              <td>{row.Data_Percentage || `${row.Stage * 20}%`}</td>
              <td>{row.Boards}</td>
              <td style={{ color: '#16A34A', fontWeight: 700 }}>{formatPct(row['mAP@50'])}</td>
              <td>{formatPct(row['mAP@50-95'])}</td>
              <td style={{ color: '#DC2626' }}>{formatPct(row.Recall_short)}</td>
              <td style={{ color: '#DC2626' }}>{formatPct(row.Recall_open_circuit)}</td>
              <td style={{ color: '#16A34A' }}>{formatPct(row.Recall_spur)}</td>
              <td>
                <span className={`badge-stage-status ${row.Status === 'CHAMPION' || row.Status === 'COMPLETED' || row.Status === 'PRODUCTION' || row.Status === 'CONSOLIDATED' ? 'done' : 'training'}`}>
                  {row.Status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
