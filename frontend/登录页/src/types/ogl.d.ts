declare module 'ogl' {
  export class Renderer {
    constructor(options?: { alpha?: boolean; premultipliedAlpha?: boolean });
    gl: any;
    setSize(width: number, height: number): void;
    render(options: { scene: any }): void;
  }

  export class Program {
    constructor(gl: any, options: { vertex: string; fragment: string; uniforms: Record<string, any> });
    uniforms: Record<string, any>;
  }

  export class Mesh {
    constructor(gl: any, options: { geometry: any; program: any });
  }

  export class Color {
    constructor(r?: number, g?: number, b?: number);
  }

  export class Triangle {
    constructor(gl: any);
  }
}
