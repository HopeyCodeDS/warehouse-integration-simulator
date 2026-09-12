export const warehouseLayout = {
  width: 980,
  height: 560,
  route: [
    { x: 146, y: 438 },
    { x: 310, y: 438 },
    { x: 310, y: 310 },
    { x: 532, y: 310 },
    { x: 532, y: 170 },
    { x: 780, y: 170 },
  ],
  racks: [
    { id: 'Rack-A1', x: 82, y: 86, width: 160, height: 74, label: 'RACK A1', sublabel: 'P100 / 18' },
    { id: 'Rack-A2', x: 82, y: 184, width: 160, height: 74, label: 'RACK A2', sublabel: 'P200 / 12' },
    { id: 'Rack-B1', x: 290, y: 86, width: 160, height: 74, label: 'RACK B1', sublabel: 'P300 / 26' },
    { id: 'Staging-A', x: 290, y: 184, width: 160, height: 74, label: 'STAGING A', sublabel: 'READY' },
  ],
  docks: [
    { id: 'Dock-1', x: 760, y: 78, width: 150, height: 64, label: 'DOCK 01' },
    { id: 'Dock-2', x: 760, y: 164, width: 150, height: 64, label: 'DOCK 02' },
    { id: 'Dock-3', x: 760, y: 250, width: 150, height: 64, label: 'DOCK 03' },
  ],
  conveyors: [
    { id: 'Conveyor-1', x: 492, y: 86, width: 178, height: 38, label: 'CONVEYOR 01' },
    { id: 'Conveyor-2', x: 492, y: 388, width: 178, height: 38, label: 'CONVEYOR 02' },
  ],
  home: { x: 146, y: 438 },
};
