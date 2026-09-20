import { useState, useEffect, useRef } from 'react';
import mqtt from 'mqtt';

const MQTT_BROKER_WS = 'ws://localhost:9001';
const ERP_API_URL = 'http://localhost:8000/api/orders';
const MONITORED_TOPICS = new Set([
  'warehouse/robot/state',
  'warehouse/tasks/new',
  'warehouse/tasks/completed',
  'warehouse/orders/completed',
  'warehouse/events/sensor',
]);

const formatLogMessage = (msg) => {
  if (typeof msg !== 'object' || msg === null) return msg;
  return JSON.stringify(msg, (_, value) => value === null ? undefined : value);
};

function App() {
  const [connected, setConnected] = useState(false);
  const [robotState, setRobotState] = useState('OFFLINE');
  const [currentOrder, setCurrentOrder] = useState(null);
  const [sensorTriggered, setSensorTriggered] = useState(false);
  const [liveLogs, setLiveLogs] = useState([]);
  const [isChecking, setIsChecking] = useState(false);
  const [healthStatus, setHealthStatus] = useState(null);

  // Command Center State
  const [customer, setCustomer] = useState('Toyota');
  const [sku, setSku] = useState('P100');
  const [quantity, setQuantity] = useState(1);
  const [dock, setDock] = useState('Dock-3');
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchMsg, setDispatchMsg] = useState(null);
  const nextSequence = useRef(1042);

  const addLog = (source, msg) => {
    const newLog = {
      time: new Date().toLocaleTimeString(),
      source,
      msg: formatLogMessage(msg)
    };
    setLiveLogs(prev => [...prev, newLog].slice(-100));
  };

  const runDiagnostics = async () => {
    setIsChecking(true);
    try {
      const res = await fetch('http://localhost:8002/api/health-check');
      setHealthStatus(await res.json());
    } catch (err) {
      console.error('Diagnostics failed', err);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    const client = mqtt.connect(MQTT_BROKER_WS);

    client.on('connect', () => {
      setConnected(true);
      client.subscribe('warehouse/robot/#');
      client.subscribe('warehouse/tasks/#');
      client.subscribe('warehouse/orders/#');
      client.subscribe('warehouse/events/#');
      addLog('SYSTEM', 'Dashboard connected to MQTT Broker');
    });

    client.on('message', (topic, message) => {
      try {
        const payload = JSON.parse(message.toString());
        if (MONITORED_TOPICS.has(topic)) {
          addLog(topic, payload);
        }

        if (topic === 'warehouse/robot/state') {
          setRobotState(payload.state);
          if (payload.order_number) setCurrentOrder(payload.order_number);
        } 
        else if (topic === 'warehouse/tasks/new') {
          setCurrentOrder(payload.order_number);
        }
        else if (topic === 'warehouse/events/sensor') {
          if (payload.event === 'PALLET_ARRIVED') {
            setSensorTriggered(true);
            setTimeout(() => setSensorTriggered(false), 2000);
          }
        }
      } catch (err) {
        console.error('Failed to parse MQTT message', err);
      }
    });

    return () => client.end();
  }, []);

  // --- Dispatch Order ---
  const handleDispatch = async (e) => {
    e.preventDefault();
    setIsDispatching(true);
    setDispatchMsg(null);

    // First Principle: The UI generates a simple ID, but the ERP validates it.
    const productionOrderNumber = `ORD-${Date.now()}`;
    const displayOrderNumber = `ORD-${nextSequence.current++}`;

    try {
      const response = await fetch(ERP_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_number: productionOrderNumber,
          customer: customer,
          destination_dock: dock,
          items: [{ product_sku: sku, requested_qty: parseInt(quantity) }]
        })
      });

      if (!response.ok) throw new Error('ERP rejected the order');

      setDispatchMsg({ type: 'success', text: `Order ${displayOrderNumber} dispatched!` });
      // Reset form
      setCustomer('');
      setQuantity(1);
    } catch {
      setDispatchMsg({ type: 'error', text: 'Failed to dispatch. Check ERP API.' });
    } finally {
      setIsDispatching(false);
      setTimeout(() => setDispatchMsg(null), 4000);
    }
  };

  const styles = {
    container: { fontFamily: 'monospace', padding: '20px', backgroundColor: '#1e1e1e', color: '#d4d4d4', minHeight: '100vh' },
    header: { borderBottom: '2px solid #333', paddingBottom: '10px', marginBottom: '20px' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px', marginBottom: '30px' },
    card: { backgroundColor: '#252526', padding: '20px', borderRadius: '8px', border: '1px solid #333' },
    statusGreen: { color: '#4caf50', fontWeight: 'bold' },
    statusRed: { color: '#f44336', fontWeight: 'bold' },
    statusYellow: { color: '#ffeb3b', fontWeight: 'bold' },
    logContainer: { backgroundColor: '#000', padding: '18px', borderRadius: '4px', minHeight: '420px', height: '62vh', maxHeight: '760px', overflowY: 'auto', fontSize: '13px', lineHeight: '1.55' },
    logEntry: { display: 'grid', gridTemplateColumns: '92px minmax(190px, 280px) 1fr', gap: '10px', marginBottom: '8px', borderBottom: '1px solid #222', paddingBottom: '8px', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' },
    monitorHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginTop: '8px' },
    clearButton: { backgroundColor: 'transparent', color: '#aaa', border: '1px solid #555', borderRadius: '4px', padding: '7px 12px', cursor: 'pointer', fontFamily: 'monospace' },
    
    // Command Center Styles
    formGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '20px' },
    inputGroup: { display: 'flex', flexDirection: 'column' },
    label: { fontSize: '12px', color: '#888', marginBottom: '5px' },
    input: { backgroundColor: '#111', border: '1px solid #444', color: '#fff', padding: '8px', borderRadius: '4px', fontFamily: 'monospace' },
    button: { backgroundColor: '#16A34A', color: '#fff', border: 'none', padding: '12px', borderRadius: '4px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer', fontFamily: 'monospace' },
    buttonDisabled: { backgroundColor: '#4b5563', cursor: 'not-allowed' }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1>🏭 Warehouse Integration Simulator (WIS)</h1>
        <p>Broker Connection: <span style={connected ? styles.statusGreen : styles.statusRed}>{connected ? 'CONNECTED' : 'DISCONNECTED'}</span></p>
      </header>

      <div style={styles.grid}>
        {/* Command Center Card */}
        <div style={{...styles.card, borderColor: '#16A34A', gridColumn: 'span 2'}}>
          <h3>📡 Command Center</h3>
          <form onSubmit={handleDispatch} style={styles.formGrid}>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Customer</label>
              <input style={styles.input} value={customer} onChange={e => setCustomer(e.target.value)} required />
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Destination Dock</label>
              <select style={styles.input} value={dock} onChange={e => setDock(e.target.value)}>
                <option value="Dock-1">Dock 1</option>
                <option value="Dock-2">Dock 2</option>
                <option value="Dock-3">Dock 3</option>
              </select>
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Product SKU</label>
              <select style={styles.input} value={sku} onChange={e => setSku(e.target.value)}>
                <option value="P100">P100 (Engine Block)</option>
                <option value="P200">P200 (Transmission)</option>
                <option value="P300">P300 (Brake Pads)</option>
              </select>
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Quantity</label>
              <input style={styles.input} type="number" min="1" value={quantity} onChange={e => setQuantity(e.target.value)} required />
            </div>
            
            <div style={{ gridColumn: 'span 2' }}>
              <button 
                type="submit" 
                style={isDispatching ? {...styles.button, ...styles.buttonDisabled} : styles.button}
                disabled={isDispatching}
              >
                {isDispatching ? 'DISPATCHING...' : '🚀 DISPATCH ORDER'}
              </button>
              {dispatchMsg && (
                <p style={{ marginTop: '10px', color: dispatchMsg.type === 'success' ? '#4caf50' : '#f44336' }}>
                  {dispatchMsg.text}
                </p>
              )}
            </div>
          </form>
        </div>

        {/* Robot State Card */}
        <div style={styles.card}>
          <h3>🤖 AMR-Ultra (Robot)</h3>
          <p>State: <span style={robotState === 'IDLE' ? styles.statusGreen : styles.statusYellow}>{robotState}</span></p>
          <p>Current Order: {currentOrder || 'None'}</p>
        </div>

        {/* Conveyor State Card */}
        <div style={styles.card}>
          <h3>⚙️ Conveyor-1 (PLC)</h3>
          <p>Dock 3 Sensor: <span style={sensorTriggered ? styles.statusGreen : styles.statusRed}>{sensorTriggered ? 'TRIGGERED (Pallet Here)' : 'CLEAR'}</span></p>
        </div>

        <div style={{...styles.card, borderColor: '#3b82f6', gridColumn: '1 / -1', justifySelf: 'center', width: 'min(100%, 700px)', boxSizing: 'border-box'}}>
          <h3>🛠️ Commissioning Mode (Site Validation)</h3>
          <button onClick={runDiagnostics}
                  style={{...styles.button, backgroundColor: '#2563eb'}}
                  disabled={isChecking}>
            {isChecking ? 'RUNNING DIAGNOSTICS...' : 'RUN SITE VALIDATION'}
          </button>
          {healthStatus && (
            <ul style={{listStyle: 'none', padding: 0, marginTop: '15px'}}>
              {Object.entries(healthStatus).map(([key, value]) => (
                <li key={key}>
                    <span>{key.replace(/_/g, ' ')}:</span>
                    <span style={{
                      color: key === 'timestamp'
                        ? '#aaa'
                        : value === 'OK' ? '#4caf50' : '#f44336',
                      fontWeight: 'bold'
                    }}>
                      {key === 'timestamp'
                        ? value
                        : value === 'OK' ? '✅ ONLINE' : `❌ ${value}`}
                    </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div style={styles.monitorHeader}>
        <h3>📡 Live Integration Monitor</h3>
        <button type="button" style={styles.clearButton} onClick={() => setLiveLogs([])}>
          Clear logs
        </button>
      </div>
      <div style={styles.logContainer}>
        {liveLogs.map((log, idx) => (
          <div key={idx} style={styles.logEntry}>
            <span style={{color: '#888'}}>[{log.time}]</span> <span style={{color: '#569cd6'}}>{log.source}</span> ➡️ {log.msg}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;