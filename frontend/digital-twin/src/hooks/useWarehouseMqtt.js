import { useEffect, useState } from 'react';
import mqtt from 'mqtt';

const MQTT_BROKER_WS = 'ws://localhost:9001';

const withoutNulls = (value) => {
  if (Array.isArray(value)) return value.map(withoutNulls);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([, item]) => item !== null)
        .map(([key, item]) => [key, withoutNulls(item)])
    );
  }
  return value;
};

const formatPayload = (payload) => JSON.stringify(withoutNulls(payload));

export function useWarehouseMqtt() {
  const [connected, setConnected] = useState(false);
  const [robot, setRobot] = useState({ robotId: 'AMR-Ultra', state: 'IDLE', orderNumber: null, correlationId: null });
  const [activeTask, setActiveTask] = useState(null);
  const [sensorActive, setSensorActive] = useState(false);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const client = mqtt.connect(MQTT_BROKER_WS);

    const addEvent = (topic, payload, severity = 'info') => {
      setEvents((current) => [{
        id: `${Date.now()}-${Math.random()}`,
        time: new Date(),
        topic,
        payload,
        severity,
      }, ...current].slice(0, 80));
    };

    client.on('connect', () => {
      setConnected(true);
      client.subscribe('warehouse/#');
      addEvent('SYSTEM', { message: 'Dashboard connected to MQTT Broker' }, 'success');
    });

    client.on('reconnect', () => setConnected(false));
    client.on('close', () => setConnected(false));
    client.on('error', (error) => addEvent('MQTT ERROR', { message: error.message }, 'error'));

    client.on('message', (topic, message) => {
      try {
        const payload = JSON.parse(message.toString());
        addEvent(topic, payload);

        if (topic === 'warehouse/robot/state') {
          setRobot({
            robotId: payload.robot_id || 'AMR-Ultra',
            state: payload.state || 'UNKNOWN',
            orderNumber: payload.order_number || null,
            correlationId: payload.correlation_id || null,
          });
        }

        if (topic === 'warehouse/tasks/new') setActiveTask(payload);
        if (topic === 'warehouse/events/sensor' && payload.event === 'PALLET_ARRIVED') {
          setSensorActive(true);
          window.setTimeout(() => setSensorActive(false), 2200);
        }
        if (topic === 'warehouse/orders/completed') {
          setActiveTask((task) => task && task.order_number === payload.order_number ? { ...task, status: 'COMPLETED' } : task);
        }
      } catch (error) {
        addEvent('MQTT PARSE ERROR', { message: error.message }, 'error');
      }
    });

    return () => client.end(true);
  }, []);

  return { connected, robot, activeTask, sensorActive, events, formatPayload };
}
