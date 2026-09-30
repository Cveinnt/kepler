(()=>{
const image = document.querySelector('#frame');
const play = document.querySelector('#play');
const scrub = document.querySelector('#scrub');
const moments = [
  {at:0,title:'Four goals. One drop.',body:'Scrub the real recording to see the routes that settled observations left out.'},
  {at:6,title:'The first goal fills.',body:'Another branch is still moving. The pink trail records the route through the pieces.'},
  {at:12,title:'The flight branches.',body:'The trail forks around the obstacles. These intermediate routes carried clues to the missing rule.'},
  {at:20,title:'All four goals filled.',body:'The branches reach the remaining goals. This is a recorded outcome, not a simulated forecast.'}
];
let frame=0,mode='motion',timer=null,ready=false;
const frames=[];
function draw(){
  const shown=mode==='settled' && frame<20 ? 0 : frame;
  image.src=`assets/sp80/frame-${String(shown).padStart(2,'0')}.png`;
  image.alt=`Recorded sp80 observation, frame ${shown} of 20. ${mode==='settled'?'Intermediate animation hidden in this viewing mode.':''}`;
  scrub.value=frame;
  document.querySelector('#count').textContent=`${String(frame).padStart(2,'0')} / 20`;
  document.querySelector('#frame-chip').textContent=mode==='settled' && frame<20 ? 'INTERMEDIATE MOTION HIDDEN' : `FRAME ${String(shown).padStart(2,'0')} / 20`;
  const moment=moments.filter(m=>m.at<=frame).at(-1);
  document.querySelector('#caption-title').textContent=mode==='settled'?'Same recording. Motion hidden.':moment.title;
  document.querySelector('#caption').textContent=mode==='settled'?'Only frames 0 and 20 are shown. This viewing aid is not a rerun or a controlled modality experiment.':moment.body;
  document.querySelectorAll('[data-frame]').forEach(b=>b.setAttribute('aria-pressed',Number(b.dataset.frame)===moment.at));
  play.textContent=timer?'Pause':frame===20?'Replay':'Play';
  play.setAttribute('aria-label',timer?'Pause recorded frames':frame===20?'Replay recorded frames':'Play recorded frames');
}
function stop(){clearInterval(timer);timer=null;draw()}
play.addEventListener('click',()=>{
  if(!ready)return;if(timer){stop();return}if(frame===20)frame=0;
  timer=setInterval(()=>{frame++;if(frame>=20){frame=20;stop()}else draw()},240);draw();
});
scrub.addEventListener('input',()=>{frame=Number(scrub.value);stop()});
document.querySelectorAll('[data-frame]').forEach(b=>b.addEventListener('click',()=>{frame=Number(b.dataset.frame);stop()}));
for(const id of ['motion','settled'])document.querySelector('#'+id).addEventListener('click',()=>{
  mode=id;document.querySelector('#motion').setAttribute('aria-pressed',id==='motion');document.querySelector('#settled').setAttribute('aria-pressed',id==='settled');stop();
});
Promise.all(Array.from({length:21},async(_,i)=>{const img=new Image();img.src=`assets/sp80/frame-${String(i).padStart(2,'0')}.png`;await img.decode();frames.push(img)})).then(()=>{ready=true;play.disabled=false;scrub.disabled=false;document.querySelectorAll('[data-frame]').forEach(b=>b.disabled=false);draw();document.querySelector('#load-status').textContent='All 21 recorded frames loaded. Ready to play.'}).catch(()=>{play.textContent='Unavailable';document.querySelector('#load-status').classList.add('failed');document.querySelector('#load-status').textContent='Some frames could not load. The initial observation remains visible; reload to retry.'});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop()});
})();
