import { useEffect, useState } from 'react';
import mqtt from 'mqtt';
import { events as seedEvents, orders as seedOrders, warehouse } from './data';

const simulatorMap = { width: 980, height: 560 };
function toWorldPoint(point, isWorld = false) {
  if (!point) return null;
  if (isWorld || point.z !== undefined) return { x: Number(point.x), z: Number(point.z) };
  return {
    x: (Number(point.x) / simulatorMap.width) * warehouse.width - warehouse.width / 2,
    z: (Number(point.y ?? point.z) / simulatorMap.height) * warehouse.depth - warehouse.depth / 2,
  };
}

function normalizeRoute(route) {
  return Array.isArray(route) ? route.map((point) => toWorldPoint(point, point.z !== undefined)).filter(Boolean) : [];
}

function normalizeRobot(payload, currentRobot) {
  const position = toWorldPoint(payload.world_position || payload.position, Boolean(payload.world_position));
  return {
    ...(currentRobot || warehouse.robots[0]),
    ...payload,
    id: payload.robot_id || currentRobot?.id || warehouse.robots[0].id,
    x: position?.x ?? currentRobot?.x ?? warehouse.robots[0].x,
    z: position?.z ?? currentRobot?.z ?? warehouse.robots[0].z,
    route: normalizeRoute(payload.route),
    task: payload.state === 'IDLE' ? 'Standby' : payload.order_number || currentRobot?.task || 'Standby',
    lastSeen: 'Live telemetry',
  };
}

export function useWarehouseState() {
  const [connected, setConnected] = useState(false);
  const [robots, setRobots] = useState(Object.fromEntries(warehouse.robots.map((robot) => [robot.id, { ...robot, lastSeen: 'Demo telemetry' }])));
  const [events, setEvents] = useState(seedEvents);
  const [orders, setOrders] = useState(seedOrders);
  const [sensorActive, setSensorActive] = useState(true);
  const [equipment, setEquipment] = useState({});
  const [simulation, setSimulation] = useState({ status: 'RUNNING', speed: 1, tick: 0, run_id: 'local-run', scenario: 'default' });

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
        if (topic === 'warehouse/tasks/new') {
          const orderNumber = payload.order_number;
          setOrders((current) => current.map((order) => order.id === orderNumber ? { ...order, status: 'Dispatched', progress: 10, robot: 'Assigning' } : order));
          addEvent(topic, `${orderNumber || 'Task'} dispatched to robot fleet`);
        }
        if (topic === 'warehouse/tasks/completed') {
          const orderNumber = payload.order_number;
          setOrders((current) => current.map((order) => order.id === orderNumber ? { ...order, status: 'Completed', progress: 100, robot: payload.robot_id } : order));
          addEvent(topic, `${orderNumber || 'Task'} completed by ${payload.robot_id || 'robot'}`);
        }
        if (topic.includes('robot')) {
          const id = payload.robot_id || 'AMR-Ultra';
          setRobots((current) => ({ ...current, [id]: normalizeRobot(payload, current[id]) }));
          if (payload.order_number) {
            const progress = payload.state === 'MOVING' ? 55 : payload.state === 'DOCKED' ? 88 : undefined;
            const status = payload.state === 'MOVING' ? 'In Transit' : payload.state === 'DOCKED' ? 'At Dock' : undefined;
            if (progress && status) setOrders((current) => current.map((order) => order.id === payload.order_number ? { ...order, status, progress, robot: id } : order));
          }
        }
        if (topic.includes('sensor')) setSensorActive(payload.event === 'PALLET_ARRIVED');
        if (topic === 'warehouse/equipment/state') {
          setEquipment((current) => ({ ...current, [payload.tag]: payload.value }));
          addEvent(topic, `${payload.tag}: ${String(payload.value)}`);
        }
        if (topic === 'warehouse/simulation/state') setSimulation((current) => ({ ...current, ...payload }));
      } catch { addEvent('mqtt/error', 'Unable to parse incoming payload'); }
    });
    return () => client.end(true);
  }, []);

  const sendSimulationCommand = (command, value) => {
    if (client.connected) client.publish('warehouse/simulation/command', JSON.stringify({ command, value }), { qos: 1 });
  };
  return { connected, robots: Object.values(robots), events, orders, sensorActive, equipment, simulation, sendSimulationCommand, setOrders };
}
