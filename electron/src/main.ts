import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';
import Store from 'electron-store';

const store = new Store();
let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;

const isDev = process.env.NODE_ENV === 'development';
const API_PORT = 8000;
const FRONTEND_PORT = 3000;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    title: 'ArchViz AI',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 15, y: 15 },
  });

  // Load the frontend
  if (isDev) {
    mainWindow.loadURL(`http://localhost:${FRONTEND_PORT}`);
    mainWindow.webContents.openDevTools();
  } else {
    // In production, load from the built Next.js export or local server
    mainWindow.loadURL(`http://localhost:${FRONTEND_PORT}`);
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

function startPythonBackend() {
  const pythonPath = process.env.PYTHON_PATH || 'python3';
  const apiPath = isDev
    ? path.join(__dirname, '..', '..', 'api')
    : path.join(process.resourcesPath, 'api');

  console.log(`Starting Python backend from: ${apiPath}`);

  pythonProcess = spawn(pythonPath, [
    '-m', 'uvicorn',
    'main:app',
    '--host', '127.0.0.1',
    '--port', String(API_PORT),
  ], {
    cwd: apiPath,
    env: {
      ...process.env,
      PYTHONPATH: isDev
        ? path.join(__dirname, '..', '..')
        : process.resourcesPath,
    },
  });

  pythonProcess.stdout?.on('data', (data) => {
    console.log(`[API] ${data}`);
  });

  pythonProcess.stderr?.on('data', (data) => {
    console.error(`[API] ${data}`);
  });

  pythonProcess.on('error', (err) => {
    console.error('Failed to start Python backend:', err);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python backend exited with code ${code}`);
    pythonProcess = null;
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
}

// IPC Handlers
ipcMain.handle('select-file', async () => {
  if (!mainWindow) return null;

  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'CAD Files', extensions: ['dwg', 'dxf'] },
      { name: 'All Files', extensions: ['*'] },
    ],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  return result.filePaths[0];
});

ipcMain.handle('select-directory', async () => {
  if (!mainWindow) return null;

  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory'],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  return result.filePaths[0];
});

ipcMain.handle('get-setting', async (_, key: string) => {
  return store.get(key);
});

ipcMain.handle('set-setting', async (_, key: string, value: unknown) => {
  store.set(key, value);
  return true;
});

ipcMain.handle('get-app-path', async () => {
  return app.getPath('userData');
});

ipcMain.handle('get-platform', async () => {
  return process.platform;
});

// App lifecycle
app.whenReady().then(() => {
  startPythonBackend();

  // Wait a bit for the backend to start
  setTimeout(createWindow, 2000);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopPythonBackend();
});

app.on('quit', () => {
  stopPythonBackend();
});
