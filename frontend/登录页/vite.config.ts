import { defineConfig } from 'vite'
import fs from 'fs'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'


function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

function frontendAppDevServer() {
  const appRoot = path.resolve(__dirname, '..')
  const mimeTypes = new Map([
    ['.html', 'text/html; charset=utf-8'],
    ['.js', 'text/javascript; charset=utf-8'],
    ['.css', 'text/css; charset=utf-8'],
    ['.json', 'application/json; charset=utf-8'],
    ['.png', 'image/png'],
    ['.jpg', 'image/jpeg'],
    ['.jpeg', 'image/jpeg'],
    ['.gif', 'image/gif'],
    ['.webp', 'image/webp'],
    ['.svg', 'image/svg+xml'],
    ['.pdf', 'application/pdf'],
    ['.ppt', 'application/vnd.ms-powerpoint'],
    ['.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'],
  ])

  return {
    name: 'frontend-app-dev-server',
    configureServer(server) {
      server.middlewares.use('/app', (req, res, next) => {
        try {
          const requestPath = decodeURIComponent((req.url || '/').split('?')[0])
          const relativePath = requestPath === '/' ? 'index.html' : requestPath.replace(/^\/+/, '')
          const filePath = path.resolve(appRoot, relativePath)

          if (filePath !== appRoot && !filePath.startsWith(appRoot + path.sep)) {
            res.statusCode = 403
            res.end('Forbidden')
            return
          }

          const stat = fs.statSync(filePath)
          if (!stat.isFile()) {
            next()
            return
          }

          res.setHeader('Content-Type', mimeTypes.get(path.extname(filePath).toLowerCase()) || 'application/octet-stream')
          fs.createReadStream(filePath).pipe(res)
        } catch (error) {
          if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
            next()
            return
          }
          next(error)
        }
      })
    },
  }
}

export default defineConfig({
  base: './',
  plugins: [
    figmaAssetResolver(),
    frontendAppDevServer(),
    // The React and Tailwind plugins are both required for Make, even if
    // Tailwind is not being actively used – do not remove them
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      // Alias @ to the src directory
      '@': path.resolve(__dirname, './src'),
    },
  },

  // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
  assetsInclude: ['**/*.svg', '**/*.csv'],
  build: {
    outDir: '../login',
    emptyOutDir: true,
  },
})
