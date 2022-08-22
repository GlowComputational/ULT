///LIBREERÍAS
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.126.0/build/three.module.js'
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.126.0/examples/jsm/controls/OrbitControls.js'
import rhino3dm from 'https://cdn.jsdelivr.net/npm/rhino3dm@0.15.0-beta/rhino3dm.module.js'
import { RhinoCompute } from 'https://cdn.jsdelivr.net/npm/compute-rhino3d@0.13.0-beta/compute.rhino3d.module.js'
import { Rhino3dmLoader } from 'https://cdn.jsdelivr.net/npm/three@0.124.0/examples/jsm/loaders/3DMLoader.js'

//GH script
const definitionName = '../static/gh/test.gh'


// //SET UP SLIDERS
const pl = document.getElementById("count").innerHTML;



// console.log(serv)
// console.log(loc)
// console.log(dist)


// serv.addEventListener('input', onChange, false)

// const loc = document.getElementById('result-location')
// loc.addEventListener('input', onChange, false)

// const dist = document.getElementById('result-distance')
// dist.addEventListener('mouseup', onChange, false)
// dist.addEventListener('touchend', onChange, false)

//COUNTER

const evaluateButton = document.getElementById('evaluateButton');
evaluateButton.onclick = evaluate



function evaluate(){
var count = document.getElementById('count');
count.innerHTML = 0;
var timeleft = 0;
var downloadTimer = setInterval(function(){
  if(timeleft >= 5){
    clearInterval(downloadTimer);
    document.getElementById("count").innerHTML = timeleft;
  } else {
    document.getElementById("count").innerHTML = timeleft;
  }
  const pl = timeleft;

  console.log(timeleft)
  compute()
  timeleft += 1;
  
}, 1000);

}




//SET UP RUN AND DOWNLOAD BUTTONS
// const runButton = document.getElementById("runButton")
// runButton.onclick = run
// const downloadButton = document.getElementById("downloadButton")
// downloadButton.onclick = download 

// set up loader for converting the results to threejs
const loader = new Rhino3dmLoader()
loader.setLibraryPath('https://cdn.jsdelivr.net/npm/rhino3dm@0.15.0-beta/')

// globals
let rhino, definition, doc
rhino3dm().then(async m => {
    console.log('Loaded rhino3dm.')
    rhino = m // global

    //RhinoCompute.url = getAuth( 'RHINO_COMPUTE_URL' ) // RhinoCompute server url. Use http://localhost:8081 if debugging locally.
    //RhinoCompute.apiKey = getAuth( 'RHINO_COMPUTE_KEY' )  // RhinoCompute server api key. Leave blank if debugging locally.
    RhinoCompute.url = 'http://localhost:8081/' //if debugging locally.


    // load a grasshopper file!
    const url = definitionName
    const res = await fetch(url)
    const buffer = await res.arrayBuffer()
    const arr = new Uint8Array(buffer)
    definition = arr

    init()
    compute()
})

  /////////////////////////////////////////////////////////////////////////////
//Unchecking aggregation checkbox when new data is to be computed
function onChange() {
    showSpinner(false)
    document.getElementById('loader').style.display = 'none'
    compute()
}

//FUNCTION TO AVOID CALLING COMPUTE ACCIDENTALLY
//Run function assigned to button
// function run() {
//     showSpinner(true)
//     document.getElementById('loader').style.display = 'block'
//     downloadButton.disabled = true
//     runButton.disabled = true
//     compute()
//   }

//COMPUTE
async function compute() {
    
    const pl = document.getElementById("count").innerHTML;
    ////Slider parameters
    ////DISTANCIA ENTRE PARTE IZQ CORAZON Y DER
    // const param1 = new RhinoCompute.Grasshopper.DataTree('server');
    // // console.log(serv)
    // param1.append([0], [serv]);

    // const param2 = new RhinoCompute.Grasshopper.DataTree('location');
    // // console.log(loc)
    // param2.append([0], [loc]);

    // const param3 = new RhinoCompute.Grasshopper.DataTree('distance');
    // // console.log(dist)
    // param3.append([0], [dist]);

    const param1 = new RhinoCompute.Grasshopper.DataTree('play');
    console.log(pl)
    param1.append([0], [pl]);

    // clear values
    const trees = []
    trees.push(param1);
    // trees.push(param2);
    // trees.push(param3);
    // trees.push(param4);

    const res = await RhinoCompute.Grasshopper.evaluateDefinition(definition, trees);

    // console.log(res)
    doc = new rhino.File3dm();

    // hide spinner
    document.getElementById('loader').style.display = 'none'

  //decode grasshopper objects and put them into a rhino document
  for (let i = 0; i < res.values.length; i++) {
    for (const [key, value] of Object.entries(res.values[i].InnerTree)) {
      for (const d of value) {
        const data = JSON.parse(d.data);
        const rhinoObject = rhino.CommonObject.decode(data);
        doc.objects().add(rhinoObject, null);
      }
    }
  }



  // go through the objects in the Rhino document

  let objects = doc.objects();
  for ( let i = 0; i < objects.count; i++ ) {
  
    const rhinoObject = objects.get( i );


     // asign geometry userstrings to object attributes
    if ( rhinoObject.geometry().userStringCount > 0 ) {
      const g_userStrings = rhinoObject.geometry().getUserStrings()
      rhinoObject.attributes().setUserString(g_userStrings[0][0], g_userStrings[0][1])
      
    }
  }


  // clear objects from scene
  scene.traverse((child) => {
    if (!child.isLight) {
      scene.remove(child);
    }
  });


    const buffer = new Uint8Array(doc.toByteArray()).buffer
    loader.parse( buffer, function ( object ) 
    {
        // debug 
        
        // object.traverse(child => {
        //   if (child.material !== undefined)
        //     child.material = new THREE.MeshNormalMaterial()
        // }, false)

        

        // // clear objects from scene. do this here to avoid blink
        // scene.traverse(child => {
        //     if (!child.isLight) {
        //         scene.remove(child)
        //     }
        // })

        object.traverse((child) => {
          if (child.isLine) {
    
            if (child.userData.attributes.geometry.userStringCount > 0) {
              
              //get color from userStrings
              const colorData = child.userData.attributes.userStrings[0]
              const col = colorData[1];
    
              //convert color from userstring to THREE color and assign it
              const threeColor = new THREE.Color("rgb(" + col + ")");
              const mat = new THREE.LineBasicMaterial({ color: threeColor, linewidth: 100});
              
              child.material = mat;
            }
          }
        });
        
        

        // add object graph from rhino model to three.js scene
        scene.add( object )

         // scene.add( line );

        // hide spinner and enable download button
        showSpinner(false)
        // downloadButton.disabled = false
        // runButton.disabled = false;
        evaluateButton.disabled = false

        // zoom to extents
        zoomCameraToSelection(camera, controls, scene.children)
    })

    
}


