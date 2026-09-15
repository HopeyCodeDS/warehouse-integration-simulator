import { useEffect, useState } from 'react';
import mqtt from 'mqtt';
import { events as seedEvents, orders as seedOrders, warehouse } from './data';

export function useWarehouseState() {
  const [connected, setConnected] = useState(false);
  const [robots, setRobots] = useState(Object.fromEntries(warehouse.robots.map((robot) => [robot.id, { ...robot, lastSeen: 'Demo telemetry' }])));
  const [events, setEvents] = useState(seedEvents);
  const [orders, setOrders] = useState(seedOrders);
  const [sensorActive, setSensorActive] = useState(true);

  useEffect(() => {
    const client = mqtt.connect('ws://localhost:9001', { reconnectPeriod: 4000, connectTimeout: 2500 });
    const addEvent = (topic, text) => setEvents((current) => [{ time: new Date().toLocaleTimeString('en-GB', { hour12: false }), topic, text }, ...current].slice(0, 8));
    client.on('connect', () => { setConnected(true); client.subscribe('warehouse/#'); addEvent('system', 'MQTT broker connected'); });
    client.on('reconnect', () => setConnected(false));
    client.on('close', () => setConnected(false));
    client.on('error', () => setConnected(false));
    client.on('message', (topic, message) => {
      try {
        const payload = JSON.parse(message.toString());
        addEvent(topic, `${payload.robot_id || payload.order_number || 'Telemetry'} updated`);
        if (topic.includes('robot')) {
          const id = payload.robot_id || 'AMR-Ultra';
          setRobots((current) => ({ ...current, [id]: { ...(current[id] || warehouse.robots[0]), ...payload, id, x: payload.position?.x ?? current[id]?.x, z: payload.position?.z ?? current[id]?.z, lastSeen: 'Live telemetry' } }));
        }
        if (topic.includes('sensor')) setSensorActive(payload.event === 'PALLET_ARRIVED');
      } catch { addEvent('mqtt/error', 'Unable to parse incoming payload'); }
    });
    return () => client.end(true);
  }, []);

  return { connected, robots: Object.values(robots), events, orders, sensorActive, setOrders };
}
