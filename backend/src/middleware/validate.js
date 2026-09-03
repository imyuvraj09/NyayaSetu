/**
 * Request validation middleware.
 * Validates request bodies and parameters with clean, dependency-free guards.
 */

const { ValidationError } = require('../utils/errors');

/**
 * Validate that sessionId in req.params is present and well-formed.
 */
function validateSessionIdParam(req, _res, next) {
  const { sessionId } = req.params;
  if (!sessionId || typeof sessionId !== 'string' || !sessionId.trim()) {
    return next(new ValidationError('Valid sessionId parameter is required.'));
  }
  const cleanId = sessionId.trim();
  // Safe character pattern for UUID or alphanumeric slug (length 4 to 64)
  if (!/^[a-zA-Z0-9_-]{4,64}$/.test(cleanId)) {
    return next(new ValidationError('Session ID contains invalid characters or exceeds valid length.'));
  }
  req.params.sessionId = cleanId;
  return next();
}

/**
 * Validate user query in POST /api/chats/:sessionId/messages.
 */
function validateMessageQuery(req, _res, next) {
  if (!req.body || typeof req.body !== 'object') {
    return next(new ValidationError('Request body must be a valid JSON object.'));
  }

  const { query } = req.body;
  if (query === undefined || query === null) {
    return next(new ValidationError("Field 'query' is required."));
  }

  if (typeof query !== 'string') {
    return next(new ValidationError("Field 'query' must be a string."));
  }

  const trimmed = query.trim();
  if (!trimmed) {
    return next(new ValidationError('Query cannot be empty or whitespace only.'));
  }

  if (trimmed.length > 2000) {
    return next(new ValidationError('Query exceeds maximum allowable length of 2,000 characters.'));
  }

  req.body.query = trimmed;
  return next();
}

/**
 * Validate pagination query params for GET /api/chats.
 */
function validatePagination(req, _res, next) {
  let page = parseInt(req.query.page, 10);
  let limit = parseInt(req.query.limit, 10);

  if (Number.isNaN(page) || page < 1) {
    page = 1;
  }
  if (Number.isNaN(limit) || limit < 1) {
    limit = 20;
  } else if (limit > 100) {
    limit = 100;
  }

  req.pagination = { page, limit, skip: (page - 1) * limit };
  return next();
}

module.exports = {
  validateSessionIdParam,
  validateMessageQuery,
  validatePagination,
};
