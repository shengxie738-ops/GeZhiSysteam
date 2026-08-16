import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, RotateCcw, Plus, Activity } from 'lucide-react';

interface TreeNode {
  id: number;
  val: number;
  x: number;
  y: number;
  leftId: number | null;
  rightId: number | null;
  parentId: number | null;
}

export default function TreeVisualizer() {
  const [nodes, setNodes] = useState<TreeNode[]>([]);
  const [activeNodeId, setActiveNodeId] = useState<number | null>(null);
  const [traversing, setTraversing] = useState(false);
  const [logMessage, setLogMessage] = useState<string>('沙箱就绪。点击插入节点或开始遍历。');

  // Initial tree setup: a simple beautiful BST
  useEffect(() => {
    resetTree();
  }, []);

  const resetTree = () => {
    const initialNodes: TreeNode[] = [
      { id: 1, val: 50, x: 250, y: 50, leftId: 2, rightId: 3, parentId: null },
      { id: 2, val: 30, x: 130, y: 130, leftId: 4, rightId: 5, parentId: 1 },
      { id: 3, val: 70, x: 370, y: 130, leftId: 6, rightId: 7, parentId: 1 },
      { id: 4, val: 20, x: 70, y: 210, leftId: null, rightId: null, parentId: 2 },
      { id: 5, val: 40, x: 190, y: 210, leftId: null, rightId: null, parentId: 2 },
      { id: 6, val: 60, x: 310, y: 210, leftId: null, rightId: null, parentId: 3 },
      { id: 7, val: 80, x: 430, y: 210, leftId: null, rightId: null, parentId: 3 }
    ];
    setNodes(initialNodes);
    setActiveNodeId(null);
    setTraversing(false);
    setLogMessage('水墨拓扑二叉树已初始化。');
  };

  const insertNode = () => {
    if (nodes.length >= 11) {
      setLogMessage('沙箱限制：当前演示树最大支持 11 个节点。');
      return;
    }

    const newVal = Math.floor(Math.random() * 90) + 10;
    
    // Simple BST insertion algorithm with position calculation
    const newNodes = [...nodes];
    let root = newNodes.find(n => n.parentId === null);
    
    if (!root) {
      const newNode: TreeNode = {
        id: Date.now(),
        val: newVal,
        x: 250,
        y: 50,
        leftId: null,
        rightId: null,
        parentId: null
      };
      setNodes([newNode]);
      setLogMessage(`树为空。创建主根节点，值: ${newVal}`);
      return;
    }

    let curr = root;
    let depth = 0;
    const maxDepth = 3;

    while (curr) {
      depth++;
      if (depth > maxDepth) {
        setLogMessage('沙箱限制：最大深度为 3 层，请重置树。');
        return;
      }

      if (newVal < curr.val) {
        if (curr.leftId === null) {
          const newId = Date.now();
          const offset = 120 / Math.pow(2, depth - 1);
          const newNode: TreeNode = {
            id: newId,
            val: newVal,
            x: curr.x - offset,
            y: curr.y + 80,
            leftId: null,
            rightId: null,
            parentId: curr.id
          };
          curr.leftId = newId;
          newNodes.push(newNode);
          setNodes(newNodes);
          setLogMessage(`插入子契节点 [${newVal}] 作为 [${curr.val}] 的左子`);
          return;
        } else {
          curr = newNodes.find(n => n.id === curr.leftId)!;
        }
      } else {
        if (curr.rightId === null) {
          const newId = Date.now();
          const offset = 120 / Math.pow(2, depth - 1);
          const newNode: TreeNode = {
            id: newId,
            val: newVal,
            x: curr.x + offset,
            y: curr.y + 80,
            leftId: null,
            rightId: null,
            parentId: curr.id
          };
          curr.rightId = newId;
          newNodes.push(newNode);
          setNodes(newNodes);
          setLogMessage(`插入子契节点 [${newVal}] 作为 [${curr.val}] 的右子`);
          return;
        } else {
          curr = newNodes.find(n => n.id === curr.rightId)!;
        }
      }
    }
  };

  // Perform In-order traversal with visual animation
  const startInOrderTraversal = async () => {
    if (traversing) return;
    setTraversing(true);
    setLogMessage('开始进行中序遍历 (左-根-右)...');

    const path: number[] = [];
    
    // In-order recursion helper
    const traverse = (nodeId: number | null) => {
      if (nodeId === null) return;
      const node = nodes.find(n => n.id === nodeId);
      if (!node) return;
      
      traverse(node.leftId);
      path.push(node.id);
      traverse(node.rightId);
    };

    const root = nodes.find(n => n.parentId === null);
    if (root) {
      traverse(root.id);
    }

    // Animate the path
    for (let i = 0; i < path.length; i++) {
      const id = path[i];
      const node = nodes.find(n => n.id === id);
      if (node) {
        setActiveNodeId(id);
        setLogMessage(`中序步进：访问节点 [${node.val}]`);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    setActiveNodeId(null);
    setTraversing(false);
    setLogMessage('中序遍历完成。树的排序结果已成：' + path.map(id => nodes.find(n => n.id === id)?.val).join(' → '));
  };

  return (
    <div className="flex flex-col items-center justify-center w-full max-w-xl p-6 rounded-2xl border border-zinc-200/50 bg-white/35 backdrop-blur-[20px] shadow-[0_12px_40px_rgba(28,43,56,0.04)] relative overflow-hidden text-[#1c2b38]">
      {/* Decorative orbital line background inside panel */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.03]">
        <svg width="100%" height="100%">
          <circle cx="50%" cy="50%" r="180" fill="none" stroke="#1c2b38" strokeWidth="1" strokeDasharray="3 3" />
          <circle cx="50%" cy="50%" r="280" fill="none" stroke="#1c2b38" strokeWidth="0.5" />
        </svg>
      </div>

      {/* Terminal Title */}
      <div className="flex items-center justify-between w-full pb-3 border-b border-[#1c2b38]/10 mb-6">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-zinc-300" />
          <div className="w-2 h-2 rounded-full bg-zinc-200" />
          <div className="w-2 h-2 rounded-full bg-zinc-100" />
          <span className="text-[10px] font-mono tracking-widest text-[#1c2b38]/40 ml-2 uppercase">bst_manuscript.ts</span>
        </div>
        <div className="flex items-center gap-1 text-[9px] font-mono text-[#b91c1c]/70 tracking-widest">
          <Activity className="w-3 h-3 text-[#b91c1c]/50" />
          <span>PRECISION_VISUAL</span>
        </div>
      </div>

      {/* Interactive Canvas */}
      <div className="relative w-full aspect-[500/280] mb-6 flex items-center justify-center bg-[#fcfbfa]/40 rounded-xl border border-zinc-200/45">
        <svg viewBox="0 0 500 280" className="w-full h-full select-none">
          {/* Render Links */}
          {nodes.map(node => {
            const leftChild = node.leftId ? nodes.find(n => n.id === node.leftId) : null;
            const rightChild = node.rightId ? nodes.find(n => n.id === node.rightId) : null;
            
            return (
              <g key={`links-${node.id}`} className="opacity-[0.25]">
                {leftChild && (
                  <line
                    x1={node.x}
                    y1={node.y}
                    x2={leftChild.x}
                    y2={leftChild.y}
                    stroke="#1c2b38"
                    strokeWidth="0.75"
                    className="transition-all duration-500"
                  />
                )}
                {rightChild && (
                  <line
                    x1={node.x}
                    y1={node.y}
                    x2={rightChild.x}
                    y2={rightChild.y}
                    stroke="#1c2b38"
                    strokeWidth="0.75"
                    className="transition-all duration-500"
                  />
                )}
              </g>
            );
          })}

          {/* Render Active Path (Behind standard nodes, styled like ink strokes) */}
          {nodes.map(node => {
            const leftChild = node.leftId ? nodes.find(n => n.id === node.leftId) : null;
            const rightChild = node.rightId ? nodes.find(n => n.id === node.rightId) : null;
            
            const isLeftLineActive = activeNodeId === node.id || (activeNodeId === node.leftId && leftChild);
            const isRightLineActive = activeNodeId === node.id || (activeNodeId === node.rightId && rightChild);

            return (
              <g key={`active-links-${node.id}`}>
                {leftChild && isLeftLineActive && (
                  <motion.line
                    x1={node.x}
                    y1={node.y}
                    x2={leftChild.x}
                    y2={leftChild.y}
                    stroke="#b91c1c"
                    strokeWidth="1.25"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.6 }}
                  />
                )}
                {rightChild && isRightLineActive && (
                  <motion.line
                    x1={node.x}
                    y1={node.y}
                    x2={rightChild.x}
                    y2={rightChild.y}
                    stroke="#b91c1c"
                    strokeWidth="1.25"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.6 }}
                  />
                )}
              </g>
            );
          })}

          {/* Render Nodes */}
          <AnimatePresence>
            {nodes.map(node => {
              const isActive = activeNodeId === node.id;
              return (
                <motion.g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0, opacity: 0 }}
                  transition={{ type: 'spring', damping: 18, stiffness: 180 }}
                  className="cursor-pointer"
                >
                  {/* Glowing background circle (Ink wash brush feel) */}
                  <motion.circle
                    r="15"
                    fill={isActive ? '#ffffff' : '#fcfbfa'}
                    stroke={isActive ? '#b91c1c' : 'rgba(28, 43, 56, 0.25)'}
                    strokeWidth={isActive ? '1.5' : '0.75'}
                    animate={isActive ? { r: [15, 17, 15] } : {}}
                    transition={{ repeat: Infinity, duration: 2 }}
                    style={{
                      filter: isActive ? 'drop-shadow(0 0 4px rgba(185,28,28,0.25))' : 'none'
                    }}
                  />

                  {/* Tiny cinnabar seal spot on nodes */}
                  <circle
                    r="1.5"
                    fill={isActive ? '#b91c1c' : 'rgba(28, 43, 56, 0.15)'}
                    cy="-5"
                  />

                  {/* Node value */}
                  <text
                    textAnchor="middle"
                    dy="4"
                    fill="#1c2b38"
                    className="text-[10px] font-mono font-light tracking-tight"
                  >
                    {node.val}
                  </text>
                </motion.g>
              );
            })}
          </AnimatePresence>
        </svg>
      </div>

      {/* Terminal Log */}
      <div className="w-full bg-[#f4f2ee]/70 border border-zinc-200/50 rounded-lg p-3 mb-6 font-mono text-[10px] text-[#1c2b38]/70 leading-relaxed text-left min-h-[48px] flex items-center">
        <span className="text-[#b91c1c] mr-2 shrink-0 select-none">■</span>
        <span>{logMessage}</span>
      </div>

      {/* Interactive Controls */}
      <div className="grid grid-cols-3 gap-2.5 w-full">
        <button
          onClick={insertNode}
          disabled={traversing}
          className="flex items-center justify-center gap-1.5 px-3 py-2 border border-[#1c2b38]/15 rounded-lg text-[10px] font-medium tracking-widest text-[#1c2b38]/80 bg-white/20 hover:bg-white/60 hover:border-[#1c2b38]/35 disabled:opacity-40 disabled:hover:bg-white/20 transition-all uppercase font-sans select-none"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>插入节点</span>
        </button>

        <button
          onClick={startInOrderTraversal}
          disabled={traversing || nodes.length === 0}
          className="flex items-center justify-center gap-1.5 px-3 py-2 border border-[#b91c1c]/30 rounded-lg text-[10px] font-medium tracking-widest text-[#b91c1c] bg-[#b91c1c]/5 hover:bg-[#b91c1c]/10 disabled:opacity-40 disabled:hover:bg-[#b91c1c]/5 transition-all uppercase font-sans select-none"
        >
          <Play className="w-3.5 h-3.5" />
          <span>中序遍历</span>
        </button>

        <button
          onClick={resetTree}
          disabled={traversing}
          className="flex items-center justify-center gap-1.5 px-3 py-2 border border-[#1c2b38]/15 rounded-lg text-[10px] font-medium tracking-widest text-[#1c2b38]/80 bg-white/20 hover:bg-white/60 hover:border-[#1c2b38]/35 disabled:opacity-40 disabled:hover:bg-white/20 transition-all uppercase font-sans select-none"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>重置沙箱</span>
        </button>
      </div>
    </div>
  );
}
