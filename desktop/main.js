const { app, BrowserWindow, Menu, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

const configPath = path.join(__dirname, 'config.json');
let config = { serverUrl: 'http://127.0.0.1:8000' };
try {
  config = Object.assign(config, JSON.parse(fs.readFileSync(configPath, 'utf8')));
} catch (e) {
  console.warn('config.json okunamadi, varsayilan sunucu kullaniliyor.');
}

let win;

function createWindow() {
  win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 900,
    minHeight: 600,
    title: 'RelAİ',
    backgroundColor: '#0f1117',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: false,
    },
  });

  Menu.setApplicationMenu(null);
  win.loadURL(config.serverUrl);

  win.webContents.on('did-fail-load', () => {
    win.loadFile(path.join(__dirname, 'error.html'));
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
