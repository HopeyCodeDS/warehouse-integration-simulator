import { Canvas, useFrame } from '@react-three/fiber';
import { ContactShadows, Line, OrbitControls, Text } from '@react-three/drei';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { warehouse } from './data';

const dockColors = { FREE: '#708391', RESERVED: '#53a9ff', LOADING: '#20d3b2', FAULT: '#ff6879' };
const palletColors = ['#b9854c', '#c99a5e', '#8b6f4d', '#d0aa68'];

function Box({ position, args, color, metalness = 0, roughness = 0.7, emissive, intensity = 0 }) {
  return <mesh position={position} castShadow receiveShadow>
    <boxGeometry args={args} />
    <meshStandardMaterial color={color} metalness={metalness} roughness={roughness} emissive={emissive || color} emissiveIntensity={intensity} />
  </mesh>;
}

function Pallet({ position, color, label }) {
  return <group position={position}>
    <Box position={[0, 0.06, 0]} args={[0.82, 0.12, 0.72]} color="#9b633b" />
    <Box position={[0, 0.28, 0]} args={[0.7, 0.38, 0.58]} color={color} roughness={0.82} />
    <Box position={[0, 0.52, 0]} args={[0.62, 0.08, 0.52]} color="#d6b276" />
    {label && <Text position={[0, 0.57, 0.27]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.1} color="#26343b" anchorX="center" anchorY="middle">{label}</Text>}
  </group>;
}

function ShelfRack({ rack, selected, onSelect }) {
  const levels = [0.56, 1.48, 2.4];
  const posts = [-rack.w / 2 + 0.18, 0, rack.w / 2 - 0.18];
  const palletCount = Math.max(2, Math.round(rack.fill / 17));
  return <group position={[rack.x, 0, rack.z]} onClick={(event) => { event.stopPropagation(); onSelect(`Rack-${rack.id}`); }}>
    {posts.map((x) => <Box key={`post-${x}`} position={[x, 1.55, 0]} args={[0.12, 3.1, rack.d]} color={selected ? '#39d7b8' : '#658795'} metalness={0.7} roughness={0.35} />)}
    {levels.map((y, levelIndex) => <group key={y}>
      <Box position={[0, y, 0]} args={[rack.w, 0.1, rack.d]} color={selected ? '#287f78' : '#496c7a'} metalness={0.55} roughness={0.38} />
      {Array.from({ length: palletCount }, (_, palletIndex) => <Pallet key={`${levelIndex}-${palletIndex}`} position={[-rack.w / 2 + 0.68 + palletIndex * 1.1, y + 0.1, 0]} color={palletColors[(palletIndex + levelIndex) % palletColors.length]} label={levelIndex === 1 && palletIndex === 0 ? rack.id : null} />)}
    </group>)}
    <Box position={[0, 3.17, 0]} args={[rack.w + 0.16, 0.14, rack.d + 0.12]} color={selected ? '#39d7b8' : '#304e5e'} metalness={0.65} />
    <Text position={[0, 3.38, 0]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.19} color={selected ? '#7ff6df' : '#9ab5bb'} anchorX="center" anchorY="middle">RACK {rack.id}</Text>
  </group>;
}

function Conveyor({ belt, equipment }) {
  const running = Boolean(equipment.Running);
  const jammed = Boolean(equipment.Jam);
  const beltColor = jammed ? '#7f3340' : running ? '#2c7b72' : '#1b3a4a';
  const rollers = Array.from({ length: 12 }, (_, index) => -belt.w / 2 + 0.3 + index * ((belt.w - 0.6) / 11));
  return <group position={[belt.x, 0, belt.z]}>
    <Box position={[0, 0.26, 0]} args={[belt.w, 0.35, belt.d]} color={beltColor} metalness={0.7} roughness={0.36} />
    {rollers.map((x) => <mesh key={x} position={[x, 0.49, 0]} rotation={[0, 0, Math.PI / 2]}>
      <cylinderGeometry args={[0.16, 0.16, belt.d - 0.08, 16]} />
      <meshStandardMaterial color={running ? '#c2e2dc' : '#93a7aa'} metalness={0.85} roughness={0.24} />
    </mesh>)}
    <Box position={[0, 0.62, 0]} args={[belt.w - 0.18, 0.05, belt.d - 0.18]} color="#294f5e" metalness={0.2} roughness={0.48} />
    <Text position={[0, 0.72, -0.7]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.16} color={jammed ? '#ff6879' : running ? '#72f3d9' : '#b4cdd0'} anchorX="center" anchorY="middle">{belt.id.toUpperCase()} / {jammed ? 'JAM' : running ? 'RUNNING' : 'STOPPED'}</Text>
  </group>;
}

function Truck({ dock }) {
  const color = dock.state === 'LOADING' ? '#3e9c91' : '#344f60';
  return <group position={[dock.x + 2.25, 0, dock.z]}>
    <Box position={[0, 0.65, 0]} args={[3.2, 1.2, 2.15]} color={color} metalness={0.2} roughness={0.65} />
    <Box position={[1.85, 0.52, 0]} args={[0.75, 0.95, 2.05]} color="#66818a" metalness={0.15} roughness={0.6} />
    <Box position={[2.22, 0.84, 0]} args={[0.05, 0.34, 1.55]} color="#b7d4d4" roughness={0.35} />
    {[-0.7, 0.7].map((z) => <mesh key={z} position={[1.75, 0.12, z]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.28, 0.28, 0.18, 20]} /><meshStandardMaterial color="#101b20" roughness={0.9} /></mesh>)}
    {[-0.7, 0.7].map((z) => <mesh key={`rear-${z}`} position={[-1.05, 0.12, z]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.28, 0.28, 0.18, 20]} /><meshStandardMaterial color="#101b20" roughness={0.9} /></mesh>)}
  </group>;
}

