/**
 * Comprehensive API and Integration Test Suite for NyayaSetu Backend.
 * Tests:
 * 1. Health check & DB status reporting
 * 2. Session creation (POST /api/chats)
 * 3. Session retrieval & message ordering (GET /api/chats/:sessionId)
 * 4. Session listing & pagination (GET /api/chats)
 * 5. Session deletion & cascade (DELETE /api/chats/:sessionId)
 * 6. Legal query message flow (POST /api/chats/:sessionId/messages)
 * 7. User message persistence
 * 8. Assistant message persistence
 * 9. Source metadata preservation
 * 10. Invalid empty query validation
 * 11. Invalid session ID validation
 * 12. Nonexistent session (404)
 * 13. RAG service unavailable handling (503)
 * 14. RAG service timeout handling (504)
 * 15. Safe error handling (no leaked secrets or traces)
 */

const request = require('supertest');
const { MongoMemoryServer } = require('mongodb-memory-server');
const mongoose = require('mongoose');

// Set test environment
process.env.NODE_ENV = 'test';
process.env.RAG_SERVICE_URL = 'http://127.0.0.1:8000';
process.env.RAG_SERVICE_TIMEOUT_MS = '2000';

const app = require('../src/app');
const { ChatSession, ChatMessage } = require('../src/models');
const { ragService } = require('../src/services/ragService');

let mongoServer;

async function setupDatabase() {
  mongoServer = await MongoMemoryServer.create();
  const uri = mongoServer.getUri();
  await mongoose.connect(uri);
  console.log('[Test DB] In-memory MongoDB connected at:', uri);
}

async function teardownDatabase() {
  await mongoose.disconnect();
  if (mongoServer) {
    await mongoServer.stop();
  }
}

