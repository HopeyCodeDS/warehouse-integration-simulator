export const warehouse = {
  width: 32,
  depth: 18,
  racks: [
    { id: 'A1', x: -10, z: -5.5, w: 7, d: 1.7, fill: 82 },
    { id: 'A2', x: -10, z: -2.8, w: 7, d: 1.7, fill: 65 },
    { id: 'B1', x: -10, z: 0.2, w: 7, d: 1.7, fill: 91 },
    { id: 'B2', x: -10, z: 3.2, w: 7, d: 1.7, fill: 48 },
    { id: 'C1', x: -10, z: 6.2, w: 7, d: 1.7, fill: 73 },
    { id: 'D1', x: 0, z: -5.5, w: 7, d: 1.7, fill: 55 },
    { id: 'D2', x: 0, z: -2.8, w: 7, d: 1.7, fill: 77 },
    { id: 'E1', x: 0, z: 3.2, w: 7, d: 1.7, fill: 68 },
    { id: 'E2', x: 0, z: 6.2, w: 7, d: 1.7, fill: 39 },
  ],
  docks: [
    { id: 'Dock-1', x: 11.8, z: -5.2, state: 'FREE' },
    { id: 'Dock-2', x: 11.8, z: -1.8, state: 'LOADING' },
    { id: 'Dock-3', x: 11.8, z: 1.6, state: 'RESERVED' },
    { id: 'Dock-4', x: 11.8, z: 5, state: 'FAULT' },
  ],
  conveyors: [
    { id: 'Inbound', x: 5.6, z: -5.2, w: 7, d: 1.1 },
    { id: 'Sort', x: 5.6, z: 0, w: 7, d: 1.1 },
    { id: 'Outbound', x: 5.6, z: 5.2, w: 7, d: 1.1 },
  ],
  robots: [
    { id: 'AMR-Ultra', x: 2.5, z: 3.3, state: 'MOVING', battery: 87, color: '#21d3b2', task: 'Pallet #204' },
    { id: 'AMR-Nova', x: 3.7, z: -0.2, state: 'IDLE', battery: 92, color: '#55aaff', task: 'Standby' },
    { id: 'AMR-Orbit', x: -3.5, z: 7, state: 'IDLE', battery: 76, color: '#b48cff', task: 'Standby' },
    { id: 'AMR-Vega', x: 9, z: 4.2, state: 'DOCKED', battery: 64, color: '#ffbf62', task: 'Pallet #198' },
  ],
};

export const orders = [
  { id: 'ORD-204', customer: 'Toyota', task: 'Pallet #204', status: 'Picking', progress: 66 },
  { id: 'ORD-203', customer: 'Bosch', task: 'Pallet #201', status: 'In Transit', progress: 48 },
  { id: 'ORD-202', customer: 'Volvo', task: 'Pallet #198', status: 'Completed', progress: 100 },
  { id: 'ORD-201', customer: 'Toyota', task: 'Pallet #184', status: 'Completed', progress: 100 },
];

export const events = [
  { time: '14:42:08', topic: 'robot/state', text: 'AMR-Ultra reached waypoint B-03' },
  { time: '14:41:52', topic: 'wms/task', text: 'ORD-204 pick task acknowledged' },
  { time: '14:41:16', topic: 'dock/sensor', text: 'Dock-2 loading sensor active' },
  { time: '14:40:58', topic: 'erp/order', text: 'ORD-203 released to integration engine' },
];
