import { contextBridge, ipcRenderer } from 'electron';

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electron', {
  // File dialogs
  selectFile: () => ipcRenderer.invoke('select-file'),
  selectDirectory: () => ipcRenderer.invoke('select-directory'),

  // Settings
  getSetting: (key: string) => ipcRenderer.invoke('get-setting', key),
  setSetting: (key: string, value: unknown) => ipcRenderer.invoke('set-setting', key, value),

  // App info
  getAppPath: () => ipcRenderer.invoke('get-app-path'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),

  // Platform detection
  isElectron: true,
});

// Type definitions for the exposed API
declare global {
  interface Window {
    electron: {
      selectFile: () => Promise<string | null>;
      selectDirectory: () => Promise<string | null>;
      getSetting: (key: string) => Promise<unknown>;
      setSetting: (key: string, value: unknown) => Promise<boolean>;
      getAppPath: () => Promise<string>;
      getPlatform: () => Promise<NodeJS.Platform>;
      isElectron: boolean;
    };
  }
}
