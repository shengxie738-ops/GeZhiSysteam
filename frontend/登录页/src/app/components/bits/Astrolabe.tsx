import { useEffect } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";

export default function Astrolabe({ activeIndex = 0 }: { activeIndex?: number }) {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Soft elastic spring motion for astronomical rings rotation
  const springConfig = { damping: 45, stiffness: 60, mass: 1 };
  const springX = useSpring(mouseX, springConfig);
  const springY = useSpring(mouseY, springConfig);

  useEffect(() => {
    const handleResize = () => {
      // Resize listener retained for future use
    };
    const handleMouseMove = (e: MouseEvent) => {
      // Normalize coordinate: -0.5 to 0.5
      const nx = (e.clientX / window.innerWidth) - 0.5;
      const ny = (e.clientY / window.innerHeight) - 0.5;
      mouseX.set(nx);
      mouseY.set(ny);
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, [mouseX, mouseY]);

  // Dynamic coordinates and transformations based on active index
  const getContainerStyle = () => {
    if (activeIndex === 1) {
      return {
        top: "12%",
        left: "4%",
        right: "auto",
        transform: "scale(1.25) rotate(120deg)",
        opacity: 0.22,
      };
    } else if (activeIndex === 2) {
      return {
        top: "8%",
        left: "50%",
        right: "auto",
        transform: "translateX(-50%) scale(1.1) rotate(240deg)",
        opacity: 0.28,
      };
    }
    // Default Hero layout (activeIndex === 0)
    return {
      top: "-5%",
      right: "-2%",
      left: "auto",
      transform: "scale(1.0) rotate(0deg)",
      opacity: 0.42,
    };
  };

  const currentStyle = getContainerStyle();

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden select-none z-0">
      {/* Astrolabe container anchored to top-right which perfectly matches the background image layout */}
      <div 
        className="absolute w-[650px] h-[650px] transition-all duration-[1200ms] ease-[cubic-bezier(0.76,0,0.24,1)]"
        style={{
          top: currentStyle.top,
          left: currentStyle.left,
          right: currentStyle.right,
          transform: currentStyle.transform,
          opacity: currentStyle.opacity,
          willChange: "top, left, right, transform, opacity"
        }}
      >
        <svg 
          viewBox="0 0 600 600" 
          className="w-full h-full text-[#1c2b38]"
          fill="none"
          stroke="currentColor"
        >
          {/* Outermost tick ring */}
          <motion.g 
            style={{
              rotate: springX,
              originX: "300px",
              originY: "300px",
            }}
          >
            <circle cx="300" cy="300" r="280" strokeWidth="0.5" strokeDasharray="1 5" />
            <circle cx="300" cy="300" r="275" strokeWidth="0.5" />
            {/* Compass degree text markers */}
            <text x="300" y="34" fontSize="6" fontFamily="monospace" textAnchor="middle" fill="currentColor" opacity="0.6">N 00°</text>
            <text x="566" y="302" fontSize="6" fontFamily="monospace" textAnchor="middle" fill="currentColor" opacity="0.6">E 90°</text>
            <text x="300" y="572" fontSize="6" fontFamily="monospace" textAnchor="middle" fill="currentColor" opacity="0.6">S 180°</text>
            <text x="34" y="302" fontSize="6" fontFamily="monospace" textAnchor="middle" fill="currentColor" opacity="0.6">W 270°</text>
          </motion.g>

          {/* Geometric orbit 2 */}
          <motion.g 
            style={{
              rotate: springY,
              originX: "300px",
              originY: "300px",
            }}
          >
            <circle cx="300" cy="300" r="230" strokeWidth="0.5" strokeDasharray="30 15 2 15" />
            {/* Cross alignments */}
            <line x1="300" y1="70" x2="300" y2="530" strokeWidth="0.25" opacity="0.4" />
            <line x1="70" y1="300" x2="530" y2="300" strokeWidth="0.25" opacity="0.4" />
            
            {/* Precise small coordinate circles */}
            <circle cx="300" cy="70" r="4" fill="none" strokeWidth="0.5" />
            <circle cx="300" cy="530" r="4" fill="none" strokeWidth="0.5" />
            <circle cx="70" cy="300" r="4" fill="none" strokeWidth="0.5" />
            <circle cx="530" cy="300" r="4" fill="none" strokeWidth="0.5" />
          </motion.g>

          {/* Inner ring 3 */}
          <motion.g 
            style={{
              // Combine X & Y coordinates to rotate faster in the opposite direction
              rotate: springX,
              originX: "300px",
              originY: "300px",
            }}
          >
            <circle cx="300" cy="300" r="180" strokeWidth="0.75" />
            {/* Precise technical tick marks */}
            {Array.from({ length: 24 }).map((_, i) => {
              const angle = (i * 360) / 24;
              const rad = (angle * Math.PI) / 180;
              const x1 = 300 + 175 * Math.cos(rad);
              const y1 = 300 + 175 * Math.sin(rad);
              const x2 = 300 + 180 * Math.cos(rad);
              const y2 = 300 + 180 * Math.sin(rad);
              return (
                <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} strokeWidth="0.5" opacity="0.7" />
              );
            })}
          </motion.g>

          {/* Innermost orbital with offset concentric circle */}
          <motion.g 
            style={{
              // Off-axis rotation for asymmetric organic physics
              x: useSpring(useSpring(mouseX, springConfig), springConfig),
              y: useSpring(useSpring(mouseY, springConfig), springConfig),
              originX: "300px",
              originY: "300px",
            }}
          >
            <circle cx="300" cy="300" r="110" strokeWidth="0.5" strokeDasharray="5 20" />
            <circle cx="280" cy="280" r="70" strokeWidth="0.25" opacity="0.5" />
            <circle cx="300" cy="300" r="3" fill="currentColor" />
          </motion.g>

          {/* Delicate astronomical constellations nodes */}
          <path d="M 300,70 L 450,150 L 530,300 M 70,300 L 150,150 L 300,70" strokeWidth="0.25" strokeDasharray="2 4" opacity="0.5" />
        </svg>
      </div>

      {/* Vertical curatorial alignment guidelines in the center background */}
      <div className="absolute left-[8%] md:left-[12%] top-0 bottom-0 w-px bg-gradient-to-b from-[#1c2b38]/10 via-[#1c2b38]/5 to-transparent pointer-events-none" />
      <div className="absolute left-[50%] top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-[#1c2b38]/4 to-transparent pointer-events-none" />
    </div>
  );
}
