/**
 * ChatSession Mongoose Model.
 * Represents an individual legal research conversation session.
 */

const mongoose = require('mongoose');

const chatSessionSchema = new mongoose.Schema(
  {
    sessionId: {
      type: String,
      required: [true, 'sessionId is required'],
      unique: true,
      index: true,
      trim: true,
    },
    title: {
      type: String,
      default: 'New Legal Conversation',
      trim: true,
      maxlength: [120, 'Title cannot exceed 120 characters'],
    },
    lastActivityAt: {
      type: Date,
      default: Date.now,
      index: true,
    },
  },
  {
    timestamps: true, // Automatically manages createdAt and updatedAt
    versionKey: false,
  }
);

// Indexes for fast retrieval
chatSessionSchema.index({ lastActivityAt: -1 });

module.exports = mongoose.model('ChatSession', chatSessionSchema);
