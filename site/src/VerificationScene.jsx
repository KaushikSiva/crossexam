import React,{useEffect,useRef,useState} from 'react';
import {useReducedMotion} from 'motion/react';

/** A real, locally rendered 3D sculpture. No remote assets or tracking. */
export default function VerificationScene(){
  const host=useRef(null),reduced=useReducedMotion();const[ready,setReady]=useState(false);
  useEffect(()=>{
    let disposed=false,cleanup=()=>{};
    Promise.all([import('three'),import('three/addons/environments/RoomEnvironment.js')]).then(([T,{RoomEnvironment}])=>{
      if(disposed)return;
      const element=host.current;let renderer;
      try{renderer=new T.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});}catch{return;}
      renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5));renderer.setClearColor(0x080808,0);
      renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;
      element.appendChild(renderer.domElement);
      const scene=new T.Scene(),camera=new T.PerspectiveCamera(37,1,.1,50);
      camera.position.set(0,.1,9.8);camera.lookAt(0,0,0);
      const pmrem=new T.PMREMGenerator(renderer),room=new RoomEnvironment();
      const environment=pmrem.fromScene(room,.04);scene.environment=environment.texture;room.dispose();
      const sculpture=new T.Group();scene.add(sculpture);
      const silver=new T.MeshStandardMaterial({color:0xd7d7d7,metalness:1,roughness:.23});
      const graphite=new T.MeshStandardMaterial({color:0x4b4b4b,metalness:.9,roughness:.3});
      const shape=new T.Shape();const s=.27,l=1.75;
      [[-s,l],[s,l],[s,s],[l,s],[l,-s],[s,-s],[s,-l],[-s,-l],[-s,-s],[-l,-s],[-l,s],[-s,s]].forEach(([x,y],i)=>i?shape.lineTo(x,y):shape.moveTo(x,y));shape.closePath();
      const cross=new T.Mesh(new T.ExtrudeGeometry(shape,{depth:.32,bevelEnabled:true,bevelSegments:4,steps:1,bevelSize:.08,bevelThickness:.08}),silver);
      cross.rotation.z=Math.PI/4;cross.position.z=.2;sculpture.add(cross);
      const rings=new T.Group();sculpture.add(rings);
      [2.25,2.52,2.79].forEach((radius,i)=>{
        const ring=new T.Mesh(new T.TorusGeometry(radius,.018+i*.005,8,128),i===1?silver:graphite);
        ring.rotation.set(.22+i*.14,.12-i*.17,0);ring.position.z=-.55-i*.18;rings.add(ring);
      });
      // The input lanes converge on the gate. One diverges after verification.
      const paths=[];
      for(let i=0;i<7;i++){
        const y=(i-3)*.38;
        const curve=new T.CatmullRomCurve3([new T.Vector3(-4.8,y,-.4),new T.Vector3(-2.4,y,-.3),new T.Vector3(0,y*.35,0),new T.Vector3(2.1,i===0?-1.7:y,.1),new T.Vector3(4.9,i===0?-2.7:y,.1)]);
        const geometry=new T.BufferGeometry().setFromPoints(curve.getPoints(100));
        const line=new T.Line(geometry,new T.LineBasicMaterial({color:i===0?0xaaaaaa:0x4b4b4b,transparent:true,opacity:i===0?.7:.3}));scene.add(line);paths.push(curve);
      }
      const particles=paths.map((curve,i)=>{const mesh=new T.Mesh(new T.SphereGeometry(i===0?.038:.022,8,6),new T.MeshBasicMaterial({color:0xffffff}));scene.add(mesh);return{mesh,curve,offset:i*.13}});
      scene.add(new T.HemisphereLight(0xffffff,0x242424,1.3));
      const key=new T.DirectionalLight(0xffffff,4);key.position.set(-3,5,5);scene.add(key);
      const rim=new T.DirectionalLight(0xffffff,2);rim.position.set(4,-2,1);scene.add(rim);
      let pointer={x:0,y:0},visible=true,frame=0,last=0;
      const move=e=>{const b=element.getBoundingClientRect();pointer={x:(e.clientX-b.left)/b.width-.5,y:(e.clientY-b.top)/b.height-.5}};
      const leave=()=>{pointer={x:0,y:0}};
      element.addEventListener('pointermove',move);element.addEventListener('pointerleave',leave);
      const resize=()=>{const w=element.clientWidth,h=element.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();renderer.render(scene,camera)};
      const observer=new ResizeObserver(resize);observer.observe(element);
      const intersection=new IntersectionObserver(([entry])=>{visible=entry.isIntersecting});intersection.observe(element);
      const render=time=>{
        if(disposed)return;frame=requestAnimationFrame(render);
        if(!visible||document.hidden||time-last<32)return;last=time;
        const t=reduced?0:time/1000;
        sculpture.rotation.y+=((-.28+(reduced?0:pointer.x*.5+Math.sin(t*.22)*.14))-sculpture.rotation.y)*.045;
        sculpture.rotation.x+=((.12+(reduced?0:pointer.y*.25))-sculpture.rotation.x)*.045;
        sculpture.position.y=reduced?0:Math.sin(t*.7)*.07;
        rings.rotation.z=reduced?0:Math.sin(t*.16)*.09;
        particles.forEach(({mesh,curve,offset})=>mesh.position.copy(curve.getPointAt((t*.075+offset)%1)));
        renderer.render(scene,camera);
      };
      resize();render(0);setReady(true);
      cleanup=()=>{cancelAnimationFrame(frame);observer.disconnect();intersection.disconnect();element.removeEventListener('pointermove',move);element.removeEventListener('pointerleave',leave);scene.traverse(object=>{object.geometry?.dispose();if(object.material){for(const material of [object.material].flat())material.dispose()}});environment.dispose();pmrem.dispose();renderer.dispose();renderer.domElement.remove()};
    }).catch(()=>{});
    return()=>{disposed=true;cleanup()};
  },[reduced]);
  return <div className={`verification-scene ${ready?'is-ready':''}`}>
    <div ref={host} className="scene-canvas" role="img" aria-label="A three-dimensional silver CrossExam gate intersects passing test signals and separates a contract violation."/>
    {!ready&&<svg className="scene-fallback" viewBox="0 0 600 500" aria-hidden="true"><ellipse cx="300" cy="250" rx="190" ry="185" fill="none" stroke="#4a4a4a"/><path d="M200 150L400 350M400 150L200 350" stroke="#d8d8d8" strokeWidth="40"/></svg>}
    <div className="scene-label scene-input"><span>EXISTING EVALUATION</span><strong>4 / 4 PASS</strong></div>
    <div className="scene-label scene-output"><span>INDEPENDENT CONTRACT</span><strong>× VIOLATION FOUND</strong></div>
    <span className="art-note">D01 COUNTEREXAMPLE · ILLUSTRATED IN 3D</span>
  </div>;
}