//DOWNLOAD BUTTON
// function download (){
//     let buffer = doc.toByteArray()
//     let blob = new Blob([ buffer ], { type: "application/octect-stream" })
//     let link = document.createElement('a')
//     link.href = window.URL.createObjectURL(blob)
//     link.download = 'corazon.3dm'
//     link.click()
// }
// more globals
let scene, camera, renderer, controls

/**
 * Sets up the scene, camera, renderer, lights and controls and starts the animation
 */
 function init() {

    // Rhino models are z-up, so set this as the default
    THREE.Object3D.DefaultUp = new THREE.Vector3( 0, 0, 1 );

    
    // create a scene and a camera
    scene = new THREE.Scene()
    // scene.background = new THREE.Color(1, 1, 1)
    camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 1)
    camera.position.set(0, 0, 1) // like perspective view
    
    // scene.add( camera );  

    // very light grey for background, like rhino
    renderer = new THREE.WebGLRenderer({ alpha: true });
    renderer.setClearColor(0x000000, 0);

    // create the renderer and add it to the html
    // renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio( window.devicePixelRatio )
    renderer.setSize(window.innerWidth, window.innerHeight)
    document.body.appendChild(renderer.domElement)

    // add some controls to orbit the camera
    controls = new OrbitControls(camera, renderer.domElement)

    // add a directional light
    const directionalLight = new THREE.DirectionalLight( 0xffffff )
    directionalLight.intensity = 2
    scene.add( directionalLight )

    const ambientLight = new THREE.AmbientLight()
    scene.add( ambientLight )

    // handle changes in the window size
    window.addEventListener( 'resize', onWindowResize, false )

    animate()
}


/**
 * Called when a slider value changes in the UI. Collect all of the
 * slider values and call compute to solve for a new scene
 */

/**
 * Helper function for window resizes (resets the camera pov and renderer size)
  */
function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
  renderer.setSize( window.innerWidth, window.innerHeight )
  animate()
}

/**
 * Helper function that behaves like rhino's "zoom to selection", but for three.js!
 */
function zoomCameraToSelection( camera, controls, selection, fitOffset = 1.2 ) {
  
  const box = new THREE.Box3();
  
  for( const object of selection ) {
    if (object.isLight) continue
    box.expandByObject( object );
  }
  
  const size = box.getSize( new THREE.Vector3() );
  const center = box.getCenter( new THREE.Vector3() );
  
  const maxSize = Math.max( size.x, size.y, size.z );
  const fitHeightDistance = maxSize / ( 2 * Math.atan( Math.PI * camera.fov / 360 ) );
  const fitWidthDistance = fitHeightDistance / camera.aspect;
  const distance = fitOffset * Math.max( fitHeightDistance, fitWidthDistance );
  
  const direction = controls.target.clone()
    .sub( camera.position )
    .normalize()
    .multiplyScalar( distance );
  controls.maxDistance = distance * 10;
  controls.target.copy( center );
  
  camera.near = distance / 100;
  camera.far = distance * 100;
  camera.updateProjectionMatrix();
  camera.position.copy( controls.target ).sub(direction);
//   camera.position.set(0, 0, 1)
  controls.update();
  
}

// function meshToThreejs(mesh, material) {
//   const loader = new THREE.BufferGeometryLoader()
//   const geometry = loader.parse(mesh.toThreejsJSON())
//   //how do I give a material to the wireframe?
//   const material = new THREE.material({ wireframe: true })
//   return new THREE.Mesh(geometry, material)
// }

/**
 * This function is called when the download button is clicked
 */

/**
 * Shows or hides the loading spinner
 */
function showSpinner(enable) {
  if (enable)
    document.getElementById('loader').style.display = 'block'
  else
    document.getElementById('loader').style.display = 'none'
}

/**
 * The animation loop!
 */
 function animate() {
  requestAnimationFrame( animate )
  controls.update()
  renderer.render(scene, camera)
}