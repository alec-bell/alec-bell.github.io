var scene = new THREE.Scene();
var camera = new THREE.PerspectiveCamera( 75, window.innerWidth/window.innerHeight, 0.1, 1000 );

var renderer = new THREE.WebGLRenderer();
renderer.setSize( window.innerWidth, window.innerHeight );
document.body.appendChild( renderer.domElement );

camera.position.z = 5;
var orbit = new THREE.OrbitControls( camera, renderer.domElement );
orbit.enableZoom = false;

var geometry = new THREE.BoxGeometry( 2.5, 2.5, 2.5 );
var material = new THREE.MeshStandardMaterial( { color: 0x156289, emissive: 0x072534, side: THREE.DoubleSide, flatShading: true } );
var cube = new THREE.Mesh( geometry, material );
scene.add( cube );

var light1 = new THREE.DirectionalLight( 0xffffff, 0.8 );
light1.position.set(0,0,1);
light1.target = cube;
scene.add(light1);

var light2 = new THREE.DirectionalLight( 0xffffff, 0.8 );
light2.position.set(0,1,0);
light2.target = cube;
scene.add(light2);

var light3 = new THREE.DirectionalLight( 0xffffff, 0.8 );
light3.position.set(1,0,0);
light3.target = cube;
scene.add(light3);

var light4 = new THREE.DirectionalLight( 0xffffff, 0.8 );
light4.position.set(0,-1,0);
light4.target = cube;
scene.add(light4);

var animate = function () {
	requestAnimationFrame( animate );

	cube.rotation.x += 0.0025;
	cube.rotation.y += 0.0025;

	renderer.render( scene, camera );
};

animate();


window.addEventListener( 'resize', function () {
	camera.aspect = window.innerWidth / window.innerHeight;
	camera.updateProjectionMatrix();

	renderer.setSize( window.innerWidth, window.innerHeight );

}, false );