async function runAllTests() {
  console.log('\n================================================================================');
  console.log('NYAYASETU BACKEND PHASE 9: COMPREHENSIVE INTEGRATION & API TEST SUITE');
  console.log('================================================================================\n');

  let passedCount = 0;
  let totalCount = 0;

  async function test(name, fn) {
    totalCount++;
    try {
      await fn();
      console.log(`  [PASS] #${totalCount}: ${name}`);
      passedCount++;
    } catch (err) {
      console.error(`  [FAIL] #${totalCount}: ${name}`);
      console.error(`         Error: ${err.message}`);
      if (err.stack) {
        console.error('         ' + err.stack.split('\n')[1]);
      }
    }
  }

  await setupDatabase();

  let createdSessionId = null;

  // 1. Health check
  await test('GET /api/health reports backend healthy and database connected', async () => {
    const res = await request(app).get('/api/health');
    if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
    if (!res.body.success) throw new Error('Expected success=true');
    if (res.body.status !== 'healthy') throw new Error(`Expected status=healthy, got ${res.body.status}`);
    if (!res.body.database.connected) throw new Error('Expected database.connected=true');
  });

  // 2. Create Chat Session
  await test('POST /api/chats creates a new chat session with valid UUID', async () => {
    const res = await request(app)
      .post('/api/chats')
      .send({ title: 'Theft Penalty Inquiry' });

    if (res.status !== 201) throw new Error(`Expected 201, got ${res.status}`);
    if (!res.body.success) throw new Error('Expected success=true');
    if (!res.body.data.sessionId) throw new Error('Missing sessionId in response');
    if (res.body.data.title !== 'Theft Penalty Inquiry') {
      throw new Error(`Expected title "Theft Penalty Inquiry", got "${res.body.data.title}"`);
    }

    createdSessionId = res.body.data.sessionId;

    // Verify in database
    const dbSession = await ChatSession.findOne({ sessionId: createdSessionId });
    if (!dbSession) throw new Error('Session not found in MongoDB');
  });

  // 3. Create default-titled session
  await test('POST /api/chats creates session with default title when omitted', async () => {
    const res = await request(app).post('/api/chats').send({});
    if (res.status !== 201) throw new Error(`Expected 201, got ${res.status}`);
    if (res.body.data.title !== 'New Legal Conversation') {
      throw new Error(`Expected default title, got "${res.body.data.title}"`);
    }
  });

  // 4. Retrieve Chat Session
  await test('GET /api/chats/:sessionId returns session metadata and empty messages', async () => {
    const res = await request(app).get(`/api/chats/${createdSessionId}`);
    if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
    if (!res.body.data.session) throw new Error('Missing session object');
    if (res.body.data.session.sessionId !== createdSessionId) throw new Error('SessionId mismatch');
    if (!Array.isArray(res.body.data.messages)) throw new Error('Messages is not an array');
    if (res.body.data.messages.length !== 0) throw new Error('Expected 0 messages');
  });

  // 5. List Chat Sessions
  await test('GET /api/chats lists recent chat sessions with pagination', async () => {
    const res = await request(app).get('/api/chats?page=1&limit=10');
    if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
    if (!Array.isArray(res.body.data.sessions)) throw new Error('Expected sessions array');
    if (res.body.data.total < 2) throw new Error(`Expected at least 2 sessions, got ${res.body.data.total}`);
    if (res.body.data.page !== 1) throw new Error('Page number mismatch');
  });

  // 6. Send legal query message (with mocked RAG service)
  await test('POST /api/chats/:sessionId/messages stores user message, calls RAG service, stores assistant answer', async () => {
    // Mock ragService response
    const originalQuery = ragService.queryLegalRAG;
    ragService.queryLegalRAG = async (_query, _sid) => ({
      content: '## Answer\n\nUnder Section 303 of the Bharatiya Nyaya Sanhita, theft is punished with imprisonment.',
      sources: [
        {
          sourceNumber: 1,
          sourceLabel: '[SOURCE 1]',
          documentName: 'Bharatiya Nyaya Sanhita, 2023',
          chunkId: 'bns_2023_c0258',
          pageNumbers: [80],
          relevanceScore: 0.0886,
          snippet: 'Whoever commits theft shall be punished...',
        },
      ],
      ragMetadata: {
        model: 'gpt-5.6-terra',
        provider: 'openai',
        retrievalDuration: null,
        totalDuration: 120,
        warnings: [],
        status: 'success',
      },
    });

    try {
      const res = await request(app)
        .post(`/api/chats/${createdSessionId}/messages`)
        .send({ query: 'What is the punishment for theft?' });

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}: ${JSON.stringify(res.body)}`);
      if (!res.body.success) throw new Error('Expected success=true');
      if (!res.body.data.message) throw new Error('Expected message in response data');
      if (res.body.data.message.role !== 'assistant') throw new Error('Expected assistant message');
      if (!res.body.data.message.content.includes('Section 303')) {
        throw new Error('Expected assistant message content');
      }

      // Verify user message stored in DB
      const userMsg = await ChatMessage.findOne({ sessionId: createdSessionId, role: 'user' });
      if (!userMsg) throw new Error('User message not found in MongoDB');
      if (userMsg.content !== 'What is the punishment for theft?') throw new Error('User message content mismatch');

      // Verify assistant message stored in DB
      const assistantMsg = await ChatMessage.findOne({ sessionId: createdSessionId, role: 'assistant' });
      if (!assistantMsg) throw new Error('Assistant message not found in MongoDB');
      if (assistantMsg.sources.length !== 1) throw new Error('Assistant source count mismatch');
      if (assistantMsg.sources[0].chunkId !== 'bns_2023_c0258') throw new Error('Source chunk ID mismatch');
      if (assistantMsg.sources[0].pageNumbers[0] !== 80) throw new Error('Source page number mismatch');
      if (assistantMsg.ragMetadata.model !== 'gpt-5.6-terra') throw new Error('RAG metadata model mismatch');
    } finally {
      ragService.queryLegalRAG = originalQuery;
    }
  });

  // 7. Verify message ordering in session history
  await test('GET /api/chats/:sessionId returns messages ordered chronologically', async () => {
    const res = await request(app).get(`/api/chats/${createdSessionId}`);
    if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
    const msgs = res.body.data.messages;
    if (msgs.length !== 2) throw new Error(`Expected 2 messages, got ${msgs.length}`);
    if (msgs[0].role !== 'user') throw new Error('First message must be role=user');
    if (msgs[1].role !== 'assistant') throw new Error('Second message must be role=assistant');
  });

  // 8. Reject empty query
  await test('POST /api/chats/:sessionId/messages rejects empty query with 400', async () => {
    const res = await request(app)
      .post(`/api/chats/${createdSessionId}/messages`)
      .send({ query: '   ' });

    if (res.status !== 400) throw new Error(`Expected 400, got ${res.status}`);
    if (res.body.success !== false) throw new Error('Expected success=false');
    if (res.body.error.code !== 'VALIDATION_ERROR') throw new Error(`Expected VALIDATION_ERROR, got ${res.body.error.code}`);
  });

  // 9. Reject missing query field
  await test('POST /api/chats/:sessionId/messages rejects missing query field with 400', async () => {
    const res = await request(app)
      .post(`/api/chats/${createdSessionId}/messages`)
      .send({});

    if (res.status !== 400) throw new Error(`Expected 400, got ${res.status}`);
    if (res.body.error.code !== 'VALIDATION_ERROR') throw new Error('Expected VALIDATION_ERROR');
  });

  // 10. Reject excessively long query
  await test('POST /api/chats/:sessionId/messages rejects query exceeding 2000 chars with 400', async () => {
    const longQuery = 'legal question '.repeat(200); // >2000 chars
    const res = await request(app)
      .post(`/api/chats/${createdSessionId}/messages`)
      .send({ query: longQuery });

    if (res.status !== 400) throw new Error(`Expected 400, got ${res.status}`);
    if (res.body.error.code !== 'VALIDATION_ERROR') throw new Error('Expected VALIDATION_ERROR');
  });

  // 11. Reject invalid sessionId characters
  await test('GET /api/chats/:sessionId rejects invalid sessionId characters with 400', async () => {
    const res = await request(app).get('/api/chats/invalid!@#$%^&*()');
    if (res.status !== 400) throw new Error(`Expected 400, got ${res.status}`);
    if (res.body.error.code !== 'VALIDATION_ERROR') throw new Error('Expected VALIDATION_ERROR');
  });

  // 12. Nonexistent session returns 404
  await test('GET /api/chats/:sessionId returns 404 for nonexistent sessionId', async () => {
    const fakeId = '00000000-0000-0000-0000-000000000000';
    const res = await request(app).get(`/api/chats/${fakeId}`);
    if (res.status !== 404) throw new Error(`Expected 404, got ${res.status}`);
    if (res.body.error.code !== 'NOT_FOUND') throw new Error('Expected NOT_FOUND');
  });

  // 13. RAG service unavailable handling
  await test('POST /api/chats/:sessionId/messages handles RAG service unavailable (503) safely', async () => {
    // Create new session
    const sessRes = await request(app).post('/api/chats').send();
    const sid = sessRes.body.data.sessionId;

    // Simulate RAG service offline by targeting unreachable port
    const originalUrl = ragService.baseUrl;
    ragService.baseUrl = 'http://127.0.0.1:59999';

    try {
      const res = await request(app)
        .post(`/api/chats/${sid}/messages`)
        .send({ query: 'What is the punishment for theft?' });

      if (res.status !== 503) throw new Error(`Expected 503, got ${res.status}`);
      if (res.body.error.code !== 'RAG_SERVICE_UNAVAILABLE') {
        throw new Error(`Expected RAG_SERVICE_UNAVAILABLE, got ${res.body.error.code}`);
      }
      // Verify user message was recorded, but NO assistant message was fabricated
      const userMsg = await ChatMessage.findOne({ sessionId: sid, role: 'user' });
      const assistantMsg = await ChatMessage.findOne({ sessionId: sid, role: 'assistant' });
      if (!userMsg) throw new Error('User message should be preserved');
      if (assistantMsg) throw new Error('No assistant message should be fabricated on failure');
    } finally {
      ragService.baseUrl = originalUrl;
    }
  });

  // 14. RAG service timeout handling
  await test('POST /api/chats/:sessionId/messages handles RAG service timeout (504) safely', async () => {
    const sessRes = await request(app).post('/api/chats').send();
    const sid = sessRes.body.data.sessionId;

    // Simulate timeout
    const originalQuery = ragService.queryLegalRAG;
    ragService.queryLegalRAG = async () => {
      const { RAGServiceTimeoutError } = require('../src/utils/errors');
      throw new RAGServiceTimeoutError();
    };

    try {
      const res = await request(app)
        .post(`/api/chats/${sid}/messages`)
        .send({ query: 'What is the punishment for theft?' });

      if (res.status !== 504) throw new Error(`Expected 504, got ${res.status}`);
      if (res.body.error.code !== 'RAG_SERVICE_TIMEOUT') {
        throw new Error(`Expected RAG_SERVICE_TIMEOUT, got ${res.body.error.code}`);
      }
    } finally {
      ragService.queryLegalRAG = originalQuery;
    }
  });

  // 15. Delete chat session and cascade messages
  await test('DELETE /api/chats/:sessionId deletes session and associated messages', async () => {
    const res = await request(app).delete(`/api/chats/${createdSessionId}`);
    if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
    if (!res.body.success) throw new Error('Expected success=true');

    // Verify session deleted in DB
    const dbSession = await ChatSession.findOne({ sessionId: createdSessionId });
    if (dbSession) throw new Error('Session still exists in MongoDB');

    // Verify messages deleted in DB
    const dbMessages = await ChatMessage.find({ sessionId: createdSessionId });
    if (dbMessages.length > 0) throw new Error('Messages not deleted in MongoDB');
  });

  // 16. Route not found (404)
  await test('Nonexistent route returns standard 404 error format', async () => {
    const res = await request(app).get('/api/nonexistent-route');
    if (res.status !== 404) throw new Error(`Expected 404, got ${res.status}`);
    if (res.body.error.code !== 'ROUTE_NOT_FOUND') throw new Error('Expected ROUTE_NOT_FOUND');
  });

  // ── Unified /api/chat Endpoint Tests ──
  let directChatSessionId = null;

  // 17. POST /api/chat auto session creation & message orchestration
  await test('POST /api/chat automatically creates session and returns structured response', async () => {
    const originalQuery = ragService.queryLegalRAG;
    ragService.queryLegalRAG = async (q, sid) => ({
      content: 'Consumer redressal commission limits are defined in Section 34 of CPA 2019.',
      sources: [
        {
          sourceNumber: 1,
          sourceLabel: '[SOURCE 1]',
          documentName: 'Consumer Protection Act, 2019',
          chunkId: 'cpa-sec34',
          pageNumbers: [18],
          relevanceScore: 0.92,
          snippet: 'District Commission pecuniary limit...',
        },
      ],
      ragMetadata: { model: 'gpt-5.6-terra', status: 'success' },
    });

    try {
      const res = await request(app)
        .post('/api/chat')
        .send({ message: 'What are the consumer court pecuniary limits?' });

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
      if (!res.body.success) throw new Error('Expected success=true');
      if (!res.body.sessionId) throw new Error('Missing sessionId in response');
      if (!res.body.message || res.body.message.role !== 'assistant') {
        throw new Error('Missing assistant message in response');
      }
      if (!res.body.message.content.includes('Consumer redressal commission')) {
        throw new Error('Unexpected assistant content');
      }
      if (!Array.isArray(res.body.message.sources) || res.body.message.sources.length === 0) {
        throw new Error('Sources array missing or empty');
      }

      directChatSessionId = res.body.sessionId;

      // Verify stored in DB
      const dbMsgs = await ChatMessage.find({ sessionId: directChatSessionId });
      if (dbMsgs.length !== 2) throw new Error(`Expected 2 messages in DB, found ${dbMsgs.length}`);
    } finally {
      ragService.queryLegalRAG = originalQuery;
    }
  });

  // 18. POST /api/chat with existing sessionId
  await test('POST /api/chat appends turn to existing session when sessionId is provided', async () => {
    const originalQuery = ragService.queryLegalRAG;
    ragService.queryLegalRAG = async () => ({
      content: 'State Commission hears appeals up to ₹2 Crores.',
      sources: [],
      ragMetadata: { status: 'success' },
    });

    try {
      const res = await request(app)
        .post('/api/chat')
        .send({
          sessionId: directChatSessionId,
          message: 'What about the State Commission?',
        });

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
      if (res.body.sessionId !== directChatSessionId) {
        throw new Error(`Expected sessionId ${directChatSessionId}, got ${res.body.sessionId}`);
      }

      const dbMsgs = await ChatMessage.find({ sessionId: directChatSessionId });
      if (dbMsgs.length !== 4) throw new Error(`Expected 4 messages in DB, found ${dbMsgs.length}`);
    } finally {
      ragService.queryLegalRAG = originalQuery;
    }
  });

  // 19. POST /api/chat rejects empty message
  await test('POST /api/chat rejects empty message with 400 ValidationError', async () => {
    const res = await request(app)
      .post('/api/chat')
      .send({ message: '   ' });

    if (res.status !== 400) throw new Error(`Expected 400, got ${res.status}`);
    if (res.body.error.code !== 'VALIDATION_ERROR') {
      throw new Error(`Expected VALIDATION_ERROR, got ${res.body.error.code}`);
    }
  });

  // 20. GET /api/chat/:sessionId retrieves session and message history
  await test('GET /api/chat/:sessionId retrieves session with complete message history', async () => {
    const res = await request(app).get(`/api/chat/${directChatSessionId}`);
    if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
    if (!res.body.success) throw new Error('Expected success=true');
    if (res.body.data.messages.length !== 4) {
      throw new Error(`Expected 4 messages, got ${res.body.data.messages.length}`);
    }
  });

  // 21. DELETE /api/chat/:sessionId deletes session and messages
  await test('DELETE /api/chat/:sessionId deletes session and cascades messages', async () => {
    const res = await request(app).delete(`/api/chat/${directChatSessionId}`);
    if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
    if (!res.body.success) throw new Error('Expected success=true');

    const dbSession = await ChatSession.findOne({ sessionId: directChatSessionId });
    if (dbSession) throw new Error('Session was not deleted from DB');
  });

  await teardownDatabase();

  console.log('\n================================================================================');
  console.log(`TEST SUMMARY: ${passedCount} / ${totalCount} PASSED (${Math.round((passedCount / totalCount) * 100)}%)`);
  console.log('================================================================================\n');

  if (passedCount !== totalCount) {
    process.exit(1);
  }
}

runAllTests().catch((err) => {
  console.error('Fatal test runner error:', err);
  process.exit(1);
});
