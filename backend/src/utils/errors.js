/**
 * Custom application error classes for NyayaSetu Backend.
 */

class AppError extends Error {
  constructor(message, statusCode = 500, code = 'INTERNAL_ERROR') {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;
    this.code = code;
    Error.captureStackTrace(this, this.constructor);
  }
}

class ValidationError extends AppError {
  constructor(message) {
    super(message, 400, 'VALIDATION_ERROR');
  }
}

class NotFoundError extends AppError {
  constructor(message = 'Resource not found') {
    super(message, 404, 'NOT_FOUND');
  }
}

class RAGServiceUnavailableError extends AppError {
  constructor(message = 'The AI legal service is temporarily unavailable. Please try again shortly.') {
    super(message, 503, 'RAG_SERVICE_UNAVAILABLE');
  }
}

class RAGServiceTimeoutError extends AppError {
  constructor(message = 'The AI legal service request timed out. Please retry.') {
    super(message, 504, 'RAG_SERVICE_TIMEOUT');
  }
}

class RAGResponseError extends AppError {
  constructor(message = 'The AI legal service returned an unprocessable response.') {
    super(message, 502, 'RAG_RESPONSE_ERROR');
  }
}

module.exports = {
  AppError,
  ValidationError,
  NotFoundError,
  RAGServiceUnavailableError,
  RAGServiceTimeoutError,
  RAGResponseError,
};
