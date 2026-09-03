/**
 * Chat and Messaging Routes for NyayaSetu API Gateway.
 */

const express = require('express');
const router = express.Router();
const chatController = require('../controllers/chat.controller');
const {
  validateSessionIdParam,
  validateMessageQuery,
  validatePagination,
} = require('../middleware/validate');

// Session & chat message dispatch
router.post('/', (req, res, next) => {
  if (req.body && (req.body.message !== undefined || req.body.query !== undefined)) {
    return chatController.handleDirectChat(req, res, next);
  }
  return chatController.createChat(req, res, next);
});
router.get('/', validatePagination, chatController.listChats);
router.get('/:sessionId', validateSessionIdParam, chatController.getChat);
router.delete('/:sessionId', validateSessionIdParam, chatController.deleteChat);

// Message query route
router.post(
  '/:sessionId/messages',
  validateSessionIdParam,
  validateMessageQuery,
  chatController.postMessage
);

module.exports = router;
