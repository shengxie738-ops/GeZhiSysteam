import { motion } from "framer-motion";

interface GezhiLogoProps {
  size?: number;
  className?: string;
  interactive?: boolean;
  variant?: "navbar" | "footer" | "hero";
}

export default function GezhiLogo({
  size = 32,
  className = "",
  interactive = true,
  variant = "navbar",
}: GezhiLogoProps) {
  // Traditional Cinnabar Red (朱砂红) and Charcoal Ink (徽墨蓝) color tokens
  const cinnabarRed = "#b91c1c";
  const charcoalInk = "#1c2b38";
  const parchmentWhite = "#fdfbf7";
  const goldDust = "#d4af37";

  // SVG Filter for ink bleeding (水墨晕染) and hand-carved stone seal distress (金石残缺)
  // This filter is the secret to rejecting AI's sterile, perfect geometric lines
  const filterId = `gezhi-ink-filter-${variant}`;

  // Gold dust particles for the hero/interactive variants
  const particles = [
    { id: 1, cx: 25, cy: 75, r: 0.8, delay: 0, duration: 3, x: [0, -4, 2], y: [0, -25, -45] },
    { id: 2, cx: 75, cy: 80, r: 0.6, delay: 0.5, duration: 3.5, x: [0, 3, -2], y: [0, -30, -50] },
    { id: 3, cx: 30, cy: 30, r: 0.7, delay: 1, duration: 4, x: [0, -2, 4], y: [0, -20, -40] },
    { id: 4, cx: 80, cy: 40, r: 0.5, delay: 1.5, duration: 3.2, x: [0, 4, -1], y: [0, -25, -45] },
    { id: 5, cx: 50, cy: 85, r: 0.9, delay: 0.8, duration: 3.8, x: [0, -1, 3], y: [0, -35, -55] },
  ];

  // Seal Script (小篆) Path for "格" (Top Half)
  const gePath = (
    <g>
      {/* 左侧：木 (Wood) */}
      {/* 竖干 (Vertical trunk) */}
      <path
        d="M 36 21 C 36 21, 35 32, 35 46"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 弯横 (Curved horizontal bar) */}
      <path
        d="M 23 27 C 29 25.5, 35 25.5, 41 27"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 左撇 (Left leg) */}
      <path
        d="M 35 33 C 31 38, 26 42, 21 45"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 右捺 (Right leg) */}
      <path
        d="M 35 33 C 39 38, 44 42, 49 45"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* 右侧：各 (Each) */}
      {/* 上部：夂 (Top curve) */}
      <path
        d="M 54 21 C 60 18, 66 18, 72 21"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M 56 28 C 61 25.5, 67 25.5, 72 28"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M 52 34 Q 63 32, 74 34"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 下部：口 (Bottom rounded box) */}
      <path
        d="M 55 40 C 55 37.5, 71 37.5, 71 40 C 71 43.5, 55 43.5, 55 40 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </g>
  );

  // Seal Script (小篆) Path for "至" (Bottom Half)
  const zhiPath = (
    <g>
      {/* 顶横 (Top horizontal bar) */}
      <path
        d="M 27 53 C 41 51, 59 51, 73 53"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 中竖 (Central vertical stem) */}
      <path
        d="M 50 53 L 50 77"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 中间双弯 (Middle wings / curves) */}
      {/* 第一层弯 (First layer curves) */}
      <path
        d="M 36 63 C 42 60, 48 60, 50 63"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M 64 63 C 58 60, 52 60, 50 63"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 第二层弯 (Second layer curves) */}
      <path
        d="M 38 71 C 43 68, 48 68, 50 71"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M 62 71 C 57 68, 52 68, 50 71"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 底横 (Bottom horizontal ground) */}
      <path
        d="M 22 77 C 40 75.5, 60 75.5, 78 77"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </g>
  );

  // Irregular, hand-carved square seal border with natural stone chips (金石残缺)
  const sealBorderPath = "M 17 14 C 15 14, 13 15, 13 17 L 14 31 C 13 36, 14 44, 13 54 L 14 69 C 13 74, 14 80, 16 82 C 17 83, 19 85, 22 84 L 34 85 C 44 84, 54 85, 64 84 L 77 85 C 80 85, 82 83, 83 81 L 82 69 C 83 59, 82 49, 83 39 L 82 26 C 83 21, 82 17, 80 15 C 78 14, 74 15, 69 14 L 54 15 C 44 14, 34 15, 24 14 Z";

  if (variant === "footer") {
    // Footer variant: Extremely clean, disciplined, monochrome or single-color
    // Matches the "intellectual silence" of the footer section
    return (
      <div
        className={`relative flex items-center justify-center ${className}`}
        style={{ width: size, height: size }}
      >
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          className="text-current transition-colors duration-300"
          style={{ color: charcoalInk }}
        >
          <defs>
            {/* Subtle filter for organic touch in footer */}
            <filter id={filterId} x="-10%" y="-10%" width="120%" height="120%">
              <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="3" result="noise" />
              <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.5" xChannelSelector="R" yChannelSelector="G" />
            </filter>
          </defs>

          <g filter={`url(#${filterId})`}>
            {/* Hand-carved seal border */}
            <path
              d={sealBorderPath}
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinejoin="round"
            />
            {/* Seal Script characters */}
            <g className="text-current">
              {gePath}
              {zhiPath}
            </g>
          </g>
        </svg>
      </div>
    );
  }

  if (variant === "hero") {
    // Large, highly detailed, luxurious hero variant
    // Features rotating astrolabe background, floating gold dust, and deep gradients
    return (
      <div
        className={`relative flex items-center justify-center ${className}`}
        style={{ width: size, height: size }}
      >
        {/* Background Astrolabe Ring */}
        <motion.div
          className="absolute inset-0 pointer-events-none opacity-[0.06]"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 60, ease: "linear" }}
        >
          <svg width="100%" height="100%" viewBox="0 0 200 200" className="text-[#1c2b38]">
            <circle cx="100" cy="100" r="95" fill="none" stroke="currentColor" strokeWidth="0.5" />
            <circle cx="100" cy="100" r="90" fill="none" stroke="currentColor" strokeWidth="0.25" strokeDasharray="1 3" />
            <circle cx="100" cy="100" r="75" fill="none" stroke="currentColor" strokeWidth="0.5" strokeDasharray="4 4" />
            <line x1="100" y1="0" x2="100" y2="200" stroke="currentColor" strokeWidth="0.25" strokeDasharray="2 2" />
            <line x1="0" y1="100" x2="200" y2="100" stroke="currentColor" strokeWidth="0.25" strokeDasharray="2 2" />
          </svg>
        </motion.div>

        {/* Floating Gold Dust Particles */}
        {interactive && (
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <svg width="100%" height="100%" viewBox="0 0 100 100">
              <defs>
                <radialGradient id="gold-glow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#fff" />
                  <stop offset="30%" stopColor={goldDust} />
                  <stop offset="100%" stopColor="transparent" />
                </radialGradient>
              </defs>
              {particles.map((p) => (
                <motion.circle
                  key={p.id}
                  cx={p.cx}
                  cy={p.cy}
                  r={p.r}
                  fill="url(#gold-glow)"
                  animate={{
                    x: p.x,
                    y: p.y,
                    opacity: [0, 0.8, 0.8, 0],
                  }}
                  transition={{
                    repeat: Infinity,
                    duration: p.duration,
                    delay: p.delay,
                    ease: "easeOut",
                  }}
                />
              ))}
            </svg>
          </div>
        )}

        {/* The Cinnabar Seal */}
        <motion.div
          className="relative cursor-pointer"
          style={{ width: "80%", height: "80%" }}
          animate={interactive ? { y: [0, -4, 0] } : {}}
          transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
          whileHover={interactive ? { scale: 1.04, rotate: -1 } : {}}
        >
          <svg
            width="100%"
            height="100%"
            viewBox="0 0 100 100"
            className="drop-shadow-[0_10px_25px_rgba(185,28,28,0.12)]"
          >
            <defs>
              <linearGradient id="hero-seal-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#c92a2a" />
                <stop offset="50%" stopColor={cinnabarRed} />
                <stop offset="100%" stopColor="#8e1c1c" />
              </linearGradient>

              {/* Advanced Ink Bleed + Distress Filter */}
              <filter id={filterId} x="-10%" y="-10%" width="120%" height="120%">
                {/* Fractal noise creates the paper fiber and stone carving distress */}
                <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="4" result="noise" />
                {/* Displace the graphics slightly to roughen the edges */}
                <feDisplacementMap in="SourceGraphic" in2="noise" scale="3.5" xChannelSelector="R" yChannelSelector="G" result="displaced" />
                {/* Blur slightly to simulate ink bleeding into paper fibers */}
                <feGaussianBlur in="displaced" stdDeviation="0.4" result="blurred" />
                <feMerge>
                  <feMergeNode in="blurred" />
                  <feMergeNode in="SourceGraphic" opacity="0.15" />
                </feMerge>
              </filter>
            </defs>

            <g filter={`url(#${filterId})`}>
              {/* Solid hand-carved seal background (白文 style) */}
              <path d={sealBorderPath} fill="url(#hero-seal-grad)" />
              
              {/* Carved-out characters (Baiwen style, rendered in parchment white) */}
              <g style={{ color: parchmentWhite }}>
                {gePath}
                {zhiPath}
              </g>
            </g>
          </svg>
        </motion.div>
      </div>
    );
  }

  // Default: Navbar variant (Small, highly optimized, elegant)
  return (
    <div
      className={`relative flex items-center justify-center group/logo ${className}`}
      style={{ width: size, height: size }}
    >
      {/* Interactive glowing red aura behind the seal */}
      {interactive && (
        <div
          className="absolute inset-0 rounded-lg bg-[#b91c1c] opacity-0 group-hover/logo:opacity-15 transition-opacity duration-500 blur-md pointer-events-none"
          style={{ transform: "scale(1.2)" }}
        />
      )}

      {/* The Cinnabar Seal Container */}
      <motion.div
        className="w-full h-full relative"
        whileHover={interactive ? { scale: 1.05, rotate: -1.5 } : {}}
        transition={{ type: "spring", stiffness: 400, damping: 15 }}
      >
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          className="w-full h-full"
        >
          <defs>
            {/* Cinnabar Red Gradient */}
            <linearGradient id="nav-seal-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#c92a2a" />
              <stop offset="100%" stopColor={cinnabarRed} />
            </linearGradient>

            {/* Ink Bleed Filter for organic, hand-stamped feel */}
            <filter id={filterId} x="-10%" y="-10%" width="120%" height="120%">
              <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="3" result="noise" />
              <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.2" xChannelSelector="R" yChannelSelector="G" result="displaced" />
              <feGaussianBlur in="displaced" stdDeviation="0.3" result="blurred" />
              <feMerge>
                <feMergeNode in="blurred" />
                <feMergeNode in="SourceGraphic" opacity="0.2" />
              </feMerge>
            </filter>
          </defs>

          <g filter={`url(#${filterId})`}>
            {/* Hand-carved seal background (白文 style) */}
            <path d={sealBorderPath} fill="url(#nav-seal-grad)" />
            
            {/* Carved-out characters in parchment white */}
            <g style={{ color: parchmentWhite }}>
              {gePath}
              {zhiPath}
            </g>
          </g>
        </svg>
      </motion.div>
    </div>
  );
}
