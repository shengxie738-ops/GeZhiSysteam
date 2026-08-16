import { useState, useEffect, useRef } from "react";
import loginBg from "@/imports/login-bg.png";
import confetti from "canvas-confetti";
import { motion } from "framer-motion";
import {
  Compass,
  Cpu,
  UserCheck,
  ArrowRight,
  Lock,
  User,
  Check,
  Code,
  Terminal,
  ChevronRight,
  Sparkles,
  ArrowUpRight,
  CheckCircle2,
  Phone,
  ShieldCheck,
} from "lucide-react";

// Import our custom premium components
import Galaxy from "./components/bits/Galaxy";
import Magnet from "./components/bits/Magnet";
import ShinyText from "./components/bits/ShinyText";
import Astrolabe from "./components/bits/Astrolabe";
import GezhiLogo from "./components/bits/GezhiLogo";
import { authApi, toBackendAssetUrl } from "../api/authApi";

const NAV_ITEMS = [
  { zh: "产品主页", en: "PORTAL", id: "hero" },
  { zh: "智能网格", en: "NETWORK", id: "architecture" },
  { zh: "格物致知", en: "PHILOSOPHY", id: "philosophy" },
];

const CODE_LINES = [
  [
    { text: "class ", className: "text-[#b91c1c]/80" },
    { text: "GeZhiSystem", className: "font-serif italic font-semibold text-[#1c2b38]" },
    { text: " {", className: "text-[#1c2b38]/85" }
  ],
  [
    { text: "  // 聚学智而启思 汇教智而授业", className: "text-zinc-400 font-serif italic" }
  ],
  [
    { text: "  students", className: "text-zinc-500" },
    { text: ": ", className: "text-[#1c2b38]/85" },
    { text: "Agent", className: "font-serif italic text-zinc-600" },
    { text: "[];", className: "text-[#1c2b38]/85" }
  ],
  [
    { text: "  teachers", className: "text-zinc-500" },
    { text: ": ", className: "text-[#1c2b38]/85" },
    { text: "Agent", className: "font-serif italic text-zinc-600" },
    { text: "[];", className: "text-[#1c2b38]/85" }
  ],
  [
    { text: "", className: "" }
  ],
  [
    { text: "  // 协众体而同频 融多方而共生", className: "text-zinc-400 font-serif italic" }
  ],
  [
    { text: "  coordinate", className: "text-indigo-900/70" },
    { text: "(): ", className: "text-[#1c2b38]/85" },
    { text: "string", className: "text-indigo-900/70" },
    { text: " {", className: "text-[#1c2b38]/85" }
  ],
  [
    { text: "    return ", className: "text-[#b91c1c]/80" },
    { text: "\"教学相长，智境天成\"", className: "text-emerald-700/90 font-serif italic" },
    { text: ";", className: "text-[#1c2b38]/85" }
  ],
  [
    { text: "  }", className: "text-[#1c2b38]/85" }
  ],
  [
    { text: "}", className: "text-[#1c2b38]/85" }
  ],
  [
    { text: "", className: "" }
  ],
  [
    { text: "interface ", className: "text-[#b91c1c]/80" },
    { text: "Agent", className: "font-serif italic font-semibold text-[#1c2b38]" },
    { text: " { id: ", className: "text-[#1c2b38]/85" },
    { text: "string", className: "text-indigo-900/70" },
    { text: "; role: ", className: "text-[#1c2b38]/85" },
    { text: "string", className: "text-indigo-900/70" },
    { text: " }", className: "text-[#1c2b38]/85" }
  ]
];

