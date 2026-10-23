// Entry point for the two local services, not an Express portfolio server.
const path = require('node:path');
const fs = require('node:fs');
const net = require('node:net');
const http = require('node:http');
const { spawn } = require('node:child_process');

const ROOT = __dirname;

function port(value, fallback, name) {
  const raw = value ?? String(fallback);
  if (!/^\d+$/.test(raw) || Number(raw) < 1024 || Number(raw) > 65535) {
    throw new Error(`${name} must be an integer between 1024 and 65535.`);
  }
  return Number(raw);
}

function config(env = process.env) {
  const webPort = port(env.PORT, 3000, 'PORT');
  const backendPort = port(env.BACKEND_PORT, 8765, 'BACKEND_PORT');
  if (webPort === backendPort) throw new Error('PORT and BACKEND_PORT must be different.');
  return { webPort, backendPort, python: env.PYTHON_COMMAND || 'python' };
}

function assertPortFree(value) {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once('error', () => reject(new Error(`Port ${value} is in use or unavailable. Stop the old project server or change .env. No process was stopped.`)));
    probe.listen(value, '127.0.0.1', () => probe.close(resolve));
  });
}

function backendReady(value) {
  return new Promise(resolve => {
    const request = http.get(`http://127.0.0.1:${value}/api/me`, response => {
      response.resume(); resolve(response.statusCode === 401);
    });
    request.setTimeout(700, () => request.destroy());
    request.on('error', () => resolve(false));
  });
}

async function main() {
  const envFile = path.join(ROOT, '.env');
  if (fs.existsSync(envFile)) process.loadEnvFile(envFile);
  const settings = config();
  const production = process.argv.includes('--production');
  const nextBin = path.join(ROOT, 'nha-xe-web', 'node_modules', 'next', 'dist', 'bin', 'next');
  if (!fs.existsSync(nextBin)) throw new Error('Frontend dependencies missing. Run npm run setup first.');
  const backendUrl = `http://127.0.0.1:${settings.backendPort}`;
  if (process.argv.includes('--build')) {
    const build = spawn(process.execPath, [nextBin, 'build'], {
      cwd: path.join(ROOT, 'nha-xe-web'), stdio: 'inherit', windowsHide: true,
      env: { ...process.env, NODE_ENV: 'production', BACKEND_URL: backendUrl },
    });
    build.on('error', error => { console.error(error.message); process.exitCode = 1; });
    build.on('exit', code => { process.exitCode = code ?? 1; });
    return;
  }
  if (production && !fs.existsSync(path.join(ROOT, 'nha-xe-web', '.next', 'BUILD_ID'))) {
    throw new Error('Production build missing. Run npm run build first.');
  }
  if (production) {
    const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'nha-xe-web', '.next', 'routes-manifest.json'), 'utf8'));
    const rewrites = Array.isArray(manifest.rewrites) ? manifest.rewrites : Object.values(manifest.rewrites).flat();
    if (!rewrites.some(rule => rule.source === '/api/:path*' && rule.destination === `${backendUrl}/api/:path*`)) {
      throw new Error('Backend port differs from the saved build. Run npm run build after changing BACKEND_PORT.');
    }
  }
  await assertPortFree(settings.webPort);
  await assertPortFree(settings.backendPort);

  const children = new Set();
  let stopping = false;
  function stop(code = 0) {
    if (stopping) return;
    stopping = true;
    process.exitCode = code;
    for (const child of children) child.kill('SIGTERM');
    // Only children created by this launcher are signaled.
    const timer = setTimeout(() => {
      for (const child of children) child.kill('SIGKILL');
    }, 3000);
    timer.unref();
  }
  function launch(command, args, cwd, env) {
    const child = spawn(command, args, { cwd, env, stdio: 'inherit', windowsHide: true, shell: false });
    children.add(child);
    child.on('error', error => { console.error(`Cannot launch ${command}: ${error.message}`); stop(1); });
    child.on('exit', code => {
      children.delete(child);
      if (!stopping) { console.error(`A service stopped (code ${code}). Closing the other service.`); stop(code || 1); }
    });
    return child;
  }
  process.on('SIGINT', () => stop(0));
  process.on('SIGTERM', () => stop(0));
  // An IPC shutdown makes the local smoke test deterministic on Windows.
  if (process.send) process.on('message', message => {
    if (message === 'shutdown') { stop(0); process.disconnect(); }
  });

  launch(settings.python, ['app.py'], path.join(ROOT, 'nha-xe-v1'), {
    ...process.env, PORT: String(settings.backendPort), PYTHONUNBUFFERED: '1', PYTHONUTF8: '1',
  });
  let ready = false;
  for (let attempt = 0; attempt < 60 && !stopping; attempt++) {
    if (await backendReady(settings.backendPort)) { ready = true; break; }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  if (stopping) return;
  if (!ready) { console.error('Backend did not become ready. Check Python installation and permissions.'); stop(1); return; }

  launch(process.execPath, [nextBin, production ? 'start' : 'dev', '--hostname', '127.0.0.1', '--port', String(settings.webPort)], path.join(ROOT, 'nha-xe-web'), {
    ...process.env,
    NODE_ENV: production ? 'production' : 'development',
    BACKEND_URL: `http://127.0.0.1:${settings.backendPort}`,
  });
  console.log(`\nNha xe: http://127.0.0.1:${settings.webPort}\nAccounts: nha-xe-v1/TAI-KHOAN.txt\nPress Ctrl+C to stop both services.\n`);
}

if (require.main === module) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
module.exports = { config, assertPortFree };
