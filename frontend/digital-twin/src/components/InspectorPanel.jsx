import { Activity, BatteryMedium, Box, MapPin, Radio, Route, Warehouse } from 'lucide-react';

function DataRow({ icon: Icon, label, value, muted = false }) {
  return <div className="data-row"><Icon size={15} /><span>{label}</span><strong className={muted ? 'muted' : ''}>{value || 'Awaiting data'}</strong></div>;
}

export function InspectorPanel({ robot, activeTask, selected }) {
  const items = activeTask?.payload?.items || [];
  const destination = activeTask?.payload?.destination_dock || 'Dock-3';
  return <section className="panel inspector-panel">
    <div className="panel-heading"><div><span className="eyebrow">ASSET INSPECTOR</span><h2>{selected === 'AMR-Ultra' ? 'AMR-Ultra' : 'Operations view'}</h2></div><span className={`state-pill ${robot.state.toLowerCase()}`}><i />{robot.state}</span></div>
    <div className="asset-summary"><div className="asset-orb"><Radio size={23} /></div><div><strong>Autonomous mobile robot</strong><span>Robot-AMR-Ultra / live telemetry</span></div></div>
    <div className="data-grid">
      <DataRow icon={Activity} label="Current state" value={robot.state} />
      <DataRow icon={MapPin} label="Position" value={robot.state === 'DOCKED' ? destination : robot.state === 'MOVING' ? 'Route / Dock 03' : 'Home station'} />
      <DataRow icon={Box} label="Order" value={robot.orderNumber} muted={!robot.orderNumber} />
      <DataRow icon={Route} label="Correlation" value={robot.correlationId} muted={!robot.correlationId} />
      <DataRow icon={Warehouse} label="Destination" value={destination} />
      <DataRow icon={BatteryMedium} label="Battery" value="Telemetry unavailable" muted />
    </div>
    <div className="task-strip"><div><span className="eyebrow">CURRENT TASK</span><strong>{activeTask?.task_type || 'NO TASK ASSIGNED'}</strong></div><div className="task-items">{items.length ? items.map((item) => <span key={item.sku}>{item.sku} / {item.qty}</span>) : <span>Standby</span>}</div></div>
  </section>;
}
