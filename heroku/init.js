const fs = require('fs');
const path = require('path');

// Directories to create
const directories = [
  'views',
  'public',
  'public/css',
  'public/js',
  'uploads',
  'processed'
];

// Create directories if they don't exist
directories.forEach(dir => {
  const dirPath = path.join(__dirname, dir);
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    console.log(`Created directory: ${dirPath}`);
  } else {
    console.log(`Directory already exists: ${dirPath}`);
  }
});

console.log('Application directory structure initialized successfully.');