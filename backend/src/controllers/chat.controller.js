/**
 * Thin Chat Controller for NyayaSetu API Gateway.
 * Delegates request processing to chatService and serializes responses
 * using the standard API contract.
 */

const { chatService } = require('../services/chatService');
const { sendSuccess } = require('../utils/apiResponse');

/**
 * POST /api/chats
 * Create a new chat session.
 */
async function createChat(req, res, next) {
  try {
    const { title } = req.body || {};
    const session = await chatService.createSession(title);
    return sendSuccess(res, session, 201, 'Chat session created successfully');
  } catch (err) {
    return next(err);
  }
}

/**
 * GET /api/chats/:sessionId
 * Retrieve a chat session and its full message history.
 */
async function getChat(req, res, next) {
  try {
    const { sessionId } = req.params;
    const chatData = await chatService.getSessionWithMessages(sessionId);
    return sendSuccess(res, chatData, 200);
  } catch (err) {
    return next(err);
  }
}

/**
 * GET /api/chats
 * List recent chat sessions with pagination.
 */
async function listChats(req, res, next) {
  try {
    const { skip, limit, page } = req.pagination;
    const result = await chatService.listSessions(skip, limit, page);
    return sendSuccess(res, result, 200);
  } catch (err) {
    return next(err);
  }
}

/**
 * DELETE /api/chats/:sessionId
 * Delete a chat session and its associated messages.
 */
async function deleteChat(req, res, next) {
  try {
    const { sessionId } = req.params;
    const result = await chatService.deleteSession(sessionId);
    return sendSuccess(res, result, 200, 'Chat session and messages deleted successfully');
  } catch (err) {
    return next(err);
  }
}

/**
 * POST /api/chats/:sessionId/messages
 * Submit a legal query within an existing chat session.
 */
async function postMessage(req, res, next) {
  try {
    const { sessionId } = req.params;
    const { query, requestId: bodyRequestId } = req.body;
    const requestId = bodyRequestId || req.headers['x-request-id'] || null;

    const result = await chatService.sendMessage(sessionId, query, requestId);

    // Conforms strictly to the response contract:
    // { success: true, data: { sessionId, message: assistantMessage, userMessage } }
    return sendSuccess(
      res,
      {
        sessionId: result.sessionId,
        message: result.assistantMessage,
        userMessage: result.userMessage,
        requestId: result.assistantMessage.ragMetadata?.requestId || requestId,
      },
      200
    );
  } catch (err) {
    return next(err);
  }
}

/**
 * POST /api/chat
 * Unified chat endpoint:
 * Receives { sessionId, message } or { sessionId, query }.
 * Creates session automatically if sessionId is omitted or not found.
 * Sends query to Python RAG service, stores messages, and returns structured response.
 */
async function handleDirectChat(req, res, next) {
  try {
    const { sessionId: rawSessionId, message: rawMessage, query: rawQuery, title, requestId: bodyRequestId } = req.body || {};
    const requestId = bodyRequestId || req.headers['x-request-id'] || null;
    const text = (rawMessage || rawQuery || '').trim();

    if (!text) {
      const { ValidationError } = require('../utils/errors');
      throw new ValidationError('Message content is required and cannot be empty.');
    }

    if (text.length > 2000) {
      const { ValidationError } = require('../utils/errors');
      throw new ValidationError('Message exceeds maximum allowed length of 2000 characters.');
    }

    let effectiveSessionId = rawSessionId && typeof rawSessionId === 'string' ? rawSessionId.trim() : null;

    // If session ID provided, verify existence or create new session
    if (effectiveSessionId) {
      const { ChatSession } = require('../models');
      const existing = await ChatSession.findOne({ sessionId: effectiveSessionId });
      if (!existing) {
        const newSession = await chatService.createSession(title || text.slice(0, 60));
        effectiveSessionId = newSession.sessionId;
      }
    } else {
      const newSession = await chatService.createSession(title || text.slice(0, 60));
      effectiveSessionId = newSession.sessionId;
    }

    const result = await chatService.sendMessage(effectiveSessionId, text, requestId);

    return res.status(200).json({
      success: true,
      sessionId: result.sessionId,
      message: {
        role: result.assistantMessage.role,
        content: result.assistantMessage.content,
        sources: result.assistantMessage.sources || [],
        metadata: result.assistantMessage.ragMetadata || result.assistantMessage.metadata || {},
        ragMetadata: result.assistantMessage.ragMetadata || {},
        generationStatus: result.assistantMessage.ragMetadata?.generationStatus || result.assistantMessage.generationStatus || 'SUCCESS',
        retrievalStatus: result.assistantMessage.ragMetadata?.retrievalStatus || result.assistantMessage.retrievalStatus || 'SUCCESS',
        validationStatus: result.assistantMessage.ragMetadata?.validationStatus || result.assistantMessage.validationStatus || 'PASSED',
        createdAt: result.assistantMessage.createdAt,
      },


      userMessage: result.userMessage,
      data: {
        sessionId: result.sessionId,
        message: result.assistantMessage,
        userMessage: result.userMessage,
      },
    });
  } catch (err) {
    return next(err);
  }
}

module.exports = {
  createChat,
  getChat,
  listChats,
  deleteChat,
  postMessage,
  handleDirectChat,
};
