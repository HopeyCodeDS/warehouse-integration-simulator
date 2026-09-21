import { useRef, useState } from 'react';
import { Activity, Bell, Box, ChevronRight, CircleHelp, Wifi, WifiOff } from 'lucide-react';
import { DispatchPanel } from './components/DispatchPanel';
import { EventRail } from './components/EventRail';
import { InspectorPanel } from './components/InspectorPanel';
import { WarehouseFloor } from './components/WarehouseFloor';
import { useWarehouseMqtt } from './hooks/useWarehouseMqtt';
import './App.css';

const ERP_API_URL = 'http://localhost:8000/api/orders';

function App() {
  const { connected, robot, activeTask, sensorActive, events, formatPayload } = useWarehouseMqtt();
  const [selected, setSelected] = useState('AMR-Ultra');
  const [dispatchMessage, setDispatchMessage] = useState(null);
  const [isDispatching, setIsDispatching] = useState(false);
  const sequence = useRef(1042);

  const handleDispatch = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const productionOrderNumber = `ORD-${Date.now()}`;
    const displayOrderNumber = `ORD-${sequence.current++}`;
    setIsDispatching(true);
    setDispatchMessage(null);

    try {
      const response = await fetch(ERP_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_number: productionOrderNumber,
          customer: form.get('customer'),
          destination_dock: form.get('dock'),
          items: [{ product_sku: form.get('sku'), requested_qty: Number(form.get('quantity')) }],
        }),
      });
      if (!response.ok) throw new Error('ERP rejected the order');
      setDispatchMessage({ type: 'success', text: `${displayOrderNumber} released to the floor` });
      event.currentTarget.reset();
    } catch (error) {
      setDispatchMessage({ type: 'error', text: error.message || 'Dispatch failed' });
    } finally {
      setIsDispatching(false);
    }
  };

  return <main className="hmi-app">
    <header className="topbar">
      <div className="brand-block"><div className="brand-mark"><Activity size={18} /></div><div><span className="brand-kicker">WIS / OPERATIONS</span><h1>Digital Twin <em>HMI</em></h1></div></div>
      <div className="topbar-status"><span className={`connection ${connected ? 'online' : 'offline'}`}><i />{connected ? 'MQTT ONLINE' : 'RECONNECTING'}</span><span className="topbar-divider" /><span className="clock-label">NORTH HALL / SHIFT A</span><button className="icon-button" title="HMI information" type="button"><CircleHelp size={17} /></button><button className="icon-button" title="Notifications" type="button"><Bell size={17} /></button></div>
    </header>

    <section className="status-strip"><div><span className="eyebrow">SYSTEM STATUS</span><strong>{connected ? 'All operational systems reporting' : 'Awaiting broker connection'}</strong></div><div className="status-items"><span><Wifi size={14} /> Broker / {connected ? 'Connected' : 'Offline'}</span><span><Box size={14} /> Active mission / {activeTask ? activeTask.task_type : 'None'}</span><span><span className={`pulse-indicator ${sensorActive ? 'active' : ''}`} /> Dock sensor / {sensorActive ? 'Pallet detected' : 'Clear'}</span></div></section>

    <div className="workspace-grid">
      <section className="floor-column"><div className="breadcrumb"><span>OPERATIONS</span><ChevronRight size={13} /><strong>LIVE WAREHOUSE FLOOR</strong></div><WarehouseFloor robot={robot} activeTask={activeTask} sensorActive={sensorActive} onSelect={setSelected} /><div className="floor-caption"><span><span className="caption-square" />Authored schematic / telemetry positions are illustrative</span><span><WifiOff size={13} /> Session live data only</span></div></section>
      <aside className="side-column"><InspectorPanel robot={robot} activeTask={activeTask} selected={selected} /><DispatchPanel onDispatch={handleDispatch} isDispatching={isDispatching} message={dispatchMessage} /></aside>
    </div>

    <EventRail events={events} formatPayload={formatPayload} />
    <footer className="footer-bar"><span>WIS DIGITAL TWIN / LOCAL COMMISSIONING BUILD</span><span>AMR-Ultra <i className="footer-dot" /> {robot.state} <i className="footer-dot" /> {events.length} EVENTS IN SESSION</span></footer>
  </main>;
}

export default App;
