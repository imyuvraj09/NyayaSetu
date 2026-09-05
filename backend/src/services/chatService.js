/**
 * Chat Service handling database operations and legal query orchestration.
 * Manages ChatSession lifecycle, message persistence, and RAG service coordination.
 */

const crypto = require('crypto');
const { ChatSession, ChatMessage } = require('../models');
const { ragService } = require('./ragService');
const { NotFoundError } = require('../utils/errors');

class ChatService {
  /**
   * Create a new chat session.
   * @param {string} [title]
   * @returns {Promise<Object>}
   */
  async createSession(title) {
    const sessionId = crypto.randomUUID();
    const session = await ChatSession.create({
      sessionId,
      title: title && typeof title === 'string' ? title.trim().slice(0, 100) : 'New Legal Conversation',
      lastActivityAt: new Date(),
    });

    return session.toObject();
  }

  /**
   * Retrieve a chat session by ID along with its chronological message history.
   * @param {string} sessionId
   * @returns {Promise<{ session: Object, messages: Array }>}
   */
  async getSessionWithMessages(sessionId) {
    const session = await ChatSession.findOne({ sessionId });
    if (!session) {
      throw new NotFoundError(`Chat session '${sessionId}' was not found.`);
    }

    const messages = await ChatMessage.find({ sessionId }).sort({ createdAt: 1 }).lean();

    return {
      session: session.toObject(),
      messages,
    };
  }

  /**
   * List recent chat sessions with pagination.
   * @param {number} skip
   * @param {number} limit
   * @param {number} page
   * @returns {Promise<{ sessions: Array, total: number, page: number, totalPages: number }>}
   */
  async listSessions(skip = 0, limit = 20, page = 1) {
    const [sessions, total] = await Promise.all([
      ChatSession.find().sort({ lastActivityAt: -1 }).skip(skip).limit(limit).lean(),
      ChatSession.countDocuments(),
    ]);

    const totalPages = Math.ceil(total / limit) || 1;

    return {
      sessions,
      total,
      page,
      limit,
      totalPages,
    };
  }

  /**
   * Delete a chat session and all associated messages.
   * @param {string} sessionId
   * @returns {Promise<{ sessionId: string, deletedMessagesCount: number }>}
   */
  async deleteSession(sessionId) {
    const session = await ChatSession.findOne({ sessionId });
    if (!session) {
      throw new NotFoundError(`Chat session '${sessionId}' was not found.`);
    }

    const [deleteMsgResult] = await Promise.all([
      ChatMessage.deleteMany({ sessionId }),
      ChatSession.deleteOne({ sessionId }),
    ]);

    return {
      sessionId,
      deletedMessagesCount: deleteMsgResult.deletedCount || 0,
    };
  }

  /**
   * Orchestrate user inquiry: store user query, query RAG service, store answer, update session.
   *
   * @param {string} sessionId
   * @param {string} query
   * @returns {Promise<{ sessionId: string, userMessage: Object, assistantMessage: Object }>}
   */
  async sendMessage(sessionId, query, requestId = null) {
    const activeRequestId = requestId || `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    // 1. Verify session exists
    const session = await ChatSession.findOne({ sessionId });
    if (!session) {
      throw new NotFoundError(`Chat session '${sessionId}' was not found.`);
    }

    // 2. Persist User Message
    const userMessage = await ChatMessage.create({
      sessionId,
      role: 'user',
      content: query,
      sources: [],
      ragMetadata: { requestId: activeRequestId },
      createdAt: new Date(),
    });

    // 3. Update session title safely from first query if still default
    if (session.title === 'New Legal Conversation') {
      const derivedTitle = query.length > 60 ? `${query.slice(0, 57)}...` : query;
      session.title = derivedTitle;
    }
    session.lastActivityAt = new Date();
    await session.save();

    // 4. Contact Python FastAPI RAG Service
    // Note: If RAG service fails or times out, typed error is caught by controller/errorHandler.
    // The user's message is safely stored, and no fabricated assistant message is written.
    const ragResponse = await ragService.queryLegalRAG(query, sessionId, activeRequestId);

    // 5. Persist Assistant Response with normalized sources and provenance
    const assistantMessage = await ChatMessage.create({
      sessionId,
      role: 'assistant',
      content: ragResponse.content,
      sources: ragResponse.sources,
      ragMetadata: ragResponse.ragMetadata,
      createdAt: new Date(),
    });

    // 6. Update session activity timestamp
    await ChatSession.updateOne({ sessionId }, { lastActivityAt: new Date() });

    return {
      sessionId,
      userMessage: userMessage.toObject(),
      assistantMessage: assistantMessage.toObject(),
    };
  }
}

const chatService = new ChatService();

module.exports = {
  ChatService,
  chatService,
};
