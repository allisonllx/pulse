'use client';
import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { ContactShadows, OrbitControls, RoundedBox } from '@react-three/drei';
import * as THREE from 'three';
import { AppearanceEvent, PLATFORMS, Source, Topic } from '@/lib/recording';
import { visitorPopulation, VisualVisitor } from '@/lib/visitors';
import { buildNeighborhoodLayout } from '@/lib/neighborhoods';

const colors = ['#e8c6a2', '#bed0b6', '#d0c5d9', '#e0bbb0', '#e3d5ab', '#b9ccd3'];
function hash(value: string) { let n = 0; for (const c of value) n = (n * 31 + c.charCodeAt(0)) >>> 0; return n; }
export function positionFor(id: string): [number, number] {
  // Stable IDs occupy deterministic lots; collision resolution happens in layoutFor.
  const n = hash(id); return [((n % 5) - 2) * 3.2, ((Math.floor(n / 5) % 4) - 1.5) * 3.2];
}
function FloatingLabel({ label, detail, position, color, small = false, dimmed = false }: { label: string; detail?: string; position: [number, number, number]; color: string; small?: boolean; dimmed?: boolean }) {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas'); canvas.width = 768; canvas.height = 192;
    const context = canvas.getContext('2d')!;
    context.fillStyle = '#fbf3e5'; context.beginPath(); context.roundRect(16, 20, 736, 150, 70); context.fill();
    context.strokeStyle = color; context.lineWidth = 10; context.stroke();
    context.fillStyle = '#393f35'; context.textAlign = 'center'; context.textBaseline = 'middle';
    context.font = '700 76px sans-serif'; context.fillText(label, 384, detail ? 74 : 94, 670);
    if (detail) { context.font = '500 42px sans-serif'; context.fillStyle = '#657060'; context.fillText(detail, 384, 132, 660); }
    const map = new THREE.CanvasTexture(canvas); map.colorSpace = THREE.SRGBColorSpace; return map;
  }, [label, detail, color, small]);
  useEffect(() => () => texture.dispose(), [texture]);
  return <sprite position={position} scale={small ? [4.6, 1.15, 1] : [6.6, 1.65, 1]} renderOrder={20}>
    <spriteMaterial map={texture} transparent depthTest={false} depthWrite={false} opacity={dimmed ? .42 : 1} toneMapped={false} />
  </sprite>;
}

