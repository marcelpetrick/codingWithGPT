import { defineConfig } from 'vite';

export default defineConfig({
  root: 'src',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: '[name].js',
        assetFileNames: '[name].[ext]',
      },
    },
  },
  server: {
    port: 3000,
    open: true,
  },
  test: {
    root: '.',
    globals: true,
    environment: 'jsdom',
    include: ['tests/**/*.js'],
    setupFiles: './tests/setup.ts',
    coverage: {
      reporter: ['text', 'html'],
    },
  },
});
