import { useEffect, useRef, useState } from 'react';
import { Circle, Group, Layer, Line, Rect, Stage, Text } from 'react-konva';
import { warehouseLayout } from '../data/warehouseLayout';

const robotRoute = warehouseLayout.route;

const stateColors = {
  IDLE: '#5e7181',
  MOVING: '#35d0ba',
  DOCKED: '#ffbd5c',
  UNKNOWN: '#ef6d7a',
};

function EquipmentTag({ x, y, label, tone = '#6d8192' }) {
  return <Text x={x} y={y} text={label} fontFamily="IBM Plex Mono" fontSize={10} fill={tone} letterSpacing={1.4} />;
}

export function WarehouseFloor({ robot, activeTask, sensorActive, onSelect }) {
  const [robotPosition, setRobotPosition] = useState(warehouseLayout.home);
  const positionRef = useRef(warehouseLayout.home);
  const animationRef = useRef(null);
  const robotColor = stateColors[robot.state] || stateColors.UNKNOWN;
  const destination = activeTask?.payload?.destination_dock || 'Dock-3';
  const dock = warehouseLayout.docks.find((item) => item.id === destination) || warehouseLayout.docks[2];

  useEffect(() => {
    const target = robot.state === 'DOCKED' ? { x: dock.x - 48, y: dock.y + 32 } : robot.state === 'MOVING' ? robotRoute[robotRoute.length - 2] : warehouseLayout.home;
    const start = positionRef.current;
    const startedAt = performance.now();
    const duration = robot.state === 'MOVING' ? 3000 : 650;

    const tick = (now) => {
      const progress = Math.min((now - startedAt) / duration, 1);
      const eased = progress * (2 - progress);
      const nextPosition = { x: start.x + (target.x - start.x) * eased, y: start.y + (target.y - start.y) * eased };
      positionRef.current = nextPosition;
      setRobotPosition(nextPosition);
      if (progress < 1) animationRef.current = requestAnimationFrame(tick);
    };

    animationRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationRef.current);
  }, [robot.state, dock.x, dock.y]);

  return (
    <div className="floor-shell">
      <div className="floor-toolbar">
        <div><span className="eyebrow">LIVE FLOOR</span><strong>WAREHOUSE / NORTH HALL</strong></div>
        <div className="floor-legend"><span><i className="legend-dot cyan" />Robot route</span><span><i className="legend-dot amber" />Dock activity</span></div>
      </div>
      <div className="canvas-wrap" onClick={() => onSelect('floor')}>
        <Stage width={warehouseLayout.width} height={warehouseLayout.height} onClick={(event) => event.target === event.target.getStage() && onSelect('floor')}>
          <Layer>
            <Rect width={980} height={560} fill="#101a20" />
            {Array.from({ length: 13 }, (_, index) => <Line key={`h-${index}`} points={[0, index * 44, 980, index * 44]} stroke="#1b2a31" strokeWidth={1} />)}
            {Array.from({ length: 23 }, (_, index) => <Line key={`v-${index}`} points={[index * 44, 0, index * 44, 560]} stroke="#17262d" strokeWidth={1} />)}
            <Text x={30} y={25} text="NORTH HALL / ZONE 01" fontFamily="IBM Plex Mono" fontSize={11} fill="#516773" letterSpacing={2} />
            <Text x={690} y={25} text="LIVE SCHEMATIC" fontFamily="IBM Plex Mono" fontSize={10} fill="#35d0ba" letterSpacing={1.6} />

            {warehouseLayout.racks.map((rack) => <Group key={rack.id} onClick={(event) => { event.cancelBubble = true; onSelect(rack.id); }}>
              <Rect x={rack.x} y={rack.y} width={rack.width} height={rack.height} fill="#16242b" stroke="#314750" strokeWidth={1} cornerRadius={4} />
              <Rect x={rack.x + 10} y={rack.y + 12} width={4} height={rack.height - 24} fill="#35d0ba" opacity={0.7} />
              <Text x={rack.x + 25} y={rack.y + 15} text={rack.label} fontFamily="IBM Plex Mono" fontSize={12} fill="#dce8e9" letterSpacing={1} />
              <Text x={rack.x + 25} y={rack.y + 40} text={rack.sublabel} fontFamily="IBM Plex Mono" fontSize={10} fill="#708995" />
            </Group>)}

            {warehouseLayout.conveyors.map((conveyor) => <Group key={conveyor.id}>
              <Rect x={conveyor.x} y={conveyor.y} width={conveyor.width} height={conveyor.height} fill="#1a2b31" stroke="#47606a" strokeWidth={1} cornerRadius={19} />
              {Array.from({ length: 6 }, (_, index) => <Line key={index} points={[conveyor.x + 18 + index * 28, conveyor.y + 8, conveyor.x + 18 + index * 28, conveyor.y + conveyor.height - 8]} stroke="#55727a" strokeWidth={2} opacity={0.8} />)}
              <Text x={conveyor.x + 12} y={conveyor.y + 13} text={conveyor.label} fontFamily="IBM Plex Mono" fontSize={9} fill="#8ba1a7" letterSpacing={1} />
            </Group>)}

            {warehouseLayout.docks.map((item) => {
              const active = item.id === destination && robot.state === 'DOCKED';
              return <Group key={item.id} onClick={(event) => { event.cancelBubble = true; onSelect(item.id); }}>
                <Rect x={item.x} y={item.y} width={item.width} height={item.height} fill={active ? '#40311e' : '#17262d'} stroke={active ? '#ffbd5c' : '#3b525b'} strokeWidth={active ? 2 : 1} cornerRadius={4} />
                <Rect x={item.x + 15} y={item.y + 15} width={8} height={item.height - 30} fill={active ? '#ffbd5c' : '#36515a'} />
                <Text x={item.x + 38} y={item.y + 17} text={item.label} fontFamily="IBM Plex Mono" fontSize={12} fill={active ? '#ffcf7d' : '#dce8e9'} letterSpacing={1} />
                <Text x={item.x + 38} y={item.y + 38} text={active ? 'ROBOT DOCKED' : 'AVAILABLE'} fontFamily="IBM Plex Mono" fontSize={9} fill={active ? '#ffbd5c' : '#607680'} />
              </Group>;
            })}

            <Line points={robotRoute.flatMap((point) => [point.x, point.y])} stroke="#234842" strokeWidth={2} dash={[8, 8]} opacity={0.9} />
            <Circle x={780} y={282} radius={sensorActive ? 16 : 8} fill="#ef6d7a" opacity={sensorActive ? 0.2 : 0.12} />
            <Circle x={780} y={282} radius={5} fill={sensorActive ? '#ef6d7a' : '#6d434a'} />
            <EquipmentTag x={760} y={326} label="SENSOR / DOCK 03" tone={sensorActive ? '#ef6d7a' : '#6d8192'} />
            <Group x={robotPosition.x} y={robotPosition.y} onClick={(event) => { event.cancelBubble = true; onSelect('AMR-Ultra'); }}>
              <Circle radius={25} fill={robotColor} opacity={0.11} />
              <Rect x={-18} y={-15} width={36} height={30} fill="#182d31" stroke={robotColor} strokeWidth={2} cornerRadius={7} shadowColor={robotColor} shadowBlur={robot.state === 'MOVING' ? 15 : 5} />
              <Circle x={-8} y={0} radius={3} fill={robotColor} />
              <Circle x={8} y={0} radius={3} fill={robotColor} />
              <Text x={-18} y={34} text="AMR-Ultra" fontFamily="IBM Plex Mono" fontSize={10} fill="#dce8e9" />
              <Text x={-18} y={48} text={robot.state} fontFamily="IBM Plex Mono" fontSize={9} fill={robotColor} />
            </Group>
          </Layer>
        </Stage>
      </div>
    </div>
  );
}
