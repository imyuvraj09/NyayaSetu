/**
 * Centralized error-handling middleware for Express.
 * Catches all operational and unexpected errors, logs them safely,
 * and formats the response to the consistent API contract.
 */

const { AppError } = require('../utils/errors');
const { sendError } = require('../utils/apiResponse');

function errorHandler(err, req, res, _next) {
  // If headers already sent, delegate to default Express handler
  if (res.headersSent) {
    return _next(err);
  }

  // Handle known operational AppError instances
  if (err instanceof AppError) {
    return sendError(res, err.code, err.message, err.statusCode);
  }

  // Handle Mongoose / MongoDB CastError (e.g. invalid ObjectId or query format)
  if (err.name === 'CastError') {
    return sendError(res, 'INVALID_IDENTIFIER', `Invalid identifier format for field: ${err.path}`, 400);
  }

  // Handle Mongoose Validation Errors
  if (err.name === 'ValidationError') {
    const messages = Object.values(err.errors || {}).map((e) => e.message);
    return sendError(res, 'VALIDATION_ERROR', messages.join('; ') || 'Database validation failed', 400);
  }

  // Handle SyntaxError in JSON body parsing
  if (err instanceof SyntaxError && err.status === 400 && 'body' in err) {
    return sendError(res, 'MALFORMED_JSON', 'Malformed JSON payload in request body', 400);
  }

  // Log unexpected errors safely without exposing secrets
  console.error(`[Unhandled Error] [${req.method} ${req.originalUrl}]:`, err.message);

  // Return generic internal error without leaking stack traces or credentials
  return sendError(
    res,
    'INTERNAL_SERVER_ERROR',
    'An unexpected error occurred while processing your request. Please try again later.',
    500
  );
}

module.exports = errorHandler;
