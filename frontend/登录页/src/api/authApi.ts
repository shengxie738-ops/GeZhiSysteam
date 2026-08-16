const API_ORIGIN = import.meta.env.VITE_API_ORIGIN || "http://127.0.0.1:8516";
const API_BASE = `${API_ORIGIN}/api`;
const ENABLE_MOCK_AUTH = import.meta.env.VITE_ENABLE_MOCK_AUTH === "true";

export function toBackendAssetUrl(path?: string): string {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return path.startsWith("/") ? `${API_ORIGIN}${path}` : path;
}

export type Role = "student" | "teacher";
export type SmsPurpose = "register" | "login";

export interface LoginRequest {
  username: string;
  password: string;
  role: Role;
}

export interface MobileLoginRequest {
  phone: string;
  sms_code: string;
  role: Role;
}

export interface SmsCodeRequest {
  phone: string;
  purpose: SmsPurpose;
  role: Role;
}

export interface RegisterRequest {
  username?: string;
  password: string;
  confirm_password?: string;
  sms_code?: string;
  phone: string;
  role: Role;
  teacher_id?: string;
  real_name?: string;
  student_id?: string;
  class_name?: string;
}

export interface UserInfo {
  username: string;
  role: Role;
  real_name: string;
  phone: string;
  avatar_url: string;
  student_id?: string;
  teacher_id?: string;
  class_name?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  data?: {
    token?: string;
    user?: UserInfo;
    mock?: boolean;
    debug_code?: string;
  };
}

async function POST(path: string, body: Record<string, unknown>): Promise<AuthResponse> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        message: errorData.message || `服务器错误 (${response.status})`,
      };
    }

    return await response.json();
  } catch (error) {
    if (ENABLE_MOCK_AUTH) {
      console.warn("[authApi] backend unavailable, using local mock auth", error);
      return mockHandler(path, body);
    }
    console.error("[authApi] backend unavailable", error);
    return {
      success: false,
      message: "后端服务不可用，请确认 FastAPI 已启动",
    };
  }
}

function readMockUsers(): Array<Record<string, unknown>> {
  return JSON.parse(localStorage.getItem("gezhi_users") || "[]") as Array<Record<string, unknown>>;
}

function writeMockUsers(users: Array<Record<string, unknown>>) {
  localStorage.setItem("gezhi_users", JSON.stringify(users));
}

function mockSmsKey(phone: string, purpose: string, role: string) {
  return `${purpose}:${role}:${phone}`;
}

function mockHandler(path: string, body: Record<string, unknown>): AuthResponse {
  const role = (body.role as Role) || "student";

  if (path === "/sms/send-code") {
    const phone = String(body.phone || "");
    const purpose = String(body.purpose || "login");
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      return { success: false, message: "请输入正确的11位手机号码" };
    }
    const code = Math.floor(100000 + Math.random() * 900000).toString();
    const codes = JSON.parse(localStorage.getItem("gezhi_sms_codes") || "{}") as Record<string, string>;
    codes[mockSmsKey(phone, purpose, role)] = code;
    localStorage.setItem("gezhi_sms_codes", JSON.stringify(codes));
    return {
      success: true,
      message: "验证码已发送",
      data: { mock: true, debug_code: code },
    };
  }

  if (path.includes("/mobile-login")) {
    const phone = String(body.phone || "");
    const smsCode = String(body.sms_code || "");
    const codes = JSON.parse(localStorage.getItem("gezhi_sms_codes") || "{}") as Record<string, string>;
    if (codes[mockSmsKey(phone, "login", role)] !== smsCode) {
      return { success: false, message: "验证码错误" };
    }

    const user = readMockUsers().find((item) => item.phone === phone && item.role === role);
    if (!user) {
      return { success: false, message: "该手机号未注册" };
    }

    return {
      success: true,
      message: "登录成功",
      data: {
        token: `mock_token_${Date.now()}`,
        user: {
          username: user.username as string,
          role,
          real_name: (user.real_name as string) || "",
          phone,
          avatar_url: "",
          student_id: (user.student_id as string) || "",
          teacher_id: (user.teacher_id as string) || "",
          class_name: (user.class_name as string) || "",
        },
      },
    };
  }

  if (path.includes("/register")) {
    const users = readMockUsers();
    const username = String(body.username || body.student_id || "");
    const exists = users.find((item) => item.username === username || item.phone === body.phone);
    if (exists) {
      return { success: false, message: "账号或手机号已注册" };
    }

    if (role === "student") {
      const codes = JSON.parse(localStorage.getItem("gezhi_sms_codes") || "{}") as Record<string, string>;
      if (codes[mockSmsKey(String(body.phone || ""), "register", role)] !== body.sms_code) {
        return { success: false, message: "请先完成手机号验证" };
      }
    }

    users.push({ ...body, username, created_at: new Date().toISOString() });
    writeMockUsers(users);
    return { success: true, message: "注册成功，请登录" };
  }

  if (path.includes("/login")) {
    const username = String(body.username || "");
    const password = String(body.password || "");
    const user = readMockUsers().find(
      (item) => item.username === username && item.role === role && item.password === password,
    );

    if (!user) {
      return { success: false, message: "用户名或密码错误" };
    }

    return {
      success: true,
      message: "登录成功",
      data: {
        token: `mock_token_${Date.now()}`,
        user: {
          username: user.username as string,
          role,
          real_name: (user.real_name as string) || "",
          phone: (user.phone as string) || "",
          avatar_url: "",
          student_id: (user.student_id as string) || "",
          teacher_id: (user.teacher_id as string) || "",
          class_name: (user.class_name as string) || "",
        },
      },
    };
  }

  return { success: false, message: "未知请求" };
}

export const authApi = {
  studentLogin: (data: LoginRequest): Promise<AuthResponse> =>
    POST("/student/login", data as unknown as Record<string, unknown>),

  teacherLogin: (data: LoginRequest): Promise<AuthResponse> =>
    POST("/teacher/login", data as unknown as Record<string, unknown>),

  studentMobileLogin: (data: MobileLoginRequest): Promise<AuthResponse> =>
    POST("/student/mobile-login", data as unknown as Record<string, unknown>),

  teacherMobileLogin: (data: MobileLoginRequest): Promise<AuthResponse> =>
    POST("/teacher/mobile-login", data as unknown as Record<string, unknown>),

  studentRegister: (data: RegisterRequest): Promise<AuthResponse> =>
    POST("/student/register", data as unknown as Record<string, unknown>),

  teacherRegister: (data: RegisterRequest): Promise<AuthResponse> =>
    POST("/teacher/register", data as unknown as Record<string, unknown>),

  sendSmsCode: (data: SmsCodeRequest): Promise<AuthResponse> =>
    POST("/sms/send-code", data as unknown as Record<string, unknown>),

  login: (data: LoginRequest): Promise<AuthResponse> =>
    data.role === "teacher"
      ? POST("/teacher/login", data as unknown as Record<string, unknown>)
      : POST("/student/login", data as unknown as Record<string, unknown>),

  mobileLogin: (data: MobileLoginRequest): Promise<AuthResponse> =>
    data.role === "teacher"
      ? POST("/teacher/mobile-login", data as unknown as Record<string, unknown>)
      : POST("/student/mobile-login", data as unknown as Record<string, unknown>),

  register: (data: RegisterRequest): Promise<AuthResponse> =>
    data.role === "teacher"
      ? POST("/teacher/register", data as unknown as Record<string, unknown>)
      : POST("/student/register", data as unknown as Record<string, unknown>),
};

export default authApi;
