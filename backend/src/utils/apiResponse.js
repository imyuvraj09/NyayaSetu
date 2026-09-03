/**
 * Standard API response helper.
 */

function sendSuccess(res, data, statusCode = 200, message = undefined) {
  const payload = { success: true };
  if (message) payload.message = message;
  if (data !== undefined) payload.data = data;
  return res.status(statusCode).json(payload);
}

function sendError(res, code, message, statusCode = 500, details = undefined) {
  const payload = {
    success: false,
    error: {
      code,
      message,
    },
  };
  if (details !== undefined && process.env.NODE_ENV !== 'production') {
    payload.error.details = details;
  }
  return res.status(statusCode).json(payload);
}

module.exports = {
  sendSuccess,
  sendError,
};
