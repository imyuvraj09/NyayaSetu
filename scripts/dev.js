/**
 * NyayaSetu Unified Development Server Orchestrator.
 * Concurrently starts:
 *   - Frontend (Vite) on http://localhost:5173
 *   - Backend (Express) on http://localhost:3000
 *   - RAG Service (FastAPI) on http://127.0.0.1:8000
 *
 * Provides synchronized prefixed logging and graceful multi-process termination.
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const readline = require('readline');

const rootDir = path.resolve(__dirname, '..');

const COLORS = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  cyan: '\x1b[36m',
  green: '\x1b[32m',
  magenta: '\x1b[35m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  gray: '\x1b[90m',
};

const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';

const SERVICES = [
  {
    name: 'backend',
    displayName: 'backend',
    color: COLORS.green,
    cwd: path.join(rootDir, 'backend'),
    command: npmCmd,
    args: ['run', 'dev'],
    shell: process.platform === 'win32',
  },
  {
    name: 'rag-service',
    displayName: 'rag-service',
    color: COLORS.magenta,
    cwd: rootDir,
    command: 'node',
    args: [path.join(rootDir, 'scripts', 'run-rag.js')],
    shell: false,
  },
  {
    name: 'frontend',
    displayName: 'frontend',
    color: COLORS.cyan,
    cwd: path.join(rootDir, 'frontend'),
    command: npmCmd,
    args: ['run', 'dev'],
    shell: process.platform === 'win32',
  },
];

console.log(`${COLORS.bold}${COLORS.yellow}================================================================${COLORS.reset}`);
console.log(`${COLORS.bold}${COLORS.yellow}  NyayaSetu — Development Environment Orchestrator${COLORS.reset}`);
console.log(`${COLORS.bold}${COLORS.yellow}================================================================${COLORS.reset}`);
console.log(`  ${COLORS.cyan}● Frontend UI  :${COLORS.reset} http://localhost:5173`);
console.log(`  ${COLORS.green}● Backend API  :${COLORS.reset} http://localhost:3000`);
console.log(`  ${COLORS.magenta}● RAG Service  :${COLORS.reset} http://127.0.0.1:8000  ${COLORS.dim}(Docs: http://127.0.0.1:8000/docs)${COLORS.reset}`);
console.log(`${COLORS.gray}----------------------------------------------------------------${COLORS.reset}\n`);

const activeChildren = [];
let isShuttingDown = false;

function formatPrefix(service) {
  const padded = service.displayName.padEnd(11, ' ');
  return `${service.color}[${padded}]${COLORS.reset} `;
}

function startService(service) {
  const child = spawn(service.command, service.args, {
    cwd: service.cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: service.shell,
    env: { ...process.env, FORCE_COLOR: '1' },
  });

  activeChildren.push({ service, child });

  const prefix = formatPrefix(service);

  const rlOut = readline.createInterface({ input: child.stdout });
  rlOut.on('line', (line) => {
    if (line.trim().length > 0) {
      console.log(`${prefix}${line}`);
    }
  });

  const rlErr = readline.createInterface({ input: child.stderr });
  rlErr.on('line', (line) => {
    if (line.trim().length > 0) {
      console.error(`${prefix}${COLORS.dim}${line}${COLORS.reset}`);
    }
  });

  child.on('error', (err) => {
    console.error(`${prefix}${COLORS.bold}\x1b[31mProcess error: ${err.message}${COLORS.reset}`);
  });

  child.on('exit', (code, signal) => {
    if (!isShuttingDown) {
      console.log(`${prefix}${COLORS.yellow}Process exited with code ${code !== null ? code : signal}${COLORS.reset}`);
    }
  });

  return child;
}

// Start all services
SERVICES.forEach(startService);

function shutdownAll(signal) {
  if (isShuttingDown) return;
  isShuttingDown = true;
  console.log(`\n${COLORS.yellow}[NyayaSetu] Received ${signal}. Stopping all services...${COLORS.reset}`);

  for (const { child } of activeChildren) {
    if (child && child.pid) {
      try {
        if (process.platform === 'win32') {
          execSync(`taskkill /pid ${child.pid} /t /f`, { stdio: 'ignore' });
        } else {
          child.kill('SIGTERM');
        }
      } catch (_e) {
        try { child.kill('SIGKILL'); } catch (_e2) {}
      }
    }
  }

  setTimeout(() => {
    console.log(`${COLORS.green}[NyayaSetu] All dev processes closed successfully.${COLORS.reset}`);
    process.exit(0);
  }, 500);
}

process.on('SIGINT', () => shutdownAll('SIGINT'));
process.on('SIGTERM', () => shutdownAll('SIGTERM'));
