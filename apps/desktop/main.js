const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow = null;
let backendProcess = null;

const BACKEND_HOST = '127.0.0.1';
const BACKEND_PORT = 8000;
const isDev = !app.isPackaged && process.env.NODE_ENV !== 'production';

// Window State Management
const stateFilePath = path.join(app.getPath('userData'), 'window-state.json');

function loadWindowState() {
  const defaultState = { width: 1400, height: 900, isMaximized: false };
  try {
    if (fs.existsSync(stateFilePath)) {
      const data = JSON.parse(fs.readFileSync(stateFilePath, 'utf8'));
      return { ...defaultState, ...data };
    }
  } catch (err) {
    console.warn('[Desktop] Could not load window state', err);
  }
  return defaultState;
}

function saveWindowState() {
  if (!mainWindow) return;
  try {
    const isMaximized = mainWindow.isMaximized();
    const bounds = mainWindow.getBounds();
    const state = {
      ...bounds,
      isMaximized,
    };
    fs.mkdirSync(path.dirname(stateFilePath), { recursive: true });
    fs.writeFileSync(stateFilePath, JSON.stringify(state, null, 2), 'utf8');
  } catch (err) {
    console.warn('[Desktop] Could not save window state', err);
  }
}

// Check if backend is alive
function checkBackendHealth() {
  return new Promise((resolve) => {
    const req = http.get(`http://${BACKEND_HOST}:${BACKEND_PORT}/api/v2/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(500, () => {
      req.destroy();
      resolve(false);
    });
  });
}

// Start local FastAPI backend process if not already running
async function startBackend() {
  const isAlive = await checkBackendHealth();
  if (isAlive) {
    console.log('[Desktop] Backend is already running on port', BACKEND_PORT);
    return;
  }

  const rootDir = path.resolve(__dirname, '../..');
  const backendDir = path.join(rootDir, 'backend');

  console.log('[Desktop] Spawning FastAPI backend process in', backendDir);
  backendProcess = spawn(
    'uv',
    ['run', 'uvicorn', 'app.main:app', '--host', BACKEND_HOST, '--port', String(BACKEND_PORT)],
    {
      cwd: backendDir,
      shell: true,
      stdio: 'inherit',
    }
  );

  // Poll until backend responds
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 500));
    if (await checkBackendHealth()) {
      console.log('[Desktop] Backend initialized successfully.');
      return;
    }
  }

  console.warn('[Desktop] Backend took longer than 15s to respond.');
}

function buildAppMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Project...',
          accelerator: 'CmdOrCtrl+N',
          click: () => mainWindow?.webContents.send('menu:action', 'new-project'),
        },
        {
          label: 'Open Project...',
          accelerator: 'CmdOrCtrl+O',
          click: () => mainWindow?.webContents.send('menu:action', 'open-project'),
        },
        { type: 'separator' },
        {
          label: 'Import Scans...',
          accelerator: 'CmdOrCtrl+I',
          click: () => mainWindow?.webContents.send('menu:action', 'import-scans'),
        },
        {
          label: 'Export Illustrations...',
          accelerator: 'CmdOrCtrl+E',
          click: () => mainWindow?.webContents.send('menu:action', 'export'),
        },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'delete' },
        { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Documentation & Dev Plan',
          click: () => shell.openExternal('https://github.com/'),
        },
        {
          label: 'About Illustration Extractor',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About Illustration Extractor',
              message: 'Illustration Extractor v2.0.0',
              detail: 'High-Fidelity Historical Book Illustration Extraction & Vectorization Suite.\nPowered by OpenSeadragon, pyvips, OpenCV, and VTracer.',
            });
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function createWindow() {
  const windowState = loadWindowState();

  mainWindow = new BrowserWindow({
    x: windowState.x,
    y: windowState.y,
    width: windowState.width,
    height: windowState.height,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: '#030712', // gray-950
    title: 'Illustration Extractor v2.0',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,
    },
  });

  if (windowState.isMaximized) {
    mainWindow.maximize();
  }

  buildAppMenu();

  // Load URL
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../../frontend/dist/index.html'));
  }

  mainWindow.on('close', () => {
    saveWindowState();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle('dialog:open-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select Folder',
  });
  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

ipcMain.handle('dialog:open-files', async (event, options = {}) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
    title: 'Select Scan Images',
    filters: [
      { name: 'Scan Images', extensions: ['png', 'jpg', 'jpeg', 'tif', 'tiff', 'webp'] },
      { name: 'All Files', extensions: ['*'] },
    ],
    ...options,
  });
  if (result.canceled) {
    return [];
  }
  return result.filePaths;
});

ipcMain.handle('shell:open-path', async (event, targetPath) => {
  if (targetPath) {
    await shell.openPath(targetPath);
  }
});

ipcMain.handle('app:get-version', () => {
  return app.getVersion();
});

// App Lifecycle
app.whenReady().then(async () => {
  await startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (backendProcess) {
    console.log('[Desktop] Terminating backend process...');
    backendProcess.kill();
    backendProcess = null;
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});
