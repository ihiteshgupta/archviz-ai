// Type definitions for Electron IPC API
declare global {
  interface Window {
    electron?: {
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

export {};
