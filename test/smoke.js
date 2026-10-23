// Read-only HTTP check against services started by this test. No cargo is created.
const { spawn } = require('node:child_process');
const path = require('node:path');
const http = require('node:http');
const { assertPortFree } = require('../server');
const root = path.resolve(__dirname, '..');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

function status(port) {
  return new Promise(resolve => {
    const request = http.get(`http://127.0.0.1:${port}/api/me`, response => {
      response.resume(); resolve(response.statusCode);
    });
    request.setTimeout(2000, () => request.destroy());
    request.on('error', () => resolve(0));
  });
}

async function main() {
  const web = 13000, backend = 18765;
  await assertPortFree(web); await assertPortFree(backend);
  const child = spawn(process.execPath, ['server.js'], {
    cwd: root, env: { ...process.env, PORT: String(web), BACKEND_PORT: String(backend) },
    stdio: ['ignore', 'inherit', 'inherit', 'ipc'], windowsHide: true,
  });
  let ended = false;
  const closed = new Promise(resolve => child.on('exit', () => { ended = true; resolve(); }));
  let passed = false;
  try {
    for (let attempt = 0; attempt < 60 && !ended; attempt++) {
      if (await status(web) === 401 && await status(backend) === 401) { passed = true; break; }
      await delay(500);
    }
    if (!passed) throw new Error('Services/proxy did not return expected unauthenticated response.');
    console.log('PASS: backend and Next proxy both return 401 without a session.');
  } finally {
    if (child.connected) child.send('shutdown');
    await Promise.race([closed, delay(8000)]);
    if (!ended) { child.kill(); throw new Error('Launcher did not stop gracefully.'); }
  }
  await assertPortFree(web); await assertPortFree(backend);
  console.log('PASS: shutdown released both ports.');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
