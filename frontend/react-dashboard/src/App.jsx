import { useState, useEffect } from 'react';
import mqtt from 'mqtt';

// First Principle: Environment Abstraction
// In Docker, this would be ws://mqtt-broker:9001. Locally, it is ws://localhost:9001
const MQTT_BROKER_WS = 'ws://localhost:9001';

function App() {
  const [connected, setConnected] = useState(false);
  const [robotState, setRobotState] = useState('OFFLINE');
  const [currentOrder, setCurrentOrder] = useState(null);
  const [sensorTriggered, setSensorTriggered] = useState(false);
  const [liveLogs, setLiveLogs] = useState([]);

  useEffect(() => {
    // 1. Connect to MQTT via WebSockets
    const client = mqtt.connect(MQTT_BROKER_WS);

    client.on('connect', () => {
      console.log('✅ Connected to MQTT Broker via WebSockets');
      setConnected(true);
      // Subscribe to ALL warehouse topics using the wildcard '#'
      client.subscribe('warehouse/#');
      addLog('SYSTEM', 'Dashboard connected to MQTT Broker');
    });

    // 2. First Principle: Event-Driven UI
    // The UI doesn't ask the database for updates. It reacts to MQTT events.
    client.on('message', (topic, message) => {
      try {
        const payload = JSON.parse(message.toString());
        addLog(topic, payload);

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
            // Auto-reset sensor visual after 2 seconds
            setTimeout(() => setSensorTriggered(false), 2000);
          }
        }
      } catch (err) {
        console.error('Failed to parse MQTT message', err);
      }
    });

    client.on('error', (err) => {
      console.error('MQTT Connection Error:', err);
      setConnected(false);
    });

    // Cleanup on component unmount
    return () => client.end();
  }, []);

  const addLog = (source, msg) => {
    const newLog = {
      time: new Date().toLocaleTimeString(),
      source,
      msg: typeof msg === 'object' ? JSON.stringify(msg) : msg
    };
    setLiveLogs(prev => [newLog, ...prev].slice(0, 15)); // Keep last 15 logs
  };

  // Simple inline styling for the dashboard
  const styles = {
    container: { fontFamily: 'monospace', padding: '20px', backgroundColor: '#1e1e1e', color: '#d4d4d4', minHeight: '100vh' },
    header: { borderBottom: '2px solid #333', paddingBottom: '10px', marginBottom: '20px' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '30px' },
    card: { backgroundColor: '#252526', padding: '20px', borderRadius: '8px', border: '1px solid #333' },
    statusGreen: { color: '#4caf50', fontWeight: 'bold' },
    statusRed: { color: '#f44336', fontWeight: 'bold' },
    statusYellow: { color: '#ffeb3b', fontWeight: 'bold' },
    logContainer: { backgroundColor: '#000', padding: '15px', borderRadius: '4px', height: '300px', overflowY: 'scroll', fontSize: '12px' },
    logEntry: { marginBottom: '5px', borderBottom: '1px solid #222', paddingBottom: '5px' }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1>🏭 Warehouse Integration Simulator (WIS)</h1>
        <p>Broker Connection: <span style={connected ? styles.statusGreen : styles.statusRed}>{connected ? 'CONNECTED' : 'DISCONNECTED'}</span></p>
      </header>

      <div style={styles.grid}>
        {/* Robot State Card */}
        <div style={styles.card}>
          <h3>🤖 AMR-01 (Robot)</h3>
          <p>State: <span style={robotState === 'IDLE' ? styles.statusGreen : styles.statusYellow}>{robotState}</span></p>
          <p>Current Order: {currentOrder || 'None'}</p>
        </div>

        {/* Conveyor State Card */}
        <div style={styles.card}>
          <h3>⚙️ Conveyor-1 (PLC)</h3>
          <p>Dock 3 Sensor: <span style={sensorTriggered ? styles.statusGreen : styles.statusRed}>{sensorTriggered ? 'TRIGGERED (Pallet Here)' : 'CLEAR'}</span></p>
        </div>

        {/* Active Tasks Card */}
        <div style={styles.card}>
          <h3>📦 Active Logistics</h3>
          <p>System: <span style={styles.statusGreen}>OPERATIONAL</span></p>
          <p>Last known Order: {currentOrder || 'Awaiting...'}</p>
        </div>
      </div>

      <h3>📡 Live Integration Monitor (MQTT Event Bus)</h3>
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