function Tree({ x, z }: { x: number; z: number }) {
  return <group position={[x, 0, z]}>
    <mesh position={[0, .45, 0]} castShadow><cylinderGeometry args={[.06, .08, .9, 6]} /><meshStandardMaterial color="#867759" /></mesh>
    <mesh position={[0, 1.1, 0]} castShadow><icosahedronGeometry args={[.48, 1]} /><meshStandardMaterial color="#56796b" flatShading /></mesh>
  </group>;
}
function ShopSign({ label,muted=false }: { label: string;muted?:boolean }) {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas'); canvas.width = 512; canvas.height = 96;
    const context = canvas.getContext('2d')!; context.fillStyle = '#f7ecd9'; context.fillRect(0, 0, 512, 96);
    context.fillStyle = '#493c31'; context.font = `600 ${label.length > 20 ? 28 : 34}px sans-serif`; context.textAlign = 'center'; context.textBaseline = 'middle';
    context.fillText(label, 256, 48, 475); const map = new THREE.CanvasTexture(canvas); map.colorSpace = THREE.SRGBColorSpace; return map;
  }, [label]);
  useEffect(() => () => texture.dispose(), [texture]);
  return <mesh position={[0, 1.2, .85]}><planeGeometry args={[1.65, .31]} /><meshStandardMaterial color={muted?'#999999':'#ffffff'} map={texture} roughness={.9} /></mesh>;
}
function Lamp({ x, z }: { x: number; z: number }) {
  return <group position={[x, 0, z]}>
    <mesh position={[0, .58, 0]} castShadow><cylinderGeometry args={[.025, .04, 1.16, 6]} /><meshStandardMaterial color="#4c514a" /></mesh>
    <mesh position={[0, 1.22, 0]}><boxGeometry args={[.16, .22, .16]} /><meshStandardMaterial color="#ffe8b0" emissive="#ffc77b" emissiveIntensity={1.7} /></mesh>
    <mesh position={[0, 1.36, 0]}><coneGeometry args={[.15, .1, 4]} /><meshStandardMaterial color="#4c514a" /></mesh>
    <mesh rotation={[-Math.PI/2,0,0]} position={[0,.03,0]}><circleGeometry args={[.4,24]} /><meshBasicMaterial color="#ffd99a" transparent opacity={.14} depthWrite={false} /></mesh>
  </group>;
}
function Building({ topic, position, selected, dimmed, muted, onSelect }: { topic: Topic; position: [number, number]; selected: boolean; dimmed: boolean; muted: boolean; onSelect: (id: string) => void }) {
  const [hovered, setHovered] = useState(false);
  const n = hash(topic.id), height = .9 + Math.min(2.8, Math.sqrt(topic.score) * .8);
  const shade=(value:string)=>new THREE.Color(value).multiplyScalar(muted?.52:1);
  const color = shade(colors[n % colors.length]);
  return <group position={[position[0], 0, position[1]]} onClick={e => { e.stopPropagation(); onSelect(topic.id); }} onPointerOver={e => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }} onPointerOut={() => { setHovered(false); document.body.style.cursor = ''; }}>
    <RoundedBox args={[2.7, .16, 2.7]} radius={.1} position={[0, .08, 0]} receiveShadow><meshStandardMaterial color={shade(selected ? '#efe2bb' : '#c5bca9')} transparent opacity={dimmed ? .25 : 1} /></RoundedBox>
    <RoundedBox args={[1.8, height, 1.65]} radius={.055} position={[0, height / 2 + .16, 0]} castShadow receiveShadow><meshStandardMaterial color={color} transparent opacity={dimmed ? .22 : 1} /></RoundedBox>
    {n % 3 === 0 ? <mesh position={[0, height + .27, 0]} rotation={[0, Math.PI / 4, 0]} castShadow><cylinderGeometry args={[0, 1.5, .6, 4]} /><meshStandardMaterial color={color.clone().multiplyScalar(.7)} transparent opacity={dimmed ? .2 : 1} /></mesh> : <group position={[0,height+.2,0]}>
      <mesh castShadow><boxGeometry args={[1.93,.12,1.78]} /><meshStandardMaterial color={shade("#b4977d")} transparent opacity={dimmed?.2:1} /></mesh>
      <mesh position={[-.4,.15,-.2]} castShadow><boxGeometry args={[.42,.25,.4]} /><meshStandardMaterial color={shade("#d9d4c3")} transparent opacity={dimmed?.2:1} /></mesh>
      <mesh position={[-.4,.15,.006]}><circleGeometry args={[.12,8]} /><meshStandardMaterial color={shade("#6a736e")} /></mesh>
      <mesh position={[.48,.11,-.4]} castShadow><boxGeometry args={[.4,.16,.32]} /><meshStandardMaterial color={shade("#c7c5b3")} transparent opacity={dimmed?.2:1} /></mesh>
    </group>}
    <mesh position={[0, .59, .837]}><planeGeometry args={[.46, .75]} /><meshStandardMaterial color={shade("#293a38")} emissive={selected || hovered ? '#e5c884' : '#b08b54'} emissiveIntensity={selected ? .8 : muted ? .02 : .2} /></mesh>
    {[-.57, .57].map(x => <mesh key={x} position={[x, .78, .84]}><planeGeometry args={[.38, .38]} /><meshStandardMaterial color={shade("#f8dea2")} emissive="#e8be76" emissiveIntensity={dimmed ? 0 : muted ? .04 : .35} transparent opacity={dimmed ? .15 : 1} /></mesh>)}
    <group position={[0, 1.03, 1.04]} rotation={[.22, 0, 0]}>{Array.from({length:8},(_,i)=><mesh key={i} position={[(i-3.5)*.23,0,0]} castShadow><boxGeometry args={[.23,.055,.52]} /><meshStandardMaterial color={shade(i%2===0?colors[(n+3)%colors.length]:'#f9eed8')} transparent opacity={dimmed?.2:1} /></mesh>)}</group>
    {!dimmed && <ShopSign muted={muted} label={topic.label.length>32?topic.label.slice(0,29)+'…':topic.label} />}
    <group position={[-.75,.26,1.08]}><mesh castShadow><boxGeometry args={[.24,.24,.22]} /><meshStandardMaterial color={shade("#a98063")} /></mesh><mesh position={[0,.2,0]}><icosahedronGeometry args={[.19,0]} /><meshStandardMaterial color={shade("#789765")} /></mesh></group>
    {selected && <><Lamp x={-1.15} z={1.13}/><Lamp x={1.15} z={1.13}/></>}
    {height > 1.9 && [-.55, 0, .55].map(x => <mesh key={x} position={[x, 1.65, .84]}><planeGeometry args={[.25, .37]} /><meshStandardMaterial color={shade("#dccfaf")} transparent opacity={dimmed ? .2 : 1} /></mesh>)}
    {(selected || hovered) && <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, .19, 0]}><ringGeometry args={[1.48, 1.55, 48]} /><meshBasicMaterial color="#d9f2a6" /></mesh>}
  </group>;
}
function Visitors({ events, lots, entrances, reduced, animate }: { events: VisualVisitor[]; lots: Map<string, [number, number]>; entrances: Map<Source, [number, number]>; reduced: boolean; animate: boolean }) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const heads = useRef<THREE.InstancedMesh>(null);
  const hair = useRef<THREE.InstancedMesh>(null);
  const clock = useRef(0);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const people = useMemo(() => events.filter(e => lots.has(e.topicId)).map((e, i) => ({ ...e, end: lots.get(e.topicId)!, entry: entrances.get(e.source) ?? lots.get(e.topicId)!, delay: (i / Math.max(events.length, 1)) * 5, color: PLATFORMS.find(p => p.id === e.source)?.color ?? '#fff' })), [events, lots, entrances]);
  useFrame((_, delta) => {
    if (!mesh.current) return;
    if (animate && !reduced) clock.current += Math.min(delta, .1);
    people.forEach((p, i) => {
      const progress = reduced || p.stationary ? 1 : Math.max(0, Math.min(1, (clock.current - p.delay) / 4));
      const t = p.kind === 'departure' ? 1 - progress : progress;
      const [startX, startZ] = p.entry;
      const bend = .62;
      const q = p.queueIndex ?? i % 10;
      const queueX = p.end[0] + (q % 5 - 2) * .23;
      const queueZ = p.end[1] + 1.04 + Math.floor(q / 5) * .22;
      const x = t < bend ? THREE.MathUtils.lerp(startX, queueX, t / bend) : queueX;
      const z = t < bend ? startZ : THREE.MathUtils.lerp(startZ, queueZ, (t - bend) / (1 - bend));
      const show = p.kind === 'departure' ? !reduced && clock.current >= p.delay && progress < 1 : reduced || p.stationary || clock.current >= p.delay;
      const bob = !reduced && animate ? Math.sin(clock.current * 11 + i) * .015 : 0;
      dummy.position.set(x, .29+bob, z); dummy.scale.set(show?.15:0,show?.22:0,show?.12:0); dummy.updateMatrix();
      mesh.current!.setMatrixAt(i, dummy.matrix); mesh.current!.setColorAt(i, new THREE.Color(p.color));
      dummy.position.y=.47+bob; dummy.scale.setScalar(show?.13:0);dummy.updateMatrix();heads.current?.setMatrixAt(i,dummy.matrix);
      dummy.position.y=.54+bob;dummy.scale.set(show?.14:0,show?.05:0,show?.14:0);dummy.updateMatrix();hair.current?.setMatrixAt(i,dummy.matrix);
    });
    mesh.current.instanceMatrix.needsUpdate = true;
    if (mesh.current.instanceColor) mesh.current.instanceColor.needsUpdate = true;
    if(heads.current)heads.current.instanceMatrix.needsUpdate=true;
    if(hair.current)hair.current.instanceMatrix.needsUpdate=true;
  });
  return people.length ? <><instancedMesh ref={mesh} args={[undefined, undefined, people.length]} frustumCulled={false} castShadow><boxGeometry /><meshStandardMaterial roughness={.9} /></instancedMesh><instancedMesh ref={heads} args={[undefined,undefined,people.length]} frustumCulled={false}><boxGeometry /><meshStandardMaterial color="#e3ba93" /></instancedMesh><instancedMesh ref={hair} args={[undefined,undefined,people.length]} frustumCulled={false}><boxGeometry /><meshStandardMaterial color="#6c5142" /></instancedMesh></> : null;
}
function Diorama({ allTopics, visible, selected, events, onSelect, reduced, animate, frameKey }: CityProps) {
  const layout = useMemo(() => buildNeighborhoodLayout(allTopics), [allTopics]);
  const sources = useMemo(() => {
    const observed = new Set(allTopics.flatMap(topic => topic.items.map(item => item.source)));
    return PLATFORMS.filter(platform => observed.has(platform.id));
  }, [allTopics]);
  const entranceWidth = sources.length ? 4.8 : 0;
  const cityWidth = layout.width + entranceWidth;
  const cityDepth = Math.max(layout.depth, sources.length * 2.8 + 2);
  const entranceX = -layout.width / 2 - entranceWidth / 2;
  const entrances = useMemo(() => new Map<Source, [number, number]>(sources.map((source, index) =>
    [source.id, [entranceX, (index - (sources.length - 1) / 2) * 2.8]])), [sources, entranceX]);
  const { camera,size }=useThree();
  useEffect(()=>{
    const ortho=camera as THREE.OrthographicCamera;
    ortho.zoom=Math.min(36,size.width/(Math.max(cityWidth,cityDepth)*1.5),size.height/(Math.max(cityWidth,cityDepth)*1.15));
    ortho.updateProjectionMatrix();
  },[camera,size.width,size.height,cityWidth,cityDepth]);
  const visibleIds = new Set(visible.map(t => t.id));
  const people = visitorPopulation(visible,events);
  const focus=layout.lots.get(selected??'');
  const lightTarget=useMemo(()=>new THREE.Object3D(),[]);
  if(focus)lightTarget.position.set(focus[0],1,focus[1]);
  return <>
    <ambientLight intensity={1.35} color="#f4e2cb" />
    <directionalLight position={[8, 18, 10]} intensity={2.5} color="#ffe4bb" castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-20} shadow-camera-right={20} shadow-camera-top={20} shadow-camera-bottom={-20} shadow-normalBias={.04} />
    <directionalLight position={[-8, 4, -6]} intensity={.8} color="#99b5e5" />
    <group position={[0, -.5, 0]}>
      {focus&&<><primitive object={lightTarget}/><spotLight color="#ffe3a1" position={[focus[0],8,focus[1]+1]} target={lightTarget} angle={.42} penumbra={.8} intensity={45} distance={15}/><mesh rotation={[-Math.PI/2,0,0]} position={[focus[0],.03,focus[1]]}><circleGeometry args={[1.9,48]}/><meshBasicMaterial color="#ffe2a1" transparent opacity={.15} depthWrite={false}/></mesh></>}
      <RoundedBox args={[cityWidth, .65, cityDepth]} radius={.18} position={[-entranceWidth / 2, -.33, 0]} receiveShadow><meshStandardMaterial color="#adad91" /></RoundedBox>
      <RoundedBox args={[cityWidth + .15, .1, cityDepth + .15]} radius={.1} position={[-entranceWidth / 2, -.66, 0]}><meshStandardMaterial color="#3d514b" /></RoundedBox>
      {sources.length > 0 && <mesh rotation={[-Math.PI / 2, 0, 0]} position={[entranceX, .035, 0]} receiveShadow><planeGeometry args={[entranceWidth - .45, cityDepth - .65]} /><meshStandardMaterial color="#59685e" /></mesh>}
      {sources.map(source => {
        const [x, z] = entrances.get(source.id)!;
        return <group key={source.id}>
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[x, .045, z]}><planeGeometry args={[entranceWidth - .7, .2]} /><meshBasicMaterial color={source.color} /></mesh>
          <FloatingLabel label={source.label} color={source.color} position={[x, 1.55, z - .15]} small />
        </group>;
      })}
      {layout.districts.map(district => <group key={district.id}>
        <RoundedBox args={[district.width, .06, district.depth]} radius={.12} position={[district.x, .015, district.z]} receiveShadow><meshStandardMaterial color={district.color} roughness={1} /></RoundedBox>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[district.x, .052, district.z + district.depth / 2 - .2]}><planeGeometry args={[district.width - .35, .3]} /><meshStandardMaterial color="#6d7869" /></mesh>
        <FloatingLabel label={district.label} detail={`${district.topicIds.filter(id => visibleIds.has(id)).length} shops in view`} color={district.color} position={[district.x, 5.3, district.z - district.depth / 2 + .25]} dimmed={!district.topicIds.some(id => visibleIds.has(id))} />
        {district.subtopics.map(group => <FloatingLabel key={group.label} label={group.label} color={district.color} position={[group.x, 3.85, group.z + .25]} small dimmed={!group.topicIds.some(id => visibleIds.has(id))} />)}
        <Lamp x={district.x - district.width / 2 + .15} z={district.z + district.depth / 2 - .2} />
        <Tree x={district.x + district.width / 2 - .2} z={district.z - district.depth / 2 + .25} />
      </group>)}
      {allTopics.filter(t => layout.lots.has(t.id)).map(t => <Building key={t.id} topic={visible.find(v => v.id === t.id) ?? t} position={layout.lots.get(t.id)!} selected={selected === t.id} dimmed={!visibleIds.has(t.id)} muted={!!selected && selected!==t.id} onSelect={onSelect} />)}
      <Visitors key={frameKey} events={people} lots={layout.lots} entrances={entrances} reduced={reduced} animate={animate} />
    </group>
    <ContactShadows position={[0, -1.25, 0]} opacity={.45} scale={40} blur={2.5} far={10} resolution={256} color="#000000" />
    <OrbitControls makeDefault enablePan={false} enableZoom minZoom={8} maxZoom={100} minPolarAngle={.3} maxPolarAngle={1.35} target={[-entranceWidth / 2, 0, 0]} />
  </>;
}
export type CityProps = { allTopics: Topic[]; visible: Topic[]; selected: string | null; events: AppearanceEvent[]; onSelect: (id: string) => void; reduced: boolean; animate: boolean; frameKey: string };
export default function City(props: CityProps) {
  return <Canvas shadows orthographic camera={{ position: [19, 18, 22], zoom: 36, near: .1, far: 100 }} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }} aria-label="Interactive miniature topic city. Use the topic list for keyboard navigation." data-focused-topic={props.selected??''} data-resident-count={props.visible.reduce((n,t)=>n+t.items.length,0)} data-departure-count={props.events.filter(e=>e.kind==='departure').length}>
    <Suspense fallback={null}><Diorama {...props} /></Suspense>
  </Canvas>;
}
