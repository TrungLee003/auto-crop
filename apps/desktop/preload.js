const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  openFolderPicker: () => ipcRenderer.invoke('dialog:open-folder'),
  openFilePicker: (options) => ipcRenderer.invoke('dialog:open-files', options),
  openPathInExplorer: (path) => ipcRenderer.invoke('shell:open-path', path),
  getAppVersion: () => ipcRenderer.invoke('app:get-version'),
  onMenuAction: (callback) => {
    const handler = (_event, action) => callback(action);
    ipcRenderer.on('menu:action', handler);
    return () => ipcRenderer.removeListener('menu:action', handler);
  },
  isElectron: true,
});
