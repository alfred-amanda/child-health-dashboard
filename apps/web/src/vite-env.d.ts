/// <reference types="vite/client" />

declare module '*.css';
declare module '*.svg?url' {
  const src: string;
  export default src;
}