function DockStation({ dock, selected, onSelect }) {
  const color = dockColors[dock.state];
  return <group position={[dock.x, 0, dock.z]} onClick={(event) => { event.stopPropagation(); onSelect(dock.id); }}>
    <Box position={[0, 0.08, 0]} args={[2.4, 0.16, 2.7]} color="#1d3b4a" roughness={0.75} />
    <Box position={[1.65, 0.04, 0]} args={[1.2, 0.08, 2.7]} color="#304b56" roughness={0.85} />
    <Box position={[0, 1.45, -1.2]} args={[2.4, 2.9, 0.12]} color={selected ? '#39d7b8' : '#446c79'} metalness={0.45} />
    <Box position={[0, 0.82, -1.05]} args={[1.7, 1.35, 0.08]} color={color} emissive={color} intensity={dock.state === 'LOADING' ? 0.35 : 0.08} />
    <Text position={[0, 2.98, -1.23]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.18} color={color} anchorX="center" anchorY="middle">{dock.id} / {dock.state}</Text>
    <Truck dock={dock} />
  </group>;
}

function AMR({ robot, selected, onSelect }) {
  const ref = useRef();
  const target = useMemo(() => new THREE.Vector3(robot.x, 0.38, robot.z), [robot.x, robot.z]);
  useFrame((_, delta) => { if (ref.current) ref.current.position.lerp(target, 1 - Math.pow(0.001, delta)); });
  return <group ref={ref} onClick={(event) => { event.stopPropagation(); onSelect(robot.id); }}>
    <Box position={[0, 0, 0]} args={[1.08, 0.32, 0.82]} color="#122b37" metalness={0.7} roughness={0.32} emissive={robot.color} intensity={selected ? 0.22 : 0.04} />
    <Box position={[0, 0.25, 0]} args={[0.72, 0.14, 0.56]} color={robot.color} metalness={0.35} roughness={0.36} />
    <Box position={[0, 0.38, -0.12]} args={[0.18, 0.18, 0.18]} color="#e8ffff" emissive="#e8ffff" intensity={1.6} />
    {[-0.32, 0.32].map((x) => <mesh key={x} position={[x, -0.18, 0]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.13, 0.13, 0.12, 16]} /><meshStandardMaterial color="#0a151b" roughness={0.85} /></mesh>)}
    <Text position={[0, 0.72, 0]} fontSize={0.17} color={robot.color} anchorX="center" anchorY="middle">{robot.id}</Text>
  </group>;
}

function AisleMarkings() {
  return <group>
    {[ -7.15, -3.95, 2.05, 5.05 ].map((z) => <mesh key={z} position={[-2.9, 0.012, z]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[5.8, 0.045]} /><meshBasicMaterial color="#c19b56" transparent opacity={0.5} /></mesh>)}
    <Text position={[-3.9, 0.03, 8.1]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.22} color="#698692" anchorX="center" anchorY="middle">AMR TRAFFIC AISLE</Text>
  </group>;
}

export function WarehouseScene({ robots, selected, setSelected, equipment = {} }) {
  return <Canvas camera={{ position: [25, 22, 26], fov: 42 }} shadows dpr={[1, 2]}>
    <color attach="background" args={['#081723']} />
    <fog attach="fog" args={['#081723', 30, 60]} />
    <ambientLight intensity={0.62} />
    <directionalLight position={[8, 22, 12]} intensity={2.3} castShadow shadow-mapSize={[2048, 2048]} />
    <pointLight position={[-10, 6, -8]} color="#27cdb5" intensity={10} distance={22} />
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow onClick={() => setSelected('floor')}><planeGeometry args={[warehouse.width, warehouse.depth]} /><meshStandardMaterial color="#0d222e" roughness={0.92} /></mesh>
    <gridHelper args={[warehouse.width, warehouse.width, '#294b59', '#173442']} position={[0, 0.02, 0]} />
    <AisleMarkings />
    {robots.filter((robot) => robot.route?.length > 1).map((robot) => <Line key={`route-${robot.id}`} points={robot.route.map((routePoint) => [routePoint.x, 0.035, routePoint.z])} color={robot.color} lineWidth={1.4} dashed dashSize={0.35} gapSize={0.22} />)}
    {warehouse.racks.map((rack) => <ShelfRack key={rack.id} rack={rack} selected={selected === `Rack-${rack.id}`} onSelect={setSelected} />)}
    {warehouse.docks.map((dock) => <DockStation key={dock.id} dock={dock} selected={selected === dock.id} onSelect={setSelected} />)}
    {warehouse.conveyors.map((belt) => <Conveyor key={belt.id} belt={belt} equipment={equipment} />)}
    {robots.map((robot) => <AMR key={robot.id} robot={robot} selected={selected === robot.id} onSelect={setSelected} />)}
    <ContactShadows position={[0, 0.04, 0]} opacity={0.58} scale={35} blur={2.5} far={12} />
    <OrbitControls enablePan={false} minDistance={15} maxDistance={42} maxPolarAngle={Math.PI / 2.15} target={[0, 0, 0]} />
  </Canvas>;
}
