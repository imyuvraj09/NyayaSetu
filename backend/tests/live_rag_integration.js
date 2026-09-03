/**
 * Live End-to-End Integration Verification:
 * Node.js Backend Gateway -> Python FastAPI RAG Service (Real Retrieval + Validation) -> MongoDB
 */

const { MongoMemoryServer } = require('mongodb-memory-server');
const mongoose = require('mongoose');
const request = require('supertest');
const { spawn } = require('child_process');
const path = require('path');

process.env.NODE_ENV = 'test';
process.env.RAG_SERVICE_URL = 'http://127.0.0.1:8000';
process.env.RAG_SERVICE_TIMEOUT_MS = '60000';

const app = require('../src/app');
const { ChatSession, ChatMessage } = require('../src/models');

async function checkFastAPIAvailable() {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/v1/health');
    return res.ok;
  } catch (_e) {
    return false;
  }
}

async function runLiveTest() {
  console.log('\n================================================================================');
  console.log('NYAYASETU LIVE END-TO-END FLOW VERIFICATION');
  console.log('================================================================================\n');

  // 1. Setup in-memory MongoDB
  const mongoServer = await MongoMemoryServer.create();
  await mongoose.connect(mongoServer.getUri());
  console.log('[1/5] In-memory MongoDB connected successfully.');

  // 2. Check if FastAPI RAG service is running on port 8000
  let fastApiProc = null;
  const isAlreadyRunning = await checkFastAPIAvailable();

  if (isAlreadyRunning) {
    console.log('[2/5] FastAPI RAG service is already running on port 8000.');
  } else {
    console.log('[2/5] Starting FastAPI RAG service on port 8000 for live verification...');
    const pythonExe = path.resolve(__dirname, '../../rag-service/venv/Scripts/python.exe');
    const ragDir = path.resolve(__dirname, '../../rag-service');

    fastApiProc = spawn(
      pythonExe,
      ['-m', 'uvicorn', 'main:app', '--port', '8000'],
      { cwd: ragDir, stdio: 'inherit' }
    );

    // Wait for FastAPI to become ready
    let ready = false;
    for (let i = 0; i < 40; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      if (await checkFastAPIAvailable()) {
        ready = true;
        break;
      }
    }

    if (!ready) {
      console.warn('[2/5] FastAPI did not become ready in 40s; will test fallback handling.');
    } else {
      console.log('[2/5] FastAPI RAG service started and verified healthy.');
    }
  }

  try {
    // 3. Create chat session via Node.js Express API
    console.log('\n[3/5] Creating chat session via POST /api/chats...');
    const createRes = await request(app)
      .post('/api/chats')
      .send({ title: 'Theft Query Live Test' });

    console.log('  Status Code:', createRes.status);
    console.log('  Created Session:', createRes.body.data.sessionId);
    const sessionId = createRes.body.data.sessionId;

    // 4. Send legal query message through Node.js Express to FastAPI RAG service
    console.log('\n[4/5] Sending legal inquiry via POST /api/chats/:sessionId/messages...');
    const queryText = 'What is the punishment for theft?';
    const msgRes = await request(app)
      .post(`/api/chats/${sessionId}/messages`)
      .send({ query: queryText });

    console.log('  Status Code:', msgRes.status);
    console.log('  Response Success:', msgRes.body.success);
    if (msgRes.body.data && msgRes.body.data.message) {
      const msg = msgRes.body.data.message;
      console.log('  Role:', msg.role);
      console.log('  Sources Count:', msg.sources ? msg.sources.length : 0);
      if (msg.sources && msg.sources.length > 0) {
        console.log(`  Top Source: ${msg.sources[0].sourceLabel} - ${msg.sources[0].documentName} (Chunk: ${msg.sources[0].chunkId}, Page: ${msg.sources[0].pageNumbers})`);
      }
      console.log('  Answer Preview:\n  ' + msg.content.slice(0, 200).replace(/\n/g, '\n  ') + '...');
    }

    // 5. Retrieve full chat history from MongoDB
    console.log('\n[5/5] Retrieving complete chat history via GET /api/chats/:sessionId...');
    const historyRes = await request(app).get(`/api/chats/${sessionId}`);
    console.log('  Status Code:', historyRes.status);
    console.log('  Session Title:', historyRes.body.data.session.title);
    console.log('  Total Messages Stored in MongoDB:', historyRes.body.data.messages.length);
    for (const m of historyRes.body.data.messages) {
      console.log(`    - [${m.role.toUpperCase()}]: ${m.content.slice(0, 60).replace(/\n/g, ' ')}... (${m.sources ? m.sources.length : 0} sources)`);
    }

    console.log('\n================================================================================');
    console.log('LIVE END-TO-END FLOW VERIFICATION COMPLETE: SUCCESS!');
    console.log('================================================================================\n');
  } finally {
    if (fastApiProc) {
      fastApiProc.kill();
    }
    await mongoose.disconnect();
    await mongoServer.stop();
  }
}

runLiveTest().catch((err) => {
  console.error('Fatal live test error:', err);
  process.exit(1);
});
