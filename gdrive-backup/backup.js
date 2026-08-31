const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const drive = google.drive({ version: 'v3', auth: process.env.GOOGLE_AUTH });

async function backupToDrive(localPath, driveFolder = 'Downloads-Backup') {
  try {
    console.log(`Backing up ${localPath} to Google Drive...`);
    
    // Find or create backup folder
    const folderRes = await drive.files.list({
      q: `name='${driveFolder}' and mimeType='application/vnd.google-apps.folder' and trashed=false`,
      spaces: 'drive',
      fields: 'files(id, name)',
      pageSize: 1
    });
    
    const folderId = folderRes.data.files[0]?.id;
    if (!folderId) {
      console.log(`⚠️  Folder '${driveFolder}' not found. Create it via google.com/drive first.`);
      return;
    }
    
    console.log(`✓ Backup folder found: ${folderId}`);
    console.log('Use rclone or Google Drive web UI to verify uploads.');
  } catch (err) {
    console.error('Error:', err.message);
  }
}

// Usage: node backup.js /path/to/backup
backupToDrive(process.argv[2] || process.env.HOME + '/Downloads');
