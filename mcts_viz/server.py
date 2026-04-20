"""Flask server for interactive MCTS visualization."""
from __future__ import annotations
import argparse
from flask import Flask, request, jsonify, Response
from .games import GAME_REGISTRY
from .game_base import GameState
from .mcts_engine import mcts_search

app = Flask(__name__)

# ── Per-game server state ─────────────────────────────────────
_sessions: dict[str, dict] = {}
_num_simulations: int = 1000
_c: float = 1.41


def _get_session(game_id: str) -> dict:
    if game_id not in _sessions:
        _sessions[game_id] = {"history": []}
    return _sessions[game_id]


def _rebuild_state(game_id: str) -> GameState:
    cls = GAME_REGISTRY[game_id]
    state = cls()
    for action in _get_session(game_id)["history"]:
        state = state.apply(action)
    return state


# ── Landing page ──────────────────────────────────────────────
@app.get("/")
def landing():
    items = "".join(
        f'<a class="game-card" href="/{gid}/">'
        f'<span class="game-name">{gid}</span></a>'
        for gid in GAME_REGISTRY
    )
    return Response(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>MCTS Visualizer</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;
  display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;}}
h1{{font-size:28px;margin-bottom:8px;}}
.subtitle{{color:#64748b;margin-bottom:32px;font-size:14px;}}
.games{{display:flex;flex-wrap:wrap;gap:16px;justify-content:center;max-width:600px;}}
.game-card{{padding:20px 32px;border:2px solid #334155;border-radius:12px;background:#1e293b;
  text-decoration:none;color:#e2e8f0;font-weight:600;font-size:16px;transition:all .15s;}}
.game-card:hover{{border-color:#3b82f6;background:#334155;}}
</style></head><body>
<h1>MCTS Visualizer</h1>
<div class="subtitle">Choose a game</div>
<div class="games">{items}</div>
</body></html>""", content_type="text/html; charset=utf-8")


# ── Per-game API ──────────────────────────────────────────────
@app.get("/<game_id>/api/state")
def get_state(game_id: str):
    if game_id not in GAME_REGISTRY:
        return jsonify({"error": "Unknown game"}), 404
    session = _get_session(game_id)
    state = _rebuild_state(game_id)
    root = mcts_search(state, _num_simulations, _c)
    return jsonify({
        "state": state.to_dict(),
        "tree": root.to_dict(_c),
        "history": session["history"],
    })


@app.post("/<game_id>/api/move")
def make_move(game_id: str):
    if game_id not in GAME_REGISTRY:
        return jsonify({"error": "Unknown game"}), 404
    session = _get_session(game_id)
    data = request.get_json(force=True)
    action = data["action"]
    state = _rebuild_state(game_id)
    if action not in state.legal_actions():
        return jsonify({"error": "Illegal action"}), 400
    session["history"].append(action)
    state = state.apply(action)

    ai_action = None
    if not state.is_terminal():
        root = mcts_search(state, _num_simulations, _c)
        ai_action = max(root.children, key=lambda ch: ch.visits).action
        session["history"].append(ai_action)
        state = state.apply(ai_action)

    tree_data = None
    if not state.is_terminal():
        tree_data = mcts_search(state, _num_simulations, _c).to_dict(_c)

    return jsonify({
        "state": state.to_dict(),
        "tree": tree_data,
        "history": session["history"],
        "ai_action": ai_action,
    })


@app.post("/<game_id>/api/reset")
def reset(game_id: str):
    if game_id not in GAME_REGISTRY:
        return jsonify({"error": "Unknown game"}), 404
    _sessions[game_id] = {"history": []}
    state = _rebuild_state(game_id)
    root = mcts_search(state, _num_simulations, _c)
    return jsonify({
        "state": state.to_dict(),
        "tree": root.to_dict(_c),
        "history": [],
    })


@app.post("/<game_id>/api/undo")
def undo(game_id: str):
    if game_id not in GAME_REGISTRY:
        return jsonify({"error": "Unknown game"}), 404
    session = _get_session(game_id)
    if session["history"]:
        session["history"].pop()
    state = _rebuild_state(game_id)
    tree_data = None
    if not state.is_terminal():
        tree_data = mcts_search(state, _num_simulations, _c).to_dict(_c)
    return jsonify({
        "state": state.to_dict(),
        "tree": tree_data,
        "history": session["history"],
    })


@app.post("/<game_id>/api/config")
def config(game_id: str):
    global _num_simulations, _c
    data = request.get_json(force=True)
    _num_simulations = data.get("num_simulations", _num_simulations)
    _c = data.get("c", _c)
    return jsonify({"num_simulations": _num_simulations, "c": _c})


# ── Serve per-game frontend ──────────────────────────────────
@app.get("/<game_id>/")
def game_page(game_id: str):
    if game_id not in GAME_REGISTRY:
        return Response("Unknown game", status=404)
    return Response(_INDEX_HTML.replace("__GAME_PREFIX__", f"/{game_id}"),
                    content_type="text/html; charset=utf-8")


_INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MCTS Visualizer</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;height:100vh;overflow:hidden;}

.container{display:flex;height:100vh;}
.left-panel{width:340px;min-width:340px;padding:20px;display:flex;flex-direction:column;gap:16px;border-right:1px solid #1e293b;background:#0f172a;}
.right-panel{flex:1;position:relative;overflow:hidden;background:#0f172a;}

h1{font-size:20px;font-weight:700;color:#f8fafc;}
.subtitle{font-size:12px;color:#64748b;}

.board-container{display:flex;justify-content:center;}
.board{display:grid;gap:4px;}
.cell{
  width:80px;height:80px;border:2px solid #334155;border-radius:8px;
  background:#1e293b;display:flex;align-items:center;justify-content:center;
  font-size:36px;font-weight:800;cursor:pointer;transition:all .15s;user-select:none;
}
.cell:hover:not(.taken){background:#334155;border-color:#475569;}
.cell.taken{cursor:default;}
.cell.x{color:#3b82f6;}
.cell.o{color:#ef4444;}
.cell.last-move{border-color:#fbbf24;box-shadow:0 0 12px rgba(251,191,36,.3);}

/* Nim */
.nim-container{text-align:center;}
.nim-stones{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin:12px 0;}
.nim-stone{width:28px;height:28px;border-radius:50%;background:#475569;border:2px solid #64748b;}
.nim-actions{display:flex;gap:8px;justify-content:center;margin-top:8px;}
.nim-btn{padding:10px 20px;border:2px solid #334155;border-radius:8px;background:#1e293b;color:#e2e8f0;font-size:15px;font-weight:700;cursor:pointer;transition:all .15s;}
.nim-btn:hover{background:#334155;border-color:#64748b;}
.nim-count{font-size:24px;font-weight:700;color:#f8fafc;margin-bottom:4px;}

/* Chopsticks */
.chop{text-align:center;font-family:'Segoe UI',system-ui,sans-serif;}
.chop-side{margin:8px 0;padding:8px;border-radius:8px;background:#1e293b;border:1px solid #334155;}
.chop-side.active{border-color:#3b82f6;}
.chop-label{font-size:11px;color:#64748b;margin-bottom:4px;}
.chop-hands{display:flex;justify-content:center;gap:24px;}
.chop-hand{font-size:32px;min-width:50px;text-align:center;}
.chop-hand.dead{opacity:.25;}
.chop-fingers{font-size:12px;color:#94a3b8;}
.chop-actions{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin-top:10px;}
.chop-btn{padding:6px 12px;border:1px solid #334155;border-radius:6px;background:#1e293b;color:#e2e8f0;font-size:12px;cursor:pointer;transition:all .15s;}
.chop-btn:hover{background:#334155;border-color:#64748b;}
.chop-btn.tap{border-color:#3b82f6;}
.chop-btn.split{border-color:#a78bfa;}

.status{text-align:center;font-size:15px;font-weight:600;padding:8px;border-radius:8px;background:#1e293b;}
.status.win{color:#22c55e;background:#052e16;}
.status.lose{color:#ef4444;background:#450a0a;}
.status.draw{color:#eab308;background:#422006;}

.controls{display:flex;gap:8px;}
.btn{flex:1;padding:10px;border:1px solid #334155;border-radius:8px;background:#1e293b;color:#e2e8f0;font-size:13px;font-weight:600;cursor:pointer;transition:all .15s;}
.btn:hover{background:#334155;}

.config{display:flex;flex-direction:column;gap:8px;font-size:12px;}
.config label{color:#94a3b8;}
.config input{width:100%;padding:6px 8px;border:1px solid #334155;border-radius:6px;background:#1e293b;color:#e2e8f0;font-size:13px;}

.info{font-size:11px;color:#475569;margin-top:auto;line-height:1.6;}

/* Tree panel */
.tree-header{position:absolute;top:12px;left:16px;right:16px;z-index:10;display:flex;align-items:center;gap:12px;}
.tree-header .label{font-size:13px;font-weight:600;color:#94a3b8;}
.zoom-controls{display:flex;gap:4px;}
.zoom-btn{padding:4px 10px;border:1px solid #334155;border-radius:6px;background:#1e293b;color:#e2e8f0;cursor:pointer;font-size:14px;}
.zoom-btn:hover{background:#334155;}
.zoom-label{font-size:11px;color:#64748b;padding:4px 6px;}

.tree-viewport{width:100%;height:100%;overflow:hidden;cursor:grab;}
.tree-viewport:active{cursor:grabbing;}
.tree-canvas{transform-origin:0 0;padding:60px 40px 40px;display:inline-block;min-width:100%;}

/* Nodes */
.tree-node{display:flex;flex-direction:column;align-items:center;}
.node-box{
  border:1px solid #334155;border-radius:6px;padding:4px 6px;
  text-align:center;font-family:'SF Mono','Fira Code',monospace;font-size:10px;
  cursor:pointer;transition:all .15s;position:relative;
  background:#1e293b;white-space:nowrap;
}
.node-box:hover{border-color:#64748b;}
.node-box.terminal{border-color:#fbbf24;border-style:dashed;}
.node-label{font-weight:700;font-size:11px;color:#f8fafc;}
.node-stats-row{color:#94a3b8;font-size:10px;margin-top:2px;}
.node-stats-row .w{color:#22c55e;}
.node-stats-row .l{color:#ef4444;}
.node-stats-row .d{color:#64748b;}
.node-stats-row .ucb{color:#a78bfa;}

.mini-board{display:inline-grid;gap:1px;margin:2px 0;}
.mini-cell{width:12px;height:12px;display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:800;background:#0f172a;border-radius:1px;}
.mini-cell.x{color:#3b82f6;}
.mini-cell.o{color:#ef4444;}

.children-row{display:flex;flex-wrap:nowrap;gap:4px;margin-top:3px;}
.connector{width:1px;height:8px;background:#334155;margin:0 auto;}

::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:#0f172a;}
::-webkit-scrollbar-thumb{background:#334155;border-radius:3px;}
</style>
</head>
<body>
<div class="container">
  <div class="left-panel">
    <div><h1>MCTS Visualizer</h1><div class="subtitle">Interactive Monte Carlo Tree Search</div></div>
    <div class="status" id="status">Your turn (X)</div>
    <div class="board-container"><div class="board" id="board"></div></div>
    <div class="controls">
      <button class="btn" onclick="doReset()">New Game</button>
      <button class="btn" onclick="doUndo()">Undo</button>
    </div>
    <div class="config">
      <label>Simulations: <input type="number" id="sims" value="1000" min="100" max="10000" step="100" onchange="updateConfig()"></label>
      <label>C (exploration): <input type="number" id="cval" value="1.41" min="0" max="5" step="0.1" onchange="updateConfig()"></label>
      <label>Min visits (filter): <input type="number" id="minVisits" value="1" min="1" max="100" step="1" onchange="rerenderTree()"></label>
    </div>
    <div class="info">
      <b>Controls:</b><br>
      &middot; Click board to play (X=you, O=MCTS AI)<br>
      &middot; Tree: drag=pan, scroll=zoom<br>
      &middot; Click node = expand/collapse children<br>
      &middot; W=Win, L=Loss, D=Draw (from that node's perspective)
    </div>
  </div>
  <div class="right-panel">
    <div class="tree-header">
      <span class="label">MCTS Tree</span>
      <div class="zoom-controls">
        <button class="zoom-btn" onclick="zoomIn()">+</button>
        <span class="zoom-label" id="zoomLabel">100%</span>
        <button class="zoom-btn" onclick="zoomOut()">&minus;</button>
        <button class="zoom-btn" onclick="zoomFit()">Fit</button>
      </div>
    </div>
    <div class="tree-viewport" id="treeViewport">
      <div class="tree-canvas" id="treeCanvas"><div style="color:#64748b;padding:40px;text-align:center">Loading...</div></div>
    </div>
  </div>
</div>
<script>
let currentState=null, currentTree=null;
let expandedNodes=new Set();  // nodes user explicitly expanded
expandedNodes.add('0');       // root always expanded

// ── Zoom & Pan ──
let zoom=1,panX=0,panY=0,isPanning=false,panStartX=0,panStartY=0;
const ZOOM_MIN=0.03,ZOOM_MAX=5;
const vp=document.getElementById('treeViewport'),cv=document.getElementById('treeCanvas');

function applyTf(){cv.style.transform=`translate(${panX}px,${panY}px) scale(${zoom})`;document.getElementById('zoomLabel').textContent=Math.round(zoom*100)+'%';}
vp.addEventListener('mousedown',e=>{if(e.target.closest('.node-box'))return;isPanning=true;panStartX=e.clientX-panX;panStartY=e.clientY-panY;});
window.addEventListener('mousemove',e=>{if(!isPanning)return;panX=e.clientX-panStartX;panY=e.clientY-panStartY;applyTf();});
window.addEventListener('mouseup',()=>isPanning=false);
vp.addEventListener('wheel',e=>{e.preventDefault();const r=vp.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,old=zoom;zoom*=e.deltaY<0?1.15:0.87;zoom=Math.max(ZOOM_MIN,Math.min(ZOOM_MAX,zoom));panX=mx-(mx-panX)*(zoom/old);panY=my-(my-panY)*(zoom/old);applyTf();},{passive:false});
function zoomIn(){zoom=Math.min(ZOOM_MAX,zoom*1.25);applyTf();}
function zoomOut(){zoom=Math.max(ZOOM_MIN,zoom*0.8);applyTf();}
function zoomFit(){zoom=1;panX=0;panY=0;applyTf();}

// ── Board ──
function renderBoard(st){
  const bd=document.getElementById('board');
  bd.innerHTML='';
  if(st.game==='nim') return renderNimBoard(st,bd);
  if(st.game==='chopsticks') return renderChopBoard(st,bd);
  const [rows,cols]=st.shape;
  const sz=cols<=3?80:cols<=5?56:44;
  bd.style.gridTemplateColumns=`repeat(${cols},${sz}px)`;
  bd.style.display='grid';
  const last=currentState?.history?.length>0?currentState.history[currentState.history.length-1]:-1;
  for(let i=0;i<st.board.length;i++){
    const c=document.createElement('div');c.className='cell';c.style.width=sz+'px';c.style.height=sz+'px';c.style.fontSize=(sz*0.45)+'px';
    const v=st.board[i];
    if(v===1){c.classList.add('taken','x');c.textContent='X';}
    if(v===-1){c.classList.add('taken','o');c.textContent='O';}
    if(i===last)c.classList.add('last-move');
    if(v===0&&!st.is_terminal)c.addEventListener('click',()=>makeMove(i));
    bd.appendChild(c);
  }
}
function renderNimBoard(st,bd){
  bd.style.display='block';
  const n=st.stones;
  let h=`<div class="nim-container">`;
  h+=`<div class="nim-count">${n} stones</div>`;
  h+=`<div class="nim-stones">`;
  for(let i=0;i<n;i++) h+=`<div class="nim-stone"></div>`;
  h+=`</div>`;
  if(!st.is_terminal){
    h+=`<div class="nim-actions">`;
    for(const k of st.allowed){
      if(k<=n) h+=`<div class="nim-btn" onclick="makeMove(${k})">Take ${k}</div>`;
    }
    h+=`</div>`;
  }
  h+=`</div>`;
  bd.innerHTML=h;
}
function renderChopBoard(st,bd){
  bd.style.display='block';
  const [p1L,p1R,p2L,p2R]=st.hands;
  const fingers=['✊','☝️','✌️','🤟','🖖'];
  const isP1=st.current_player===1;
  const tapNames=['L→L','L→R','R→L','R→R'];

  let h='<div class="chop">';
  // Opponent (P2) on top
  h+=`<div class="chop-side${!isP1?' active':''}"><div class="chop-label">Player 2 (O)${!isP1?' ← turn':''}</div>`;
  h+=`<div class="chop-hands"><div class="chop-hand${p2L===0?' dead':''}">${fingers[p2L]}<div class="chop-fingers">${p2L}</div></div>`;
  h+=`<div class="chop-hand${p2R===0?' dead':''}">${fingers[p2R]}<div class="chop-fingers">${p2R}</div></div></div></div>`;
  // Player (P1) on bottom
  h+=`<div class="chop-side${isP1?' active':''}"><div class="chop-label">Player 1 (X)${isP1?' ← turn':''}</div>`;
  h+=`<div class="chop-hands"><div class="chop-hand${p1L===0?' dead':''}">${fingers[p1L]}<div class="chop-fingers">${p1L}</div></div>`;
  h+=`<div class="chop-hand${p1R===0?' dead':''}">${fingers[p1R]}<div class="chop-fingers">${p1R}</div></div></div></div>`;

  if(!st.is_terminal){
    h+='<div class="chop-actions">';
    for(const a of st.legal_actions){
      if(a<10){
        h+=`<div class="chop-btn tap" onclick="makeMove(${a})">Tap ${tapNames[a]}</div>`;
      }else{
        const nL=a-10, my=isP1?[p1L,p1R]:[p2L,p2R], tot=my[0]+my[1], nR=tot-nL;
        h+=`<div class="chop-btn split" onclick="makeMove(${a})">Split ${nL}|${nR}</div>`;
      }
    }
    h+='</div>';
  }
  h+='</div>';
  bd.innerHTML=h;
}
function updateStatus(st){
  const el=document.getElementById('status');el.className='status';
  if(st.is_terminal){
    const isP=(st.game==='nim'||st.game==='chopsticks');
    const p1=isP?'Player 1':'X', p2=isP?'Player 2':'O';
    if(st.winner===1){el.textContent=p1+' wins!';el.classList.add('win');}
    else if(st.winner===-1){el.textContent=p2+' wins!';el.classList.add('lose');}
    else{el.textContent='Draw!';el.classList.add('draw');}
  }else{
    if(st.game==='nim'||st.game==='chopsticks'){
      el.textContent=st.current_player===1?'Player 1\'s turn':'Player 2 (AI) turn';
    }else{
      el.textContent=st.current_player===1?'Your turn (X)':'Your turn (O)';
    }
  }
}

// ── Mini board ──
function miniBoard(state){
  if(state.game==='nim'){
    return `<div style="font-size:12px;font-weight:700;color:#f8fafc;margin:2px 0">${state.stones}\u25CF</div>`;
  }
  if(state.game==='chopsticks'){
    const [a,b,c,d]=state.hands;
    return `<div style="font-size:10px;color:#f8fafc;margin:2px 0;line-height:1.4">P1:${a}|${b}<br>P2:${c}|${d}</div>`;
  }
  const cols=state.shape[1];
  let h=`<div class="mini-board" style="grid-template-columns:repeat(${cols},12px)">`;
  for(const v of state.board){
    let cls='mini-cell',ch='\u00b7';
    if(v===1){cls+=' x';ch='X';}
    if(v===-1){cls+=' o';ch='O';}
    h+=`<div class="${cls}">${ch}</div>`;
  }
  return h+'</div>';
}

// ── Tree ──
function renderTree(node,path='0'){
  if(!node) return '<div style="color:#64748b;padding:40px;text-align:center">Game over</div>';
  const minV=parseInt(document.getElementById('minVisits').value)||1;
  const isExpanded=expandedNodes.has(path);
  const isTerminal=node.state.is_terminal;

  const gm=node.state.game;
  let aLbl='ROOT';
  if(node.action!==null){
    if(gm==='nim') aLbl=`take ${node.action}`;
    else if(gm==='chopsticks'){
      if(node.action<10){const tn=['L\u2192L','L\u2192R','R\u2192L','R\u2192R'];aLbl=tn[node.action];}
      else aLbl=`split`;
    }else aLbl=`a=${node.action}`;
  }
  const ucb=node.ucb!==null?node.ucb.toFixed(2):'';

  const kids=node.children.filter(c=>c.visits>=minV);
  const hidden=node.children.length-kids.length;
  const hasKids=kids.length>0;

  let childrenHtml='';
  if(hasKids&&isExpanded){
    childrenHtml='<div class="connector"></div><div class="children-row">';
    kids.forEach((k,i)=>childrenHtml+=renderTree(k,path+'.'+i));
    if(hidden>0) childrenHtml+=`<div style="color:#475569;font-size:9px;padding:4px;align-self:center">+${hidden}</div>`;
    childrenHtml+='</div>';
  }

  const arrow=hasKids?(isExpanded?'\u25BC':'\u25B6'):'';
  const termClass=isTerminal?' terminal':'';

  return `<div class="tree-node">
    <div class="node-box${termClass}" onclick="toggleExpand('${path}',event)">
      <div class="node-label">${arrow} ${aLbl}</div>
      ${miniBoard(node.state)}
      <div class="node-stats-row"><span class="w">W${node.W}</span> <span class="l">L${node.L}</span> <span class="d">D${node.D}</span> n=${node.visits}${ucb?' <span class="ucb">ucb='+ucb+'</span>':''}</div>
    </div>
    ${childrenHtml}
  </div>`;
}

function toggleExpand(path,e){
  e.stopPropagation();
  if(expandedNodes.has(path)) expandedNodes.delete(path);
  else expandedNodes.add(path);
  rerenderTree();
}
function rerenderTree(){if(currentTree) cv.innerHTML=renderTree(currentTree);}

// ── API ──
async function fetchState(){
  const d=await(await fetch('__GAME_PREFIX__/api/state')).json();
  currentState=d;currentTree=d.tree;
  renderBoard(d.state);updateStatus(d.state);
  expandedNodes.clear();expandedNodes.add('0');
  rerenderTree();
}
async function makeMove(a){
  document.getElementById('status').textContent='MCTS thinking...';
  const d=await(await fetch('__GAME_PREFIX__/api/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:a})})).json();
  if(d.error){alert(d.error);return;}
  currentState=d;currentTree=d.tree;
  renderBoard(d.state);updateStatus(d.state);
  expandedNodes.clear();expandedNodes.add('0');
  rerenderTree();
}
async function doReset(){
  const d=await(await fetch('__GAME_PREFIX__/api/reset',{method:'POST'})).json();
  currentState=d;currentTree=d.tree;
  renderBoard(d.state);updateStatus(d.state);
  expandedNodes.clear();expandedNodes.add('0');
  rerenderTree();
}
async function doUndo(){
  const d=await(await fetch('__GAME_PREFIX__/api/undo',{method:'POST'})).json();
  currentState=d;currentTree=d.tree;
  renderBoard(d.state);updateStatus(d.state);
  expandedNodes.clear();expandedNodes.add('0');
  rerenderTree();
}
async function updateConfig(){
  await fetch('__GAME_PREFIX__/api/config',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({num_simulations:parseInt(document.getElementById('sims').value)||1000,
                         c:parseFloat(document.getElementById('cval').value)||1.41})});
}

fetchState();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="MCTS Visualizer Server")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--sims", type=int, default=1000)
    args = parser.parse_args()

    global _num_simulations
    _num_simulations = args.sims

    print(f"MCTS Visualizer — http://localhost:{args.port}")
    print(f"Games: {', '.join(GAME_REGISTRY.keys())}")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