export default function App() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [galaxySpeed, setGalaxySpeed] = useState(0.15);

  const [scrollY, setScrollY] = useState(0);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [role, setRole] = useState<"student" | "teacher">("student");
  
  // Login Form States
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [realName, setRealName] = useState("");
  const [studentId, setStudentId] = useState("");
  const [className, setClassName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loginMethod, setLoginMethod] = useState<"password" | "mobile">("password");
  const [phone, setPhone] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [code, setCode] = useState("");
  const [countdown, setCountdown] = useState(0);
  const [smsTip, setSmsTip] = useState("");
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const [loginState, setLoginState] = useState<"idle" | "loading" | "success">("idle");
  const [activeAgent, setActiveAgent] = useState(0);

  // Typewriter Terminal effect
  const [typedCharCount, setTypedCharCount] = useState(0);
  const [isTypingComplete, setIsTypingComplete] = useState(false);

  useEffect(() => {
    const totalLength = CODE_LINES.reduce((sum, line) => {
      return sum + line.reduce((lineSum, token) => lineSum + token.text.length, 0);
    }, 0);

    if (typedCharCount >= totalLength && !isTypingComplete) {
      setIsTypingComplete(true);
      const timer = setTimeout(() => {
        setIsTypingComplete(false);
        setTypedCharCount(0);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [typedCharCount, isTypingComplete]);

  useEffect(() => {
    if (isTypingComplete) return;

    const totalLength = CODE_LINES.reduce((sum, line) => {
      return sum + line.reduce((lineSum, token) => lineSum + token.text.length, 0);
    }, 0);

    const timer = setInterval(() => {
      setTypedCharCount((prev) => {
        if (prev >= totalLength) {
          return prev;
        }
        return prev + 1;
      });
    }, 50); // Slower, more natural typing speed (50ms per character)

    return () => clearInterval(timer);
  }, [isTypingComplete]);

  // Scroll visibility observers
  const [visible, setVisible] = useState({
    architecture: false,
    philosophy: false,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const archRef = useRef<HTMLDivElement>(null);
  const philRef = useRef<HTMLDivElement>(null);
  const lastScrollTime = useRef(0);
  const touchStartY = useRef(0);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Handle standard scroll on mobile, or synchronize states on desktop
  useEffect(() => {
    if (isMobile) {
      const handleScroll = () => {
        const sy = window.scrollY;
        const maxScroll = document.body.scrollHeight - window.innerHeight;
        setScrollY(sy);
        setScrollProgress(maxScroll > 0 ? sy / maxScroll : 0);

        const checkVisibility = (
          ref: React.RefObject<HTMLDivElement | null>,
          key: keyof typeof visible
        ) => {
          if (ref.current) {
            const rect = ref.current.getBoundingClientRect();
            if (rect.top < window.innerHeight * 0.85) {
              setVisible((prev) => ({ ...prev, [key]: true }));
            }
          }
        };

        checkVisibility(archRef, "architecture");
        checkVisibility(philRef, "philosophy");
      };

      window.addEventListener("scroll", handleScroll, { passive: true });
      handleScroll();
      return () => window.removeEventListener("scroll", handleScroll);
    } else {
      // Desktop: synchronise visible states with activeIndex
      setVisible({
        architecture: activeIndex === 1,
        philosophy: activeIndex === 2,
      });
      setScrollProgress(activeIndex / 2);
    }
  }, [isMobile, activeIndex]);

  // Galaxy speed boost during desktop transitions (creates a gorgeous hyperspace feel)
  useEffect(() => {
    if (!isMobile) {
      setGalaxySpeed(2.8);
      const timer = setTimeout(() => {
        setGalaxySpeed(0.15);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [activeIndex, isMobile]);

  // Desktop Mouse Wheel snap-scrolling
  useEffect(() => {
    if (isMobile) return;

    const preventDefault = (e: TouchEvent) => {
      e.preventDefault();
    };

    const handleWheelGlobal = (e: WheelEvent) => {
      e.preventDefault();

      const now = Date.now();
      if (isTransitioning || now - lastScrollTime.current < 1200) {
        return;
      }

      if (e.deltaY > 15) {
        // Scroll down -> next page
        if (activeIndex < 2) {
          lastScrollTime.current = now;
          setIsTransitioning(true);
          setActiveIndex((prev) => prev + 1);
          setTimeout(() => setIsTransitioning(false), 1200);
        }
      } else if (e.deltaY < -15) {
        // Scroll up -> prev page
        if (activeIndex > 0) {
          lastScrollTime.current = now;
          setIsTransitioning(true);
          setActiveIndex((prev) => prev - 1);
          setTimeout(() => setIsTransitioning(false), 1200);
        }
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener("wheel", handleWheelGlobal, { passive: false });
      container.addEventListener("touchmove", preventDefault, { passive: false });
    }

    return () => {
      if (container) {
        container.removeEventListener("wheel", handleWheelGlobal);
        container.removeEventListener("touchmove", preventDefault);
      }
    };
  }, [activeIndex, isTransitioning, isMobile]);

  // Touch Swiping for mobile-like gesture swipe support on desktop/tablet devices
  useEffect(() => {
    if (isMobile) return;

    const handleTouchStart = (e: TouchEvent) => {
      touchStartY.current = e.touches[0].clientY;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      const touchEndY = e.changedTouches[0].clientY;
      const deltaY = touchStartY.current - touchEndY; // Positive means swipe up (scrolling down)
      
      const now = Date.now();
      if (isTransitioning || now - lastScrollTime.current < 1200) {
        return;
      }

      if (deltaY > 50) {
        // Swipe up -> Scroll down
        if (activeIndex < 2) {
          lastScrollTime.current = now;
          setIsTransitioning(true);
          setActiveIndex((prev) => prev + 1);
          setTimeout(() => setIsTransitioning(false), 1200);
        }
      } else if (deltaY < -50) {
        // Swipe down -> Scroll up
        if (activeIndex > 0) {
          lastScrollTime.current = now;
          setIsTransitioning(true);
          setActiveIndex((prev) => prev - 1);
          setTimeout(() => setIsTransitioning(false), 1200);
        }
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener("touchstart", handleTouchStart, { passive: true });
      container.addEventListener("touchend", handleTouchEnd, { passive: true });
    }

    return () => {
      if (container) {
        container.removeEventListener("touchstart", handleTouchStart);
        container.removeEventListener("touchend", handleTouchEnd);
      }
    };
  }, [activeIndex, isTransitioning, isMobile]);

  // Keyboard navigation on desktop
  useEffect(() => {
    if (isMobile) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const now = Date.now();
      if (isTransitioning || now - lastScrollTime.current < 1200) {
        return;
      }

      if (["ArrowDown", "PageDown", " "].includes(e.key)) {
        e.preventDefault();
        if (activeIndex < 2) {
          lastScrollTime.current = now;
          setIsTransitioning(true);
          setActiveIndex((prev) => prev + 1);
          setTimeout(() => setIsTransitioning(false), 1200);
        }
      } else if (["ArrowUp", "PageUp"].includes(e.key)) {
        e.preventDefault();
        if (activeIndex > 0) {
          lastScrollTime.current = now;
          setIsTransitioning(true);
          setActiveIndex((prev) => prev - 1);
          setTimeout(() => setIsTransitioning(false), 1200);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [activeIndex, isTransitioning, isMobile]);

  // Cleanup SMS countdown timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const handleSendCode = async () => {
    if (!phone || !/^1[3-9]\d{9}$/.test(phone)) {
      setSmsTip("请输入正确的11位手机号码");
      setTimeout(() => setSmsTip(""), 3000);
      return;
    }

    const res = await authApi.sendSmsCode({
      phone,
      purpose: authMode === "register" ? "register" : "login",
      role,
    });
    if (!res.success) {
      setSmsTip(res.message);
      setTimeout(() => setSmsTip(""), 3000);
      return;
    }

    const debugCode = res.data?.debug_code ? `：${res.data.debug_code}` : "";
    setSmsTip(`${res.message}${debugCode}`);

    setCountdown(60);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // Register sequence
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const requiredStudentMissing = role === "student" && (
      !realName || !studentId || !className || !password || !confirmPassword || !phone || !code
    );
    const requiredTeacherMissing = role === "teacher" && (!username || !password || !confirmPassword || !teacherId);

    if (requiredStudentMissing || requiredTeacherMissing) {
      setSmsTip("请填写所有必填信息");
      setTimeout(() => setSmsTip(""), 3000);
      return;
    }
    if (password !== confirmPassword) {
      setSmsTip("两次密码输入不一致");
      setTimeout(() => setSmsTip(""), 3000);
      return;
    }
    if (role === "teacher" && !teacherId) {
      setSmsTip("教师身份需填写工号");
      setTimeout(() => setSmsTip(""), 3000);
      return;
    }

    setLoginState("loading");
    try {
      const res = await authApi.register({
        username: role === "student" ? studentId : username,
        password,
        confirm_password: confirmPassword,
        phone,
        role,
        real_name: role === "student" ? realName : undefined,
        student_id: role === "student" ? studentId : undefined,
        class_name: role === "student" ? className : undefined,
        sms_code: role === "student" ? code : undefined,
        teacher_id: role === "teacher" ? teacherId : undefined,
      });

      if (res.success) {
        setSmsTip("注册成功，请登录！");
        setTimeout(() => {
          setSmsTip("");
          setAuthMode("login");
          setLoginState("idle");
          setPassword("");
          setConfirmPassword("");
          setCode("");
        }, 1500);
      } else {
        setSmsTip(res.message);
        setTimeout(() => setSmsTip(""), 3000);
        setLoginState("idle");
      }
    } catch (err) {
      setSmsTip("系统错误，请稍后再试");
      setTimeout(() => setSmsTip(""), 3000);
      setLoginState("idle");
    }
  };

  const goToAppHome = () => {
    const devAppHome = `${window.location.origin}/app/index.html`;
    window.location.href = import.meta.env.DEV ? devAppHome : "../index.html";
  };

  // Premium login sequence with classic cinnabar red seal
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (authMode === "register") {
      return handleRegister(e);
    }

    const loginUser = loginMethod === "password" ? username : phone;
    if (loginMethod === "password") {
      if (!username || !password) return;
    } else {
      if (!phone || !code) return;
    }

    setLoginState("loading");
    
    try {
      const res = loginMethod === "password"
        ? await authApi.login({ username: loginUser, password, role })
        : await authApi.mobileLogin({ phone, sms_code: code, role });

      if (!res.success) {
        setSmsTip(res.message);
        setTimeout(() => setSmsTip(""), 3000);
        setLoginState("idle");
        return;
      }

      setLoginState("success");
      confetti({
        particleCount: 140,
        spread: 90,
        origin: { y: 0.62 },
        colors: ["#b91c1c", "#b45309", "#d4af37", "#fdfbf7", "#1c2b38"],
      });

      const user = res.data?.user;

      // Set localStorage to integrate with frontend auth
      localStorage.setItem("isLoggedIn", "true");
      localStorage.setItem("currentUser", JSON.stringify({
        username: user?.username || loginUser,
        real_name: user?.real_name || "",
        student_id: user?.student_id || "",
        teacher_id: user?.teacher_id || "",
        class_name: user?.class_name || "",
        phone: user?.phone || phone,
        avatar_url: toBackendAssetUrl(user?.avatar_url)
      }));
      localStorage.setItem("currentRole", role);
      localStorage.setItem("currentView", role === "student" ? "dashboard" : "t_dashboard");
      localStorage.setItem("isTeacherLogin", role === "teacher" ? "true" : "false");
      if (res.data?.token) {
        localStorage.setItem("token", res.data.token);
      }

      // Auto redirect after 2.2 seconds to show cinematic success
      setTimeout(() => {
        goToAppHome();
      }, 2200);

    } catch (err) {
      setSmsTip("系统错误，请稍后再试");
      setTimeout(() => setSmsTip(""), 3000);
      setLoginState("idle");
    }
  };

  const handleResetLogin = () => {
    setLoginState("idle");
    setUsername("");
    setRealName("");
    setStudentId("");
    setClassName("");
    setPassword("");
    setConfirmPassword("");
    setPhone("");
    setTeacherId("");
    setCode("");
    setSmsTip("");
    setCountdown(0);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  // Parallax / Dynamic Background parameters
  const bgStyle = isMobile
    ? {
        top: "-15%",
        transform: `translateY(${scrollY * 0.22}px)`,
        willChange: "transform",
        opacity: 1,
      }
    : {
        top: "-10%",
        transform: `translateY(${activeIndex * -70}px) scale(${1.02 + activeIndex * 0.04})`,
        filter: `blur(${activeIndex * 2.5}px)`,
        transition: "transform 1.2s cubic-bezier(0.76, 0, 0.24, 1), filter 1.2s cubic-bezier(0.76, 0, 0.24, 1)",
        willChange: "transform, filter",
        opacity: 0.95,
      };

  const navOpacity = isMobile ? Math.min(scrollY / 120, 1) : 1;

  // 4 AI Agents blueprint parameters
  const AGENTS_DATA = [
    {
      title: "导师 Agent (Coach)",
      role: "Socratic Method",
      icon: Cpu,
      color: "from-[#b91c1c]/10 to-transparent",
      borderColor: "border-[#b91c1c]/25",
      glowColor: "rgba(185, 28, 28, 0.15)",
      desc: "采用苏格拉底式启发教学。不直接提供解法，而是敏锐解析代码逻辑漏洞，通过精准对立问题引导学子主动推演状态机演变。",
      perks: ["逻辑路径对立诊断", "苏格拉底步进引导", "自适应认知匹配"],
    },
    {
      title: "图谱 Agent (Mapper)",
      role: "Astrolabe Engine",
      icon: Compass,
      color: "from-zinc-500/10 to-transparent",
      borderColor: "border-zinc-300",
      glowColor: "rgba(28, 43, 56, 0.1)",
      desc: "动态扫描并绘制个人专属的知识脉络拓扑。将庞杂抽象的概念解耦为微观星群路径，实现真正的自适应图谱引导。",
      perks: ["星流概念拓扑映射", "前驱知识断点智能扫描", "自适应记忆留存曲线预测"],
    },
    {
      title: "沙箱 Agent (Evaluator)",
      role: "Visual Arbitrator",
      icon: Code,
      color: "from-amber-600/10 to-transparent",
      borderColor: "border-amber-500/25",
      glowColor: "rgba(180, 83, 9, 0.15)",
      desc: "直接接管浏览器底层编译引擎。解构用户书写的每一次指针交换与递归调用，无缝投影为物理层面的树形分支和堆栈涟漪。",
      perks: ["内存堆栈微动轨迹追踪", "时空复杂度全量解构", "瞬时轻量即时编译"],
    },
    {
      title: "画像 Agent (Profiler)",
      role: "Silent Profiler",
      icon: UserCheck,
      color: "from-zinc-400/10 to-transparent",
      borderColor: "border-zinc-400/30",
      glowColor: "rgba(28, 43, 56, 0.12)",
      desc: "静默重塑多维度的习作行为模型。深度归纳学子的调试时长、编码心流、边界卡顿等多阶隐性特征，绘制高维度素养画像。",
      perks: ["行为流心电热力图", "认知过载静默预警", "能力模型量化追踪"],
    },
  ];

  return (
    <div
      className={
        isMobile
          ? "relative text-[#1c2b38] bg-[#e1e5e8] min-h-screen overflow-x-hidden selection:bg-[#b91c1c]/20 selection:text-[#b91c1c]"
          : authMode === "register"
            ? "relative text-[#1c2b38] bg-[#e1e5e8] h-screen w-screen overflow-x-hidden overflow-y-auto selection:bg-[#b91c1c]/20 selection:text-[#b91c1c]"
            : "relative text-[#1c2b38] bg-[#e1e5e8] h-screen w-screen overflow-hidden selection:bg-[#b91c1c]/20 selection:text-[#b91c1c]"
      }
      style={{
        fontFamily: "'Barlow', 'Barlow Condensed', 'Noto Serif SC', sans-serif",
      }}
    >
      {/* ── BACKGROUND LAYER ───────────────────────────────── */}
      <div className="fixed inset-0 -z-20 overflow-hidden pointer-events-none">
        {/* Parallax Chinese Ink Landscape Background Image */}
        <img
          src={loginBg}
          alt="Chinese ink wash astronomy landscape"
          className="absolute w-full h-[135%] object-cover object-center scale-102"
          style={bgStyle}
        />
        {/* Subtle, expensive parchment paper texture filter overlay */}
        <div
          className="absolute inset-0 opacity-[0.22] pointer-events-none mix-blend-multiply"
          style={{
            background: "radial-gradient(circle at 50% 50%, transparent 0%, rgba(28, 43, 56, 0.08) 80%, rgba(28, 43, 56, 0.15) 100%)",
          }}
        />
      </div>

      {/* ── INTERACTIVE WEBGL CELESTIAL PARTICLE SHIMMER ────── */}
      <div className="fixed inset-0 -z-10 pointer-events-none">
        <Galaxy
          density={0.7}
          starSpeed={0.03} // Extremely tranquil, slow float
          glowIntensity={0.2}
          speed={isMobile ? 0.15 : galaxySpeed}
          hueShift={180} // Silver, steel blue tone
          saturation={0} // Completely monochromatic grayscale stars
          mouseRepulsion={true}
          repulsionStrength={1.5}
          transparent={true}
        />
      </div>

      {/* ── INTERACTIVE ASTROLABE GEOMETRY OVERLAY ───────────── */}
      <Astrolabe activeIndex={isMobile ? 0 : activeIndex} />

      {/* ── GLOWING SCROLL PROGRESS LINE ─────────────────────── */}
      <div
        className="fixed top-0 left-0 h-[2px] z-50 transition-all duration-[1200ms] ease-[cubic-bezier(0.76,0,0.24,1)]"
        style={{
          width: `${scrollProgress * 100}%`,
          background: "linear-gradient(to right, #1c2b38, #b91c1c)",
        }}
      />

      {/* ── CURATORIAL GLASSMORPHISM NAVIGATION ────────────────── */}
      <nav
        className="fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-6 md:px-16 py-4 transition-all duration-500"
        style={{
          backdropFilter: `blur(${navOpacity * 16}px) saturate(180%)`,
          WebkitBackdropFilter: `blur(${navOpacity * 16}px) saturate(180%)`,
          background: `rgba(240, 236, 230, ${navOpacity * 0.35})`,
          borderBottom: `1px solid rgba(28, 43, 56, ${navOpacity * 0.06})`,
        }}
      >
        {/* Curatorial Logo (Click to reset slide on desktop) */}
        <button
          onClick={() => {
            if (isMobile) {
              window.scrollTo({ top: 0, behavior: "smooth" });
            } else {
              const now = Date.now();
              lastScrollTime.current = now;
              setIsTransitioning(true);
              setActiveIndex(0);
              setTimeout(() => setIsTransitioning(false), 1200);
            }
          }}
          className="flex items-center gap-4.5 group cursor-pointer border-none bg-transparent outline-none p-0 text-left"
        >
          <GezhiLogo size={54} variant="navbar" />
          <div className="flex flex-col text-left justify-center">
            <span className="font-serif text-[22px] font-medium tracking-[0.2em] text-[#1c2b38] leading-none">
              格至
            </span>
            <span className="font-mono text-[9px] font-light tracking-[0.45em] text-[#1c2b38]/50 mt-2">
              GÉZHI SPACE
            </span>
          </div>
        </button>

        {/* Center Pill Navigation (Smooth slider transition on desktop) */}
        <div className="hidden md:flex items-center gap-1 px-1 py-1 rounded-full border border-black/5 bg-white/10 backdrop-blur-md">
          {NAV_ITEMS.map((item, idx) => (
            <button
              key={item.id}
              onClick={() => {
                const now = Date.now();
                lastScrollTime.current = now;
                setIsTransitioning(true);
                setActiveIndex(idx);
                setTimeout(() => setIsTransitioning(false), 1200);
              }}
              className={`px-4.5 py-1.5 rounded-full text-[10px] font-medium tracking-[0.22em] transition-all duration-300 uppercase cursor-pointer border-none outline-none ${
                activeIndex === idx
                  ? "text-[#1c2b38] bg-white/40 shadow-sm font-semibold"
                  : "text-[#1c2b38]/60 hover:text-[#1c2b38] hover:bg-white/20"
              }`}
            >
              {item.zh}
            </button>
          ))}
        </div>

        {/* Right Console Access */}
        <div className="flex items-center gap-4">
          <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded border border-[#1c2b38]/10 bg-white/10">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#b91c1c]"></span>
            </span>
            <span className="font-mono text-[8px] text-[#1c2b38]/70 tracking-[0.25em]">POETIC PRECISION</span>
          </div>

          <button
            onClick={() => {
              if (isMobile) {
                const el = document.getElementById("philosophy");
                el?.scrollIntoView({ behavior: "smooth" });
              } else {
                const now = Date.now();
                lastScrollTime.current = now;
                setIsTransitioning(true);
                setActiveIndex(2);
                setTimeout(() => setIsTransitioning(false), 1200);
              }
            }}
            className="px-5 py-2 rounded border border-[#1c2b38]/15 bg-white/20 hover:bg-white/50 text-[#1c2b38] transition-all duration-400 font-mono text-[9px] tracking-[0.28em] cursor-pointer outline-none"
            style={{ backdropFilter: "blur(4px)" }}
          >
            探索
          </button>
        </div>
      </nav>

      {/* ── RIGHT DOT INDICATOR (Desktop only showcase) ─────────────────── */}
      {!isMobile && (
        <div className="fixed right-6 md:right-10 top-1/2 -translate-y-1/2 z-40 flex flex-col gap-4">
          {[0, 1, 2].map((idx) => (
            <button
              key={idx}
              onClick={() => {
                const now = Date.now();
                lastScrollTime.current = now;
                setIsTransitioning(true);
                setActiveIndex(idx);
                setTimeout(() => setIsTransitioning(false), 1200);
              }}
              className="group relative flex items-center justify-end border-none bg-transparent outline-none cursor-pointer"
            >
              {/* Tooltip on hover */}
              <span className="absolute right-6 opacity-0 group-hover:opacity-100 transition-all duration-300 font-mono text-[9px] tracking-widest text-[#1c2b38]/70 uppercase select-none mr-2 bg-white/50 px-2 py-0.5 rounded backdrop-blur-sm pointer-events-none">
                {NAV_ITEMS[idx].zh}
              </span>
              <div
                className={`w-1.5 h-1.5 rounded-full transition-all duration-500 ${
                  activeIndex === idx
                    ? "bg-[#b91c1c] scale-[1.6] shadow-[0_0_8px_rgba(185,28,28,0.5)]"
                    : "bg-[#1c2b38]/25 hover:bg-[#1c2b38]/60 hover:scale-125"
                }`}
              />
            </button>
          ))}
        </div>
      )}

      {/* ── SECTIONS WRAPPER (Cinematic 3D slider system) ────────────────────── */}
      <motion.div
        ref={containerRef}
        animate={isMobile ? { y: 0 } : { y: `-${activeIndex * 100}vh` }}
        transition={{ duration: 1.2, ease: [0.76, 0, 0.24, 1] }}
        className="w-full h-full"
      >
        {/* ── HERO SECTION ───────────────────────────────────── */}
        <section
          id="hero"
          className={
            isMobile
              ? "relative min-h-screen flex items-center px-6 pt-24 pb-16"
              : authMode === "register"
                ? "relative min-h-screen w-full flex items-start px-16 pt-28 pb-10 max-w-7xl mx-auto overflow-visible"
                : "relative h-screen w-full flex items-center px-16 max-w-7xl mx-auto overflow-hidden"
          }
        >
          <div className={`grid grid-cols-1 ${!isMobile && authMode === "register" ? "xl:grid-cols-12" : "lg:grid-cols-12"} gap-12 lg:gap-8 w-full z-10 ${!isMobile && authMode === "register" ? "items-start" : "items-center"}`}>
            
            {/* LEFT COLUMN: BRANDING, MASSIVE DISPLAY TITLES, SEAL AND BLUEPRINTS */}
            <motion.div 
              animate={isMobile ? {} : {
                opacity: activeIndex === 0 ? 1 : 0,
                x: activeIndex === 0 ? 0 : -80,
                scale: activeIndex === 0 ? 1 : 0.96,
              }}
              transition={{ duration: 1.0, ease: [0.76, 0, 0.24, 1] }}
              className={`${!isMobile && authMode === "register" ? "hidden xl:flex xl:col-span-7" : "lg:col-span-7 flex"} flex-col items-start text-left mt-4 md:mt-0 relative`}
            >
              
              {/* Traditional vertical stamp metadata */}
              <div className="absolute left-[-40px] top-[15%] hidden xl:flex flex-col items-center gap-3 text-center select-none text-[#1c2b38]/40">
                <span className="text-[10px] font-mono tracking-widest uppercase [writing-mode:vertical-lr]">COORD // 45.10.E</span>
                <div className="w-[1px] h-12 bg-[#1c2b38]/15" />
                {/* Red wax stamp vector badge */}
                <div className="w-5 h-5 rounded border border-[#b91c1c] text-[#b91c1c] text-[8px] flex items-center justify-center font-serif leading-none font-bold">
                  印
                </div>
              </div>

              {/* Curatorial Tagline Eyebrow */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded border border-[#1c2b38]/10 bg-white/20 mb-6">
                <Sparkles className="w-3 h-3 text-[#b91c1c]" />
                <span className="font-mono text-[9px] tracking-[0.28em] text-[#1c2b38]/75 uppercase">
                  大学格物篇 · 自适应拓扑网络
                </span>
              </div>

              {/* Massive Display Title */}
              <h1 
                className="font-serif text-[48px] sm:text-[62px] md:text-[80px] leading-[1.2] text-[#1c2b38] tracking-[0.12em] mb-4 select-none"
                style={{ textWrap: "balance" }}
              >
                <motion.span
                  initial={{ opacity: 0, filter: "blur(8px)", scale: 0.95 }}
                  animate={{ opacity: 1, filter: "blur(0px)", scale: 1 }}
                  transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
                  className="inline-block"
                  style={{ textShadow: "0 0 1px rgba(28, 43, 56, 0.1), 0 0 12px rgba(185, 28, 28, 0.03)" }}
                >
                  格至
                </motion.span>
                <br />
                <span className="font-sans font-extralight text-[32px] sm:text-[44px] md:text-[54px] tracking-normal block mt-1 text-[#1c2b38]/75">
                  <ShinyText 
                    text="多智能体学习系统" 
                    color="#1c2b38" 
                    shineColor="#ffffff" 
                    speed={2.8} 
                    spread={150}
                  />
                </span>
              </h1>

              {/* Decoded Paragraph Description */}
              <p 
                className="text-[#1c2b38]/75 text-xs md:text-sm font-light tracking-wider leading-relaxed max-w-lg mb-8"
                style={{ textWrap: "pretty" }}
              >
                格至学习系统（GEZHISYSTEM）以多智体协同相济，为课堂教习铸就精良研学之器。
                于此，求知与践习不复为枯涩刻板的记诵之学，而为进学途中静然流转的思脉、躬行践履与成长阶石。
              </p>

              {/* Elegant horizontal grid of interactive micro-cards */}
              <div className="grid grid-cols-2 gap-4 max-w-lg w-full mb-8">
                {[
                  { label: "多智能体引导教育", desc: "AI精准前置诊断，导师同频启发点拨", cap: "EDU-AGENT" },
                  { label: "全域学情拓扑画像", desc: "从个体知识雷达到班级错题预警干预", cap: "TOPOLOGY" },
                  { label: "智能编程沙箱", desc: "沉浸式代码演练，教师云端无感巡航", cap: "SANDBOX" },
                  { label: "代码项目仓库", desc: "课题级资产沉淀，师生开源级协作流", cap: "REPOSITORY" },
                ].map((badge, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col p-4 rounded-xl border border-zinc-200/50 bg-white/10 hover:bg-white/40 hover:border-[#1c2b38]/20 transition-all duration-400 group relative overflow-hidden"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[13px] font-serif font-bold tracking-wide text-[#1c2b38]">
                        {badge.label}
                      </span>
                      <span className="font-mono text-[9px] text-[#1c2b38]/30 tracking-widest">{badge.cap}</span>
                    </div>
                    <span className="text-[11px] text-[#1c2b38]/65 font-light tracking-wide">
                      {badge.desc}
                    </span>
                    {/* Subtle red indicator on hover */}
                    <div className="absolute right-0 bottom-0 w-[2px] h-0 bg-[#b91c1c] group-hover:h-full transition-all duration-400" />
                  </div>
                ))}
              </div>

              {/* Curatorial Code Sandbox Terminal Card */}
              <div className="relative w-full max-w-xl rounded-xl border border-zinc-300/40 bg-white/20 backdrop-blur-md overflow-hidden shadow-[0_8px_30px_rgba(28,43,56,0.03)]">
                <div className="flex items-center justify-between px-4 py-2 bg-[#fcfbfa]/60 border-b border-zinc-200/40">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-zinc-300" />
                    <div className="w-2 h-2 rounded-full bg-zinc-200" />
                    <span className="text-[9px] font-mono tracking-widest text-zinc-400 ml-2">gezhi_system.ts</span>
                  </div>
                  <div className="flex items-center gap-1 font-mono text-[8px] text-[#b91c1c]/60">
                    <Terminal className="w-3 h-3 text-[#b91c1c]/50" />
                    <span>INK SYSTEM v2.0</span>
                  </div>
                </div>

                {/* Code lines snippet */}
                <div className="p-4 font-mono text-xs text-left leading-relaxed text-[#1c2b38]/85 bg-white/5 min-h-[270px]">
                  {(() => {
                    // Pre-calculate line start indices to avoid side-effects during render
                    let accum = 0;
                    const lineStartIndices = CODE_LINES.map((line) => {
                      const start = accum;
                      accum += line.reduce((sum, token) => sum + token.text.length, 0);
                      return start;
                    });

                    // Find which line is currently active
                    let activeLineIdx = 0;
                    let tempAcc = 0;
                    for (let i = 0; i < CODE_LINES.length; i++) {
                      const lineLength = CODE_LINES[i].reduce((sum, token) => sum + token.text.length, 0);
                      if (typedCharCount >= tempAcc && typedCharCount <= tempAcc + lineLength) {
                        activeLineIdx = i;
                        break;
                      }
                      tempAcc += lineLength;
                    }

                    return CODE_LINES.map((line, lineIdx) => {
                      const lineStartIndex = lineStartIndices[lineIdx];
                      
                      // Only render the line if we've started typing it
                      if (typedCharCount < lineStartIndex && lineIdx > 0) {
                        return null;
                      }

                      let tokenAccum = lineStartIndex;

                      return (
                        <div key={lineIdx} className="flex gap-4">
                          <span className="text-[#1c2b38]/35 select-none w-5 text-right">
                            {lineIdx + 1}
                          </span>
                          <span className="relative">
                            {line.map((token, tokenIdx) => {
                              const tokenLength = token.text.length;
                              const tokenStartIndex = tokenAccum;
                              tokenAccum += tokenLength;

                              if (typedCharCount >= tokenStartIndex + tokenLength) {
                                // Entire token is typed
                                return (
                                  <span key={tokenIdx} className={token.className}>
                                    {token.text}
                                  </span>
                                );
                              } else if (typedCharCount > tokenStartIndex) {
                                // Token is partially typed
                                const visibleLength = typedCharCount - tokenStartIndex;
                                return (
                                  <span key={tokenIdx} className={token.className}>
                                    {token.text.substring(0, visibleLength)}
                                  </span>
                                );
                              } else {
                                // Token is not typed yet
                                return null;
                              }
                            })}
                            {/* Render blinking cursor at the active line's typing end */}
                            {lineIdx === activeLineIdx && (
                              <span className="inline-block w-[6px] h-[14px] bg-[#b91c1c] ml-0.5 align-middle animate-pulse" />
                            )}
                          </span>
                        </div>
                      );
                    });
                  })()}
                </div>
              </div>

            </motion.div>

            {/* RIGHT COLUMN: LUXURIOUS PARCHMENT ASTROLABE LOGIN CARD */}
            <motion.div 
              animate={isMobile ? {} : {
                opacity: activeIndex === 0 ? 1 : 0,
                x: activeIndex === 0 ? 0 : 120,
                rotateY: activeIndex === 0 ? 0 : 25,
                scale: activeIndex === 0 ? 1 : 0.88,
              }}
              transition={{ duration: 1.1, ease: [0.76, 0, 0.24, 1] }}
              style={{ perspective: 1000 }}
              className={`${!isMobile && authMode === "register" ? "xl:col-span-5 flex justify-center xl:justify-end" : "lg:col-span-5 flex justify-center lg:justify-end"} z-10`}
            >
              <div className={`w-full max-w-[390px] ${authMode === "register" ? "p-5" : "p-7"} rounded-2xl border border-white/60 bg-gradient-to-br from-white/65 to-white/35 backdrop-blur-[28px] saturate-[180%] shadow-[0_24px_60px_rgba(28,43,56,0.06),_inset_0_1px_2px_rgba(255,255,255,0.9)] relative overflow-hidden transition-all duration-500 group/card`}>
                
                {/* Internal astronomical micro-coordinates overlay */}
                <div className="absolute inset-0 pointer-events-none opacity-[0.03] overflow-hidden select-none">
                  <svg width="100%" height="100%" viewBox="0 0 400 400" className="text-[#1c2b38]">
                    <circle cx="200" cy="200" r="160" fill="none" stroke="currentColor" strokeWidth="0.5" />
                    <circle cx="200" cy="200" r="154" fill="none" stroke="currentColor" strokeWidth="0.25" strokeDasharray="1 3" />
                    <line x1="200" y1="0" x2="200" y2="400" stroke="currentColor" strokeWidth="0.25" strokeDasharray="5 5" />
                    <line x1="0" y1="200" x2="400" y2="200" stroke="currentColor" strokeWidth="0.25" strokeDasharray="5 5" />
                  </svg>
                </div>

                {/* Internal abstract glowing orbs */}
                <div className="absolute top-0 right-0 w-36 h-36 bg-[#b91c1c]/3 blur-3xl rounded-full pointer-events-none" />
                <div className="absolute bottom-0 left-0 w-36 h-36 bg-amber-500/3 blur-3xl rounded-full pointer-events-none" />

                <div className="relative z-10">
                  
                  {/* Header text with elegant traditional red wax seal */}
                  <div className={`${authMode === "register" ? "mb-5" : "mb-7"} flex justify-between items-start`}>
                    <div className="text-left space-y-1">
                      <h2 className="font-serif text-[26px] font-light text-[#1c2b38] tracking-[0.05em] leading-none select-none">开始学纪</h2>
                      <div className="flex gap-4 mt-2 mb-1">
                        <button
                          onClick={() => setAuthMode("login")}
                          className={`text-[11px] tracking-[0.2em] font-medium transition-all duration-300 border-b-2 outline-none cursor-pointer ${
                            authMode === "login" 
                              ? "text-[#1c2b38] border-[#b91c1c]" 
                              : "text-[#1c2b38]/40 border-transparent hover:text-[#1c2b38]/70"
                          }`}
                        >
                          登录
                        </button>
                        <button
                          onClick={() => setAuthMode("register")}
                          className={`text-[11px] tracking-[0.2em] font-medium transition-all duration-300 border-b-2 outline-none cursor-pointer ${
                            authMode === "register" 
                              ? "text-[#1c2b38] border-[#b91c1c]" 
                              : "text-[#1c2b38]/40 border-transparent hover:text-[#1c2b38]/70"
                          }`}
                        >
                          注册
                        </button>
                      </div>
                    </div>
                    {/* Traditional design stamp symbol */}
                    <div 
                      className="flex items-center justify-center select-none"
                      style={{
                        transform: "rotate(3deg)",
                      }}
                    >
                      <GezhiLogo size={36} variant="navbar" interactive={true} />
                    </div>
                  </div>

                  {/* IDLE & FORM STATE */}
                  {loginState !== "success" && (
                    <form onSubmit={handleLogin} className={`${authMode === "register" ? "space-y-3" : "space-y-5"} text-left`}>
                      
                      {/* Switcher Tab Student / Teacher */}
                      <div className="relative p-1 rounded-lg bg-[#1c2b38]/5 border border-[#1c2b38]/5 flex items-center mb-4">
                        {/* Sliding selection background */}
                        <div
                          className="absolute top-1 bottom-1 w-[48%] rounded bg-[#1c2b38] shadow-[0_3px_8px_rgba(28,43,56,0.18)] transition-transform duration-500 ease-[cubic-bezier(0.23,1,0.32,1)]"
                          style={{
                            transform: role === "student" ? "translateX(2%)" : "translateX(104%)",
                          }}
                        />

                        <button
                          type="button"
                          onClick={() => setRole("student")}
                          className={`relative z-10 w-1/2 py-2 text-[10px] font-medium tracking-[0.25em] text-center transition-all duration-300 uppercase select-none flex items-center justify-center gap-1 border-none bg-transparent outline-none cursor-pointer`}
                          style={{ color: role === "student" ? "#ffffff" : "rgba(28,43,56,0.5)" }}
                        >
                          {role === "student" && <span className="w-1.5 h-1.5 rounded-full bg-[#b91c1c] animate-pulse" />}
                          <span>学子</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setRole("teacher")}
                          className={`relative z-10 w-1/2 py-2 text-[10px] font-medium tracking-[0.25em] text-center transition-all duration-300 uppercase select-none flex items-center justify-center gap-1 border-none bg-transparent outline-none cursor-pointer`}
                          style={{ color: role === "teacher" ? "#ffffff" : "rgba(28,43,56,0.5)" }}
                        >
                          {role === "teacher" && <span className="w-1.5 h-1.5 rounded-full bg-[#b91c1c] animate-pulse" />}
                          <span>导师</span>
                        </button>
                      </div>

                      {authMode === "login" && (
                        <div className="flex justify-center gap-6 text-[10px] tracking-[0.2em] mb-4 text-[#1c2b38]/50">
                          <button
                            type="button"
                            onClick={() => setLoginMethod("password")}
                            className={`pb-1 border-b transition-all duration-300 cursor-pointer bg-transparent border-none outline-none ${
                              loginMethod === "password"
                                ? "border-[#b91c1c] text-[#1c2b38] font-medium"
                                : "border-transparent hover:text-[#1c2b38]/85"
                            }`}
                          >
                            凭证登录
                          </button>
                          <button
                            type="button"
                            onClick={() => setLoginMethod("mobile")}
                            className={`pb-1 border-b transition-all duration-300 cursor-pointer bg-transparent border-none outline-none ${
                              loginMethod === "mobile"
                                ? "border-[#b91c1c] text-[#1c2b38] font-medium"
                                : "border-transparent hover:text-[#1c2b38]/85"
                            }`}
                          >
                            手机验证
                          </button>
                        </div>
                      )}

                      {/* Common fields based on auth mode */}
                      {((authMode === "login" && loginMethod === "password") || (authMode === "register" && role === "teacher")) && (
                        <div className="space-y-1.5 group/input">
                          <label className="text-[8.5px] tracking-[0.32em] text-zinc-400 uppercase font-mono select-none block transition-colors duration-300 group-focus-within/input:text-[#1c2b38]/85">
                            用户名 CODE_ID
                          </label>
                          <div className="relative">
                            <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 transition-colors duration-300 group-focus-within/input:text-[#b91c1c]" />
                            <input
                              type="text"
                              required
                              value={username}
                              onChange={(e) => setUsername(e.target.value)}
                              placeholder="账号 / 电子邮址"
                              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/20 focus:bg-white/60 focus:border-[#1c2b38]/45 focus:ring-1 focus:ring-[#1c2b38]/5 outline-none text-xs text-[#1c2b38] placeholder-zinc-350 tracking-wider transition-all duration-350 shadow-[inset_0_1px_2px_rgba(28,43,56,0.01)]"
                            />
                          </div>
                        </div>
                      )}

                      {authMode === "register" && role === "student" && (
                        <>
                          <div className="space-y-1.5 group/input animate-fade-in">
                            <label className="text-[8.5px] tracking-[0.32em] text-zinc-400 uppercase font-mono select-none block transition-colors duration-300 group-focus-within/input:text-[#1c2b38]/85">
                              学生姓名 STUDENT_NAME
                            </label>
                            <div className="relative">
                              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 transition-colors duration-300 group-focus-within/input:text-[#b91c1c]" />
                              <input
                                type="text"
                                required
                                value={realName}
                                onChange={(e) => setRealName(e.target.value)}
                                placeholder="输入学生姓名"
                                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/20 focus:bg-white/60 focus:border-[#1c2b38]/45 focus:ring-1 focus:ring-[#1c2b38]/5 outline-none text-xs text-[#1c2b38] placeholder-zinc-350 tracking-wider transition-all duration-350 shadow-[inset_0_1px_2px_rgba(28,43,56,0.01)]"
                              />
                            </div>
                          </div>

                          <div className="space-y-1.5 group/input animate-fade-in">
                            <label className="text-[8.5px] tracking-[0.32em] text-zinc-400 uppercase font-mono select-none block transition-colors duration-300 group-focus-within/input:text-[#1c2b38]/85">
                              学号 STUDENT_ID
                            </label>
                            <div className="relative">
                              <Code className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 transition-colors duration-300 group-focus-within/input:text-[#b91c1c]" />
                              <input
                                type="text"
                                required
                                value={studentId}
                                onChange={(e) => setStudentId(e.target.value)}
                                placeholder="输入学号，学号将作为账号"
                                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/20 focus:bg-white/60 focus:border-[#1c2b38]/45 focus:ring-1 focus:ring-[#1c2b38]/5 outline-none text-xs text-[#1c2b38] placeholder-zinc-350 tracking-wider transition-all duration-350 shadow-[inset_0_1px_2px_rgba(28,43,56,0.01)]"
                              />
                            </div>
                          </div>

                          <div className="space-y-1.5 group/input animate-fade-in">
                            <label className="text-[8.5px] tracking-[0.32em] text-zinc-400 uppercase font-mono select-none block transition-colors duration-300 group-focus-within/input:text-[#1c2b38]/85">
                              班级号 CLASS_ID
                            </label>
                            <div className="relative">
                              <Compass className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 transition-colors duration-300 group-focus-within/input:text-[#b91c1c]" />
                              <input
                                type="text"
                                required
                                value={className}
                                onChange={(e) => setClassName(e.target.value)}
                                placeholder="输入班级号"
                                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/20 focus:bg-white/60 focus:border-[#1c2b38]/45 focus:ring-1 focus:ring-[#1c2b38]/5 outline-none text-xs text-[#1c2b38] placeholder-zinc-350 tracking-wider transition-all duration-350 shadow-[inset_0_1px_2px_rgba(28,43,56,0.01)]"
                              />
                            </div>
                          </div>
                        </>
                      )}

                      {(authMode === "register" || loginMethod === "password") && (
                        <div className="space-y-1.5 group/input">
                          <label className="text-[8.5px] tracking-[0.32em] text-zinc-400 uppercase font-mono select-none block transition-colors duration-300 group-focus-within/input:text-[#1c2b38]/85">
                            秘密凭证 ACCESS_PASS
                          </label>
                          <div className="relative">
                            <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 transition-colors duration-300 group-focus-within/input:text-[#b91c1c]" />
                            <input
                              type="password"
                              required
                              value={password}
                              onChange={(e) => setPassword(e.target.value)}
                              placeholder="输入绝密凭证"
                              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/20 focus:bg-white/60 focus:border-[#1c2b38]/45 focus:ring-1 focus:ring-[#1c2b38]/5 outline-none text-xs text-[#1c2b38] placeholder-zinc-350 tracking-wider transition-all duration-350 shadow-[inset_0_1px_2px_rgba(28,43,56,0.01)]"
                            />
                          </div>
                        </div>
                      )}

                      {/* Register Specific Fields */}
                      {authMode === "register" && (
                        <div className="space-y-1.5 group/input">
                          <label className="text-[8.5px] tracking-[0.32em] text-zinc-400 uppercase font-mono select-none block transition-colors duration-300 group-focus-within/input:text-[#1c2b38]/85">
                            确认凭证 CONFIRM_PASS
                          </label>
                          <div className="relative">
                            <ShieldCheck className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 transition-colors duration-300 group-focus-within/input:text-[#b91c1c]" />
                            <input
                              type="password"
                              required
                              value={confirmPassword}
                              onChange={(e) => setConfirmPassword(e.target.value)}
                              placeholder="再次输入绝密凭证"
                              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/20 focus:bg-white/60 focus:border-[#1c2b38]/45 focus:ring-1 focus:ring-[#1c2b38]/5 outline-none text-xs text-[#1c2b38] placeholder-zinc-350 tracking-wider transition-all duration-350 shadow-[inset_0_1px_2px_rgba(28,43,56,0.01)]"
                            />
                          </div>
                        </div>
                      )}

                      {(authMode === "register" || loginMethod === "mobile") && (
                        <div className="space-y-1.5 group/input">
                          <label className="text-[8.5px] tracking-[0.32em] text-zinc-400 uppercase font-mono select-none block transition-colors duration-300 group-focus-within/input:text-[#1c2b38]/85">
                            手机号码 MOBILE_PHONE
                          </label>
                          <div className="relative">
                            <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 transition-colors duration-300 group-focus-within/input:text-[#b91c1c]" />
                            <input
                              type="tel"
                              required
                              value={phone}
                              onChange={(e) => setPhone(e.target.value)}
                              placeholder="输入11位手机号码"
                              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/20 focus:bg-white/60 focus:border-[#1c2b38]/45 focus:ring-1 focus:ring-[#1c2b38]/5 outline-none text-xs text-[#1c2b38] placeholder-zinc-350 tracking-wider transition-all duration-350 shadow-[inset_0_1px_2px_rgba(28,43,56,0.01)]"
                            />
                          </div>
                        </div>
                      )}

                      {/* Verification Code */}
                      {((authMode === "register" && role === "student") || (authMode === "login" && loginMethod === "mobile")) && (
                        <div className="space-y-1.5 group/input">
                          <label className="text-[8.5px] tracking-[0.32em] text-zinc-400 uppercase font-mono select-none block transition-colors duration-300 group-focus-within/input:text-[#1c2b38]/85">
                            安全验证码 VERIFY_CODE
                          </label>
                          <div className="relative flex gap-2">
                            <div className="relative flex-1">
                              <ShieldCheck className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 transition-colors duration-300 group-focus-within/input:text-[#b91c1c]" />
                              <input
                                type="text"
                                required
                                maxLength={6}
                                value={code}
                                onChange={(e) => setCode(e.target.value)}
                                placeholder="输入6位验证码"
                                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/20 focus:bg-white/60 focus:border-[#1c2b38]/45 focus:ring-1 focus:ring-[#1c2b38]/5 outline-none text-xs text-[#1c2b38] placeholder-zinc-350 tracking-wider transition-all duration-350 shadow-[inset_0_1px_2px_rgba(28,43,56,0.01)]"
                              />
                            </div>
                            <button
                              type="button"
                              disabled={countdown > 0}
                              onClick={handleSendCode}
                              className="px-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/30 disabled:bg-zinc-100/10 disabled:text-zinc-400 text-xs text-[#1c2b38] font-medium tracking-wider transition-all duration-300 outline-none cursor-pointer select-none whitespace-nowrap min-w-[100px]"
                            >
                              {countdown > 0 ? `${countdown}s` : "获取验证码"}
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Register Specific: Teacher ID */}
                      {authMode === "register" && role === "teacher" && (
                        <div className="space-y-1.5 group/input animate-fade-in">
                          <label className="text-[8.5px] tracking-[0.32em] text-zinc-400 uppercase font-mono select-none block transition-colors duration-300 group-focus-within/input:text-[#1c2b38]/85">
                            教师工号 TEACHER_ID
                          </label>
                          <div className="relative">
                            <UserCheck className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 transition-colors duration-300 group-focus-within/input:text-[#b91c1c]" />
                            <input
                              type="text"
                              required
                              value={teacherId}
                              onChange={(e) => setTeacherId(e.target.value)}
                              placeholder="输入教师工号以供审核"
                              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-zinc-200/75 bg-white/10 hover:bg-white/20 focus:bg-white/60 focus:border-[#1c2b38]/45 focus:ring-1 focus:ring-[#1c2b38]/5 outline-none text-xs text-[#1c2b38] placeholder-zinc-350 tracking-wider transition-all duration-350 shadow-[inset_0_1px_2px_rgba(28,43,56,0.01)]"
                            />
                          </div>
                        </div>
                      )}

                      {/* SMS Tip / Error Message */}
                      {smsTip && (
                        <div className="text-[10px] text-emerald-700 bg-emerald-50/50 border border-emerald-200/40 rounded px-3 py-1.5 font-mono animate-fade-in flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                          <span>{smsTip}</span>
                        </div>
                      )}

                      {/* Submit Button */}
                      <div className="pt-2">
                        <Magnet padding={40} magnetStrength={4} wrapperClassName="w-full">
                          <button
                            type="submit"
                            disabled={loginState === "loading"}
                            className="w-full py-3 rounded-lg bg-[#1c2b38] hover:bg-[#253645] active:scale-[0.985] text-[10.5px] font-medium tracking-[0.35em] text-white transition-all duration-300 shadow-[0_5px_15px_rgba(28,43,56,0.15)] flex items-center justify-center gap-2 select-none uppercase group/btn border-none outline-none cursor-pointer"
                          >
                            {loginState === "loading" ? (
                              <>
                                <div className="w-3.5 h-3.5 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                                <span>{authMode === "register" ? "录入中..." : "建立连接中..."}</span>
                              </>
                            ) : (
                              <>
                                <span>{authMode === "register" ? "开启学纪" : "进入阁内"}</span>
                                <ArrowRight className="w-3.5 h-3.5 text-[#b91c1c] transition-transform duration-300 group-hover/btn:translate-x-1" />
                              </>
                            )}
                          </button>
                        </Magnet>
                      </div>

                      {/* Divider decoration */}
                      <div className="flex items-center justify-center gap-3 py-1.5">
                        <div className="w-full h-[0.5px] bg-[#1c2b38]/10" />
                        <span className="text-[8px] font-mono text-zinc-400 tracking-[0.25em] shrink-0 select-none">· {authMode === "register" ? "REGISTRATION" : "AUTHENTICATE"} ·</span>
                        <div className="w-full h-[0.5px] bg-[#1c2b38]/10" />
                      </div>

                      {/* Access portal helper */}
                      <div className="flex justify-between items-center text-[9px] text-[#1c2b38]/50 font-mono">
                        {authMode === "login" ? (
                          <>
                            <a href="#" className="relative group/link hover:text-[#b91c1c] transition-colors py-0.5">
                              <span>忘记密码</span>
                              <span className="absolute bottom-0 left-0 w-0 h-[0.5px] bg-[#b91c1c] transition-all duration-300 group-hover/link:w-full" />
                            </a>
                            <a href="#" onClick={(e) => { e.preventDefault(); setAuthMode("register"); }} className="relative group/link hover:text-[#b91c1c] transition-colors py-0.5">
                              <span>没有账号？ → 注册</span>
                              <span className="absolute bottom-0 left-0 w-0 h-[0.5px] bg-[#b91c1c] transition-all duration-300 group-hover/link:w-full" />
                            </a>
                          </>
                        ) : (
                          <div className="w-full text-center">
                            <a href="#" onClick={(e) => { e.preventDefault(); setAuthMode("login"); }} className="relative group/link hover:text-[#b91c1c] transition-colors py-0.5">
                              <span>已有账号？ → 登录</span>
                              <span className="absolute bottom-0 left-0 w-0 h-[0.5px] bg-[#b91c1c] transition-all duration-300 group-hover/link:w-full" />
                            </a>
                          </div>
                        )}
                      </div>

                    </form>
                  )}

                  {/* LOGIN SUCCESS CINEMATIC PANEL */}
                  {loginState === "success" && (
                    <div className="py-7 text-center space-y-5">
                      <div className="inline-flex items-center justify-center w-13 h-13 rounded bg-[#b91c1c]/5 border border-[#b91c1c]/25 text-[#b91c1c] mb-2 relative shadow-[inset_0_1px_3px_rgba(185,28,28,0.1),_0_3px_8px_rgba(185,28,28,0.05)]">
                        <Check className="w-5.5 h-5.5 stroke-[2.5]" />
                        <div className="absolute inset-0 rounded bg-[#b91c1c]/10 blur-sm opacity-25 animate-ping" />
                      </div>

                      <div className="space-y-2">
                        <h3 className="font-serif text-[20px] text-[#1c2b38] tracking-wider font-light">凭证已鉴</h3>
                        <p className="text-zinc-500 text-[10px] tracking-wide max-w-[270px] mx-auto leading-relaxed">
                          指纹比对成功。已为您挂载 <span className="text-[#b91c1c] font-medium">{role === "student" ? "学子博古斋" : "导师讲坛"}</span>。正在分配个人专属的星群 AI 节点。
                        </p>
                      </div>

                      <div className="p-3.5 rounded-lg bg-[#1c2b38]/5 border border-[#1c2b38]/10 font-mono text-[9px] text-[#1c2b38]/70 text-left space-y-1 shadow-[inset_0_1px_2px_rgba(28,43,56,0.02)]">
                        <div>&gt; ATTACH TO ASTROLABE_NODE_05</div>
                        <div>&gt; INJECTING PEDAGOGICAL_WEIGHTS...</div>
                        <div className="text-emerald-700 font-medium">&gt; INK_TUNNEL ESTABLISHED [SECURE_SHELL]</div>
                      </div>

                      <button
                        onClick={goToAppHome}
                        className="px-6 py-2 rounded border border-zinc-200 bg-white/40 hover:bg-white text-[9px] font-mono tracking-widest text-[#1c2b38] transition-all duration-300 uppercase shadow-sm active:scale-[0.97] cursor-pointer outline-none"
                      >
                        返回山水
                      </button>
                    </div>
                  )}

                  {/* Card footer details */}
                  <div className="mt-6 pt-4 border-t border-[#1c2b38]/10 text-center">
                    <span className="font-mono text-[8px] tracking-[0.4em] text-[#1c2b38]/40 uppercase">
                      MISTRAL_GRID · INTELLECTUAL SILENCE
                    </span>
                  </div>

                </div>

              </div>
            </motion.div>

          </div>
        </section>

        {/* ── SECTION 2: THE NETWORK OF POETIC COOPERATION (四大智能体规约) ── */}
        <section
          id="architecture"
          ref={archRef}
          className={
            isMobile
              ? "relative py-28 px-6 border-t border-[#1c2b38]/15 max-w-7xl mx-auto w-full text-center"
              : "relative h-screen w-full flex flex-col justify-center px-16 max-w-7xl mx-auto text-center overflow-hidden"
          }
        >
          <div
            className="transition-all duration-1000 ease-[cubic-bezier(0.16,1,0.3,1)]"
            style={{
              opacity: visible.architecture ? 1 : 0,
              transform: visible.architecture ? "translateY(0)" : "translateY(30px)",
            }}
          >
            {/* Section heading */}
            <div className="text-center max-w-xl mx-auto mb-12">
              <span className="font-mono text-[9px] tracking-[0.6em] text-[#1c2b38]/40 uppercase block">
                COOPERATIVE BLUEPRINT NETWORKS
              </span>
              <h2 className="font-serif text-3xl md:text-4xl text-[#1c2b38] tracking-wider mt-3 mb-4 font-light">
                四大 AI 规约协同网格
              </h2>
              <div className="w-8 h-px bg-[#b91c1c]/40 mx-auto my-5" />
              <p className="text-zinc-500 text-[11px] md:text-xs font-light leading-relaxed tracking-wider">
                无缝解耦。智能体各司其职，遵循“格物致知”之训，将庞杂算法体系解构为静默运行、完美衔接的信息阶梯。
              </p>
            </div>

            {/* Blueprint Agent Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 max-w-6xl mx-auto mb-10 text-left">
              {AGENTS_DATA.map((agent, idx) => {
                const Icon = agent.icon;
                const isActive = activeAgent === idx;
                return (
                  <motion.div
                    key={idx}
                    onClick={() => setActiveAgent(idx)}
                    initial={isMobile ? {} : { opacity: 0, y: 60, rotateX: 15 }}
                    animate={
                      isMobile
                        ? {}
                        : {
                            opacity: activeIndex === 1 ? 1 : 0,
                            y: activeIndex === 1 ? 0 : 60,
                            rotateX: activeIndex === 1 ? 0 : 15,
                          }
                    }
                    transition={{
                      duration: 0.8,
                      delay: activeIndex === 1 ? idx * 0.12 : 0,
                      ease: [0.25, 1, 0.5, 1],
                    }}
                    style={isMobile ? {} : { transformStyle: "preserve-3d" }}
                    className={`cursor-pointer p-5.5 rounded-xl border transition-all duration-500 flex flex-col justify-between aspect-[1/1.04] relative overflow-hidden group ${
                      isActive
                        ? `bg-white/45 ${agent.borderColor}`
                        : "bg-white/10 border-zinc-200/40 hover:border-zinc-300"
                    }`}
                  >
                    {/* Subtle red stamp index */}
                    <span className="absolute top-4 right-4 font-mono text-[8px] text-[#1c2b38]/20 select-none">0{idx + 1}</span>

                    {/* Icon & Title */}
                    <div>
                      <div
                        className={`w-9 h-9 rounded flex items-center justify-center mb-5 border transition-all ${
                          isActive
                            ? "bg-[#1c2b38] text-white border-transparent"
                            : "bg-white/20 border-zinc-200/40 text-[#1c2b38]/50 group-hover:text-[#1c2b38]"
                        }`}
                      >
                        <Icon className="w-4.5 h-4.5" />
                      </div>

                      <h3 className="font-serif text-lg font-light text-[#1c2b38] tracking-wide mb-1">
                        {agent.title}
                      </h3>
                      <p className="font-mono text-[8px] tracking-[0.25em] text-[#b91c1c]/70 uppercase">
                        {agent.role}
                      </p>
                    </div>

                    {/* Desc on active / Arrow indicator on default */}
                    <div className="mt-4">
                      {isActive ? (
                        <p className="text-zinc-600 text-[11px] font-light leading-relaxed tracking-wide animate-fade-in">
                          {agent.desc}
                        </p>
                      ) : (
                        <div className="flex items-center gap-1.5 text-[8px] text-zinc-400 font-mono tracking-widest uppercase transition-colors group-hover:text-[#b91c1c]">
                          <span>解析规约 PROTOCOL</span>
                          <ChevronRight className="w-2.5 h-2.5" />
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Active Agent Protocol breakdown */}
            <motion.div 
              initial={isMobile ? {} : { opacity: 0, y: 40, scale: 0.97 }}
              animate={
                isMobile
                  ? {}
                  : {
                      opacity: activeIndex === 1 ? 1 : 0,
                      y: activeIndex === 1 ? 0 : 40,
                      scale: activeIndex === 1 ? 1 : 0.97,
                    }
              }
              transition={{ duration: 0.9, delay: isMobile ? 0 : 0.5, ease: [0.76, 0, 0.24, 1] }}
              className="max-w-6xl mx-auto rounded-xl border border-zinc-200/40 bg-white/25 backdrop-blur-md p-6 md:p-8 text-left grid grid-cols-1 md:grid-cols-12 gap-8 items-center shadow-[0_8px_32px_rgba(28,43,56,0.02)]"
            >
              <div className="md:col-span-8 space-y-4">
                <span className="font-mono text-[8px] tracking-[0.45em] text-[#b91c1c] uppercase block">
                  COOPERATIVE RULESPEC
                </span>
                <h4 className="font-serif text-xl text-[#1c2b38] font-light tracking-wide">
                  {AGENTS_DATA[activeAgent].title} · 实时调度规约
                </h4>
                <p className="text-zinc-500 text-xs font-light leading-relaxed tracking-wider">
                  {AGENTS_DATA[activeAgent].desc}
                </p>
                
                <div className="flex flex-wrap gap-2 pt-2">
                  {AGENTS_DATA[activeAgent].perks.map((perk, pIdx) => (
                    <div
                      key={pIdx}
                      className="flex items-center gap-1.5 px-3 py-1 rounded border border-[#1c2b38]/10 bg-white/30 font-mono text-[9px] text-[#1c2b38]/80"
                    >
                      <CheckCircle2 className="w-3 h-3 text-[#b91c1c]/70" />
                      <span>{perk}</span>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Terminal Mock Protocol Data */}
              <div className="md:col-span-4 bg-[#fcfbfa]/60 border border-zinc-200/50 p-4 rounded-lg font-mono text-[9px] text-[#1c2b38]/80 leading-relaxed text-left shrink-0">
                <div className="text-[#1c2b38]/40 uppercase tracking-widest text-[8px] mb-3 pb-1.5 border-b border-[#1c2b38]/10">
                  system_channel.log
                </div>
                <div>[COORD] SYNCING SYSTEM_FEED_{activeAgent}...</div>
                <div>[COORD] KNOWLEDGE_REALLOCATION: SUCCESS</div>
                <div className="text-amber-800">[COORD] SECURE SHELL MOUNTED OVER LANDSCAPE</div>
              </div>
            </motion.div>

          </div>
        </section>


        {/* ── SECTION 3: THE PHILOSOPHY & FOOTER (哲学论述：格物致知) ── */}
        <section
          id="philosophy"
          ref={philRef}
          className={
            isMobile
              ? "relative py-24 px-6 border-t border-[#1c2b38]/15 text-center max-w-5xl mx-auto w-full"
              : "relative h-screen w-full flex flex-col justify-between pt-28 pb-6 px-16 max-w-5xl mx-auto text-center overflow-hidden"
          }
        >
          <div
            className={isMobile ? "space-y-10" : "flex-1 flex flex-col justify-center items-center space-y-10"}
            style={{
              opacity: visible.philosophy ? 1 : 0,
              transform: visible.philosophy ? "translateY(0)" : "translateY(30px)",
              transition: "all 1s cubic-bezier(0.16, 1, 0.3, 1)",
            }}
          >
            {/* Eyebrow */}
            <motion.span 
              animate={isMobile ? {} : {
                opacity: activeIndex === 2 ? 1 : 0,
                y: activeIndex === 2 ? 0 : -15,
              }}
              transition={{ duration: 0.8, ease: [0.76, 0, 0.24, 1] }}
              className="font-mono text-[11px] md:text-[12px] tracking-[0.6em] text-[#1c2b38]/40 uppercase block select-none"
            >
              GEZHI SYSTEM PHILOSOPHY
            </motion.span>
            
            {/* Blur-Fade Title */}
            <motion.h2 
              animate={isMobile ? {} : {
                opacity: activeIndex === 2 ? 1 : 0,
                y: activeIndex === 2 ? 0 : 20,
                filter: activeIndex === 2 ? "blur(0px)" : "blur(10px)",
              }}
              transition={{ duration: 1.2, delay: 0.1, ease: [0.76, 0, 0.24, 1] }}
              className="flex flex-col items-center justify-center select-none"
            >
              <span 
                style={{ fontFamily: "'Ma Shan Zheng', cursive" }} 
                className="text-[54px] md:text-[72px] lg:text-[88px] font-normal text-[#1c2b38] tracking-[0.12em] leading-tight mb-2 hover:scale-[1.03] hover:rotate-[-0.5deg] transition-all duration-500 cursor-pointer drop-shadow-[0_4px_12px_rgba(28,43,56,0.05)]"
              >
                格物致知
              </span>
              <span 
                style={{ fontFamily: "'Zhi Mang Xing', cursive" }} 
                className="text-[28px] md:text-[36px] lg:text-[42px] font-normal text-[#b91c1c] tracking-[0.2em] mt-1.5 block hover:scale-[1.05] hover:rotate-[0.5deg] transition-all duration-500 cursor-pointer drop-shadow-[0_2px_8px_rgba(185,28,28,0.08)]"
              >
                抱朴守拙
              </span>
            </motion.h2>

            <div className="w-12 h-px bg-[#b91c1c]/40 mx-auto" />

            {/* Body text */}
            <motion.p 
              animate={isMobile ? {} : {
                opacity: activeIndex === 2 ? 1 : 0,
                y: activeIndex === 2 ? 0 : 20,
              }}
              transition={{ duration: 1.0, delay: 0.3, ease: [0.76, 0, 0.24, 1] }}
              className="text-zinc-600 text-sm md:text-base lg:text-lg font-light leading-relaxed tracking-wider max-w-2xl mx-auto select-text"
              style={{ textWrap: "pretty" }}
            >
              “格物致知”出自《礼记·大学》，意为推究事物的原理而获得知识。我们坚信，格至多智能体学习系统不应只是一种理性的运算规约，它有着其本身的力学平衡、律动美与形态哲学。通过多智能体与可视化物理沙箱，我们将隐性的代码流转显现为感官的艺术。
            </motion.p>

            {/* Interactive Magnet button */}
            <motion.div 
              animate={isMobile ? {} : {
                opacity: activeIndex === 2 ? 1 : 0,
                scale: activeIndex === 2 ? 1 : 0.85,
              }}
              transition={{ duration: 0.8, delay: 0.4, ease: [0.76, 0, 0.24, 1] }}
              className="pt-4"
            >
              <Magnet padding={25} magnetStrength={3}>
                <button
                  onClick={() => {
                    if (isMobile) {
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    } else {
                      const now = Date.now();
                      lastScrollTime.current = now;
                      setIsTransitioning(true);
                      setActiveIndex(0);
                      setTimeout(() => setIsTransitioning(false), 1200);
                    }
                  }}
                  className="inline-flex items-center gap-2 px-8.5 py-3.5 border border-[#1c2b38]/20 bg-white/25 hover:bg-white/60 text-[10px] font-mono tracking-widest text-[#1c2b38] uppercase transition-all select-none cursor-pointer outline-none"
                >
                  <span>即刻开始探索</span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#b91c1c]" />
                </button>
              </Magnet>
            </motion.div>
          </div>

          {/* ── FOOTER (Curatorial & Poetic, integrated on desktop) ── */}
          {!isMobile && (
            <footer className="w-full border-t border-[#1c2b38]/10 bg-white/5 backdrop-blur-sm py-5 px-0 text-center mt-auto">
              <div className="flex flex-col md:flex-row items-center justify-between gap-6 max-w-7xl mx-auto">
                <div className="flex items-center gap-3">
                  <GezhiLogo size={28} variant="footer" />
                  <span className="font-serif text-[11px] font-light tracking-widest text-[#1c2b38]/60">
                    © 2026 格至 · POETIC ALGORITHMIC LAB. ALL RIGHTS CURATED.
                  </span>
                </div>

                <div className="flex items-center gap-6 font-mono text-[8.5px] tracking-widest text-zinc-400 uppercase">
                  <a href="#" className="hover:text-[#b91c1c] transition-colors">卷轴声明</a>
                  <a href="#" className="hover:text-[#b91c1c] transition-colors">密算协议</a>
                  <a href="#" className="hover:text-[#b91c1c] transition-colors">中央账簿</a>
                </div>

                <span className="font-serif text-[11px] text-[#b91c1c]/50 tracking-[0.22em] uppercase select-none">
                  格物致知 · 抱朴守拙
                </span>
              </div>
            </footer>
          )}
        </section>

      </motion.div>

      {/* ── FOOTER (Rendered outside of sliding wrapper for mobile viewport only) ── */}
      {isMobile && (
        <footer className="border-t border-[#1c2b38]/10 bg-white/15 backdrop-blur-md py-10 px-6 text-center">
          <div className="flex flex-col items-center justify-between gap-6 max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <GezhiLogo size={28} variant="footer" />
              <span className="font-serif text-[11px] font-light tracking-widest text-[#1c2b38]/60">
                © 2026 格至 · POETIC ALGORITHMIC LAB. ALL RIGHTS CURATED.
              </span>
            </div>

            <div className="flex items-center gap-6 font-mono text-[9px] tracking-widest text-zinc-400 uppercase">
              <a href="#" className="hover:text-[#b91c1c] transition-colors">卷轴声明</a>
              <a href="#" className="hover:text-[#b91c1c] transition-colors">密算协议</a>
              <a href="#" className="hover:text-[#b91c1c] transition-colors">中央账簿</a>
            </div>

            <span className="font-serif text-xs text-[#b91c1c]/50 tracking-[0.22em] uppercase select-none">
              格物致知 · 抱朴守拙
            </span>
          </div>
        </footer>
      )}

      {/* Embedded style overrides for smooth cinematic control */}
      <style>{`
        /* Smooth scrolling */
        html {
          scroll-behavior: smooth;
        }

        /* Hide scrollbars on desktop for full slideshow feel */
        @media (min-width: 768px) {
          ::-webkit-scrollbar {
            display: none;
          }
          html, body {
            scrollbar-width: none;
            -ms-overflow-style: none;
            overflow: hidden;
          }
        }

        /* Pure ease-out fade in animation */
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        /* Perfect translucent focus styles for light form inputs */
        input:-webkit-autofill,
        input:-webkit-autofill:hover, 
        input:-webkit-autofill:focus {
          -webkit-text-fill-color: #1c2b38;
          -webkit-box-shadow: 0 0 0px 1000px #fbfaf8 inset;
          transition: background-color 5000s ease-in-out 0s;
        }
      `}</style>
    </div>
  );
}
